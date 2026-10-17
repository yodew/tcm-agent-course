## 第三周：持久化、并发与服务可靠性

### 工程参考 E15｜将 Agent 接成稳定的 HTTP 服务

**本节功能。** 通过稳定 API 连接认证用户、会话状态和模型运行；业务逻辑在 `Services`，HTTP 路由只解析请求、绑定身份并返回合同。依赖生命周期用 FastAPI lifespan 管理。[官方生命周期文档](https://fastapi.tiangolo.com/advanced/events/)

源码：`src/tcm_agent/api.py`。

{{snippet:src/tcm_agent/api.py:create_app}}

**代码详解。** 引擎、连接池和 HTTP 客户端属于应用生命周期，不是每次工具调用创建。测试可注入 gateway，但真实服务按照显式配置选择模型。空鉴权配置拒绝启动；没有用默认管理员身份兜底。资源通过应用闭包注入，不依赖未类型化的 `app.state` 散落全局。

**操作。** 启动服务后，在另一个终端设置 `TCM_CLIENT_TOKEN` 为同一个本地教学令牌：

```bash
export TCM_CLIENT_TOKEN='local-course-token-change-before-sharing'
uv run python examples/smoke_api.py
```

也可以手动调用：

```bash
curl -s http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer $TCM_CLIENT_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"consent":true}'
```

拿到 session_id 后提交 `request_id`、`expected_version`、`text`。request_id 是客户端为同一次提交生成的 UUID；重试时保留它，新的用户消息生成新 UUID。

**验收。** `/docs` 能展示合同；无令牌 401、他人会话 404、缺少同意 422，错误代码稳定。真实 HTTP smoke 与内存 TestClient 都要跑，前者覆盖启动和网络入口。


### 工程参考 E16｜数据库模型、迁移与持久化状态

**本节功能。** 将会话快照与请求执行记录分开。快照服务于读取当前状态；操作记录服务于幂等、原文溯源和失败恢复。最小部署使用 SQLite；PostgreSQL 使用相同 SQLAlchemy 仓库接口。

源码：`src/tcm_agent/models.py`。

{{snippet:src/tcm_agent/models.py:VisitRow}}

{{snippet:src/tcm_agent/models.py:OperationRow}}

**代码详解。** `VisitRow.version` 贯穿所有修改。`OperationRow` 使用 `(session_id, request_id)` 复合主键，保存请求哈希、原始输入、状态、租约和最终响应。健康正文只在受控数据库中保存，不加入指标标签。`state` 使用序列化合同减少教学项目的表数量，但每次修改整个快照有写放大；规模增长后可以拆分事实表和回合表。

迁移文件固定初始结构，不从未来的 ORM 模型动态推导历史。服务启动不偷偷执行 create_all；先执行 `uv run tcm init-db`。测试初始化辅助函数仅用于隔离数据库。一个 AsyncSession 不应在多个并发任务之间共享。[SQLAlchemy 异步会话文档](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

**操作与验收。** 连续运行两次 `uv run tcm init-db` 都应成功。重启服务后旧会话可读取。检查迁移表版本；未来更改结构必须新增迁移，不能修改已部署的 0001。


### 工程参考 E17｜请求幂等与结果重放

**本节功能。** 对同一用户消息的网络重试返回原结果，而不是重复执行并重复修改状态。请求 ID 不只是日志追踪 ID。

![幂等与事务](assets/transactions.png)

源码：`src/tcm_agent/operations.py`。

{{snippet:src/tcm_agent/operations.py:OperationStore.claim}}

**代码详解。** 第一次请求插入唯一记录；相同键再次插入触发唯一约束，再读取已有状态。请求哈希防止客户端用同一个键提交不同文本。已完成请求重放保存的 `TurnResponse`，包括原 turn ID 和 version，而不是重新计算一个“看起来差不多”的结果。

同键同内容正在执行时返回 409；客户端可以延迟后以相同键重试。已失败请求可以重新认领。幂等重放检查必须先于 expected_version 校验，否则首次请求已将版本加一后，合法重试会被误判为旧版本。

**操作与验收。** `uv run pytest tests/test_api.py -k 'replayed or reused' -q`。逐字段比较首次与重放响应。将同一 request_id 的 text 改掉，应该得到 payload_conflict。若模型供应商已经执行请求但你的进程崩溃，外部请求仍可能重复；不能宣称整个链路 exactly-once。


### 工程参考 E18｜乐观并发、版本 CAS 与丢失更新

**本节功能。** 防止用户在两个页面同时操作，或模型运行期间用户更正事实，导致后完成的请求覆盖新状态。

源码：`src/tcm_agent/repository.py`。

{{snippet:src/tcm_agent/repository.py:VisitRepository.replace}}

**代码详解。** CAS 条件包含 session、owner 和旧 version；只有版本仍匹配才能成功更新。`returning` 判断是否命中，不依赖不同数据库对 rowcount 的细微差异。新状态版本等于旧版本加一。

两个请求读取同一 version=3，在事务外分别计算；提交时一个写到 4，另一个条件不匹配，返回 409。失败请求必须重新读取新状态，由客户端决定是否作为新操作提交，不能在旧模型结果上盲目把 version 改成 4 强行重试。

SQLAlchemy 的 ORM version_id_col 可帮助普通 ORM 更新检测冲突；本项目使用显式条件更新，因此直接维护 CAS 条件，不能误以为配置 ORM 版本计数会自动覆盖所有 bulk update。[官方版本计数说明](https://docs.sqlalchemy.org/en/20/orm/versioning.html)

**操作与验收。** `uv run pytest tests/test_api.py -k 'concurrent or stale' -q`。同版本两次并发提交恰好一个成功，状态版本只增加一。解释为什么进程内 Lock 无法单独保护多进程部署。


### 工程参考 E19｜租约 fencing、崩溃恢复与原子提交

**本节功能。** 已占用请求的进程崩溃后，系统不能永久认为它还在运行；旧工作者恢复后也不能覆盖新的执行结果。

源码：`src/tcm_agent/operations.py`。

{{snippet:src/tcm_agent/operations.py:OperationStore.reclaim}}

{{snippet:src/tcm_agent/operations.py:OperationStore.commit}}

**代码详解。** 超过“总时限+缓冲”的运行记录可以重新认领，但必须通过旧 lease、status、started 的条件更新。新的随机 lease 是 fencing token，不是增加等待时间就获得正确性的魔法。旧工作者提交时租约不匹配，整笔事务回滚。

提交事务先 CAS 修改会话，再核对并更新本次操作记录；两步必须同事务。若租约已失效，即使会话 UPDATE 暂时执行过，也会回滚。删除流程采用兼容的锁顺序，减少数据库死锁。外部模型调用始终在这些短事务之外。

**操作与验收。** 阅读租约测试，分别模拟正常重放、过期重领、旧租约提交、版本冲突。检查失败提交不会留下“状态变了但重放记录没保存”的半成功。不要把一秒钟 sleep 当作崩溃恢复测试的主要证据，应直接构造可控的过期记录。


### 工程参考 E20｜超时、重试、降级与取消

**本节功能。** 模型调用失败时仍可交付已经确认的就诊资料，并清楚标注 degraded。失败不能伪装成模型成功，也不能让网络异常泄露上游响应体。

源码：`src/tcm_agent/service.py`。

{{snippet:src/tcm_agent/service.py:Services.turn}}

**代码详解。** 应用服务读取快照、认领请求、校验版本后，在总时限内运行 Agent。已知供应商故障或超时返回已确认资料摘要；参数、越权、来源错误等 4xx 不降级成成功答案。finally 在短暂屏蔽取消的窗口内释放未完成租约。客户端断线后，任务取消向内传播；若已经提交，之后的相同请求能重放结果。

网关对 429 和部分 5xx 最多重试两次，带有界抖动；连接建立重试由 HTTP transport 处理。总时限防止层层重试放大时延。401、协议参数错误、内容拒绝不能靠重试修好。当前实现未解析供应商 Retry-After 的所有形式，扩展时仍须服从总 deadline。

**操作与验收。** `uv run pytest tests/test_failure.py -q`。核对 degraded 明确标记、无新增事实、状态可读取。进一步练习注入慢模型与取消，检查请求不会永久卡在 running。


### 工程参考 E21｜真实 SSE、背压与断线处理

**本节功能。** 客户端在任务执行期间收到真实阶段事件：accepted、model_step、tool_started、validated，随后收到 committed 和 done。不会把完整文本生成后逐字 sleep 来伪装 token streaming。

![SSE 与取消传播](assets/streaming.png)

源码：`src/tcm_agent/streaming.py`。

{{snippet:src/tcm_agent/streaming.py:stream_turn}}

**代码详解。** AnyIO memory stream 容量是 16，消费者慢会对生产者施加背压。任务组将请求工作绑定到连接生命周期，finally 取消未完成工作。没有往进度事件放工具参数、模型原文或病史正文。最终结果在事务提交后才发送，客户端不应把 accepted 或 progress 当作已保存。

流建立之后，业务失败通过 error 事件呈现，HTTP 状态通常已是 200。客户端必须一直解析到 committed/done 或 error。当前选择工作流事件流，是为了先校验最终内容；上游模型 token 流适配没有实现，不能在面试中说已经做了原生模型逐 token 输出。

**阶段验收。** 运行 `uv run python examples/smoke_api.py`；观察真实事件顺序。慢模型下 accepted 和 progress 应先于完成事件到达。客户端断开连接后请求应取消或已经提交，不能同时出现未保存却宣称成功的最终事件。

