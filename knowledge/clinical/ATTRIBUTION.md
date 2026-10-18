# 来源署名、许可与变更说明

本目录不继承根目录 MIT 对全部材料的假定授权；代码仍按项目 MIT，原创问题与文档按 CC BY 4.0，第三方派生数据按各自来源条件。任何上游作者均未为本项目的医学用途作背书。

| 文件或内容 | 归属与许可 | 本项目变更 |
|---|---|---|
| questions.json | tcm-agent-course contributors；CC BY 4.0 | 原创表达、工程分组、来源与原因标记；未临床审核 |
| terms.json 的 TCMEval 来源、associations.json、candidate_cards.json | Wang Z., Hao M., Peng S. et al. / TCMEval contributors；[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 只取 train；选择字段、分隔标签、过滤低频/长观察、去重、生成稳定 ID 和共现计数；未保留原始病例 |
| terms.json 的 MTCMB 来源 | MTCMB contributors；数据声明 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，代码另为 Apache-2.0 | 仅短病名、证名与证素标签；未保留原题、叙述答案、病例或方药 |
| literature_cards.json | Poon M.M.K., Chung K.F., Yeung W.F., Yau V.H.K., Zhang S.P.；文章声明 Creative Commons Attribution，版本未明示 | Table 2 部分表现的中文整理、局限与问题链接；不是完整翻译或诊断规则 |
| 标准信息 | 国家市场监督管理总局、国家标准化管理委员会及其官方解读 | 仅题录、链接和原创组织说明，不分发标准全文 |

TCMEval 论文：[Wang et al. 2025](https://doi.org/10.1038/s41597-025-04772-9)。数据及许可声明分别位于 [固定提交目录](https://github.com/zhuyan166/TCMEval/tree/12473b50ce94ad2fd22b1e984b826b0a618c4407/evaluation/TCMEval-SDT) 与其 readme.md。

MTCMB：[固定提交](https://github.com/Wayyuanyuan/MTCMB/tree/faffd813c67fe012cef74277a23270d5dd6db9b8)，ReadMe.md 明确将数据许可与代码许可分开。原教材等第三方来源的权利不能由仓库声明完全保证，因此本次只保留有限短标签用于研究词表。

文献：[Poon et al., 2012, DOI 10.1155/2012/735078](https://doi.org/10.1155/2012/735078)，[PMC 文章与开放署名声明](https://pmc.ncbi.nlm.nih.gov/articles/PMC3414091/)。仅登记公开来源，不暗示本包通过其作者验证。

许可允许的再使用不等于临床有效性或患者隐私授权。原始个案、教材、规范全文没有随本仓库重新授权；本包不提供原始患者记录，也不声称完成临床验证。详细来源版本、限制与校验哈希见 sources.json、inputs.json 和 receipts.json。
