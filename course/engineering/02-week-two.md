## 第二周：知识、检索与事实记忆

### 工程参考 E08｜建立可追溯的知识来源清单

**本节功能。** 知识不是随便下载的 PDF。系统需要知道文本来自哪里、什么版本、是否允许使用、谁批准进入当前语料。你要先有来源清单，再有向量索引。

源码：`src/tcm_agent/ingestion.py` 与 `knowledge/entries.json`。

{{snippet:src/tcm_agent/ingestion.py:SourceSpec}}

**代码详解。** `license` 不允许空字符串；`approved` 是管理员提供的工程准入状态，不是模型自我审核，也不等于医师审核。`version` 代表资料版本，后续还会绑定内容哈希。`source_url` 是出处定位。本课程内置条目使用 `course://` 标识作者原创教材，而不是伪造一个外部权威引用。

知识数据与评测数据用途不同。发布原始语料前需要确认权利和用途；公开可访问并不等于可复制或商用。进入私人病史的内容不应自动成为公共检索数据。

**操作。** 自己写一个无医学诊疗建议的 Markdown 资料 `data/notes.md`，再创建 `data/manifest.json`：

```json
[{"path":"notes.md","title":"课程项目操作说明","source_url":"course://notes","version":"v1","license":"original author permission","approved":true}]
```

```bash
uv run tcm ingest data/manifest.json --destination data/knowledge.json
```

**验收。** 产物带来源和版本；未批准文件不进入产物。不要把内置评测切换到自建语料后仍沿用旧标准答案，必须重新标注。


### 工程参考 E09｜切块、重叠与文档级上下文

**本节功能。** 将较长文档变成适合召回的单元，保持顺序与来源。RAG 原始论文提出将检索到的外部信息与生成结合；本项目把知识选择和引用控制落实为可观察的工具链路。[RAG 论文](https://arxiv.org/abs/2005.11401)

![知识入库与检索](assets/rag.png)

源码：`src/tcm_agent/ingestion.py`。

{{snippet:src/tcm_agent/ingestion.py:chunk_text}}

**代码详解。** 默认 600 字符与 80 字符重叠是课程起始参数，不是通用最优值。切分器优先在后半段找段落边界，避免切得过碎；末块明确终止，防止 overlap 造成无限循环。字符预算便于中文资料在无 tokenizer 时运行，但正式检索需要根据目标模型、结构和评测集调整。

重叠增加召回覆盖，也增加索引和上下文重复。文档中“全部单位为毫克”“以下适用于成人”这样的上位约束不能靠任意 overlap 保证保留。当前入库保存标题元数据；有复杂适用条件的医学资料应进行结构化审核和条件绑定，不能直接当作通用医学知识导入。

**操作与验收。** `uv run pytest tests/test_ingestion.py -q`。用段落、单行长文本、空文档和中文混合资料观察边界。将 overlap 改为与 size 相等，应立即拒绝。新增规则后比较检索指标与输入成本，不能只凭片段看起来漂亮决定。


### 工程参考 E10｜实现一个解释得清的中文 BM25 基线

**本节功能。** 没有 Embedding 服务时也能进行真实检索。基线使用中文单字、双字片段与英文词项，让“望闻问切”这样的无空格文本具有可匹配的检索单元。

源码：`src/tcm_agent/retrieval.py`。

{{snippet:src/tcm_agent/retrieval.py:tokenize}}

{{snippet:src/tcm_agent/retrieval.py:KnowledgeBase.sparse}}

**代码详解。** `tf` 表示词在一个文档中的频率，`df` 表示出现该词的文档数；稀有词的区分作用更强。长度归一化避免长文档仅因内容多而长期占优。这里使用 k1=1.2、b=0.75，代码公开公式，便于观察和替换。它不是语义向量检索，不能把词形相近误称为理解同义词。

当前实现每次遍历整个小语料，适合教学和受控小规模资料；不是百万文档的搜索引擎。若语料扩大，应预计算统计并采用倒排索引，先测召回与时延，再选搜索服务。

**操作与验收。** `uv run pytest tests/test_retrieval.py -q`。用“药名”“用药记录”“既往服药”测试同义改写，记录失败原因。执行 `uv run tcm evaluate`，注意报告只含 8 条小样本，不可宣传为全场景准确率。


### 工程参考 E11｜接入真实 Embedding，处理维度与版本

**本节功能。** 通过供应商 `/embeddings` 得到真实向量，而不是用随机数或哈希向量冒充语义能力。默认该能力关闭；开启需要平台确实支持 Embedding 模型。

源码：`src/tcm_agent/embeddings.py`。

{{snippet:src/tcm_agent/embeddings.py:ProviderEmbedder.embed}}

**代码详解。** 返回结果按 index 排序，并检查完整性。不能假设服务返回顺序必然等于输入顺序。查询和文档使用同一配置的向量模型；维度漂移必须报错，不能让 zip 静默截断。即使两个模型维度相同，也不意味着它们处于同一向量空间。

本项目在进程启动时为小语料构建内存向量索引，重启重新计算；没有声称实现大规模向量数据库。真实平台若用不同的 Embedding 基地址或独立密钥，当前适配器需要扩展独立配置，不能误把聊天密钥发送给未确认的地址。

**操作与验收。** 配置 `TCM_EMBEDDING_MODEL` 后重启服务，并运行评测。没有真实向量服务时只做合同测试，报告保留“未验证”。比较同义问题的召回与额外延迟；检索指标不改善就不要为了技术栈好看而强行启用。


### 工程参考 E12｜混合检索、RRF 与重排的边界

**本节功能。** 将 BM25 与向量结果按排名融合，避免直接相加不可比的分数。BM25 分数与 cosine 数值的尺度并不相同。

源码：`src/tcm_agent/retrieval.py`。

{{snippet:src/tcm_agent/retrieval.py:KnowledgeBase.search}}

**代码详解。** RRF 对各路中的第 r 名增加 `1/(60+r)`。60 是平滑常数；它不是模型输出概率。每路保留前 10，再选融合后的前 4。关闭 Embedding 时只有一条 BM25 排名，不应宣传为混合检索。这里计算的是完整候选排名，而不是 ANN；这与当前小知识库的规模一致。

重排与融合不同：RRF 结合各路排序；cross-encoder 对 query/document 联合打分，可以识别更细粒度相关性，但需要额外推理与延迟。当前主线没有接入 cross-encoder，课程会讲清升级点，面试时不能声称已经上线。

**操作与验收。** 比较 BM25-only 与 hybrid 的 Recall@4、MRR@4、单次耗时。做一个失败记录：某查询两路都没有正确条目时，再好的融合也无法补救。练习为同一文档多个 chunk 去重，说明为什么会减少来源多样性偏差。


### 工程参考 E13｜让每个知识解释都能回到证据

**本节功能。** 模型只能引用本回合实际检索过的条目，并且引文必须是该条目原文片段。引用有效性不能靠模型自己声明。

源码：`src/tcm_agent/domain.py`。

{{snippet:src/tcm_agent/domain.py:Evidence}}

{{snippet:src/tcm_agent/domain.py:CitationDraft}}

**代码详解。** `Evidence` 同时携带 entry ID、出处、版本、许可和本次排名分数。模型终态只提交 ID 和 quote，服务端从自己的 `retrieved` 登记表补齐可信元数据。模型不能把一个好看的外部 URL 填进最终来源字段。render_answer 只使用通过包含校验的片段，降低生成未经证据支持的新医学说法的机会。

需要区分三层：来源真实存在、引文确实来自该来源、引文能够支持当前回答。前两层可用机械校验覆盖一部分，第三层需要相关性评估与领域审核。古籍、科普和临床研究也不能被当成同等级证据。

**操作与验收。** `uv run pytest tests/test_runtime.py -k citation -q`。先构造从未检索过但真实存在的 entry ID，应失败；再构造不存在的引文，也应失败。检查知识解释对未知问题的有限回答，不用虚构链接兜底。


### 工程参考 E14｜事实记忆、人类确认与确定性摘要

**本节功能。** 将用户确认写成真正的应用状态变化。用户输入中的事实片段先成为候选；确认时可以改正字段归类；同一字段的新确认替换旧值，版本加一。

![事实与记忆](assets/memory.png)

源码：`src/tcm_agent/repository.py` 与 `policy.py`。

{{snippet:src/tcm_agent/repository.py:VisitRepository.confirm}}

{{snippet:src/tcm_agent/policy.py:render_summary}}

**代码详解。** 确认请求必须引用已有候选的 source_turn_id 和 quote，防止把助手推断当作用户既往输入。字段由用户确认决定，因此即使模型把“我没有说过敏”错误分类成过敏事实，也不能在用户确认前生效。摘要遍历固定字段，未提供始终标记为未提供，不把“没问到”写成“没有”。

更正流程是：用户发来新表述 → 形成新候选 → 确认该字段 → 替换旧值。删除某个已确认字段有独立 API，同样需要版本号。正式事实的存在不依赖旧聊天历史是否还在上下文里。

**阶段验收。** `uv run pytest tests/test_api.py -k 'summary or confirm' -q`。先不确认直接导出，摘要不含候选；确认后导出，原话出现；更正再导出，仅保留新事实。能够解释用户确认与 LangGraph 的 interrupt 为何不是同一层问题。

