from abc import ABC, abstractmethod
from omegaconf import DictConfig
from ..protocol import Paper, CorpusPaper
import numpy as np
from typing import Type
import os
import yaml
from loguru import logger

class BaseReranker(ABC):
    def __init__(self, config:DictConfig):
        self.config = config
        self.feedback_data = self._load_feedback()

    def _load_feedback(self) -> dict:
        """Load feedback data from feedback.yaml"""
        feedback_path = os.path.join(os.getcwd(), 'feedback.yaml')
        if not os.path.exists(feedback_path):
            logger.warning(f"Feedback file not found at {feedback_path}, using default weights")
            return {'interested_papers': [], 'not_interested_papers': [], 'interest_keywords': []}

        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                logger.info(f"Loaded feedback data: {len(data.get('interested_papers', []))} interested, {len(data.get('not_interested_papers', []))} not interested")
                return data
        except Exception as e:
            logger.warning(f"Failed to load feedback file: {e}")
            return {'interested_papers': [], 'not_interested_papers': [], 'interest_keywords': []}

    def _calculate_tag_weight(self, tags: list[str]) -> float:
        """Calculate weight based on Zotero tags (5-star rating system)

        Philosophy: All starred papers represent your interests, just at different quality levels.
        The weight differences are moderate to avoid over-fitting to only 5-star papers.
        """
        tag_config = self.config.reranker.get('tag_weights', {})

        # Moderate weight differences - all stars matter!
        # 5-star and 4-star are similar (both are your core interests)
        # 3-star still has strong influence (relevant topics, maybe just not as well-written)
        default_weights = {
            '⭐⭐⭐⭐⭐': 2.5,  # 5 stars - excellent papers in your field
            '⭐⭐⭐⭐': 2.3,    # 4 stars - very good papers (similar weight to 5-star)
            '⭐⭐⭐': 2.0,      # 3 stars - good papers (still strong influence)
            '⭐⭐': 1.5,        # 2 stars - relevant but less influential
            '⭐': 1.2,          # 1 star - somewhat relevant
            # Alternative text tags
            '5-star': 2.5,
            '4-star': 2.3,
            '3-star': 2.0,
            '2-star': 1.5,
            '1-star': 1.2,
        }

        # Merge config with defaults
        tag_weights = {**default_weights, **tag_config}

        # Find the highest weight tag
        max_weight = 1.0  # default weight for untagged papers
        for tag in tags:
            if tag in tag_weights:
                max_weight = max(max_weight, tag_weights[tag])

        return max_weight

    def rerank(self, candidates:list[Paper], corpus:list[CorpusPaper]) -> list[Paper]:
        corpus = sorted(corpus,key=lambda x: x.added_date,reverse=True)

        # Calculate time decay weight
        time_decay_weight = 1 / (1 + np.log10(np.arange(len(corpus)) + 1))
        time_decay_weight: np.ndarray = time_decay_weight / time_decay_weight.sum()

        # Calculate tag-based weights for each corpus paper
        tag_weights = np.array([self._calculate_tag_weight(paper.tags) for paper in corpus])

        # Combine time decay and tag weights
        combined_weight = time_decay_weight * tag_weights
        combined_weight = combined_weight / combined_weight.sum()  # normalize

        # Calculate similarity scores
        sim = self.get_similarity_score([c.abstract for c in candidates], [c.abstract for c in corpus])
        assert sim.shape == (len(candidates), len(corpus))

        # Calculate final scores with combined weights
        scores = (sim * combined_weight).sum(axis=1) * 10 # [n_candidate]

        # Add diversity bonus for "surprise" papers
        diversity_bonus = self._calculate_diversity_bonus(candidates, scores, sim, combined_weight)
        scores = scores + diversity_bonus

        # Generate match information for each candidate
        for i, (s, c) in enumerate(zip(scores, candidates)):
            c.score = s
            c.match_info = self._generate_match_info(sim[i], corpus, tag_weights, combined_weight)

        candidates = sorted(candidates,key=lambda x: x.score,reverse=True)

        logger.info(f"Reranked {len(candidates)} papers with tag weights (avg weight: {tag_weights.mean():.2f})")
        return candidates

    def _generate_match_info(self, similarities: np.ndarray, corpus: list[CorpusPaper],
                            tag_weights: np.ndarray, combined_weights: np.ndarray) -> str:
        """
        Generate information about which starred papers this candidate matches.
        Returns a string describing the match (e.g., "Matches your 5-star papers in Computer Vision")
        """
        # Find top 3 most similar papers
        top_indices = np.argsort(similarities)[-3:][::-1]
        top_sims = similarities[top_indices]

        # Get star ratings for top matches
        star_ratings = []
        for idx in top_indices:
            if idx < len(corpus):
                tags = corpus[idx].tags
                # Determine star rating
                if '⭐⭐⭐⭐⭐' in tags or '5-star' in tags:
                    star_ratings.append(5)
                elif '⭐⭐⭐⭐' in tags or '4-star' in tags:
                    star_ratings.append(4)
                elif '⭐⭐⭐' in tags or '3-star' in tags:
                    star_ratings.append(3)
                elif '⭐⭐' in tags or '2-star' in tags:
                    star_ratings.append(2)
                elif '⭐' in tags or '1-star' in tags:
                    star_ratings.append(1)
                else:
                    star_ratings.append(0)

        # Calculate average similarity and star rating
        avg_sim = top_sims.mean()
        max_star = max(star_ratings) if star_ratings else 0

        # Determine match type
        if avg_sim > 0.7:
            match_type = "Highly similar to"
        elif avg_sim > 0.5:
            match_type = "Similar to"
        elif avg_sim > 0.3:
            match_type = "Related to"
        else:
            match_type = "Exploration beyond"

        # Generate star description
        if max_star >= 5:
            star_desc = "your ⭐⭐⭐⭐⭐ papers"
        elif max_star >= 4:
            star_desc = "your ⭐⭐⭐⭐ papers"
        elif max_star >= 3:
            star_desc = "your ⭐⭐⭐ papers"
        elif max_star >= 2:
            star_desc = "your ⭐⭐ papers"
        elif max_star >= 1:
            star_desc = "your ⭐ papers"
        else:
            star_desc = "your library"

        # Add diversity note if similarity is moderate
        if 0.3 <= avg_sim <= 0.7:
            diversity_note = " (potential new direction 🌟)"
        else:
            diversity_note = ""

        return f"{match_type} {star_desc}{diversity_note}"

    def _calculate_diversity_bonus(self, candidates: list[Paper], scores: np.ndarray,
                                   sim: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """
        Add small bonus to diverse/surprising papers to avoid echo chamber.
        Papers that are moderately similar (not too high, not too low) get a small boost.
        """
        diversity_config = self.config.reranker.get('diversity', {})
        if not diversity_config.get('enabled', True):
            return np.zeros_like(scores)

        bonus_strength = diversity_config.get('bonus_strength', 0.3)  # Max bonus as fraction of score

        # Calculate average similarity for each candidate
        avg_similarity = (sim * weights).sum(axis=1)

        # Papers with moderate similarity (0.3-0.7) get bonus
        # This helps surface interesting but not too similar papers
        diversity_score = np.zeros_like(avg_similarity)
        mask = (avg_similarity > 0.3) & (avg_similarity < 0.7)
        diversity_score[mask] = 1.0 - np.abs(avg_similarity[mask] - 0.5) * 2  # Peak at 0.5

        # Apply bonus (scaled by current score to maintain relative ordering)
        bonus = diversity_score * scores * bonus_strength

        return bonus

    @abstractmethod
    def get_similarity_score(self, s1:list[str], s2:list[str]) -> np.ndarray:
        raise NotImplementedError

registered_rerankers = {}

def register_reranker(name:str):
    def decorator(cls):
        registered_rerankers[name] = cls
        return cls
    return decorator

def get_reranker_cls(name:str) -> Type[BaseReranker]:
    if name not in registered_rerankers:
        raise ValueError(f"Reranker {name} not found")
    return registered_rerankers[name]