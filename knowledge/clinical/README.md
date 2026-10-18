# 问诊、诊断与辨证研究知识库 v0.2

整理日期：2026-10-18。本库为新版多模态辅助问诊方向提供结构化资料、可持久化的全文索引和只读 Agent 工具。当前运行的问诊准备服务仍使用原有教学知识；本包没有接入患者诊断流程，没有把模型改成可独立确诊的系统。

已经实际完成采集与整理，而非待办目录：

| 内容 | 数量 | 当前用途 |
|---|---:|---|
| 来源登记 | 6 | 记录出处、版本、许可、用途与局限 |
| 原创问诊条目 | 63 | 展示问题、采集字段、原因、前置问题与场景 |
| 来源术语 | 845 | 病名、证名、观察、病位和病性分别保留 |
| 描述性观察—证候关联 | 769 | 原始训练分片中的共现；不是诊断条件 |
| 候选证候资料卡 | 294 | 汇总来源记录数和关联观察；不计算患者诊断 |
| 文献参考卡 | 3 | 睡眠相关历史综述中的部分表现与重叠限制 |

**稀疏性：267 张候选卡只涉及一条训练记录，40 张没有保留下来的观察特征，只能作为来源标签资料。这些数量不能作为诊断依据充分性的证明。**

数量由 [实际审计](../../evidence/clinical-knowledge-audit.json) 生成。200 条 TCMEval 训练记录可以包含多个证候标签，因此候选证候数可以大于病例数；不能把每个标签当作一个独立患者。术语也有跨来源重复标签合并，合并只针对同一种类的完全相同文本，不自动进行繁简转换或医学同义归并。

## 已转成可实际调用的知识库

结构化 JSON 是可追溯的源数据；现在已有独立的转换、索引、检索和引用回查链路，不再只是资料目录。共生成 **1,205 份检索文档**：63 份问诊、845 份术语、294 份语料共现卡、3 份文献参考。769 条共现关系收在对应证候卡里，保留来源记录计数，没有作为 769 个独立医学依据重复检索。

| 层次 | 已实现内容 |
|---|---|
| 源数据 | 严格合同、固定来源版本、许可和引用定位 |
| 文档转换 | 稳定文档 ID；每份文档附证据类型、来源、许可和局限 |
| 检索索引 | 本地 SQLite FTS5 + BM25；中文双字词、单字回退，标题加权 |
| 检索接口 | 分类过滤、最多 20 条结果、文档 ID 精确回查 |
| Agent 工具 | MCP 的 search_clinical_references、get_clinical_document |
| 更新保护 | 文档内容和来源元数据指纹；变更后拒绝使用旧索引，原子重建 |
| 可移植输出 | JSONL 文档及指纹，供后续接入嵌入模型和向量库 |

```mermaid
flowchart LR
    A[固定版本公开来源] --> B[许可登记与字段投影]
    B --> C[结构化 JSON 与引用定位]
    C --> D[1205 份自带来源及局限的检索文档]
    D --> E[SQLite FTS5 持久索引]
    D --> F[JSONL 可移植文档]
    G[Agent 检索请求] --> H[MCP 只读工具]
    H --> E
    E --> I[分类结果与稳定文档 ID]
    I --> J[原始 URL 版本 许可 定位]
```

**可检索不等于已获得临床诊断资格。** 每条返回结果保留 clinical_use=disabled；这表示资料尚未完成临床验证，而不是关闭检索。BM25 relevance 只表示文字匹配程度，不是诊断概率。`corpus_association` 是病例标签共现，`literature_reference` 是历史文献参考，两者不会自动升级为诊断标准。

知识库已经可以由支持 MCP 的 Agent 调用。当前主服务的问诊准备流程仍使用原有工具注册表；本次没有声称已将其升级为诊断 Agent，也未完成 DeepSeek 或面舌脉诊 API 接入。

## 已采集的两个开源数据源

### TCMEval-SDT 训练分片

固定提交 `12473b50ce94ad2fd22b1e984b826b0a618c4407`；读取 200 条 Train_TCM_Data_v1.json。子目录 README 明确提供 CC BY 4.0 链接。论文：Wang Z., Hao M., Peng S. et al., *TCMEval-SDT: a benchmark dataset for syndrome differentiation thought of traditional Chinese medicine*, Scientific Data 12, 437 (2025), [DOI](https://doi.org/10.1038/s41597-025-04772-9)。

只投影 Clinical Information 与 TCM Syndrome。观察标签只有至少在两个训练记录出现、通过保守字符/长度与敏感模式过滤后才导出；该阈值只是减少碎片和长片段的工程策略，不是医学阈值，也不保证任意文本已匿名。语料仍具有健康语义。

同一记录内重复观察和标签去重；关联的 record_count 是训练记录数，不是人群概率、独立证据数量、因果强度或诊断权重。没有把“病例出现过”推导成“具备这些条件就确诊”。

未下载 test/validation 作为知识输入；当前也没有将它们作为已完成评测的证据。以后评测仍需检查跨来源和跨分片重复，单凭原分片名称不能保证独立性。

### MTCMB TCM-Diagnosis

固定提交 `faffd813c67fe012cef74277a23270d5dd6db9b8`；读取 200 条。README 区分数据 CC BY 4.0 与代码 Apache-2.0；本包没有执行或复制上游代码。

只保留 answer 中的疾病名称、证名、病位证素与病性证素短标签。题干、叙述性病例、治疗、方药和用量均未导出。上游说明存在教材来源，本包保留来源局限，不能仅以仓库许可推断全部第三方原始材料的权利已经清理。

MTCMB 仅用于词表，不从它生成观察—证候诊断规则，也不作为独立留出验证集。完整声明见 [来源登记](sources.json)、[采集回执](receipts.json)、[来源处置记录](source_review.json) 与 [署名/许可](ATTRIBUTION.md)。

## 问诊条目是什么依据

条目文字由本项目原创。官方《中医四诊操作规范》系列解读用于组织采集域：病程、寒热、汗、疼痛与身体不适、饮食、二便、情绪、睡眠及相关生殖健康信息等。我们核查了官方题录和解读，未声称逐条解析或再分发标准全文。

每条数据都包含 prompt、target_field、reason、source_refs、profiles、priority、prerequisites 和 review_status。问题能解释“为什么采集”，但尚不是针对某个患者的经过审核的临床决策。general、sleep、digestive、pain 是工程预览场景，不代表四条已经验证的专病诊疗路径。

排序先看工程优先级，再看前置问题是否已处理。answered 只代表这一问题已经处理，包括未知或拒答；它不代表症状阴性，也不保证已经获得充分诊断证据。受询者不应被迫回答全部问题，采集完成也不能自动等价于可以出诊断。

第一版不覆盖儿童、妊娠、急危重症或全部专病人群。相关信息用于标明需要专门流程，不建立自动排除风险的结论。

## 文献卡与诊断规则的区别

三张文献卡摘取并用中文重新整理 Poon 等 2012 年睡眠相关系统综述 Table 2 的少量描述性表现，涉及心脾两虚、阴虚火旺和心胆气虚。论文开放署名许可版本未明确，因此登记为 CC-BY (version unspecified)，没有擅自改写成 CC BY 4.0。

这是一篇历史综述，检索截至 2008 年；作者明确指出证候间表现重叠，建议的清单仍需验证。本包不把它称为当前指南，也不把相关表现当作必有症状。每张卡都保留适用局限、原表定位与可关联的采集问题。

所有资料卡的诊断必要条件、排除条件或鉴别规则尚未从这些资料中取得，使用 null 表示未知。不能改成空数组后利用“全部条件均满足”的逻辑把未知当成功。八纲、脏腑、病位/病性标签也没有自动组成统一的诊断树。

后续应按首批目标主诉补充当前指南、适用人群、必要/支持/反对条件、鉴别与证据等级，核查来源具体条款，再以独立病例评测和专业审核验证。软件可以辅助这项整理，不能凭预训练知识伪造已经存在的规则或临床审核记录。

## 如何使用与重建

```bash
uv run python scripts/clinical_knowledge.py audit
uv run python scripts/clinical_knowledge.py questions --profile sleep --limit 8
uv run python scripts/clinical_knowledge.py search --query 心脾
uv run python scripts/clinical_knowledge.py schemas

# 首次构建：无需模型服务、密钥或重新下载原始病例
uv run python scripts/clinical_knowledge.py build-index
uv run python scripts/clinical_knowledge.py query --query 心脾两虚 --kind literature_reference --limit 3
uv run python scripts/clinical_knowledge.py query --query 睡眠 --kind question --limit 3
uv run python scripts/clinical_knowledge.py document literature-insomnia-heart-spleen

# 真实 MCP 客户端会启动服务、发现工具、检索和回查引用
uv run --extra mcp python examples/clinical_mcp_client.py
```

重建上游派生数据：

```bash
uv run python scripts/collect_clinical_sources.py
uv run python scripts/build_clinical_knowledge.py
uv run pytest tests/test_clinical_knowledge.py -q
```

collector 只访问 inputs.json 中固定提交的公开原始文件和许可声明，校验 SHA256 后保存在被忽略的 tmp/；不执行外部代码，不读取模型密钥。builder 使用严格字段投影，输出可以离线审计。源码包不携带原始病例和下载的原始文件。若来源文件变化，哈希不符会拒绝，不偷偷接受新版本。

[对接合同](INTEGRATION.md) 说明明天面舌诊与脉诊示例到达后如何映射。索引位于被忽略的 `data/clinical-index.sqlite`，导出文档位于 `data/clinical-documents.jsonl`，不提交二进制数据库或运行数据。修改源资料后重新执行 build-index；旧索引会被拒绝。当前是词法检索，不宣称支持语义同义词、患者诊断或已经完成临床准确率评测。后续可从导出文档建立向量索引，仍需保留分类和来源限制。

实现参见 [文档转换](../../src/tcm_agent/clinical/documents.py)、[索引与检索](../../src/tcm_agent/clinical/index.py)、[MCP 服务](../../examples/mcp_server.py)、[检索测试](../../tests/test_clinical_index.py)。原服务仍使用 knowledge/entries.json。
