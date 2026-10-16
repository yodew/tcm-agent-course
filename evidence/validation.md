# 交付验证记录

日期：2026-10-16（Asia/Shanghai）。主机：macOS arm64，Python 3.12.13，uv 0.13.1。下面是实际执行范围，不把配置文件存在等同于外部能力验收。

## 已通过

| 范围 | 执行方式 | 结果 / 证据 |
|---|---|---|
| 依赖安装 | `uv sync --all-extras --frozen` | 源码 ZIP 解压到独立临时目录，重新同步依赖、迁移、运行、测试与课程检查均通过；[干净安装记录](clean-install.txt) |
| 类型检查 | `uv run basedpyright` | 核心应用 `src/tcm_agent`：0 errors、0 warnings；源码规则审计包含 UI，无违规 |
| 静态检查 | `uv run ruff check src tests examples scripts ui` | 无问题；格式检查单独执行 |
| 自动化行为 | `uv run pytest --cov=tcm_agent` | 49 passed、2 skipped；[完整结果](tests.txt) |
| 代码覆盖 | pytest-cov statement coverage | 84%；[机器报告](coverage.json)。CLI、浏览器与评测另行执行，未计入该测试进程覆盖率 |
| 双模型协议 | HTTP-level MockTransport 合同测试 | 两种请求格式、调用结果关联、推理条目重放、截断/错误拒绝；不是用户平台连通测试 |
| 会话与隔离 | FastAPI TestClient + 真实 SQLite | 授权、确认、摘要、来源校验、重放、并发冲突、删除、SSE |
| 崩溃与取消 | 真实 SQLite、可控租约/任务取消 | 旧租约被拒绝且回滚，取消后相同请求可重试 |
| 真实 HTTP | 独立 uvicorn 进程 + smoke 客户端 | 创建 201、提交/确认 200、摘要忠实、重放一致、SSE 阶段事件、导出 2 回合、删除 204；[结果](http-smoke.json) |
| MCP | 真实 stdio 子进程初始化、发现与调用 | 唯一公共检索工具；[结果](mcp-smoke.txt) |
| LangGraph | 实际执行条件图两个分支 | 知识分支完成，风险分支 handoff；[结果](graph-smoke.jsonl) |
| 小样本检索 | `uv run tcm evaluate` | 8 条原创教学问题，Recall@4=1、MRR@4=1；[逐题结果](retrieval-eval.json) |
| 图文课程 | 构建与链接脚本、Python 节选语法检查 | 30 节、80 题、10 组 PNG/SVG/Mermaid；实际源码同步 |
| Chainlit HTTP 适配 | MockTransport + 真实 FastAPI/SQLite | 同请求重试、截断流拒绝、错误体脱敏、明确版本冲突、确认/撤回/删除和跨身份隔离 |
| Chainlit 浏览器 | 本机 Chainlit 2.12.0 + 真实独立 API 进程 | 登录、同意、对话、确认前后摘要、撤回、知识引用与删除后清屏；[桌面实图](../docs/images/chainlit.png)、[手机实图](../docs/images/chainlit-mobile.png)、[验收范围](ui-validation.md) |

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
uv run python scripts/check_course.py
```

真实 HTTP 重现需先按 README 启动服务，再运行 smoke 客户端。测试数据均为合成输入；报告不包含 API Key、认证头或真实患者信息。
