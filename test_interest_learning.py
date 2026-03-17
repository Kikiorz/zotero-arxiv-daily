"""
Test script for interest learning features
"""
import sys
sys.path.insert(0, 'src')

from zotero_arxiv_daily.protocol import CorpusPaper, Paper
from zotero_arxiv_daily.reranker.base import BaseReranker
from omegaconf import OmegaConf
from datetime import datetime
import numpy as np

class MockReranker(BaseReranker):
    def get_similarity_score(self, s1: list[str], s2: list[str]) -> np.ndarray:
        # Return random similarity scores for testing
        return np.random.rand(len(s1), len(s2))

def test_tag_weights():
    """Test that tag weights are correctly applied"""
    print("Testing tag weight calculation...")

    # Create mock config
    config = OmegaConf.create({
        'reranker': {
            'tag_weights': {
                '⭐⭐⭐': 3.0,
                '⭐⭐': 2.0,
                '⭐': 1.5,
                'high-interest': 3.0,
            }
        }
    })

    reranker = MockReranker(config)

    # Test different tag combinations
    test_cases = [
        ([], 1.0, "No tags"),
        (['⭐'], 1.5, "One star"),
        (['⭐⭐'], 2.0, "Two stars"),
        (['⭐⭐⭐'], 3.0, "Three stars"),
        (['high-interest'], 3.0, "High interest tag"),
        (['⭐⭐', '⭐⭐⭐'], 3.0, "Multiple tags (should use max)"),
        (['random-tag'], 1.0, "Unknown tag"),
    ]

    for tags, expected_weight, description in test_cases:
        weight = reranker._calculate_tag_weight(tags)
        status = "✓" if abs(weight - expected_weight) < 0.01 else "✗"
        print(f"{status} {description}: tags={tags}, weight={weight:.2f} (expected {expected_weight:.2f})")

def test_reranking():
    """Test that reranking works with tags"""
    print("\nTesting reranking with tags...")

    config = OmegaConf.create({
        'reranker': {
            'tag_weights': {
                '⭐⭐⭐': 3.0,
                '⭐⭐': 2.0,
                '⭐': 1.5,
            }
        }
    })

    reranker = MockReranker(config)

    # Create corpus papers with different tags
    corpus = [
        CorpusPaper(
            title="High interest paper",
            abstract="This is about transformers",
            added_date=datetime(2024, 1, 1),
            paths=["Research"],
            tags=['⭐⭐⭐']
        ),
        CorpusPaper(
            title="Medium interest paper",
            abstract="This is about CNNs",
            added_date=datetime(2024, 1, 2),
            paths=["Research"],
            tags=['⭐⭐']
        ),
        CorpusPaper(
            title="Low interest paper",
            abstract="This is about RNNs",
            added_date=datetime(2024, 1, 3),
            paths=["Research"],
            tags=[]
        ),
    ]

    # Create candidate papers
    candidates = [
        Paper(
            source="arxiv",
            title="New paper 1",
            authors=["Author 1"],
            abstract="A paper about transformers and attention",
            url="https://arxiv.org/abs/2401.00001"
        ),
        Paper(
            source="arxiv",
            title="New paper 2",
            authors=["Author 2"],
            abstract="A paper about CNNs and convolution",
            url="https://arxiv.org/abs/2401.00002"
        ),
    ]

    # Rerank
    reranked = reranker.rerank(candidates, corpus)

    print(f"✓ Reranked {len(reranked)} papers")
    for i, paper in enumerate(reranked):
        print(f"  {i+1}. {paper.title} (score: {paper.score:.4f})")

def test_feedback_loading():
    """Test that feedback file is loaded correctly"""
    print("\nTesting feedback file loading...")

    config = OmegaConf.create({
        'reranker': {
            'tag_weights': {}
        }
    })

    reranker = MockReranker(config)

    if reranker.feedback_data:
        print(f"✓ Feedback data loaded")
        print(f"  Interested papers: {len(reranker.feedback_data.get('interested_papers', []))}")
        print(f"  Not interested papers: {len(reranker.feedback_data.get('not_interested_papers', []))}")
    else:
        print("✓ No feedback data (this is OK if feedback.yaml doesn't exist)")

if __name__ == "__main__":
    print("=" * 60)
    print("Interest Learning System - Test Suite")
    print("=" * 60)

    test_tag_weights()
    test_reranking()
    test_feedback_loading()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
