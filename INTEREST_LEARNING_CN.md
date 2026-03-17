# 兴趣学习系统使用指南

## 功能概述

现在系统支持两种方式学习你的兴趣偏好：

### 方案 3：Zotero 标签权重
在 Zotero 中给论文打标签，系统会根据标签调整推荐权重。

### 方案 5：持久化反馈文件
通过 `feedback.yaml` 文件记录你感兴趣/不感兴趣的论文。

---

## 快速开始

### 1. 使用 Zotero 标签（推荐）

在 Zotero 中给论文添加标签：

**星级标签：**
- `⭐⭐⭐` - 非常感兴趣（权重 3.0 倍）
- `⭐⭐` - 感兴趣（权重 2.0 倍）
- `⭐` - 有点兴趣（权重 1.5 倍）

**文字标签：**
- `high-interest` - 高兴趣（权重 3.0 倍）
- `medium-interest` - 中等兴趣（权重 2.0 倍）
- `low-interest` - 低兴趣（权重 1.0 倍）

标签权重越高的论文，对推荐的影响越大。

### 2. 使用反馈文件

编辑 `feedback.yaml` 记录你看过的论文：

```yaml
interested_papers:
  - arxiv_id: "2401.12345"
    score: 5  # 5=非常感兴趣, 4=感兴趣, 3=有点兴趣
    date: "2024-01-15"
    reason: "与我的多模态学习研究相关"

not_interested_papers:
  - arxiv_id: "2401.99999"
    score: 1  # 1=不感兴趣, 2=不太感兴趣
    date: "2024-01-16"
    reason: "太理论化"
```

---

## 配置说明

### 自定义标签权重

在 `config/custom.yaml` 中自定义标签权重：

```yaml
reranker:
  tag_weights:
    ⭐⭐⭐: 5.0  # 提高三星论文的权重
    ⭐⭐: 3.0
    ⭐: 2.0
    my-core-topic: 4.0  # 添加自定义标签
    related-work: 1.5
```

### 完整配置示例

```yaml
zotero:
  user_id: ${oc.env:ZOTERO_ID}
  api_key: ${oc.env:ZOTERO_KEY}
  include_path: "Research/**"  # 可选：只使用特定集合

executor:
  reranker: api  # 推荐使用 api 模式（更快）
  max_paper_num: 100
  max_workers: 8

reranker:
  api:
    key: ${oc.env:OPENAI_API_KEY}
    base_url: ${oc.env:OPENAI_API_BASE}
    model: BAAI/bge-m3  # 或 text-embedding-3-small
    batch_size: 100
  tag_weights:
    ⭐⭐⭐: 3.0
    ⭐⭐: 2.0
    ⭐: 1.5
  feedback_file: feedback.yaml
```

---

## 工作原理

推荐分数计算公式：

```
最终分数 = Σ(相似度 × 时间衰减 × 标签权重) / 总权重
```

其中：
- **相似度**：新论文与你 Zotero 库中论文的 embedding 相似度
- **时间衰减**：最近添加的论文权重更高（对数衰减）
- **标签权重**：基于标签的权重（未标记论文默认 1.0）

---

## 使用建议

1. **从简单开始**：先给 10-20 篇最相关的论文打星级标签
2. **保持一致**：对所有论文使用相同的标签系统
3. **定期更新**：随着兴趣变化，更新旧论文的标签
4. **结合集合**：配合 `include_path` 聚焦特定研究领域
5. **记录反馈**：定期更新 `feedback.yaml`

---

## 推荐工作流程

1. **初始设置**：给最相关的 20 篇论文打 `⭐⭐⭐` 标签
2. **每日查看**：检查邮件中的推荐论文
3. **添加到 Zotero**：把感兴趣的论文加入 Zotero 并打标签
4. **可选**：在 `feedback.yaml` 中记录你阅读过的论文
5. **迭代优化**：随着文献库增长，系统会越来越准确

---

## GitHub Action 部署

反馈文件存储在你的仓库中，会在每次运行时保持：

1. 在仓库根目录创建 `feedback.yaml`
2. 提交并推送到 GitHub
3. Workflow 会自动使用它进行推荐
4. 定期在 GitHub 上直接编辑或本地更新

---

## 故障排查

**标签不生效？**
- 确保标签是在 Zotero 客户端中添加的
- 同步你的 Zotero 文献库
- 检查日志中的 "Loaded feedback data" 消息

**权重看起来不对？**
- 检查 `tag_weights` 配置
- 确认标签拼写正确（区分大小写）
- 查看日志中显示的平均权重

**找不到反馈文件？**
- 确保 `feedback.yaml` 在项目根目录
- 检查文件权限
- 系统在没有反馈文件时也能正常工作

---

## 测试

运行测试脚本验证功能：

```bash
python3 test_interest_learning_simple.py
```

所有测试应该通过 ✓
