## 第四周：协议扩展、评测与交付

### 第 22 节：MCP 服务端与客户端完整往返

**本节功能。** 将公共知识检索作为 MCP 工具暴露给其它受控客户端，并实际经历初始化、发现工具和执行调用。MCP 解决工具连接协议，模型如何选择工具仍属于调用侧的 Agent 逻辑。[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

源码：`examples/mcp_server.py`。

{{snippet:examples/mcp_server.py:search_public_knowledge}}

源码：`examples/mcp_client.py`。

{{snippet:examples/mcp_client.py:main}}

**代码详解。** 服务端只提供公共教学知识，不提供会话病史。客户端启动一个真实子进程，通过 stdio 交换协议消息。stdout 是协议通道，不应随意 print 调试内容；日志走 stderr。初始化后获取工具清单，再发送已校验参数。工具返回的数据仍不可信，不能因为来自 MCP 就自动成为系统指令。

本示例不开放网络端口；迁移到远程传输时，需要独立身份验证、授权、受众校验和网络边界。不能将你的模型供应商密钥透传给任意 MCP 服务。[MCP 安全实践](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)

**操作与验收。** `uv run --extra mcp python examples/mcp_client.py`。应发现唯一工具并获得带来源的检索结果；`uv run pytest tests/test_optional.py -k mcp -q` 验证真实进程往返。练习解释新增私有数据工具时，身份需要在哪个可信边界绑定。

**面试关联。** Q03：如何将 LLM、RAG 和 MCP 组合？Q04：MCP 调用有哪些阶段？Q49：MCP 与 Function Calling 如何分工？

### 第 23 节：LangGraph 对照与工作流选型

**本节功能。** 用明确 state、node、edge 描述“风险分流→Agent 或 handoff”的执行路径，同时复用相同业务运行时。目的在于理解框架的收益与责任边界，不为一个短循环强行引入大型平台。[LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)

源码：`examples/graph_workflow.py`。

{{snippet:examples/graph_workflow.py:exercise}}

**代码详解。** `GraphState` 传递业务上下文和结果；条件边决定进入哪个节点。节点是普通函数，不必每个都调用模型。图编译检查结构；运行中仍需自己的权限、总预算和业务结果校验。当前示例没有持久 checkpointer，不能把它描述成已具备跨进程节点级恢复。

主服务保留显式循环，因为只有三种工具和短回合。出现长流程、多个可恢复阶段、人审暂停、多分支或跨节点观测需要时，再评估图框架。即使加 checkpointer，外部副作用也要幂等；它不能替代应用数据库中原子保存用户事实与返回结果的合同。

**操作与验收。** `uv run --extra graph python examples/graph_workflow.py`，分别观察知识问题与风险输入。`uv run pytest tests/test_optional.py -k graph -q`。练习增加审核节点，先明确暂停期间保存哪些状态，再讨论存储与恢复，不能仅在内存里暂停就叫“人工审核上线”。

**面试关联。** Q50：何时选择 LangGraph？Q51：为什么不直接上多 Agent？

### 第 24 节：建立分层评测，而不是一个“准确率”

**本节功能。** 分别度量检索、模型动作、事实忠实性、工具执行和最终业务完成。工程测试通过只能证明确定性合同；不能自动证明真实模型选择的动作合理。

![分层评测](assets/evaluation.png)

源码：`src/tcm_agent/evaluation.py`。

{{snippet:src/tcm_agent/evaluation.py:evaluate_retrieval}}

**代码详解。** 每个查询有独立相关条目集合。Recall@4 的分母是相关条目总数，MRR@4 取首个相关结果名次的倒数，未命中为 0，最后按查询宏平均。当前每条查询只有一个相关条目，所以 Recall@4 等价于 Hit@4，但代码可处理多个相关条目。

内置 8 条样本用于验证评测程序和基础召回，包含明显词面提示，不能代表真实分布或外部泛化。后续需要独立构建同义改写、多意图、未知、否定、矛盾与对抗保留集。调整检索方案时不得不断根据保留集调参数。[评测设计参考](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)

**模型评测表。** 记录任务类别、正确动作、应采集字段、相关证据、禁止行为、实际工具路径和失败原因。来源包含校验是机械指标；引用是否回答问题需要标注或经校准的 judge。LLM-as-judge 要与人工标签对照，不应直接当医学裁判。

**操作与验收。** `uv run tcm evaluate --output evidence/retrieval-eval.json`。修改一个 relevant ID 为不存在值，指标应下降，而不是评测仍然全绿。把新增失败问题加入开发集，另留一组不参与调参的样本。

**面试关联。** Q05：怎么评估 Agent/RAG？Q52：如何建立 golden set？Q53：LLM-as-judge 有什么偏差？

### 第 25 节：指标、脱敏与失败归因

**本节功能。** 在不记录健康正文的前提下，知道系统是否可靠、哪里慢、消耗多少。指标与内容审计应分开管理。

源码：`src/tcm_agent/observability.py`。

{{snippet:src/tcm_agent/observability.py:Metrics.create}}

**代码详解。** 每个应用实例独立 registry，避免测试或 reload 重复注册。回合计数只使用固定集合的 action/status 标签；token 只分 input/output，不能用 user_id、session_id 或患者问题作为指标维度。Histogram 支持时延分布，而平均值会掩盖长尾。

`/metrics` 已受 Bearer 保护，但当前没有单独管理员角色；受控单租户部署可以使用，扩大用户范围前要拆分运维权限。供应商日志仅记录响应状态，不输出请求体、API key、完整 URL 或健康内容。当前没有接好外部 tracing 后端与告警渠道，需在部署环境补齐，不能把指标端点当作“告警已上线”。

**故障归因顺序。** HTTP/认证 → 幂等与版本 → 模型传输 → 模型协议解析 → 工具选择 → 检索 → 来源/事实校验 → 事务提交。记录稳定错误类别和版本标识；保留内容样本必须获得适用授权并限制访问。

**操作与验收。** `uv run pytest tests/test_api.py -k metrics -q`。指标中应没有 session UUID 或健康正文。请求完成后查看 `/metrics` 的回合与耗时变化。将一次失败归到明确阶段，而不是统一称为“模型幻觉”。

**面试关联。** Q54：Agent 线上要观测什么？Q55：如何在保护隐私的同时排查 badcase？

### 第 26 节：性能、容量与费用预算

**本节功能。** 从已有后端经验出发，把模型视作昂贵且不稳定的外部依赖。先测完整链路，再决定并发、缓存和模型路由。

源码：`src/tcm_agent/observability.py`。

{{snippet:src/tcm_agent/observability.py:RateLimiter.check}}

源码：`src/tcm_agent/http_client.py`。

{{snippet:src/tcm_agent/http_client.py:create_client}}

**代码详解。** 连接池复用减少建立连接成本，连接/读/写/池等待分开设置超时。配置中的连接数不是吞吐承诺；单次请求可能多次调用模型，供应商还有 RPM/TPM 配额。当前限流器是进程内按认证身份计数，多个 worker 各有一份；分布式部署应使用共享网关或 Redis 原子限流，不能直接乘 worker 数后仍声称全局限制准确。

估算单回合费用：`输入token×输入单价 + 输出token×输出单价 + embedding费用 + 重试费用`。单价按供应商实际账单单位换算，不能假定输出永远是输入的固定倍数。记录失败前已发生的供应商消耗也很重要；当前失败后降级的 usage 不包含未返回的计费详情，需要账单对账补足。

可以用 Little 定律粗估并发占用 `L≈吞吐λ×平均驻留时间W`，但仍要验证尾延迟与配额。主线没有跨用户答案缓存；个体健康上下文不适合未经权限设计的语义缓存。

**操作与验收。** 将限流设为 1，第二次新请求应 429；重放已经完成的同键请求不应重复扣一次。测量真实供应商时只用合成输入，小批量逐步增加并发并记录失败率。课程不提供未经实测的 QPS 或费用结论。

**面试关联。** Q56：如何降低 token 与时延成本？Q57：怎样处理供应商配额与流量峰值？

### 第 27 节：安全、个人资料控制与删除

**本节功能。** 在代码边界阻止越权操作，提供资料更正、导出和删除。安全设计不是在 System Prompt 末尾添加“请保护隐私”。

源码：`src/tcm_agent/repository.py`。

{{snippet:src/tcm_agent/repository.py:VisitRepository.load}}

{{snippet:src/tcm_agent/repository.py:VisitRepository.delete}}

**代码详解。** 从令牌配置得到 owner，客户端不能提交任意 owner 冒充他人。查询实际包含 owner 条件，而不是先查出内容再依赖模型自觉。不存在和不属于本人都返回 404，减少会话存在性泄露。删除在一个事务内移除快照和操作记录，包括重放中保存的健康资料。

删除数据库记录不等于已清除数据库物理页、快照备份、供应商日志和历史导出。对外服务要有可执行保留政策与备份过期策略。这里演示的是应用数据库的逻辑删除合同。医疗健康敏感信息的真实处理方案应根据实际服务和部署位置另行审核。

Prompt injection 可以影响模型对工具或引文的选择，因此仍需对抗评测；但模型没有任意 SQL、跨用户读取或写事实工具，降低了被诱导后的权限范围。检索资料中的指令只作为数据，不能改变工具集合。[OWASP LLM 风险参考](https://owasp.org/projects/top-10-for-large-language-model-applications)

**操作与验收。** 用两个令牌分别操作同一 session ID，所有读取、提交、导出、删除均应被隔离。执行删除后重放原请求应 404。检查记录导出能把事实的 source_turn_id 回到原始输入。

**面试关联。** Q06：敏感数据 RAG 怎么保护？Q58：如何抵御提示注入？Q59：删除数据有哪些遗漏？

### 第 28 节：部署、迁移、CI 与回滚

**本节功能。** 让另一个人按文档复现安装、验证与运行。部署有先后顺序和状态证据，不是给出一份 YAML 就声称生产可用。

![部署与运行](assets/deployment.png)

源码：`Dockerfile`、`compose.yaml`、`migrations/` 与 `.github/workflows/ci.yml`。

```bash
uv sync --all-extras --frozen
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run basedpyright
uv run pytest
uv run tcm init-db
uv run tcm evaluate
```

**配置详解。** Docker 镜像在构建时同步运行依赖，容器使用非 root 用户。Compose 为 PostgreSQL 配置健康检查，migration 成功后才启动 API。数据库端口不映射到宿主公网。`TCM_DB_PASSWORD` 由本地环境提供；URI 中的特殊字符需要正确编码，不能直接把含 `@`、`/` 的密码拼进连接串后当作正确配置。

```bash
# 在本地 .env 完成应用配置后，使用 URI 安全的随机数据库密码。
export TCM_DB_PASSWORD='自行生成的长随机字母数字值'
docker compose up --build
```

uv.lock 固定 Python 依赖解析结果；基础容器 tag 并非不可变 digest，严格发布应固定经过验证的镜像摘要。CI 会执行项目检查，真实模型测试默认跳过，不把密钥写入仓库。外部平台、容器构建与 PostgreSQL 的实际验证情况见 [验证报告](../evidence/validation.md)。

回滚先确认新旧应用是否兼容当前 schema。对破坏性迁移优先做前向修复或 expand/contract，不在健康资料库上盲目 downgrade。课程没有替你部署公网、购买服务或配置对外通知。

**阶段验收。** 新目录安装后可启动；迁移重复执行安全；检查命令全部通过；没有配置的外部验证明确列为未执行。按报告重放真实 HTTP smoke，确认代码与教程一致。

**面试关联。** Q60：如何发布和回滚 Agent？Q61：怎样证明项目可运行而不夸大？

## 第 29—30 节：集成验收与项目答辩

### 第 29 节：用故障演练检验整个系统

**本节功能。** 从用户结果倒推测试，不按模块数量堆“覆盖率”。下面每一行都必须观察最终状态和可见结果，而不只是断言某个函数被调用。

| 演练 | 操作 | 必须观察到的结果 |
|---|---|---|
| 正常就诊准备 | 描述困扰→确认→导出 | 原文进入摘要，缺失字段不编造 |
| 主动跳过 | 输入跳过或直接取 summary | 已有确认资料可导出，不要求完整问卷 |
| 信息更正 | 新表述→候选→确认同字段 | 新值替代旧值，version 增加 |
| 重复提交 | 同 request_id 与同请求体 | 原样重放，不新增一次状态更新 |
| 键冲突 | 相同键、不同文本 | 409，不混用第一次结果 |
| 并发冲突 | 同 version 两个请求 | 一个提交成功，另一个 409 |
| 模型故障 | 注入供应商失败或超时 | 标记 degraded，只交付已确认信息 |
| 来源伪造 | 引用未检索条目或虚构片段 | 校验失败，不对外生成伪来源 |
| 越权访问 | B 的 token 读取 A 的会话 | 404，模型未获得 A 的内容 |
| 崩溃恢复 | 旧租约过期后重新认领 | 新租约能提交，旧租约被 fenced |
| SSE 断开 | 工作中关闭消费者 | 取消传播，或已提交后可重放 |
| 删除 | 删除会话再重放 | 404，旧正文不从重放记录复活 |

源码：`examples/smoke_api.py`。

{{snippet:examples/smoke_api.py:main}}

**代码详解。** smoke 通过真实 HTTP 服务执行完整业务，不直接调用仓库内部方法。它使用合成输入，并在最后删除本次会话。断言只检查可观察结果：摘要内容、事件类型、重放结果与删除状态。测试环境的公开令牌不可用于真实部署。

**验收命令。** `uv run pytest`、`uv run python examples/smoke_api.py`。把结果保存到 evidence，而不是在简历上凭记忆填写“高可用”。真实平台使用 `tests/test_live.py` 单独验收，不拿 offline 结果代替。

**面试关联。** Q07：讲一个具体困难与解决过程。Q62：一次失败如何做根因分析？

### 第 30 节：形成可审查交付与项目叙事

**本节功能。** 将业务价值、技术取舍、运行证据和剩余限制组织成可以被追问的项目作品。你必须能解释哪些是自己实现、哪些是第三方能力、哪些仅是扩展设计。

**交付检查。** 一个新环境至少能通过 README 找到安装方法、配置变量、运行入口、测试、评测、数据初始化和错误处理。核心源码和课程引用一致；10 张图展示实际结构；原始图源可修改；面试题来源可追溯；未执行项不藏在脚注。

**推荐项目介绍结构。** 先说用户任务，再说约束，再画架构，最后给出验证证据。例如：“我做的是就诊前资料整理助手，模型负责动态追问与知识检索，正式摘要只使用用户确认事实。我解决了重复请求、并发更正、来源伪造和模型故障问题。当前证据来自本地端到端、协议合同与小样本检索评测；真实模型与公开医疗服务上线另行验收。”

这段话可以按实际结果改写，不要添加没有运行过的调用量、准确率、临床审核或用户规模。公开面经也有针对具体实现、添加功能位置和遇到困难的追问，背名词无法替代可复现经历。[公开面经自述](https://api-cdn.nowcoder.com/discuss/800455656703590400?sourceSSR=users)

**最终练习。** 在不看答案的情况下，完成 15 分钟项目讲解、10 分钟架构追问、10 分钟 badcase 定位，再解释为什么暂时不做多 Agent、不加个体处方、不开启跨用户语义缓存。自己动手新增一个只读工具，补 Schema、分发、协议、运行测试和评测样本，确认只改 Prompt 不足以完成这件事。

**毕业标准。** 能从输入一路追踪到工具、证据、状态、事务和响应；能重现失败并定位；能说明指标分母和验证范围；能独立接通自己的兼容平台。完成课程不代表获得诊疗资质或证明临床有效。

**面试关联。** Q08：新增能力要改哪些地方？Q63：如何设计系统扩容？Q64：你的项目最重要的取舍是什么？
