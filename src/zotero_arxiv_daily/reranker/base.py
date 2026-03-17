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
        """Calculate weight based on Zotero tags (5-star rating system)"""
        tag_config = self.config.reranker.get('tag_weights', {})

        # Default 5-star rating weights
        default_weights = {
            '⭐⭐⭐⭐⭐': 5.0,  # 5 stars - extremely relevant
            '⭐⭐⭐⭐': 4.0,    # 4 stars - very relevant
            '⭐⭐⭐': 3.0,      # 3 stars - relevant
            '⭐⭐': 2.0,        # 2 stars - somewhat relevant
            '⭐': 1.5,          # 1 star - slightly relevant
            # Alternative text tags
            '5-star': 5.0,
            '4-star': 4.0,
            '3-star': 3.0,
            '2-star': 2.0,
            '1-star': 1.5,
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

        for s,c in zip(scores,candidates):
            c.score = s

        candidates = sorted(candidates,key=lambda x: x.score,reverse=True)

        logger.info(f"Reranked {len(candidates)} papers with tag weights (avg weight: {tag_weights.mean():.2f})")
        return candidates

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