# Interest Learning System

This document explains how to use the interest learning features to improve paper recommendations.

## Overview

The system now learns from your interests in two ways:
1. **Zotero Tags** (方案3): Tag papers in your Zotero library to indicate interest level
2. **Feedback File** (方案5): Track papers you found interesting or not interesting

## How to Use

### Method 1: Zotero Tags (Recommended)

Add tags to papers in your Zotero library to indicate your interest level:

**Star Rating Tags:**
- `⭐⭐⭐` - Very interested (weight: 3.0x)
- `⭐⭐` - Interested (weight: 2.0x)
- `⭐` - Somewhat interested (weight: 1.5x)

**Text Tags:**
- `high-interest` - High interest (weight: 3.0x)
- `medium-interest` - Medium interest (weight: 2.0x)
- `low-interest` - Low interest (weight: 1.0x)

Papers with higher weight tags will have more influence on recommendations.

### Method 2: Feedback File

Edit `feedback.yaml` to track papers you've reviewed:

```yaml
interested_papers:
  - arxiv_id: "2401.12345"
    score: 5  # 5=very interested, 4=interested, 3=somewhat
    date: "2024-01-15"
    reason: "Relevant to my research on multimodal learning"

not_interested_papers:
  - arxiv_id: "2401.99999"
    score: 1  # 1=not interested, 2=slightly not interested
    date: "2024-01-16"
    reason: "Too theoretical"
```

## Configuration

### Custom Tag Weights

You can customize tag weights in your `config/custom.yaml`:

```yaml
reranker:
  tag_weights:
    ⭐⭐⭐: 5.0  # Increase weight for 3-star papers
    ⭐⭐: 3.0
    ⭐: 2.0
    my-core-topic: 4.0  # Add custom tags
    related-work: 1.5
```

### Feedback File Location

By default, the system looks for `feedback.yaml` in the project root. You can change this:

```yaml
reranker:
  feedback_file: path/to/your/feedback.yaml
```

## How It Works

The recommendation score is calculated as:

```
final_score = Σ(similarity × time_decay × tag_weight) / total_weight
```

Where:
- **similarity**: Embedding similarity between new paper and your library papers
- **time_decay**: Recent papers have higher weight (logarithmic decay)
- **tag_weight**: Weight based on tags (default 1.0 for untagged papers)

## Tips

1. **Start Simple**: Begin by tagging 10-20 papers in your Zotero library with star ratings
2. **Be Consistent**: Use the same tagging system across all papers
3. **Update Regularly**: As your interests evolve, update tags on older papers
4. **Use Collections**: Combine with `include_path` to focus on specific research areas
5. **Track Feedback**: Periodically update `feedback.yaml` with papers you found useful

## Example Workflow

1. **Initial Setup**: Tag your top 20 most relevant papers with `⭐⭐⭐`
2. **Daily Review**: Check recommended papers in your email
3. **Add to Zotero**: Add interesting papers to Zotero with appropriate tags
4. **Optional**: Update `feedback.yaml` with arxiv IDs of papers you read
5. **Iterate**: The system learns as your library grows

## GitHub Action Setup

The feedback file is stored in your repository, so it persists across runs:

1. Create `feedback.yaml` in your repo root
2. Commit and push it to GitHub
3. The workflow will automatically use it for recommendations
4. Update it periodically by editing directly on GitHub or locally

## Troubleshooting

**Tags not working?**
- Make sure tags are added in Zotero (not just in the web interface)
- Sync your Zotero library
- Check the logs for "Loaded feedback data" message

**Weights seem wrong?**
- Check your `tag_weights` configuration
- Verify tags are spelled correctly (case-sensitive)
- Look at the log message showing average weight

**Feedback file not found?**
- Ensure `feedback.yaml` exists in the project root
- Check file permissions
- The system will work without it (just won't use feedback data)
