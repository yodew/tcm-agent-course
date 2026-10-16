# 从 Python 后端到 Agent 工程：中医就诊准备助手实战课程

**版本：1.0 · 编写与核查日期：2026-10-16 · 面向已有后端工程经验的 Python 开发者**

这是一套围绕同一个真实业务闭环展开的课程：用户描述困扰，助手选择必要追问，检索可核查知识，提出待确认事实，用户核对后导出就诊摘要。你会从模型协议一直做到事务、并发、故障恢复、评测和部署，不需要重新学习 Python 基础。

“一个月”表示 30 个有依赖关系的学习节点，不限制每天投入。你可以按自己的节奏推进；每节的验收通过后再进入下一节。本文件包含全部课程正文、代码节选与详解，以及最后独立的项目面试题模块。配套仓库中的源码是执行依据，文中的节选从对应源码自动提取，避免教程和实现各说各话。

## 阅读导航

- [项目目标与交付边界](#项目目标与交付边界)
- [快速启动与运行方式](#快速启动与运行方式)
- [30 节课程路线](#30-节课程路线)
- [第一周：协议、合同与执行循环](#第一周协议合同与执行循环)
- [第二周：知识、检索与事实记忆](#第二周知识检索与事实记忆)
- [第三周：持久化、并发与服务可靠性](#第三周持久化并发与服务可靠性)
- [第四周：协议扩展、评测与交付](#第四周协议扩展评测与交付)
- [第 29—30 节：集成验收与项目答辩](#第-2930-节集成验收与项目答辩)
- [独立模块：项目面试题与答案解析](#独立模块项目面试题与答案解析)
- [来源与证据分级](#来源与证据分级)

## 项目目标与交付边界

项目名称为 **TCM Visit Preparation Agent，中医就诊准备助手**。它围绕问诊前的信息采集展开，不生成个体诊断、处方或剂量，不把舌象照片当作已验证的诊断输入。中医场景的价值在于：术语解释要有出处、病史不能编造、用户更正必须立即生效、记录涉及个人健康信息。这些约束正好迫使我们把 Agent 工程做完整。

已有产品需求见 [原始需求](../docs/product-requirements.md)。课程沿用主场景，以 Chainlit 浏览器界面、API 后端、终端工具和交互式 OpenAPI 文档为入口。Chainlit 仅承担交互，通过 HTTP 调用同一套后端，事实和权限仍由后端掌握。

| 能力 | 本项目实际实现 | 实际边界 |
|---|---|---|
| 模型接入 | Responses 与 Chat Completions 分别适配、原生工具调用 | 用户平台尚未配置，真实连接与效果未验收 |
| 自主决策 | 模型选择检索、读取确认事实、追问或结束 | 工具集合和最终输出由代码约束 |
| 知识检索 | 中文 BM25；可选真实 Embedding、余弦排序、RRF | 默认 8 条原创教学知识，不称为临床知识库 |
| 问诊记录 | 候选事实、显式确认、同字段更正、原文溯源 | 精确匹配只能证明文本来源，不能证明语义分类正确 |
| 就诊摘要 | 确定性生成、缺失标记、导出 | 无自动诊断、无未确认信息 |
| 可靠性 | 幂等、版本 CAS、租约 fencing、事务外模型调用、超时降级 | 不宣称外部模型调用 exactly-once |
| 服务运行 | 鉴权隔离、进程内限流、SSE 进度、Prometheus 指标 | 多进程共享限流、外部告警接收端需要部署集成 |
| 扩展对照 | 可运行 MCP 服务端/客户端、LangGraph 条件路由 | 独立教学示例，不伪称主服务已改为分布式多 Agent |
| 交付 | 锁文件、数据库迁移、容器与 Compose、自动化检查 | 容器和 PostgreSQL 的验证状态见最终验证报告 |

医疗服务上线另有资质、专业审核与数据处理要求。国家卫健委发布的互联网诊疗监管细则明确约束 AI 替代医师和自动生成处方；课程按就诊准备定位设计，不能因为软件测试通过就声称完成医疗上线审核。[官方文件](https://www.nhc.gov.cn/yzygj/c100068/202203/2072f0e8988249e59d942e1b2a933916.shtml) · [官方政策解读](https://www.nhc.gov.cn/yzygj/c100067/202203/61bb44c669144ad1a4266fc4d63dd7a4.shtml)

![系统架构](assets/architecture.png)

架构图的可编辑源码：[Mermaid](assets/architecture.mmd) · [SVG](assets/architecture.svg)。后文全部图示也提供这两种源文件。

## 快速启动与运行方式

在仓库根目录执行。需要 Python 3.12 与 uv；uv 可按[官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)安装。首次依赖同步需要联网，后续使用锁定环境。

```bash
uv sync --all-extras --frozen
uv run tcm init-db
uv run tcm run --text '什么是四诊？'
uv run pytest
uv run tcm evaluate
```

未设置配置时，`run` 使用 **offline 确定性工程夹具**，旨在让你立即验证安装、工具循环和数据链路。它不是语言模型，也不用于证明问诊理解、语义检索或医学能力。课程实际模型路径已实现，切换配置后走第三方平台。

启动可交互服务需显式配置访问令牌。以下令牌是公开的本地教学值，不能用于公开部署：

```bash
export TCM_MODEL_MODE=offline
export TCM_ACCESS_TOKENS='{"local-course-token-change-before-sharing":"learner"}'
uv run tcm serve
```

浏览 [交互式 API 文档](http://127.0.0.1:8000/docs)，点 Authorize 输入令牌，按顺序调用创建会话、提交回合、确认事实、生成摘要。完整的 HTTP 请求方法见第 15 节。服务只绑定本机；不要直接将教学令牌映射公开到互联网。

接入你的兼容平台时，在本地 `.env` 配置，密钥不进入 Git 或聊天：

```dotenv
TCM_MODEL_MODE=responses
TCM_MODEL_BASE_URL=https://your-provider.example/v1
TCM_MODEL_NAME=your-provider-model-name
TCM_MODEL_API_KEY=由你在本地填写
TCM_ACCESS_TOKENS={"由你生成的长随机访问令牌":"learner"}
```

推理型 Responses 模型通常需要回传加密 reasoning 条目，默认请求 `include=["reasoning.encrypted_content"]`。若第三方不支持该字段且使用非推理模型，可显式设 `TCM_RESPONSES_INCLUDE_REASONING=false`；不要对需要该状态的模型随意关闭。Chat 模型若要求 `max_completion_tokens`，设置 `TCM_CHAT_TOKEN_PARAMETER=max_completion_tokens`。这些兼容开关都应重新做 live 工具往返验收。

这里填写的是 API **基地址**，不要再附加 `/responses`。如果供应商只支持 `/chat/completions`，显式改为 `TCM_MODEL_MODE=chat`；项目不会在请求失败后偷偷改变协议。访问令牌用于你的应用鉴权，模型 API Key 用于供应商鉴权，两者不是同一把密钥。

```bash
uv run tcm doctor
uv run tcm run --text '请检索知识库解释四诊并给出引用'
TCM_RUN_LIVE=1 uv run pytest tests/test_live.py -m live -q
```

真实模型验收要求至少完成“模型发出检索调用 → 服务执行工具 → 模型收到工具结果 → 提交有引用的终态”。只收到 HTTP 200 或普通文本不算通过。测试失败可能说明平台协议子集、模型能力、参数支持或提示策略不同，应根据失败类型处理，不能直接关闭校验。

## 30 节课程路线

![课程路线](assets/roadmap.png)

| 周 | 节点 | 技术推进 | 阶段验收 |
|---|---|---|---|
| 第一周 | 01—07 | 产品合同、协议、类型、工具调用、Agent Loop、上下文、策略 | 一次完整的模型—工具—结果闭环；失败可解释 |
| 第二周 | 08—14 | 知识清单、切块、BM25、Embedding、RRF、引用、事实记忆 | 有出处的知识解释；更正后的事实可用于摘要 |
| 第三周 | 15—21 | API、存储、事务、幂等、版本冲突、恢复、SSE | 多用户隔离；并发不覆盖；重复请求不重复落库 |
| 第四周 | 22—28 | MCP、LangGraph、评测、可观测性、容量、安全、部署 | 可复现检查；能定位 badcase；运行状态有证据 |
| 集成 | 29—30 | 故障演练、交付审查、项目答辩 | 独立复现项目，解释方案与尚未完成的验证 |

### 代码阅读地图

```text
src/tcm_agent/
  domain.py          所有应用合同
  gateway.py         两种模型协议的发送与重放
  wire.py            供应商响应解析
  runtime.py         有界 Agent 执行循环
  policy.py          最终输出与摘要约束
  context.py         上下文预算
  ingestion.py       知识入库
  retrieval.py       BM25、余弦、RRF
  embeddings.py      真实向量接口
  repository.py      用户会话与事实存取
  operations.py      幂等、租约与原子提交
  service.py         完整回合的应用服务
  routes.py          HTTP 入口与鉴权
  streaming.py       SSE 与取消传播
  observability.py   指标与限流
  api.py             生命周期与依赖组装
```

以下代码块是具名函数或类型的源码节选。需要完整导入与上下文时，打开标注的源文件；每节给出的命令运行的是完整项目，节选不要求脱离仓库独立粘贴运行。课程节点是阅读、实现练习和验收顺序，不是 30 个互不关联的 demo。
