# 独立练习：从验收条件写出实现

对应主课程 11、12、15、26 节，以及深讲 W2—W4。先阅读合同，再实现 [starter.py](starter.py)，最后才看 [solution.py](solution.py)。四个函数均没有网络或数据库副作用；这是机制练习，完整工程继续使用主项目。

```bash
uv sync --all-extras --frozen
TCM_EXERCISE=starter uv run pytest exercises/acceptance.py -q
TCM_EXERCISE=solution uv run pytest exercises/acceptance.py -q
```

starter 的首次失败是预期学习起点；它故意抛出 pending 错误。异常路径题有些会先通过，因此不能只数绿点；必须所有验收通过并能解释。常规 `uv run pytest` 只运行 tests/，不会收集未完成作业。参考答案的独立验收为 16 项。禁止修改验收测试来迎合错误实现；可以补充反例。

## 练习 1：上下文选择

输入：必需字符串元组、按旧到新排列的历史、字符总预算。输出：全部必需内容加连续的最近历史，保持原顺序。必要内容超限抛 DataContractError；最新历史放不下时停止，不可跳过它加入更旧消息。

先写三个表格例子：全部正好放下、仅必要内容放下、最新过长。提示：先扣除必需体积，再倒序遍历历史；不要反转最终会话。

<details><summary>答案与考点</summary>

参考 select_context：减去必要字符数，检查负值；使用剩余额度选择连续后缀。元组新建避免修改输入。这里不计角色/分隔符，也不做 Token 化。常见错法是把必要内容一起裁掉、打乱时序，或继续跳过过长的新消息。项目 ContextBuilder 有更完整的消息组织。

</details>

## 练习 2：确认绑定版本与原文

输入：当前版本、(审批版本, 引文)、原文。输出：逐字返回合法引文。旧版本、空引文、不存在于原文的引文均抛 DataContractError。不要做同义改写或删除否定词。

提示：把“未提供”变成“无”是语义变化。此函数不负责分类、账户授权或持久保存。

<details><summary>答案与考点</summary>

参考 confirm_quote：同时检查版本一致、引文非空、原文包含。返回原始引文即可。这只证明来源字符串和当前审批一致，不能保证字段语义正确。完整确认还需受认证身份、来源回合和数据库版本约束。错误答案往往仅做 contains，遗漏旧审批；或者用 replace 去掉否定词。

</details>

## 练习 3：计算 RR@k

输入：唯一的排名 ID、非空相关集合、正整数 k。第一个命中在位置 r 时返回 1/r，前 k 无命中返回 0。重复排名、空标签、k≤0 抛 DataContractError。

提示：排名从 1 开始；只在前 k 中找第一个命中。自己手算 wrong,B,A 与相关集 {A,B} 的 RR、Recall、Precision。

<details><summary>答案与考点</summary>

参考 reciprocal_rank：先检查合同，再对 ranking[:k] 从 1 枚举。示例 k=3 时 RR=.5、Recall=1、Precision=2/3。把 A 移出前三可降低 Recall 而不改变 RR。这里不允许空相关集合；未知问题要用单独的拒答指标，不能让零分母自动得到满分。

</details>

## 练习 4：重试是否仍是原操作

输入：原 (request_id, body_hash) 与重试二元组。只有 ID、哈希都非空且分别相同才返回 True，其余 False。相同 ID 换正文、相同正文换 ID 都不能直接当作原请求重放。

<details><summary>答案与考点</summary>

参考 retry_identity：先检查原身份非空，再比较整个二元组。它只判断身份，不授权执行，不代表租约已到期，也不代表结果已提交。完整 OperationStore 还会检查状态、会话版本和租约；业务结果幂等不能阻止供应商在崩溃恢复时再次收费。

</details>

## 提交作业时应附什么

四段实现、16 项验收结果、每题一个新增反例，以及“此函数没有保证什么”的说明。若只贴参考代码而不能解释反例，不算完成。下一步是 [核心机制深讲](../course/COURSE.md#核心机制深讲与故障工作坊) 与 [生产演练](../course/OPERATIONS_LAB.md)。
