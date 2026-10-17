# 六组 Agent 机制实验

先在仓库根目录同步依赖，再使用模块方式执行：

```bash
uv sync --frozen
uv run python -m labs.run_all
uv run pytest tests/test_labs.py -q
```

实验只验证指定机制，不向模型平台发请求，也不读取平台密钥。完整项目的真实模型接入、API 和 Chainlit 仍按 [README](../README.md) 配置。这里的小实验不取代完整项目，也不能作为真实 LLM 效果证据。

| 实验 | 主课程节点 | 单独执行 | 应观察到什么 |
|---|---|---|---|
| 概率与请求输入 | 01—03 | `uv run python -m labs.model_mechanics` | 温度改变固定 logits 的分布；四诊为 2 字符、6 字节，Token 未知；未传历史就没有历史 |
| 工具执行循环 | 04、06—10 | `uv run python -m labs.tool_loop` | 固定 call-1 被实际词表工具执行，观察保留调用编号，然后终止 |
| 上下文与事实 | 11—12 | `uv run python -m labs.context_memory` | 候选不自动确认；显式确认推进版本；按字符预算保留必需信息和最近历史 |
| 检索与融合 | 13—14 | `uv run python -m labs.retrieval` | 手工垂直向量余弦为 0，RRF 将 B 排第一，真实 BM25 命中课程“四诊”条目 |
| 工作流与计划 | 09、16—20 | `uv run python -m labs.workflows` | 固定依赖按 retrieve→explain→review 排序，不声称使用模型规划或多 Agent |
| 指标与任务判分 | 15、29 | `uv run python -m labs.evaluation` | Recall、Precision、RR 分别计算；答案正确但越权的任务仍失败 |

## 建议的改错实验

1. 把温度设为 0：数学函数拒绝，不冒充供应商的 greedy 实现。
2. 把工具名改为 shell、给参数加 owner、重复 call_id，或把预算设为 1：应分别在受控边界失败。
3. 用旧版本确认事实，或确认原文中不存在的句子：都应拒绝。
4. 给余弦输入不同维度、给排名融合重复 ID：应明确报错，不静默截断或重复加分。
5. 让两个任务互相依赖：执行前应识别环。
6. 保持第一个命中文档位置不变、移走另一个相关文档：比较 Recall 与 RR，避免把指标当同义词。

测试不会把错误输入“修复”为成功。命令默认展示正常路径；错误路径使用 `tests/test_labs.py` 重现，阅读 Given/When/Then 后再改动。

## 与真实系统的衔接

- 模型输入与概率：学习概念，不加载模型、不训练 Transformer，不宣称算出了平台 Token。
- 工具循环：决策明确来自 ScriptedDecisions；可测试执行器，不能测试模型选工具的能力。真实 Responses/Chat 适配在 `src/tcm_agent/gateway.py`，供应商连通与行为另行验收。
- Embedding：手工向量只演示几何；真实向量入口是 `src/tcm_agent/embeddings.py`，没有配置就不运行语义模型。
- 人工介入：`uv run --extra graph python examples/checkpoint_approval.py` 真正运行 LangGraph 的暂停与恢复，但检查点在内存中，不耐进程重启，也不执行外部写操作。
- MCP：`uv run --extra mcp python examples/mcp_client.py` 真正初始化 stdio 会话、发现并调用工具。主服务仍可直接调用进程内检索。

完整实现与边界见 [工程源码参考](../course/ENGINEERING_REFERENCE.md)，学习顺序见 [主课程](../course/COURSE.md)。

## 进阶：真实执行轨迹、对比与恢复

```bash
uv run python -m labs.trace_demo
uv run python -m labs.benchmark
uv run python -m labs.crash_recovery
```

trace_demo 对实际 AgentRuntime 运行 7 条成功/失败轨迹；决策为固定夹具，记录器只保留工具白名单、步骤、错误码和用量，不保留模型正文与参数。benchmark 使用 40 条带理由的合成题，比较关键词、固定 BM25 和离线策略的证据选择；真实模型必须显式指定 `--live` 且设置 `TCM_RUN_LIVE=1`，可用 `--limit 5` 先试跑。live 报告只写 tmp/，不默认公开。

crash_recovery 使用真正退出的子进程和临时 SQLite，控制租约时间而非等待；它不读取本地数据库配置。不能把 SQLite 子进程验证当作断电或 PostgreSQL 容灾验证。详情见 [核心机制深讲](../course/COURSE.md#核心机制深讲与故障工作坊)、[独立练习](../exercises/README.md)、[生产演练](../course/OPERATIONS_LAB.md)。
