# 解决 GitHub Action 超时问题

## 问题

你的配置导致处理 **1227 篇论文**，GitHub Action 运行 46 分钟后超时失败。

```
Converting papers: 60% | 740/1227 [46:05<30:20]
Error: The operation was canceled.
```

---

## 原因分析

### 1. 论文数量太多
```yaml
source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL","cs.RO","cs.SY","cs.CE"]  # 7 个类别
    include_cross_list: true  # 包含交叉列表
```

**每天新论文估算：**
- cs.AI: ~50 篇
- cs.CV: ~100 篇
- cs.LG: ~80 篇
- cs.CL: ~60 篇
- cs.RO: ~30 篇
- cs.SY: ~40 篇
- cs.CE: ~20 篇
- Cross-list: ~300 篇
- **总计：~680-1200 篇/天**

### 2. PDF 提取很慢
```
PDF extraction timed out for ...
```

每篇论文需要下载 PDF 并提取文本，平均 3-5 秒/篇。

---

## 解决方案

### 方案 A：减少类别（推荐）

只保留你最关心的 3 个类别：

```yaml
source:
  arxiv:
    category: ["cs.AI","cs.LG","cs.RO"]  # 只保留核心类别
    include_cross_list: false  # 关闭交叉列表
```

**预计论文数：** ~160 篇/天
**预计时间：** 10-15 分钟

---

### 方案 B：使用 embedding 预筛选

先用 embedding 快速筛选出 200 篇，再处理：

```yaml
executor:
  max_paper_num: 50  # 最终推荐 50 篇
  pre_filter_num: 200  # 先筛选出 200 篇候选

source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL","cs.RO"]  # 5 个类别
    include_cross_list: false
```

需要修改代码添加预筛选功能。

---

### 方案 C：分批处理

每天只处理部分类别，轮流推荐：

**周一/三/五：**
```yaml
category: ["cs.AI","cs.LG","cs.RO"]
```

**周二/四/六��**
```yaml
category: ["cs.CV","cs.CL"]
```

**周日：**
```yaml
category: ["cs.SY","cs.CE"]
```

---

### 方案 D：禁用 PDF 提取

不提取 PDF 全文，只用 abstract 生成 TLDR：

需要修改代码，跳过 PDF 下载步骤。

---

## 推荐配置（方案 A）

我已经创建了 `config/fast_config.yaml`：

```yaml
source:
  arxiv:
    category: ["cs.AI","cs.LG","cs.RO"]  # 3 个核心类别
    include_cross_list: false

executor:
  max_workers: 16
  max_paper_num: 50
  reranker: local  # 使用 local 更快
```

**优点：**
- ✅ 快速（10-15 分钟）
- ✅ 稳定（不会超时）
- ✅ 聚焦核心领域

**缺点：**
- ❌ 可能错过其他领域的好论文

---

## 如果你想保留所有类别

### 选项 1：增加 GitHub Action 超时时间

在 workflow 中添加：
```yaml
jobs:
  calculate-and-send:
    runs-on: ubuntu-latest
    timeout-minutes: 120  # 2 小时超时
```

但这样每天要等 1-2 小时。

### 选项 2：使用自己的服务器

在自己的服务器上运行，不受 GitHub Action 限制。

---

## 我的建议

**立即使用方案 A：**
1. 更新 `CUSTOM_CONFIG` 为 `fast_config.yaml` 的内容
2. 只保留 3 个核心类别
3. 关闭 cross-list
4. 使用 local reranker

**如果还想要更多论文：**
- 可以逐步增加类别，测试每个配置的运行时间
- 或者使用方案 C（分批处理）

需要我帮你实现哪个方案？
