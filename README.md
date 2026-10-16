# 中医就诊准备 Agent · Python 工程实战

为有经验的 Python 后端开发者准备的完整课程与配套项目。30 个递进学习节点，80 道面试题及答案/考点解析，10 组原创架构与原理图。一个仓库贯穿工具调用、RAG、事实确认、幂等、并发、SSE、评测和部署。

**从这里开始：[完整课程 Markdown](course/COURSE.md)。** 运行证据与未执行项见 [验证报告](evidence/validation.md)。课程直接在 GitHub 阅读，不再生成或分发 PDF。

仓库仅保存源码、课程、原创教学数据和去除个人路径的验证记录。配置密钥前请阅读 [配置与数据保护说明](SECURITY.md)。

GitHub CI 模板位于 [`.github/ci.yml.example`](.github/ci.yml.example)。当前上传凭据没有 `workflow` 权限，因此尚未启用 Actions；在有相应权限的环境将它移到 `.github/workflows/ci.yml` 后提交即可启用。相同检查可在本地运行 `make check`。

## 项目做什么

用户描述困扰 → 模型选择追问或知识检索 → 提出可溯源候选事实 → 用户确认/更正 → 导出确定性就诊摘要。内置知识为少量原创教学条目，不是临床知识库。项目不自动诊断、开方或提供剂量。

- 真实模型入口：第三方 OpenAI 兼容 Responses / Chat，两套协议显式选择。
- 本地可运行入口：offline 确定性工程夹具，明确不冒充语言模型。
- 工程主线：FastAPI、Pydantic、SQLAlchemy、AnyIO，SQLite 起步，PostgreSQL 可选。
- 交互：Chainlit 浏览器界面、`/docs`、API、终端命令；SSE 输出实时工作流进度，最终结果在提交后发送。
- 扩展：真实 stdio MCP 往返和 LangGraph 条件路由示例。

![架构](course/assets/architecture.png)

## 安装与本地启动

在仓库根目录，使用 Python 3.12 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

```bash
uv sync --all-extras --frozen
uv run tcm init-db
uv run tcm run --text '什么是四诊？'
uv run pytest
```

启动服务需访问令牌；下面是**公开的本地教学值**，对外使用前替换为长随机值：

```bash
export TCM_MODEL_MODE=offline
export TCM_ACCESS_TOKENS='{"local-course-token-change-before-sharing":"learner"}'
uv run tcm serve
```

打开 [API 文档](http://127.0.0.1:8000/docs)，Authorize 输入本地访问令牌。终端保持服务运行，在另一个终端执行完整 HTTP 流程：

```bash
export TCM_CLIENT_TOKEN='local-course-token-change-before-sharing'
uv run python examples/smoke_api.py
```

## 启动 Chainlit 界面

在同一个仓库根目录，先按上面的步骤启动后端，再开启另一个终端：

```bash
uv sync --extra ui --frozen
export TCM_MODEL_MODE=offline
export TCM_ACCESS_TOKENS='{"local-course-token-change-before-sharing":"learner"}'
export TCM_SERVER_URL=http://127.0.0.1:8000
uv run --extra ui chainlit create-secret
# 将上一条命令生成的 CHAINLIT_AUTH_SECRET 配置行粘贴到本地 .env；不要提交。
uv run --extra ui chainlit run ui/app.py --host 127.0.0.1 --port 8001
```

访问 [浏览器界面](http://127.0.0.1:8001)。登录输入框默认标为“电子邮箱”，实际填写应用身份 `learner`；密码填写对应的**应用访问令牌**，上例为公开教学值 `local-course-token-change-before-sharing`，不是模型平台密钥。UI 和后端必须使用相同的 `TCM_ACCESS_TOKENS` 映射。

使用顺序：同意并开始 → 描述困扰 → 确认候选事实 → 查看摘要。可以撤回事实后重新描述；知识问题会显示引用。删除记录需要再次确认，成功后清除当前页面的对话消息。模型处理中展示真实工作流进度，不显示内部推理，也不伪造逐字输出。

开始后会显示从 API 读取的实际后端模式；`offline` 明确标为固定策略工程夹具，不冒充真实语言模型。

![Chainlit 交互界面，使用合成测试输入](docs/images/chainlit.png)

连接失败或流中断时，可点击“重试同一请求”；按钮复用原请求编号，后端幂等合同仍然有效。UI 尚未配置历史持久化，刷新后不会恢复原会话，请在刷新前查看摘要或删除记录。页面连接短暂断开时，Chainlit 在内存中保留会话最多 300 秒。

端口 8000 是 API，8001 是界面；默认只监听本机。如通过反向代理对外部署，需要 TLS，并在 `.chainlit/config.toml` 中设置准确的 `allow_origins`，同时落实后端身份与数据生命周期要求。[界面实现与课程讲解](course/COURSE.md#补充实战chainlit-交互验证界面)。

## 接入你的兼容 API 平台

复制 `.env.example` 为本地 `.env`，填写地址、模型名、模型密钥、应用访问令牌。密钥只在本地填写；`.env` 已忽略。

```dotenv
TCM_MODEL_MODE=responses
TCM_MODEL_BASE_URL=https://your-provider.example/v1
TCM_MODEL_NAME=your-model-name
TCM_MODEL_API_KEY=在本地填写
TCM_ACCESS_TOKENS={"在本地生成的长随机值":"learner"}
```

- 基地址不带 `/responses` 或 `/chat/completions`。
- 只兼容 Chat 的平台设置 `TCM_MODEL_MODE=chat`。
- Responses 默认请求加密 reasoning 条目，以支持无服务端存储的工具往返。平台不支持该字段且使用非推理模型时，可设 `TCM_RESPONSES_INCLUDE_REASONING=false`。需要推理状态的模型不能盲目关掉。
- Chat 模型若要求 `max_completion_tokens`，设 `TCM_CHAT_TOKEN_PARAMETER=max_completion_tokens`。
- 必须支持工具调用与工具结果回传。仅能聊天不满足本项目合同。
- 真实 Embedding 是额外能力，设置 `TCM_EMBEDDING_MODEL` 才启用。当前与模型共用基地址/密钥，平台分开部署时需扩展配置。

```bash
uv run tcm doctor
uv run tcm run --text '请检索知识库解释四诊并给出引用'
TCM_RUN_LIVE=1 uv run pytest tests/test_live.py -m live -q
```

`doctor` 只打印安全元数据，不输出密钥。真实供应商尚未配置时，live 测试明确跳过，不能宣称已验证该平台。

## API 最短流程

| 请求 | 用途 |
|---|---|
| `POST /sessions`，`{"consent":true}` | 创建当前身份会话 |
| `POST /sessions/{id}/turns` | 提交 `request_id`、`expected_version`、`text` |
| `PATCH /sessions/{id}/facts` | 确认候选的 `field`、`quote`、`source_turn_id`，附当前版本 |
| `GET /sessions/{id}/summary` | 无模型依赖的就诊摘要 |
| `GET /sessions/{id}/records` | 原始输入与已提交响应导出 |
| `DELETE /sessions/{id}/facts/{field}?version=N` | 撤回已确认字段 |
| `POST /sessions/{id}/events` | SSE：accepted/progress/committed/done 或 error |
| `DELETE /sessions/{id}` | 删除应用数据库会话与操作记录 |
| `GET /metrics` | 受令牌保护的运行指标 |

`request_id` 同一次提交重试时保持不变；新消息生成新值。每次成功修改 version 加一；409 后先读取新状态，不要强行提交旧模型结果。

## 学习与验证命令

```bash
uv run ruff check src tests examples scripts
uv run ruff format --check src tests examples scripts
uv run basedpyright
uv run pytest
uv run tcm evaluate
uv run --extra mcp python examples/mcp_client.py
uv run --extra graph python examples/graph_workflow.py
```

`examples` 的推荐运行方法是 **uv run python 文件名**，复用项目锁定环境；直接让 uv 按单文件元数据解析会建立另一环境。

```bash
uv run python scripts/build_course.py
uv run python scripts/render_figures.py
```

文档构建从真实源码提取具名代码节选；修改代码后重建课程。图像重建需要 Heiti 或 Noto Sans CJK 字体；阅读已有 PNG/SVG 不需要安装绘图依赖。

## 自建知识与评测

管理员以 Markdown + 来源清单入库，参见课程第 8—13 节。

```bash
uv run tcm ingest data/manifest.json --destination data/knowledge.json
```

将 `TCM_KNOWLEDGE_PATH` 指向新产物后重启。`approved` 是工程准入，不是临床审核。自建语料要同时创建对应评测标签，不能拿旧 relevant IDs 评价新资料。默认评测仅 8 条，不能证明真实用户或医学效果。

## PostgreSQL 与容器

```bash
# 本地 .env 先填好应用配置；数据库密码使用 URI 安全的随机字母数字值。
export TCM_DB_PASSWORD='自行生成的长随机字母数字值'
docker compose up --build
```

迁移先运行，成功后启动 API。主服务仍是单进程，限流为进程内；多副本前应增加共享配额控制。公网部署还需 TLS、完整身份/角色管理、数据生命周期、审核运维与相应专业流程。

可对**专用测试数据库**执行 PostgreSQL 合同测试，该测试创建随机 schema 并在结束时移除它：

```bash
TCM_TEST_DATABASE_URL='postgresql+asyncpg://user:password@localhost/test_db' \
  uv run pytest tests/test_postgres.py -m postgres -q
```

当前环境没有 Docker/PostgreSQL，配置已提供但不声称运行验证通过。应用数据库删除合同不覆盖备份物理页和供应商记录。当前代码适合受控工程验证，不等于完成公开医疗服务上线。

## 目录与许可

`course/COURSE.md` 为主交付；`src/` 为完整实现；`tests/` 为行为验证；`examples/` 为集成入口；`knowledge/` 为原创教学语料；`evidence/` 保存结果。已有 `docs/` 研究材料保留。

新编写源码 MIT；原创课程、图示与教学知识 CC BY 4.0。外部来源权利不变，详见 LICENSE 与 COURSE-LICENSE.md。
