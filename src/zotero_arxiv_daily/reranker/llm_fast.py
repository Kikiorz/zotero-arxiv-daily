from .base import BaseReranker, register_reranker
from openai import OpenAI
import numpy as np
from loguru import logger
import json

@register_reranker("llm_fast")
class LLMFastReranker(BaseReranker):
    """
    Fast LLM-based reranker for first-stage filtering.
    Uses batch processing and simplified prompts for speed.
    """

    def get_similarity_score(self, s1: list[str], s2: list[str]) -> np.ndarray:
        """
        Use LLM to quickly judge relevance between candidate papers and corpus papers.
        Optimized for speed with larger batches and simpler prompts.
        """
        client = OpenAI(
            api_key=self.config.llm.api.key,
            base_url=self.config.llm.api.base_url
        )

        n_candidates = len(s1)
        n_corpus = len(s2)

        # Initialize similarity matrix
        sim = np.zeros((n_candidates, n_corpus))

        # Sample corpus papers for efficiency
        max_corpus_samples = self.config.reranker.get('llm_fast', {}).get('max_corpus_samples', 10)
        corpus_indices = list(range(min(n_corpus, max_corpus_samples)))

        logger.info(f"LLM Fast Reranker: Comparing {n_candidates} candidates against {len(corpus_indices)} corpus papers")

        # Large batch size for speed
        batch_size = self.config.reranker.get('llm_fast', {}).get('batch_size', 20)

        for j in corpus_indices:
            corpus_abstract = s2[j][:500]  # Truncate for speed

            for i in range(0, n_candidates, batch_size):
                batch_candidates = s1[i:i+batch_size]
                batch_indices = list(range(i, min(i+batch_size, n_candidates)))

                # Truncate candidate abstracts for speed
                batch_candidates_truncated = [c[:300] for c in batch_candidates]

                # Create prompt for batch comparison
                prompt = self._create_fast_comparison_prompt(batch_candidates_truncated, corpus_abstract)

                try:
                    response = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": """You are a fast paper relevance scorer. Rate how relevant each candidate abstract is to the reference abstract.

Output ONLY a JSON array of scores from 0.0 to 1.0.
- 1.0: Highly relevant (same topic, similar methods)
- 0.5: Moderately relevant (related field)
- 0.0: Not relevant

Example: [0.8, 0.3, 0.6, 0.9, 0.2]

Be FAST. Focus on topic overlap and method similarity."""
                            },
                            {"role": "user", "content": prompt}
                        ],
                        model=self.config.llm.generation_kwargs.model,
                        max_tokens=100,  # Very short response
                        temperature=0.1  # Low temperature for consistency
                    )

                    # Parse scores
                    scores_text = response.choices[0].message.content.strip()
                    # Extract JSON array
                    import re
                    json_match = re.search(r'\[[\d\.,\s]+\]', scores_text)
                    if json_match:
                        scores = json.loads(json_match.group(0))
                    else:
                        scores = json.loads(scores_text)

                    # Assign scores to similarity matrix
                    for k, score in enumerate(scores):
                        if i + k < n_candidates:
                            sim[i + k, j] = float(score)

                except Exception as e:
                    logger.warning(f"LLM fast reranking failed for batch {i}-{i+batch_size}, corpus {j}: {e}")
                    # Fallback to neutral score
                    for k in range(len(batch_candidates)):
                        if i + k < n_candidates:
                            sim[i + k, j] = 0.5

        # Fill remaining corpus papers with average scores
        if n_corpus > max_corpus_samples:
            avg_scores = sim[:, :max_corpus_samples].mean(axis=1, keepdims=True)
            sim[:, max_corpus_samples:] = avg_scores * 0.8

        logger.info(f"LLM Fast Reranker: Completed scoring")
        return sim

    def _create_fast_comparison_prompt(self, candidate_abstracts: list[str], reference_abstract: str) -> str:
        """Create a fast comparison prompt with truncated abstracts"""
        prompt = f"Reference: {reference_abstract}\n\nCandidates:\n"
        for i, abstract in enumerate(candidate_abstracts):
            prompt += f"{i+1}. {abstract}\n"

        prompt += f"\nRate relevance of {len(candidate_abstracts)} candidates (0.0-1.0):"
        return prompt
