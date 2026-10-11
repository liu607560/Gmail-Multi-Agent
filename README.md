# Gmail Multi-Agent 邮件自动化分类回复

基于 LangGraph 的客服邮件处理项目，通过 Gmail API 读取邮件，结合知识库生成回复并审核。审核通过后自动发送；最多尝试 3 次仍未通过时，保存最后一版为 Gmail 草稿，供人工复核。

本项目在已有邮件工作流基础上进行了二次开发，主要改进包括 PostgreSQL/pgvector 接入、Google Cloud Pub/Sub 事件通知、自动发送与审核失败保存草稿、重复邮件过滤和日志优化。

## 功能与流程

1. Gmail 邮箱变化通过 Pub/Sub 发布通知，本地 Python 程序通过 Pull 接口接收。
2. 邮件分类为产品咨询、客户投诉、客户反馈或无关邮件。
3. 产品咨询生成检索问题，通过 pgvector 检索知识库；投诉和反馈直接进入回复生成。
4. 回复审核通过后发送，未通过则结合反馈重写，最多生成 3 版，仍未通过则保存草稿。
5. 无关邮件添加标签；已有草稿的线程和已有回复的邮件被过滤，减少重复处理。

监听每天自动续期；没有待处理邮件时保持安静，通知处理异常时等待 30 秒后继续尝试。

## 技术栈

- Python / LangGraph / LangChain：状态管理、流程路由和模型调用。
- ChatOpenAI：通过 OpenAI 兼容接口完成分类、查询生成、回复和审核。
- Gemini Embeddings：使用 `models/gemini-embedding-001` 生成向量。
- PostgreSQL / pgvector：知识库向量存储与检索。
- Gmail API / OAuth 2.0：邮箱授权、读取、监听、草稿和发送。
- Google Cloud Pub/Sub：邮箱变化通知。
- FastAPI / LangServe：可选 HTTP 工作流接口，运行 `main.py` 不依赖它。

## 项目结构

```text
main.py                    接收通知并运行工作流
create_index.py             文本切分、向量化和入库
deploy_api.py              可选 HTTP API 入口
data/agency.txt            示例产品知识
src/
  graph.py                 工作流节点与路由
  nodes.py                 业务步骤
  agents.py                模型与 RAG 链
  prompts.py               提示词
  state.py                 邮件结构和工作流状态
  structure_outputs.py     模型结构化输出
  tools/GmailTools.py       Gmail 操作
```

## 本地运行

以下命令以 Windows PowerShell 为例。准备 Python 环境、启用 pgvector 的 PostgreSQL 实例和模型 API 权限。

### 获取代码

```powershell
git clone https://github.com/liu607560/Gmail-Multi-Agent.git
cd Gmail-Multi-Agent/langgraph-email-automation-main
python -m pip install -r requirements.txt
```

### 环境配置

在 `main.py` 所在目录创建 `.env`，填写自己的配置：

```dotenv
MY_EMAIL=your_email@gmail.com
NEBULA_API_KEY=your_model_api_key
NEBULA_BASE_URL=https://your-provider.example/v1
GOOGLE_API_KEY=your_gemini_api_key
PGVECTOR_CONNECTION_STRING=postgresql+psycopg://user:password@localhost:5432/email_db
PGVECTOR_COLLECTION=email_knowledge
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id
GMAIL_PUBSUB_TOPIC=gmail-notifications
GMAIL_PUBSUB_SUBSCRIPTION=gmail-notifications-sub
```

当前模型名在 `src/agents.py` 和 `create_index.py` 中配置为 `gpt-6.1-sol`，使用其他服务商时需改成其支持的模型。

需要代理时额外配置，端口以自己的代理软件为准：

```dotenv
PROXY_URL=http://127.0.0.1:7897
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
NO_PROXY=localhost,127.0.0.1,::1
```

### Google Cloud 配置

在同一个 Google Cloud 项目中：

1. 启用 Gmail API 和 Cloud Pub/Sub API。
2. 配置 OAuth 同意屏幕，创建桌面应用 OAuth 客户端，将下载凭证命名为 `credentials.json`，放到 `main.py` 所在目录。
3. 创建主题 `gmail-notifications` 和 Pull 订阅 `gmail-notifications-sub`。
4. 在主题上为 `gmail-api-push@system.gserviceaccount.com` 授予 `Pub/Sub Publisher`。
5. 确保本地登录账号有接收订阅消息及设置配额项目所需的权限。

安装 Google Cloud CLI 后，配置本机应用默认凭证（ADC）：

```powershell
gcloud.cmd auth application-default login
gcloud.cmd auth application-default set-quota-project YOUR_PROJECT_ID
```

将 `YOUR_PROJECT_ID` 替换为自己的项目 ID。ADC 用于 Pub/Sub；Gmail 使用单独的 OAuth 授权，首次运行时打开浏览器，成功后生成 `token.json`。

### 建立知识库并启动

修改 `data/agency.txt` 为需要的业务资料，然后执行：

```powershell
python create_index.py
python main.py
```

当前切分参数为 `chunk_size=300`、`chunk_overlap=50`，检索 `k=3`。建库脚本还会运行测试查询；未实现文档自动替换或去重，重复运行可能追加重复片段。

程序启动监听后等待通知。开启监听本身也会产生初始通知，可能处理现有待处理邮件。审核通过会真实发送，建议先用测试邮箱验证。

电脑、程序、数据库和所需网络连接应保持运行，按 `Ctrl+C` 停止。当前读取范围为最近 8 小时、最多 50 封，并非完整的邮件历史同步系统。

## 可选 API 入口

```powershell
python deploy_api.py
```

该入口通过 FastAPI / LangServe 提供工作流接口，默认端口 `8000`，文档路径 `/docs`。它独立于通知监听，不会代替 `main.py` 的接收循环。当前未接入 MCP。

## 示例资料和本地凭证

`data/agency.txt` 中的 Agentia 是示例产品，`src/prompts.py` 中回复署名为 `The Agentia Team`。使用自己的业务时应同时调整知识资料和回复署名。

`.env`、`credentials.json`、`token.json` 和 ADC 凭证属于本地配置，不应提交。忽略规则不会清除历史中的敏感信息。

## 项目来源

基于 [kaymen99/langgraph-email-automation](https://github.com/kaymen99/langgraph-email-automation) 二次开发。本仓库增加了事件通知接入、向量库迁移、自动发送与审核失败保存草稿等改进；原始工作流来自上述项目。
