# 交付验证记录

课程增强与代码验证：2026-10-18；既有 HTTP、MCP、界面验收：2026-10-16（Asia/Shanghai）。主机：macOS arm64，Python 3.12.13，uv 0.13.1。下面是实际执行范围，不把配置文件存在等同于外部能力验收。

## 已通过

| 范围 | 执行方式 | 结果 / 证据 |
|---|---|---|
| 依赖安装 | `uv sync --all-extras --frozen` | 源码 ZIP 解压到独立临时目录，重新同步依赖、迁移、运行、测试与课程检查均通过；[干净安装记录](clean-install.txt) |
| 类型检查 | `uv run basedpyright` | 核心应用 `src/tcm_agent`、`labs` 与作业参考实现：0 errors、0 warnings；源码规则审计包含 UI，无违规 |
| 静态检查 | `uv run ruff check src tests examples scripts ui labs exercises` | 无问题；格式检查单独执行 |
| 自动化行为 | `uv run pytest --cov=tcm_agent` | 88 passed、2 skipped；[完整结果](tests.txt) |
| 代码覆盖 | pytest-cov statement coverage | 85%；[机器报告](coverage.json)。CLI、浏览器与评测另行执行，未计入该测试进程覆盖率 |
| 双模型协议 | HTTP-level MockTransport 合同测试 | 两种请求格式、调用结果关联、推理条目重放、截断/错误拒绝；不是用户平台连通测试 |
| 会话与隔离 | FastAPI TestClient + 真实 SQLite | 授权、确认、摘要、来源校验、重放、并发冲突、删除、SSE |
| 崩溃与取消 | 真实 SQLite、可控租约/任务取消 | 旧租约被拒绝且回滚，取消后相同请求可重试 |
| 真实 HTTP | 独立 uvicorn 进程 + smoke 客户端 | 创建 201、提交/确认 200、摘要忠实、重放一致、SSE 阶段事件、导出 2 回合、删除 204；[结果](http-smoke.json) |
| MCP | 真实 stdio 子进程初始化、发现与调用 | 唯一公共检索工具；[结果](mcp-smoke.txt) |
| LangGraph | 实际执行条件图两个分支 | 知识分支完成，风险分支 handoff；[结果](graph-smoke.jsonl) |
| 小样本检索 | `uv run tcm evaluate` | 8 条原创教学问题，Recall@4=1、MRR@4=1；[逐题结果](retrieval-eval.json) |
| 图文课程 | 构建与链接脚本、Python 节选语法检查 | 30 个完整学习节点、80 道六段式答案、16 组 PNG/SVG/Mermaid；源码同步、Python 语法与本地锚点通过 |
| Chainlit HTTP 适配 | MockTransport + 真实 FastAPI/SQLite | 同请求重试、截断流拒绝、错误体脱敏、明确版本冲突、确认/撤回/删除和跨身份隔离 |
| Chainlit 浏览器 | 本机 Chainlit 2.12.0 + 真实独立 API 进程 | 登录、同意、对话、确认前后摘要、撤回、知识引用与删除后清屏；[桌面实图](../docs/images/chainlit.png)、[手机实图](../docs/images/chainlit-mobile.png)、[验收范围](ui-validation.md) |

## v1.3 增强验收（2026-10-18）

- 四个深讲工作坊已并入主文档：实际执行轨迹、上下文/事实、评测排障、崩溃恢复。新增 30 节直达、术语索引、生产演练和综合答辩评分。
- 四项独立作业含 starter、solution、解释和 16 项验收，参考实现全部通过；[结果](exercises.txt)。起始实现实际运行得到 9 失败/7 通过，这是待完成作业的预期状态，不放进正常项目套件。
- 40 条原创合成问题先给标签与理由，比较关键词、固定 BM25 和离线策略：证据选择分别为 25/40、31/40、14/40；[逐题报告](benchmark.json)。数据与语料哈希、分类分母、延迟、用量都记录；这是单机证据选择评测，不是总体任务/医学/真实模型能力评估。
- 7 条真实 Runtime 轨迹：正常检索、未知工具、参数错误、重复编号、虚构事实、未见引用、步数耗尽；[记录](runtime-traces.json)。决策是公开固定夹具，记录不含 Prompt、参数、正文或认证头。
- 真正子进程在认领持久化后退出 73，随后验证到期前阻塞、重领、旧租约回滚、新提交与幂等重放；[结果](crash-recovery.json)。时钟通过测试 SQL 控制；不宣称 PostgreSQL、断电或跨机容灾。
- 独立实际 API 进程、临时 SQLite、回环随机端口、临时令牌：24 请求/并发 4，24 项成功；[结果](load-probe.json)。单请求耗时只计 turn，创建/删除不计入；总耗时包含整个探测。限流在隔离探测中提高，不据此推算真实供应商容量。
- 新增 HTTP 边界故障验证：429 后成功、持续 503 的三次上限、总 deadline 取消；同时保留真实平台未验收状态。正常套件合计 88 passed/2 skipped，作业参考验收另计 16 passed。
- 真实模型入口需 --live 与 TCM_RUN_LIVE=1，报告只写被忽略的 tmp/；默认路径不读取本地模型配置。当前未执行真实供应商收费请求。
- 新增材料本地文件与锚点、节选 Python 语法检查通过；本次未修改 UI 行为，既有浏览器截图保留原验收日期；不生成 PDF。

## v1.2 课程重编记录（2026-10-17）

- 30 节均按“问题与目标、原理与机制、最小实验、代码详解、项目映射、练习与验收、面试关联”组织；每节包含可执行命令。主线先基础、再编排和项目、最后生产工程。原工程细节保留在独立参考文档，旧题号附完整迁移表。
- 6 组实验已全部运行，包含固定 logits 的温度计算、有界工具执行、上下文预算与事实确认、BM25/余弦/RRF、计划依赖校验与任务评测；[实际输出](labs.txt)。固定决策与手工向量明确标识，不能当作真实模型结果。
- 新增真实 LangGraph interrupt/resume 示例，成功恢复及过期审批拒绝均执行；[实际输出](checkpoint-approval.txt)。使用 InMemorySaver，不宣称进程重启后可恢复。
- 新增 20 项参数化/行为测试，覆盖错误参数、重复调用、步数耗尽、过期确认、来源缺失、依赖环、指标分母与实际暂停/恢复。合计 69 项通过，2 项按条件跳过。
- 80 道题按基础、方案设计、项目、生产重排；逐题含核心回答、原理、证据、常见错误、考点及追问。来源区分作者自述、公开题库和项目延伸，不将“高频主题”冒充市场统计。
- 新增 6 张原理图并重绘路线；实际查看全部新增 PNG 与路线，检查中文、箭头、边界和布局。16 组图的 PNG、SVG、Mermaid 与清单一致。
- 本次没有修改 UI 交互代码；浏览器验收沿用上次记录并标明日期。继续只分发 Markdown 和源码，不生成 PDF。

## 未执行 / 不作成功声明

- **用户真实模型平台**：缺少平台地址、模型名与凭据；`tests/test_live.py` 显式跳过。Responses/Chat 协议实现与 wire 测试不能替代它。
- **真实 Embedding 和 hybrid 效果**：未配置模型服务，默认 BM25；向量路径代码不等于已经取得真实语义检索效果。
- **PostgreSQL**：当前主机无该服务；`tests/test_postgres.py` 显式跳过。可在专用测试数据库中执行隔离 schema 合同测试。
- **Docker/Compose**：当前主机无 Docker 可执行程序；容器配置未构建运行。
- **临床效果、医学审核、真实用户研究、公网服务规模与长期 SLO**：未完成，不由课程测试替代。

## 质量解释

8 条检索问题规模很小，且词面提示明显；100% 只说明当前教学集的基线表现，不是对真实用户分布、复杂问诊或医学正确性的估计。offline 是公开固定策略的工程夹具，不是真实模型。

工程自审检查了：模块职责、供应商与应用信任边界、健康信息的访问与日志、数据库原子提交、租约回收条件、流取消清理、文档与实现一致性。主要剩余限制在课程及 README 中明确列出：单进程限流、小语料扫描、受控 token 身份、无外部告警后端、抽取式引用相关性仍需评测。

## 重现

```bash
uv sync --all-extras --frozen
uv run tcm init-db
uv run ruff check src tests examples scripts ui
uv run ruff format --check src tests examples scripts ui
uv run basedpyright
uv run pytest
uv run tcm evaluate
uv run python -m labs.run_all
uv run --extra graph python examples/checkpoint_approval.py
uv run python scripts/check_course.py
TCM_EXERCISE=solution uv run pytest exercises/acceptance.py -q
uv run python -m labs.trace_demo
uv run python -m labs.benchmark
uv run python -m labs.crash_recovery
uv run python examples/load_probe.py
```

真实 HTTP 重现需先按 README 启动服务，再运行 smoke 客户端。测试数据均为合成输入；报告不包含 API Key、认证头或真实患者信息。
