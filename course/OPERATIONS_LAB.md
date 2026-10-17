# 生产演练手册：以证据说明可交付范围

这份手册先完成当前环境能复现的验证，再为外部环境留下明确验收入口。当前实现不是公开医疗服务上线方案，教学资料和风险关键词也未经临床审核。只使用合成输入和专用数据库。

## 本机已经可以完成的故障实验

```bash
uv run python -m labs.crash_recovery
uv run pytest tests/test_crash_recovery.py tests/test_operations.py -q
uv run pytest tests/test_cancellation.py tests/test_failure.py -q
uv run pytest tests/test_api.py -k 'concurrent or replayed or stale' -q
```

第一条创建全新临时数据库，实际子进程在认领成功后突然退出。到期前拒绝重复认领、控制到期后的重新认领、旧工作者提交回滚、新结果提交和重放都经真实 SQLite 执行。旧工作者提交由父进程模拟；租约时钟通过更新 started 控制，没有伪称进行了真实等待。[结果](../evidence/crash-recovery.json)。

取消与故障测试针对真实 SQLite 和任务取消，供应商失败来自受控夹具。不要把“取消了本地任务”解释为“供应商没有继续运行或计费”。提交后断线应保留原 request_id/body，并查询或重放结果。只有明确的版本拒绝才按最新状态重建操作。

## 环境能力表

| 能力 | 本次状态 | 能说明什么 |
|---|---|---|
| SQLite 真实子进程退出恢复 | 已执行 | 持久认领、回滚与 fencing 合同 |
| 同版本并发、取消和降级 | 已执行 | 当前服务的行为边界 |
| 本机 HTTP 并发探测 | 见 load-probe.json 的实际环境与样本数 | 仅本机 offline 模式，不代表真实模型容量 |
| 真实兼容模型 | 尚未配置 | 协议测试不替代真实平台验收 |
| PostgreSQL | 当前无可用服务/客户端 | 配置与专用合同测试入口存在，未宣称成功 |
| Docker/Compose | 当前无可执行程序 | 文件存在不代表镜像可构建或启动 |
| 跨主机故障、多副本、长期 SLO | 未执行 | 本机小样本不外推生产稳定性 |

## 真实模型验收矩阵

按 README 配置自己的第三方平台。密钥只存本地忽略文件；不要把认证头、完整错误响应或患者输入放进工单。

| 阶段 | 验收行为 | 成功证据 | 不可混淆的情况 |
|---|---|---|---|
| 配置 | doctor 检查模式、模型和凭据存在 | 只打印安全元数据 | 配置存在不代表连通 |
| 工具协议 | tests/test_live.py | 真实检索→工具观察→带来源终态 | Chat 支持不等于 Responses 支持 |
| 小批试跑 | benchmark --live --limit 5 | mode、逐题错误码和用量 | 顺序前 5 题不是均衡效果集 |
| 全集 | benchmark --live --limit 40 | 保留所有失败、数据/语料哈希 | 题库有限且未经独立盲审 |
| 故障合同 | tests/test_gateway.py 等 | 截断、错误参数、错误关联等 wire 验证 | HTTP 夹具不是平台实际故障 |
| 平台故障演练 | 在专用网关限流/断链、受控超时 | 尝试数、总 deadline、错误类型、费用记录 | 本课程未对真实供应商执行故障注入 |

```bash
uv run tcm doctor
TCM_RUN_LIVE=1 uv run pytest tests/test_live.py -m live -q
TCM_RUN_LIVE=1 uv run python -m labs.benchmark --live --limit 5
```

live 报告只写 tmp/，不默认发布。记录器不保存 Prompt、工具参数、原始响应或私有推理；decision 次数不是 HTTP 重试次数，Token 也不能替代平台账单。若需要货币成本，使用实际合同的输入、缓存、输出价格与账单核对，不能拿离线零用量估计。

## 容器与 PostgreSQL 验收

在具备 Docker 的专用环境，按 README 配置本地 .env 与随机数据库密码后执行 `docker compose up --build`。先保存镜像构建和迁移退出码，再验证健康、创建会话、提交、确认、更正、导出、删除、原请求重放。构建失败就记录失败，不能只看容器名存在。

专用 PostgreSQL 合同测试：

```bash
TCM_TEST_DATABASE_URL='postgresql+asyncpg://user:password@localhost/test_db' \
  uv run pytest tests/test_postgres.py -m postgres -q
```

这是公开占位连接串，不是真实凭据。测试会创建独立随机 schema 后清理，仍应使用专用测试库。当前 PostgreSQL 测试范围以 tests/test_postgres.py 为准，不能自动升级为“覆盖 SQLite 全部路径”。扩展时补并发提交、旧租约、取消、删除与回放，核对真实事务隔离及连接池行为。

## 本机并发探测怎么读

[探测脚本](../examples/load_probe.py)只接受回环地址，创建全新临时 SQLite 和应用进程，生成临时令牌；不读取开发者数据库与平台密钥。并发请求各用独立会话，避免把业务版本冲突和容量混在一个统计里。结果包括成功/失败、p50/p95、样本数、并发数和 elapsed，总计请求量明确。

```bash
uv run python examples/load_probe.py
```

默认 24 次请求、并发 4，只是快速压力探测。不能从一次低延迟推算线上 QPS；offline 无远端模型等待，运行时间短，也没有持续增长和突发流量。下一步应分别测试同会话竞争、模型延迟、取消、客户端慢读和限流。限流是进程内计数，多副本前必须有共享配额或网关策略。

## 发布与回滚演练

1. 保存版本、依赖锁、迁移号、语料哈希、合成验收输入与输出；检查源码包没有 .env、数据库、原始追踪或 PDF。
2. 在独立目录安装源码包，执行迁移、CLI、实验和测试。包里的证据应写明适用范围，不把历史浏览器记录改成今日新验收。
3. 在专用数据库备份后演练升级失败。代码回滚前判断 schema 是否向后兼容；不要在真实健康数据上盲目 downgrade。
4. 恢复旧版本时保留幂等结果与身份规则，避免回滚造成重复提交；索引、语料和模型配置也要成套回滚。
5. 发布后按错误类型、降级率、延迟和任务成功率观察；告警阈值需要流量与业务目标，不能用课程单机 p95 直接设 SLO。

本手册的完成标准是“命令、环境、预期、实际、证据和限制都可核对”。未具备的外部环境保留为待执行，不用配置文件或截图替代。
