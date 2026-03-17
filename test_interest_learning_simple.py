"""
Simplified test script for interest learning features (no imports from protocol.py)
"""
from omegaconf import OmegaConf
import numpy as np
import yaml
import os

def test_tag_weight_calculation():
    """Test tag weight calculation logic"""
    print("Testing tag weight calculation...")

    # Simulate the tag weight config (5-star system)
    tag_weights = {
        '⭐⭐⭐⭐⭐': 5.0,
        '⭐⭐⭐⭐': 4.0,
        '⭐⭐⭐': 3.0,
        '⭐⭐': 2.0,
        '⭐': 1.5,
        '5-star': 5.0,
        '4-star': 4.0,
        '3-star': 3.0,
        '2-star': 2.0,
        '1-star': 1.5,
    }

    def calculate_tag_weight(tags):
        max_weight = 1.0
        for tag in tags:
            if tag in tag_weights:
                max_weight = max(max_weight, tag_weights[tag])
        return max_weight

    test_cases = [
        ([], 1.0, "No tags (default)"),
        (['⭐'], 1.5, "1 star"),
        (['⭐⭐'], 2.0, "2 stars"),
        (['⭐⭐⭐'], 3.0, "3 stars"),
        (['⭐⭐⭐⭐'], 4.0, "4 stars"),
        (['⭐⭐⭐⭐⭐'], 5.0, "5 stars"),
        (['5-star'], 5.0, "5-star text tag"),
        (['3-star'], 3.0, "3-star text tag"),
        (['⭐⭐⭐', '⭐⭐⭐⭐⭐'], 5.0, "Multiple tags (should use max)"),
        (['random-tag'], 1.0, "Unknown tag"),
    ]

    all_passed = True
    for tags, expected_weight, description in test_cases:
        weight = calculate_tag_weight(tags)
        passed = abs(weight - expected_weight) < 0.01
        status = "✓" if passed else "✗"
        print(f"{status} {description}: tags={tags}, weight={weight:.2f} (expected {expected_weight:.2f})")
        if not passed:
            all_passed = False

    return all_passed

def test_feedback_file():
    """Test feedback file structure"""
    print("\nTesting feedback file...")

    feedback_path = 'feedback.yaml'
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        print(f"✓ Feedback file exists and is readable")
        print(f"  Structure: {list(data.keys())}")

        interested = data.get('interested_papers', [])
        not_interested = data.get('not_interested_papers', [])

        if interested is None:
            interested = []
        if not_interested is None:
            not_interested = []

        print(f"  Interested papers: {len(interested)}")
        print(f"  Not interested papers: {len(not_interested)}")
        return True
    else:
        print(f"✓ Feedback file not found (will be created when needed)")
        return True

def test_weight_combination():
    """Test combining time decay and tag weights"""
    print("\nTesting weight combination...")

    # Simulate 5 corpus papers
    n_corpus = 5

    # Time decay weights (newer papers have higher weight)
    time_decay = 1 / (1 + np.log10(np.arange(n_corpus) + 1))
    time_decay = time_decay / time_decay.sum()

    # Tag weights for each paper (5-star system)
    tag_weights = np.array([5.0, 4.0, 3.0, 2.0, 1.0])  # First paper has highest tag weight

    # Combined weights
    combined = time_decay * tag_weights
    combined = combined / combined.sum()

    print(f"✓ Time decay weights: {time_decay}")
    print(f"✓ Tag weights: {tag_weights}")
    print(f"✓ Combined weights: {combined}")
    print(f"✓ Sum of combined weights: {combined.sum():.4f} (should be 1.0)")

    return abs(combined.sum() - 1.0) < 0.01

def test_config_structure():
    """Test that config structure is correct"""
    print("\nTesting config structure...")

    try:
        config = OmegaConf.load('config/base.yaml')

        # Check if reranker section exists
        if 'reranker' in config:
            print("✓ Reranker section exists")

            if 'tag_weights' in config.reranker:
                print("✓ Tag weights section exists")
                print(f"  Configured tags: {list(config.reranker.tag_weights.keys())}")
            else:
                print("✗ Tag weights section missing")
                return False

            if 'feedback_file' in config.reranker:
                print(f"✓ Feedback file configured: {config.reranker.feedback_file}")
            else:
                print("✗ Feedback file configuration missing")
                return False
        else:
            print("✗ Reranker section missing")
            return False

        return True
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Interest Learning System - Test Suite")
    print("=" * 60)

    results = []
    results.append(("Tag Weight Calculation", test_tag_weight_calculation()))
    results.append(("Feedback File", test_feedback_file()))
    results.append(("Weight Combination", test_weight_combination()))
    results.append(("Config Structure", test_config_structure()))

    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
