from dataclasses import dataclass
from typing import Optional, TypeVar
from datetime import datetime
import re
import tiktoken
from openai import OpenAI
from loguru import logger
import json
RawPaperItem = TypeVar('RawPaperItem')

@dataclass
class Paper:
    source: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None
    tldr: Optional[str] = None
    affiliations: Optional[list[str]] = None
    score: Optional[float] = None
    keywords: Optional[list[str]] = None
    match_info: Optional[str] = None  # Information about which starred papers this matches

    def _generate_tldr_with_llm(self, openai_client:OpenAI,llm_params:dict) -> str:
        lang = llm_params.get('language', 'English')
        prompt = f"Given the following information of a paper, generate a concise summary in {lang}:\n\n"
        if self.title:
            prompt += f"Title: {self.title}\n\n"

        if self.abstract:
            prompt += f"Abstract: {self.abstract}\n\n"

        if self.full_text:
            prompt += f"Preview of main content:\n {self.full_text}\n\n"

        if not self.full_text and not self.abstract:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return "Failed to generate TLDR. Neither full text nor abstract is provided"

        # use gpt-4o tokenizer for estimation
        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
        prompt = enc.decode(prompt_tokens)

        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert research assistant specializing in AI, Computer Science, Large Language Models, Robotics, Automation, and Mathematics.

Create a CONCISE technical summary in {lang} following this EXACT structure:

TLDR: [Problem] [Motivation] [Method - FOCUS HERE with technical details] [Results]

Format requirements:
- Total length: 2-3 sentences maximum
- Use precise technical terminology from AI/CS/Robotics/Math domains
- Method section should be 50% of the content with specific technical components
- Be quantitative when possible (e.g., "reduces memory by 60%", "achieves 95% accuracy")

Keywords: [4-6 technical keywords from the paper's domain]

Example:
TLDR: Existing vision transformers suffer from quadratic memory complexity limiting their use on high-resolution images. This paper proposes a sparse attention mechanism using learnable token pruning based on attention scores (top-k selection with k=0.3N) combined with a reconstruction loss (λ=0.1) to preserve semantic information. Achieves 60% memory reduction while maintaining 94.2% accuracy on ImageNet, with surprising 2.1% improvement on small datasets due to implicit regularization.

Keywords: Vision Transformers, Sparse Attention, Token Pruning, Efficient Deep Learning

CRITICAL: Do NOT use ** for formatting. Keep it plain text. Be technical and precise.""",
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get('generation_kwargs', {})
        )
        tldr_en = response.choices[0].message.content

        # Extract keywords if present
        if "Keywords:" in tldr_en:
            parts = tldr_en.split("Keywords:")
            if len(parts) == 2:
                keywords_text = parts[1].strip()
                self.keywords = [k.strip() for k in keywords_text.split(',')]

        # Generate Chinese translation
        try:
            # Use a separate max_tokens for translation to ensure it completes
            translation_kwargs = llm_params.get('generation_kwargs', {}).copy()
            translation_kwargs['max_tokens'] = min(translation_kwargs.get('max_tokens', 1024), 1024)

            cn_response = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """Role: You are a senior academic researcher specializing in Computer Science, Artificial Intelligence, and Robotics (specifically Embodied AI, Control Theory, and Computer Vision). You are an expert in the terminology and stylistic conventions of IEEE/RSJ publications.

Task: Provide a proficient and precise translation from English to Chinese of the academic text.

Core Instructions:

Domain-Specific Accuracy: Utilize precise technical terminology. For instance, translate Policy as 策略, Action Chunking as 动作分块, Gating as 门控, End-to-end as 端到端, and Robustness as 鲁棒性.

Intelligent Semantic Completion: Use your specialized knowledge in robotics and AI to ensure the translation is coherent and professionally sound.

Tone and Style: Maintain a formal, rigorous academic tone consistent with top-tier conferences like CoRL, RSS, or ICRA.

Output Format: Keep the same format with TLDR: and Keywords: markers in Chinese (使用 摘要: 和 关键词:). Do NOT use ** for bold.

Keywords Translation: Translate each keyword individually and keep them in the SAME ORDER as the English version. Format: 关键词: [中文1, 中文2, 中文3, ...]

Example:
English: Keywords: Computer Vision, Sparse Attention, Vision Transformers
Chinese: 关键词: 计算机视觉, 稀疏注意力, 视觉Transformer

Output Constraints: Provide only the translated result without any additional explanation.""",
                    },
                    {"role": "user", "content": f"Translate this academic summary to Chinese:\n\n{tldr_en}"},
                ],
                **translation_kwargs
            )
            tldr_cn = cn_response.choices[0].message.content

            # Combine English and Chinese
            tldr = f"{tldr_en}\n\n{tldr_cn}"
            logger.info(f"Successfully generated bilingual TLDR for {self.url}")
        except Exception as e:
            logger.warning(f"Failed to generate Chinese translation for {self.url}: {e}")
            tldr = tldr_en

        return tldr
    
    def generate_tldr(self, openai_client:OpenAI,llm_params:dict) -> str:
        try:
            tldr = self._generate_tldr_with_llm(openai_client,llm_params)
            self.tldr = tldr
            return tldr
        except Exception as e:
            logger.warning(f"Failed to generate tldr of {self.url}: {e}")
            tldr = self.abstract
            self.tldr = tldr
            return tldr

    def _generate_affiliations_with_llm(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        if self.full_text is not None:
            prompt = f"Given the beginning of a paper, extract the PRIMARY institutions (universities/labs) of the authors:\n\n{self.full_text}"
            # use gpt-4o tokenizer for estimation
            enc = tiktoken.encoding_for_model("gpt-4o")
            prompt_tokens = enc.encode(prompt)
            prompt_tokens = prompt_tokens[:2000]  # truncate to 2000 tokens
            prompt = enc.decode(prompt_tokens)
            affiliations = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at extracting institutional affiliations from academic papers.

Task: Extract the PRIMARY institutions (universities and research labs) where the work was conducted.

Output format: Python list of strings, e.g., ["MIT CSAIL", "Stanford AI Lab", "Google DeepMind"]

Rules:
1. Include BOTH university name AND lab/department if mentioned (e.g., "MIT CSAIL" not just "MIT")
2. For industry labs, include company and lab name (e.g., "Google DeepMind", "Meta FAIR")
3. Keep in author order (first author's institution first)
4. Remove duplicates
5. Use official English names
6. If no affiliation found, return []

Examples:
- "MIT Computer Science and Artificial Intelligence Laboratory" → "MIT CSAIL"
- "Stanford University, Department of Computer Science" → "Stanford CS"
- "Google Research, Brain Team" → "Google Brain"
- "清华大学" → "Tsinghua University"

Return ONLY the Python list, nothing else.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                **llm_params.get('generation_kwargs', {})
            )
            affiliations = affiliations.choices[0].message.content

            # Try to extract JSON array
            json_match = re.search(r'\[.*?\]', affiliations, flags=re.DOTALL)
            if json_match:
                affiliations = json.loads(json_match.group(0))
            else:
                # If no JSON found, try to parse the whole response
                affiliations = json.loads(affiliations)

            affiliations = list(dict.fromkeys(affiliations))  # Remove duplicates while preserving order
            affiliations = [str(a) for a in affiliations]

            return affiliations if affiliations else None
    
    def generate_affiliations(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        try:
            affiliations = self._generate_affiliations_with_llm(openai_client,llm_params)
            self.affiliations = affiliations
            return affiliations
        except Exception as e:
            logger.warning(f"Failed to generate affiliations of {self.url}: {e}")
            self.affiliations = None
            return None
@dataclass
class CorpusPaper:
    title: str
    abstract: str
    added_date: datetime
    paths: list[str]
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []