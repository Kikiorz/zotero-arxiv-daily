# 测试指南

## 方法 1：本地测试（推荐，快速验证）

### 前提条件
1. 安装依赖
2. 设置环境变量
3. 有一些 Zotero 论文（至少 20 篇）

### 步骤

#### 1. 安装依赖
```bash
# 如果有 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 或者用 pip
pip install -r requirements.txt
```

#### 2. 创建本地配置文件
```bash
cp config/base.yaml config/local_test.yaml
```

编辑 `config/local_test.yaml`：
```yaml
zotero:
  user_id: "你的ZOTERO_ID"
  api_key: "你的ZOTERO_KEY"
  include_path: null

email:
  sender: "你的发件邮箱"
  receiver: "你的收件邮箱"
  smtp_server: smtp.qq.com
  smtp_port: 465
  sender_password: "你的邮箱密码"

llm:
  api:
    key: "你的OPENAI_API_KEY"
    base_url: "你的OPENAI_API_BASE"
  generation_kwargs:
    model: deepseek-chat
    max_tokens: 200
  language: English

reranker:
  local:
    model: jinaai/jina-embeddings-v5-text-nano
    encode_kwargs:
      task: retrieval
      prompt_name: document
  diversity:
    enabled: true
    bonus_strength: 0.3

source:
  arxiv:
    category: ["cs.AI","cs.CV"]  # 先测试 2 个类别
    include_cross_list: false

executor:
  send_empty: false
  max_workers: 4
  max_paper_num: 10  # 先测试 10 篇
  reranker: local
  debug: true
  source: ['arxiv']
```

#### 3. 运行测试
```bash
# 使用 uv
uv run src/zotero_arxiv_daily/main.py --config config/local_test.yaml

# 或者直接用 python
python src/zotero_arxiv_daily/main.py --config config/local_test.yaml
```

#### 4. 检查输出
- 查看日志中的 "Loaded feedback data"
- 查看 "avg weight" 是否合理
- 查看推荐的论文分数
- 检查邮件是否收到

---

## 方法 2：GitHub Action 测试（真实环境）

### 步骤

#### 1. 在 Zotero 中准备数据
给至少 20 篇论文打星级：
- 5-10 篇打 ⭐⭐⭐⭐⭐
- 5-10 篇打 ⭐⭐⭐⭐
- 5-10 篇打 ⭐⭐⭐

#### 2. 提交代码到 GitHub
```bash
git add .
git commit -m "Add 5-star interest learning system"
git push
```

#### 3. 设置 GitHub Secrets
进入你的 GitHub 仓库 → Settings → Secrets and variables → Actions

添加以下 Secrets：
- `ZOTERO_ID`
- `ZOTERO_KEY`
- `SENDER`
- `SENDER_PASSWORD`
- `RECEIVER`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE`

#### 4. 设置 GitHub Variables
进入 Variables 标签，添加 `CUSTOM_CONFIG`：

```yaml
zotero:
  user_id: ${oc.env:ZOTERO_ID}
  api_key: ${oc.env:ZOTERO_KEY}
  include_path: null

email:
  sender: ${oc.env:SENDER}
  receiver: ${oc.env:RECEIVER}
  smtp_server: smtp.qq.com
  smtp_port: 465
  sender_password: ${oc.env:SENDER_PASSWORD}

llm:
  api:
    key: ${oc.env:OPENAI_API_KEY}
    base_url: ${oc.env:OPENAI_API_BASE}
  generation_kwargs:
    model: deepseek-chat
    max_tokens: 200
  language: English

reranker:
  local:
    model: jinaai/jina-embeddings-v5-text-nano
    encode_kwargs:
      task: retrieval
      prompt_name: document
  diversity:
    enabled: true
    bonus_strength: 0.3
  tag_weights:
    ⭐⭐⭐⭐⭐: 2.5
    ⭐⭐⭐⭐: 2.3
    ⭐⭐⭐: 2.0

source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL"]
    include_cross_list: true

executor:
  send_empty: false
  max_workers: 16
  max_paper_num: 50
  reranker: local
  source: ['arxiv']
```

#### 5. 手动触发 Workflow
1. 进入 GitHub 仓库
2. 点击 `Actions` 标签
3. 选择 `Send emails daily`
4. 点击 `Run workflow`
5. 选择 `main` 分支
6. 点击绿色的 `Run workflow` 按钮

#### 6. 查看运行结果
1. 点击运行中的 workflow
2. 查看日志输出
3. 检查是否有错误
4. 等待邮件（大约 5-15 分钟）

---

## 方法 3：快速验证（只测试权重计算）

```bash
# 运行测试脚本
python3 test_interest_learning_simple.py
```

应该看到：
```
✓ PASSED: Tag Weight Calculation
✓ PASSED: Feedback File
✓ PASSED: Weight Combination
✓ PASSED: Config Structure
```

---

## 检查清单

### 测试前
- [ ] Zotero 中至少有 20 篇论文
- [ ] 给论文打了星级标签（⭐⭐⭐⭐⭐, ⭐⭐⭐⭐, ⭐⭐⭐）
- [ ] 设置了所有必需的环境变量/Secrets
- [ ] `feedback.yaml` 文件存在（可以是空的）

### 测试中
- [ ] 查看日志：是否成功获取 Zotero 论文
- [ ] 查看日志：是否加载了 feedback 数据
- [ ] 查看日志：平均权重是否合理（应该在 1.5-2.5 之间）
- [ ] 查看日志：是否成功 rerank 论文

### 测试后
- [ ] 收到邮件
- [ ] 邮件中有推荐论文
- [ ] TLDR 质量好（突出创新、影响、惊喜）
- [ ] 推荐的论文覆盖不同星级的主题
- [ ] 有一些"小惊喜"论文（不太相似但有趣）

---

## 常见问题

### 本地测试失败

**错误：ModuleNotFoundError**
```bash
pip install pyzotero arxiv sentence-transformers openai loguru omegaconf pyyaml
```

**错误：Zotero API 失败**
- 检查 `user_id` 和 `api_key` 是否正确
- 确认 API key 有读取权限

**错误：SMTP 失败**
- 检查邮箱密码是否是"授权码"而不是登录密码
- QQ 邮箱：设置 → 账户 → 开启 SMTP → 获取授权码

### GitHub Action 失败

**Secrets 未设置**
- 确认所有 Secrets 都已添加
- 注意大小写

**Workflow 不运行**
- 检查 `.github/workflows/main.yml` 是否存在
- 确认 workflow 文件格式正确

**运行超时**
- 减少 `max_paper_num`
- 减少 arxiv 类别数量

---

## 推荐测试流程

1. **先运行快速验证**（方法 3）
   ```bash
   python3 test_interest_learning_simple.py
   ```

2. **如果有本地环境，运行本地测试**（方法 1）
   - 设置 `max_paper_num: 10` 快速测试
   - 检查日志和邮件

3. **最后在 GitHub Action 测试**（方法 2）
   - 手动触发一次
   - 检查完整流程

4. **调整参数**
   - 根据结果调整 `diversity.bonus_strength`
   - 调整 `tag_weights` 如果需要

---

需要我帮你设置哪个测试方法？
