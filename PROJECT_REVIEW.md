# 项目全面检查报告

## ✅ 已完成的功能

### 1. 核心功能
- ✅ 5 星评分系统（适度权重差异）
- ✅ 基于标签的兴趣学习
- ✅ 持久化反馈文件支持
- ✅ 多样性奖励机制（避免回声室）
- ✅ 三种 Reranker：local, api, llm

### 2. TLDR 生成
- ✅ 3-4 句话详细描述
- ✅ 包含方法细节
- ✅ 关键词提取
- ✅ 双语支持（英文 + 中文）
- ✅ 专业学术翻译

### 3. 匹配信息
- ✅ 显示基于哪个星级推荐
- ✅ 标注潜在新方向 🌟

### 4. 邮件格式
- ✅ 移除 Relevance 分数
- ✅ 清晰的布局
- ✅ 匹配信息显示

---

## ⚠️ 潜在问题

### 1. **LLM Reranker 性能问题**

**问题：** LLM reranker 会非常慢
- 50 篇候选 × 20 篇对比 ÷ 5 批 = 200 次 LLM 调用
- 每次调用约 2-3 秒
- 总时间：**10-15 分钟**

**建议：**
```yaml
reranker:
  llm:
    max_corpus_samples: 10  # 减少到 10 篇
    batch_size: 10  # 增加批量大小
```

这样可以减少到 5 分钟左右。

---

### 2. **max_tokens 配置问题**

**当前配置：**
```yaml
llm:
  generation_kwargs:
    max_tokens: 1024
```

**问题：**
- 英文 TLDR（3-4 句）+ 关键词 ≈ 300 tokens
- 中文翻译 ≈ 400 tokens
- 总共需要 ≈ 700 tokens
- 1024 应该够用，但如果论文很复杂可能不够

**建议：** 保持 1024 或增加到 1536

---

### 3. **并发问题**

**当前配置：**
```yaml
executor:
  max_workers: 16
```

**问题：**
- 生成 TLDR 时，每篇论文调用 2 次 LLM（英文 + 中文）
- 16 个并发可能会触发 API 限流

**建议：**
```yaml
executor:
  max_workers: 8  # 降低并发
```

---

### 4. **错误处理**

**当前：** 如果 LLM 调用失败，会回退到 abstract

**问题：** 用户可能不知道失败了

**建议：** 在邮件中标注哪些论文的 TLDR 生成失败了

---

### 5. **Token 消耗估算**

**使用 LLM reranker + 双语 TLDR：**

| 步骤 | 调用次数 | 每次 tokens | 总计 |
|------|---------|------------|------|
| LLM Reranking | 200 | 500 | 100k |
| 英文 TLDR | 50 | 300 | 15k |
| 中文翻译 | 50 | 400 | 20k |
| Affiliations | 50 | 200 | 10k |
| **总计** | | | **145k tokens/天** |

**成本（deepseek-chat）：**
- 输入：$0.14/M tokens
- 输出：$0.28/M tokens
- 估算：**$0.03-0.05/天**

---

## 🔧 推荐的优化配置

### 配置 A：平衡版（推荐）
```yaml
executor:
  max_workers: 8
  max_paper_num: 50
  reranker: llm

llm:
  generation_kwargs:
    model: deepseek-chat
    max_tokens: 1536

reranker:
  llm:
    max_corpus_samples: 15  # 平衡准确性和速度
    batch_size: 10
  diversity:
    enabled: true
    bonus_strength: 0.3
```

**预计时间：** 8-10 分钟
**预计成本：** $0.03/天

---

### 配置 B：快速版
```yaml
executor:
  max_workers: 8
  max_paper_num: 50
  reranker: local  # 使用 embedding

llm:
  generation_kwargs:
    model: deepseek-chat
    max_tokens: 1536

reranker:
  local:
    model: jinaai/jina-embeddings-v5-text-nano
  diversity:
    enabled: true
    bonus_strength: 0.3
```

**预计时间：** 3-5 分钟
**预计成本：** $0.01/天

---

### 配置 C：高质量版
```yaml
executor:
  max_workers: 4  # 降低并发避免限流
  max_paper_num: 30  # 减少论文数
  reranker: llm

llm:
  generation_kwargs:
    model: deepseek-chat
    max_tokens: 2048  # 更长的 TLDR

reranker:
  llm:
    max_corpus_samples: 30  # 更多对比
    batch_size: 5
  diversity:
    enabled: true
    bonus_strength: 0.4  # 更多惊喜
```

**预计时间：** 15-20 分钟
**预计成本：** $0.05/天

---

## 🐛 需要修复的 Bug

### 1. **LLM Reranker 的 batch 处理逻辑**

当前代码中，batch 处理可能有问题。让我检查一下...

### 2. **中文翻译可能失败**

如果第一次 LLM 调用（英文 TLDR）就失败了，不会尝试翻译。

---

## 📋 测试清单

在 push 到 GitHub 之前，建议测试：

- [ ] 本地运行 `python3 test_interest_learning_simple.py`
- [ ] 检查 LLM reranker 是否正确注册
- [ ] 测试 10 篇论文的完整流程
- [ ] 检查邮件格式是否正确
- [ ] 验证中文翻译是否出现
- [ ] 检查匹配信息是否显示

---

## 🎯 建议的下一步

1. **先用配置 B（快速版）测试**
   - 验证所有功能正常
   - 检查邮件格式
   - 确认翻译工作

2. **如果满意，切换到配置 A（平衡版）**
   - 使用 LLM reranker
   - 获得更准确的推荐

3. **根据实际效果调整**
   - 如果推荐太保守 → 增加 `bonus_strength`
   - 如果速度太慢 → 减少 `max_corpus_samples`
   - 如果成本太高 → 切换回 `local` reranker

---

需要我帮你修复哪个问题？
