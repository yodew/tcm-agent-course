## 第一周：协议、合同与执行循环

### 工程参考 E01｜把业务目标变成可执行合同

**本节功能。** 把“帮我问诊”拆成采集资料、理解知识、核对事实和准备摘要四种任务。先明确最终输出，才能决定模型需要哪些能力。资深后端开发者容易把 Agent 理解成一个智能服务方法；关键变化是服务内部存在不确定的决策，而外部合同仍须稳定。

本项目的最终决策不是任意文本，而是 `FinalTurn`。问什么、何时检索交给模型选择；输出哪些动作、哪些字段允许存在由类型限制。

源码：`src/tcm_agent/domain.py`。

{{snippet:src/tcm_agent/domain.py:FinalTurn}}

**代码详解。** `action` 是业务动作枚举；`question` 是经过产品审核的问题枚举。`facts` 是候选事实，不是正式病史；`citations` 是待校验引用。列表长度上限限制输出体积。所有字段必填，避免模型把遗漏字段与空列表混淆。`Contract.extra="forbid"` 会拒绝模型额外偷偷添加的 `diagnosis` 或 `prescription` 字段。

**操作与验收。** 阅读 `Action`、`FactField` 和 `QuestionKey`，画出输入到输出的合同。执行 `uv run pytest tests/test_runtime.py -q`。在分支练习中给终态加入一个新动作，先观察类型检查如何要求补齐渲染逻辑，再撤销练习改动。能说明“类型正确”和“业务事实正确”的区别才算通过。


### 工程参考 E02｜亲手分清 Responses 与 Chat Completions

**本节功能。** 通过一个统一的 `Conversation.step()` 使用两种协议，但不混用其请求字段。你所说的“response 格式”需要最终通过供应商协议确认；Responses 常见端点是 `/v1/responses`，Chat 是 `/v1/chat/completions`。

官方工具调用文档展示了 Responses 中 `function_call` 与 `function_call_output` 的关联方式；本项目据此实现兼容适配，但第三方平台是否完整实现仍需实测。[协议依据](https://developers.openai.com/api/docs/guides/function-calling)

![双协议适配](assets/protocols.png)

源码：`src/tcm_agent/gateway.py`。

{{snippet:src/tcm_agent/gateway.py:NativeConversation.step}}

**代码详解。** Responses 的函数描述放在工具对象顶层；Chat 将函数放进 `function` 子对象。Responses 用 `call_id` 回传结果；Chat 用 `role="tool"` 与 `tool_call_id`。同一份 Pydantic Schema 在协议边界转成 JSON。适配器只负责通信，不决定业务是否可信。每次回合构造独立 transcript，避免两个用户共享模型重放状态。

Responses 设置 `store=false` 表示请求不使用该接口的服务端存储能力，**不代表第三方平台已经承诺不记录数据**。平台的数据策略需要单独确认。本地保留会话状态，跨回合不依赖供应商保存的 response ID。

**操作与验收。** `uv run pytest tests/test_gateway.py -q`。检查测试捕获的实际请求体，解释两个协议的差异。故意把 `call_id` 改错，看协议断言失败。真实平台接入执行 `TCM_RUN_LIVE=1 uv run pytest tests/test_live.py -q`，没有平台配置则保留待验收状态。


### 工程参考 E03｜结构化输出与边界解析

**本节功能。** 把供应商的 JSON 变成内部类型，在信任边界拒绝不完整或错误响应。结构化输出解决形状问题，不能证明事实、来源或权限正确。

源码：`src/tcm_agent/wire.py`。

{{snippet:src/tcm_agent/wire.py:parse_responses}}

**代码详解。** `ResponseEnvelope` 对 `output` 和 `usage` 建立合同；非 `completed` 状态不能当成完整答案。函数调用必须带标识和名称。`replay` 保留原始 output 条目，而不是只留下提取出的工具调用；这样推理型模型所需的 reasoning 等条目不会在下一轮丢失。它们只是供应商协议数据，不是我们能解释或展示的思维链。

应用合同拒绝多余字段，供应商 envelope 则允许协议添加非关键字段：前者保护业务，后者避免因供应商新增元数据而无意义失败。要理解为什么这两个边界采用不同策略。

**操作与验收。** 运行 `uv run pytest tests/test_gateway.py -k 'parse or native_protocol' -q`。准备三个输入：没有 output、status=incomplete、带 reasoning 与 function_call。前两个应失败，第三个保留重放条目。不要用补右括号来“修复”截断后的参数。


### 工程参考 E04｜设计工具，而不是给模型一个万能函数

**本节功能。** 提供三个职责明确的工具：检索公共知识、读本会话确认事实、提交本回合终态。工具没有 `owner`、SQL、文件路径、密钥或通用 HTTP URL 参数，模型无法通过工具参数扩大访问范围。

源码：`src/tcm_agent/tool_schema.py`。

{{snippet:src/tcm_agent/domain.py:SearchArgs}}

{{snippet:src/tcm_agent/domain.py:ToolCall}}

**代码详解。** `query` 长度在边界限制。`ToolCall.arguments` 仍是字符串，因为协议中的工具参数就是序列化 JSON；执行前必须用具体工具参数类型解析，不能直接 `eval`。`call_id` 用于结果关联，不等于业务幂等键。模型可能给出不同 call ID 的重复语义调用，所以还需要步数和任务层预算。

工具描述是模型的操作说明书。描述应说明输入含义、返回信息和限制，不应该用“这是一个超级强大的万能助手”替代合同。新增写工具前先定义授权、校验和幂等策略。

**操作与验收。** 阅读 `TOOLS` 注册表，运行 `uv run pytest tests/test_runtime.py -k 'unknown or arguments' -q`。在练习中尝试构造 `delete_all_patients` 调用，应该被执行器拒绝，且不会触达仓库。讨论如果将来新增预约接口，为什么不能只添一条 Prompt。


### 工程参考 E05｜实现可终止、可调试的 Agent Loop

**本节功能。** 模型根据观察决定下一步，执行器循环校验与调用工具。这里有真实的模型决策接口，offline 路径只是确定性夹具。ReAct 的核心启发是让决策和环境反馈交替发生；工程系统不需要索取或记录私有思维链。[ReAct 论文](https://arxiv.org/abs/2210.03629)

![执行循环](assets/agent-loop.png)

源码：`src/tcm_agent/runtime.py`。这是主线最重要的一段代码，建议完整阅读。

{{snippet:src/tcm_agent/runtime.py:AgentRuntime.run}}

**代码详解。** 执行顺序是：前置策略 → 上下文 → 模型决策 → 单调用限制 → call ID 去重 → 参数解析 → 工具观察/终态校验。每轮检索返回的证据登记到 `retrieved`，最终引用只能使用本轮见过的条目。`submit_turn` 结束循环，其它普通文本不直接发给用户。没有工具调用、一次多个调用、重复标识、未知工具、超预算都具有明确失败结果。

最大步数限制只控制循环次数。总时间由应用服务约束，单次输出 token 由网关约束，输入体积另有预算。这些限制共同工作，不能用一个 recursion_limit 代替全部运行控制。

**操作与验收。** `uv run tcm run --text '什么是四诊？'`，观察 `steps=2`、引用和零 token 的 offline 标记。执行 `uv run pytest tests/test_runtime.py -q`，再阅读实际模型运行入口。能逐步解释一次 search→observation→submit 才算通过。


### 工程参考 E06｜上下文工程与记忆预算

**本节功能。** 将确认事实与当前输入视为必需信息，把最近对话视为可裁剪信息。不是把数据库所有历史拼成一个越来越大的字符串。

源码：`src/tcm_agent/context.py`。

{{snippet:src/tcm_agent/context.py:ContextBuilder.build}}

**代码详解。** 当前输入始终位于最后。确认事实独立标记为数据，不依赖模型从旧助手回复里重新推断。历史从新到旧填入剩余额度；必需内容放不下就明确报错，不静默删除用户已确认资料。本实现按字符做可移植预算，网关还按请求字节限制体积；二者都不是精确 token 计数。生产接入应使用目标模型的 tokenizer 或供应商计数能力测量安全余量。

保留更多历史不一定更准确：会引入过时事实、错误回复和更多无关信息。摘要也可能丢失否定、时间与药名。事实存储与对话压缩必须分别设计。

**操作与验收。** 阅读 `apply_turn` 对历史最多保留 12 条消息的实现。构造长度超限的必要事实，验证系统拒绝，而不是悄悄遗忘。解释为什么完整原始回合仍可在 records 导出，而不必每次都发送给模型。


### 工程参考 E07｜业务策略、模型自由度与确定性输出

**本节功能。** 使用代码决定可对外呈现的内容。模型选择动作、问题字段和证据片段；最终答案由固定问题、核对后的资料和精确引文组成。这样仍有 Agent 的动态决策，同时缩小健康场景中自由生成的风险。

源码：`src/tcm_agent/policy.py`。

{{snippet:src/tcm_agent/policy.py:validate_final}}

{{snippet:src/tcm_agent/policy.py:render_answer}}

**代码详解。** 候选事实必须是当前用户输入的原文片段；同一字段不能重复。非追问动作不能再携带追问字段。摘要走确定性代码。知识回答只展示已经核对出处的引文；来源不足时给出有限回答。这个设计不能证明引文相关、条目医学正确或模型对字段归类正确，后续仍要用评测和用户确认弥补。

`needs_handoff` 的关键词集合只是保守的工程演示，不是医学分诊模型。它可能误报，也可能漏报。项目不以此声称识别全部急症；所有输出都不提供个体诊疗方案。

**阶段验收。** `uv run pytest tests/test_runtime.py tests/test_api.py -q`。越权工具、虚构事实、未经检索的引用必须拒绝。未确认事实不能进入摘要。已知风险触发走 handoff，且不调用模型。

