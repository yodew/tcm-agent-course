# 课程 v1.2 学习路径迁移

本版由项目实现顺序改为 Agent 学习顺序。应用主线和 Chainlit 继续保留；新增六组离线机制实验与真正的 LangGraph 审批暂停/恢复示例。没有生成 PDF。

## 从旧工程模块找到新版位置

| 旧模块 | 新版学习位置 |
|---|---|
| E01、E07 业务合同与策略 | 03 结构化输出、21 需求与系统 |
| E02、E03 双协议与边界解析 | 06 工具往返；细节查工程参考 |
| E04、E05 工具与 Runtime | 07 工具、08 执行循环 |
| E06 上下文 | 11 上下文、12 记忆 |
| E08、E09 来源与分块 | 13 RAG 全链路 |
| E10—E13 检索、向量、融合与引用 | 14 检索、15 评测、22 知识链路 |
| E14 确认与摘要 | 12 记忆、23 事实生命周期 |
| E15、E16 API 与持久化 | 25 服务与存储 |
| E17—E19 幂等、CAS、租约 | 26 并发与提交 |
| E20、E21 恢复与 SSE | 27 失败与流式合同 |
| E22 MCP | 19 工具连接协议 |
| E23 LangGraph | 17 状态与人审、18 框架比较 |
| E24—E26 评测、观测与容量 | 15 基础指标、29 治理 |
| E27 安全与数据 | 28 权限、注入与生命周期 |
| E28—E30 交付、故障、答辩 | 30 生产准备与验收 |
| 原 Chainlit 补充章节 | 24 完整界面链路 |

全部工程源码解读保留在 [ENGINEERING_REFERENCE.md](ENGINEERING_REFERENCE.md)。E 编号只用于查阅模块，新的学习顺序以 [COURSE.md](COURSE.md) 的 01—30 为准。

新增或重新系统展开的知识包括：模型推理与能力边界、Token/采样、Agent 定义、架构辨析、计划与反思、状态图和人审恢复，以及先做机制实验再映射到完整项目的方法。

## 面试题编号迁移

题意与来源归类保留，按基础原理、设计取舍、项目追问、生产排障重排。每题补充原理解释、实现/边界证据与常见错误；旧题使用 legacy-q 锚点供新版正文稳定引用。旧版文档的直接 q 编号需按下表查找。

| 旧题号 | 新题号 | 题目 |
|---|---|---|
| Q01 | [Q36](COURSE.md#q36) | 请用业务结果介绍这个 Agent 项目 |
| Q02 | [Q37](COURSE.md#q37) | 一个 Agent 接口怎样分层，各层负责什么？ |
| Q03 | [Q38](COURSE.md#q38) | 如何把模型 API、RAG 和 MCP 组合成 Agent？ |
| Q04 | [Q39](COURSE.md#q39) | MCP 工具从发现到执行经过哪些阶段？ |
| Q05 | [Q40](COURSE.md#q40) | 生成式 Agent/RAG 如何评价效果，能用一个准确率吗？ |
| Q06 | [Q41](COURSE.md#q41) | RAG 涉及敏感资料时，具体怎样防泄露？ |
| Q07 | [Q42](COURSE.md#q42) | 讲一个项目中的具体技术困难和解决过程 |
| Q08 | [Q43](COURSE.md#q43) | 给这个 Agent 新增一个功能，代码要改哪里？ |
| Q09 | [Q21](COURSE.md#q21) | 哪些逻辑放在编排器，哪些交给模型？ |
| Q10 | [Q06](COURSE.md#q06) | 平台说兼容 OpenAI，为什么项目仍可能接不通？ |
| Q11 | [Q07](COURSE.md#q07) | 工具调用从模型输出到应用完成的完整链路是什么？ |
| Q12 | [Q05](COURSE.md#q05) | JSON Mode、严格 Schema 与业务校验分别解决什么？ |
| Q13 | [Q03](COURSE.md#q03) | temperature=0 是否保证相同答案和稳定格式？ |
| Q14 | [Q23](COURSE.md#q23) | 模型选错工具、传错参数，优先改什么？ |
| Q15 | [Q08](COURSE.md#q08) | Function Calling 能保证工具执行安全吗？ |
| Q16 | [Q24](COURSE.md#q24) | 如何终止无限规划或反复调用工具？ |
| Q17 | [Q22](COURSE.md#q22) | 什么时候应该用固定工作流而不是 Agent？ |
| Q18 | [Q09](COURSE.md#q09) | 短期上下文与长期记忆怎么划分？ |
| Q19 | [Q10](COURSE.md#q10) | 长上下文为什么会退化，如何处理？ |
| Q20 | [Q44](COURSE.md#q44) | 如何减少健康助手中的幻觉？ |
| Q21 | [Q45](COURSE.md#q45) | 为什么不能让模型自己管理权限？ |
| Q22 | [Q46](COURSE.md#q46) | 如何保证 RAG 的输入资料质量？ |
| Q23 | [Q47](COURSE.md#q47) | 私有资料如何做检索权限过滤？ |
| Q24 | [Q48](COURSE.md#q48) | chunk 大小和 overlap 应如何确定？ |
| Q25 | [Q49](COURSE.md#q49) | 分块后如何保留文档级单位或适用条件？ |
| Q26 | [Q11](COURSE.md#q11) | BM25 与向量检索分别擅长什么？ |
| Q27 | [Q12](COURSE.md#q12) | BM25 的主要组成和长度归一化有什么作用？ |
| Q28 | [Q13](COURSE.md#q13) | 如何选 Embedding 模型并安全迁移？ |
| Q29 | [Q14](COURSE.md#q14) | HNSW 和当前精确扫描有什么区别？ |
| Q30 | [Q15](COURSE.md#q15) | 混合检索为什么常用 RRF 而不是分数直接相加？ |
| Q31 | [Q16](COURSE.md#q16) | 为什么已有向量召回还要 reranker？ |
| Q32 | [Q17](COURSE.md#q17) | 回答带引用就能证明它正确吗？ |
| Q33 | [Q50](COURSE.md#q50) | 检索看似相关但答案不对，如何排查？ |
| Q34 | [Q29](COURSE.md#q29) | Human-in-the-loop 应放在什么位置？ |
| Q35 | [Q30](COURSE.md#q30) | 怎样防止长期记忆被错误回复或旧事实污染？ |
| Q36 | [Q58](COURSE.md#q58) | 认证成功以后，为什么还需要授权过滤？ |
| Q37 | [Q51](COURSE.md#q51) | 为什么同时保存当前快照和回合记录？ |
| Q38 | [Q59](COURSE.md#q59) | 为什么不在数据库事务内等待模型？ |
| Q39 | [Q52](COURSE.md#q52) | call ID、turn ID 和 request ID 为什么不能合并？ |
| Q40 | [Q60](COURSE.md#q60) | 幂等结果重放是否等于 exactly-once 执行？ |
| Q41 | [Q61](COURSE.md#q61) | 两个并发回合同时修改一个会话怎么办？ |
| Q42 | [Q62](COURSE.md#q62) | 为什么不用一个 Python Lock 解决所有竞争？ |
| Q43 | [Q63](COURSE.md#q63) | 租约已经过期，为什么旧工作者仍然危险？ |
| Q44 | [Q64](COURSE.md#q64) | 状态已保存但响应记录没保存，会发生什么？ |
| Q45 | [Q65](COURSE.md#q65) | LLM 请求如何设置超时和重试，避免重试风暴？ |
| Q46 | [Q66](COURSE.md#q66) | 供应商不可用时怎样降级，不伤害用户信任？ |
| Q47 | [Q67](COURSE.md#q67) | SSE 进度与模型 token 流是什么关系？ |
| Q48 | [Q68](COURSE.md#q68) | 用户关闭页面后任务应该取消还是继续？ |
| Q49 | [Q19](COURSE.md#q19) | MCP 和 Function Calling 如何分工？ |
| Q50 | [Q31](COURSE.md#q31) | 什么时候选择 LangGraph，checkpoint 能解决什么？ |
| Q51 | [Q32](COURSE.md#q32) | 为什么不拆成问诊、检索、诊断、审核多个 Agent？ |
| Q52 | [Q69](COURSE.md#q69) | 如何建立 golden set，避免评测泄漏？ |
| Q53 | [Q70](COURSE.md#q70) | 如何使用 LLM-as-judge，避免自己骗自己？ |
| Q54 | [Q71](COURSE.md#q71) | Agent 在线观测要记录哪些指标？ |
| Q55 | [Q72](COURSE.md#q72) | 不记录患者正文，怎么定位 badcase？ |
| Q56 | [Q73](COURSE.md#q73) | 如何降低 Agent 成本和延迟？ |
| Q57 | [Q74](COURSE.md#q74) | 流量峰值如何避免压垮模型供应商？ |
| Q58 | [Q75](COURSE.md#q75) | 如何防范用户或检索资料中的 Prompt Injection？ |
| Q59 | [Q76](COURSE.md#q76) | 用户要求删除会话时，哪些数据容易漏掉？ |
| Q60 | [Q77](COURSE.md#q77) | 怎样发布、灰度和回滚一个 Agent？ |
| Q61 | [Q53](COURSE.md#q53) | 你怎样证明这个项目能运行？ |
| Q62 | [Q54](COURSE.md#q54) | 如果用户说摘要写错了，你怎么定位？ |
| Q63 | [Q78](COURSE.md#q78) | 如果要扩展到更多用户和大知识库，先改什么？ |
| Q64 | [Q55](COURSE.md#q55) | 这个项目最值得保留的取舍，以及最大的不足是什么？ |
| Q65 | [Q01](COURSE.md#q01) | Transformer 自注意力为什么适合语言模型？ |
| Q66 | [Q02](COURSE.md#q02) | Token、上下文窗口、prefill、decode 和 KV cache 有什么关系？ |
| Q67 | [Q04](COURSE.md#q04) | Prompt 工程、上下文工程与 Agent Harness 如何区分？ |
| Q68 | [Q25](COURSE.md#q25) | ReAct、Plan-and-Execute 和反思机制如何选？ |
| Q69 | [Q26](COURSE.md#q26) | 何时选 RAG、Prompt、SFT/LoRA 或更大模型？ |
| Q70 | [Q20](COURSE.md#q20) | Skills、工具、MCP 和记忆分别是什么？ |
| Q71 | [Q27](COURSE.md#q27) | 为什么多步骤和多 Agent 的整体可靠性可能下降？ |
| Q72 | [Q18](COURSE.md#q18) | Recall@k、Precision@k、MRR 与 nDCG 怎么算？ |
| Q73 | [Q28](COURSE.md#q28) | 什么时候允许模型并行调用工具？ |
| Q74 | [Q79](COURSE.md#q79) | Python 异步、GIL 与数据库会话有哪些常见坑？ |
| Q75 | [Q33](COURSE.md#q33) | 模型选型怎样同时比较质量、时延与费用？ |
| Q76 | [Q34](COURSE.md#q34) | RAG 和 Agent 缓存怎样设计才不会串数据？ |
| Q77 | [Q35](COURSE.md#q35) | 何时需要 query rewrite、多跳检索或 GraphRAG？ |
| Q78 | [Q56](COURSE.md#q56) | 如果加舌象或报告 OCR，工程上需要补哪些环节？ |
| Q79 | [Q80](COURSE.md#q80) | 安全评测中，拒答和未知问题怎样计分？ |
| Q80 | [Q57](COURSE.md#q57) | 如何把这个项目讲成可信的高级工程师作品？ |