# 中国 C 端中医助手：资源可行性与产品范围

编写日期：2026-10-11。主要来源核查于2026-10-10，关键发布资产于2026-10-11补查。本文是需求与资源研究，未进行模型推理、医学效果验证或生产部署。

## 可实现的首版

建议定位为“中医知识、健康记录与就诊准备助手”。用户可以描述困扰，由助手补充询问、整理可修改的健康记录、解释有来源的知识、保存自愿上传的舌象和面部照片，并准备就诊摘要。后续接入医疗机构及真实医师服务。这是依据工程资产与用户已确认边界提出的产品建议，尚未验证市场需求或付费意愿。

2026-10-11用户进一步确认首版优先“准备就诊与理解中医”。因此先交付追问、知识解释和可编辑摘要；日常打卡与持续管理后置。该选择是产品发起人的范围决定，仍需真实用户任务验证。

公开资源足以提供模型、图像分割和数据研究的起点，但不能证明一个零医疗资源团队已经具备独立诊疗能力。舌象的可见形态、面色的照片颜色、体质、证型和疾病是不同输出层级；不能将研究标签直接当作真实用户的诊断。[S10](https://github.com/cshan-github/TongueSAM)[S11](https://datadryad.org/dataset/doi%3A10.5061/dryad.1c59zw48r)[S14](https://arxiv.org/html/2508.14706v1#Sx14)[S36](https://medinform.jmir.org/2026/1/e87237)[S48](https://arxiv.org/html/2512.21988v4)

开方需要独立处理。互联网诊疗规则要求接诊医师本人开具处方，并禁止人工智能自动生成处方；同一规则也禁止AI冒用或替代医师本人提供诊疗服务。因此首版做已有方药信息解释和就诊资料整理，真正个体诊疗与处方交由后续医疗机构服务。一般AI辅助政策不能自动替代医疗服务资质。[S13](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881875.shtml)[S16](https://wjw.hubei.gov.cn/bmdt/ztzl/bmhqzcwjk/sjzc/202608/t20260828_6002909.shtml)[S19](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881770.shtml)

## 功能分层与验收依赖

| 能力 | 首版范围建议 | 资源能支持什么 | 上线前仍须完成 |
|---|---|---|---|
| 主动询问 | 采集不适、持续时间、既往情况和用户目标；生成可编辑摘要 | 通用模型与领域模型提供语言理解起点 | 补问规则、信息抽取准确性、对高风险情况的处理、专业内容审核 |
| 中医知识问答 | 解释术语、传统理论及知识来源，标清证据层级 | 通用底座、白泽等领域候选 | 条目级来源授权、引用核对、事实评估和适用范围 |
| 健康档案 | 用户确认后保存信息，支持更正、导出、删除 | 主要是普通软件能力 | 身份隔离、敏感信息同意、删除验证、留存策略 |
| 舌象采集 | 拍摄指导、照片质量反馈、记录；分析功能独立开关 | 分割代码、公开特征数据可用于研发 | 外部权重取件、代码与数据清权、真实手机失败样本测试 |
| 舌象描述 | 特征逐项验证后描述可见形态；低把握不输出 | TongueSAM、TOM、TCM-Tongue与领域视觉模型 | 标注一致性、各特征错误率、跨设备光照测试、未知样本拒绝 |
| 面部望诊 | 首版拍摄与记录；面色解释暂列研究功能 | 通用视觉与颜色校准邻近研究 | 中医面色数据权利、肤色覆盖、色彩校准和目标场景验证 |
| 体质/证型 | 候选研究项目，不以照片给确定结论 | 论文与部分多模态资源 | 量表权利与适用性、专业标注、医学评估、产品属性核实 |
| 已有处方解读 | 用户提供处方，解释有据可查的名称和信息；识别结果先确认 | OCR和受审知识库可作起点 | 药名/炮制/剂量识别核对；药物来源可靠性；禁止自动加减方 |
| 自动开方 | 不进入独立健康助手 | 研究模型可输出方药文本，但不构成临床或授权证明 | 后续机构与医师真实接诊、自主开具及药学流程 |
| 跟踪提醒 | 用户设置作息记录、复诊准备和记录提醒 | 软件工作流能力 | 通知授权、时区、重复/取消、不可达处理 |

表中“首版”是建议范围，不代表已经实现。政策支持健康教育与咨询方向，但具体输出是否构成医疗行为、是否涉及医用软件分类，需要按最终页面、宣传与用途核实。[S16](https://wjw.hubei.gov.cn/bmdt/ztzl/bmhqzcwjk/sjzc/202608/t20260828_6002909.shtml)[S20](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)[S28](https://www.nmpa.gov.cn/xxgk/ggtg/ylqxggtg/ylqxqtggtg/20210708111147171.html)[S29](https://yjj.beijing.gov.cn/yjj/ztzl48/ylqxjgfwzn/zxwdzl68/743634809/index.html)

## 文本模型与知识资产

许可结论分别针对代码、权重和数据。平台标签是发布者声明，不能替代完整许可证、上游权利和数据授权核查。选型不依据名字、机构知名度或考试成绩；本轮没有运行模型对比实验。

| 资源 | 实际公开状态与权利 | 本项目决定 |
|---|---|---|
| Qwen3.5-9B | 第一方模型卡提供视觉与文本底座，标Apache-2.0；不代表中医专科验证。[S7](https://huggingface.co/Qwen/Qwen3.5-9B) | 作为通用能力对照候选；具体大小由延迟、效果与运行测量决定 |
| 白泽V3-8B | HF实际有权重分片；权重与问答数据均标Apache-2.0。卡片仍有示例占位名称，数据来源细节和评估不足。[S31](https://huggingface.co/DigitalIntelligenceCenter-of-ICMM/Baize-Traditional-Chinese-Medicine-Large-Language-Model-V3-16bit)[S32](https://huggingface.co/datasets/DigitalIntelligenceCenter-of-ICMM/Baize-TCM-Corpus-for-Large-Language-Models-V3) | 进入领域问答离线对比；问答数据先检查来源、格式与质量，不直接充当医学事实库 |
| ShizhenGPT | 文本、视觉及Omni模型有公开卡片；视觉权重实际存在。权重卡标Apache-2.0，论文明确未完成实际临床测试并强调研究用途。[S5](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-Omni)[S14](https://arxiv.org/html/2508.14706v1#Sx14)[S34](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-VL) | 研究对照，核实完整权利与用途表述后再决定可部署范围；不从论文用途文字自行作许可证法律裁决 |
| Lingdan-V2 | README明确作者拥有权利的权重与资料采用Apache-2.0；受限原始病历不公开。既有临床评估为回顾性文本处方一致性评估。[S15](https://github.com/TCMAI-BJTU/Lingdan-V2/blob/main/README.md) | 研究候选；权重实际获取、运行、健康助手适用性另验，不把处方一致性当治疗效果 |
| Xinghe1.2-9B | 模型卡标Apache-2.0，面向经典解释与调养知识；作者说明缺系统临床及第三方验证。[S3](https://huggingface.co/zsyjsld/Xinghe1.2-9B) | 经典解释候选；训练边界与作者自测不能替代本产品评测 |
| ShenNong-TCM-LLM | README明确限制商业用途，与部分平台许可标签存在不一致。[S9](https://github.com/michael-wzhu/ShenNong-TCM-LLM) | 暂不进入商业产品资产；如需要，先获得明确权利澄清 |
| CMLM-ZhongJing | GitHub代码许可显示MIT，固定版本README同时有商业需许可和临床限制；同名通用医学项目需另区分。[S8](https://github.com/pariskang/CMLM-ZhongJing/blob/120529288b44e0cb2fa2e90f289b2ca01b227fc1/README.md) | 按具体资产澄清权利后再考虑；当前不作为商业底座 |
| TCM-SD / ZY-BERT | 作者README明确数据为CC BY-NC-SA，代码许可不能覆盖其数据。[S33](https://github.com/Borororo/ZY-BERT) | 商业训练/评测用途须另获许可；保留研究参考 |
| 古籍、知识图谱和药物研究库 | 未完成逐项内容来源、版本与授权审计；古籍原文、现代校注/翻译和数据库汇编权利不同 | 建立自己的可追溯知识条目；不将整站抓取或研究问答当作授权完成 |

知识库优先保存“来源、版本、原文定位、权利记录、适用人群、证据层级、审核记录”。经典理论可用于解释传统观点；现代药物安全、危险情况与治疗有效性需要相应证据。这个记录结构是产品设计决定，不是某个开源库已经提供的能力。

## 舌象、面色与多模态资产

| 资源 | 公开资产/许可证据 | 可用范围与缺口 |
|---|---|---|
| TongueSAM | 原始作者仓库有代码和MIT文件；权重与TongueSet3通过外部云盘链接提供；网页来源图片权利未清。[S10](https://github.com/cshan-github/TongueSAM) | 舌体分割对照。尚未取件、运行或验证；分割成功不证明诊断可靠 |
| TOM | HF目录真实存在TOM_S.pth及桌面程序，模型卡标MIT；GitHub许可文件与训练数据权利需继续核实。[S38](https://huggingface.co/orangeshushu/TOM/tree/main)[S39](https://github.com/orangeshushu/TOM-Tongue-Segmentation-Model) | 分割/标注辅助研究候选 |
| TCM-Tongue / TMC-Tongue | Dryad存档存在，API声明CC0；数据集规模为6,719张（来源报告），含特征标注。论文有“学术免费”措辞但未据此认定明确禁止商业。[S11](https://datadryad.org/dataset/doi%3A10.5061/dryad.1c59zw48r)[S12](https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.1c59zw48r)[S37](https://doi.org/10.62762/bish.2026.303296) | 形态研究优先候选。类别数量说明不一致，且混有传统脏腑区域标签；受控设备照片不能自动代表手机场景 |
| TongueAtlas-4K | 论文与Zenodo元数据存在，声明CC BY 4.0；2026-10-11 API标restricted，匿名访问返回files为空，完整文件需申请或进一步获取。[S50](https://zenodo.org/records/17557646)[S51](https://arxiv.org/abs/2511.10013) | 先列待获取，当前不计入可下载训练数据 |
| BioHit | 原始仓库提供设备采集分割数据，未确认商用许可。[S40](https://github.com/BioHit/TongeImageDataset) | 小规模分割对照；许可通过后才能复用 |
| ShizhenGPT-VL及视觉评测 | HF实际有视觉权重和评测文件；知识与图谱来源权利另审。[S34](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-VL)[S35](https://huggingface.co/datasets/FreedomIntelligence/TCM-Vision-Benchmark/tree/main) | 图像描述研究对照；不能从综合视觉题得分推出真实手机诊断效果 |
| TongueVLM | 论文存在，数据需申请；本轮未确认公开模型权重和代码。[S36](https://medinform.jmir.org/2026/1/e87237) | 后续申请合作线索 |
| ZhongJing-OMNI | GitHub与HF目录无广告所述题库目录，HF只有说明、示意图等。[S41](https://huggingface.co/datasets/CMLM/ZhongJing-OMNI/tree/main) | 当前不作为已实现的评测资源 |
| Suwen-CTM | 有训练/QC等参考脚本；API目录审计未发现声称的诊断检查点和图像语料，未发现许可证。[S42](https://github.com/au-han17/Suwen-CTM) | 阅读工程思路，取得权利前不复制部署；“生产已部署”属作者说法 |
| tcm-ai-assistant | 代码有权重路径，也有模拟分析相关描述/路径；无已确认许可。PPG血压任务不能替代中医脉象标签。[S43](https://github.com/ansonlovecoding/tcm-ai-assistant) | 演示架构参考，须代码实查区分真实与模拟输出，不直接推荐商用 |
| TCM-CAS | 主仓库当前以README与链接为主，所述多模态体质研究不等于完整可复现发布。[S44](https://github.com/thuiar/TCM-CAS) | 研究参考，不作为首版现成系统 |
| 医院舌象特征研究 | PLOS论文明确数据受保密限制，公开文章不等于开放病例图像。[S45](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296070) | 后续学术申请线索 |
| LingLan（2026年9月） | 论文描述私有记录与待发布权重；与LingLanMiDian评测不同。[S46](https://arxiv.org/html/2609.25715v1)[S6](https://arxiv.org/abs/2602.01779) | 跟踪发布，不纳入现有生产底座 |
| TongueDx2相关仓库 | 补检仓库含划分/标签文件与转换脚本，未确证完整图像、权重及商用许可；示例引用还有占位作者。[S52](https://github.com/tmai110605/TMC_TongueLab)[S53](https://arxiv.org/html/2607.28148v1) | 用于调查手机领域差异；尚不算可直接使用的成套资产 |
| 面色/手机颜色校准 | FFHQ上游含非商业和逐图权利条件；regional-ccm研究提供校准思路，原图需申请，亦非中医诊断数据。[S47](https://github.com/NVlabs/ffhq-dataset)[S48](https://arxiv.org/html/2512.21988v4)[S49](https://github.com/hpicsk/regional-ccm) | 面部记录与拍摄指导可先做；可靠中医面色分析仍需数据、校准和验证 |

本轮没有确认同时具备明确商用权利、可获取资产与独立手机临床验证的面色诊断方案。这是所查资源的结论，并非声称世界上不存在有效面色研究。进一步发现资源时，按同一标准重新评估。

## 中国首发的实际边界

健康教育与健康管理有政策支持；平台仍需按实际服务履行数据与生成内容等义务。后续真人诊疗必须落到适当医疗机构及医师工作流，不能用“医生最后点击确认”替代真实接诊及医师开具处方。[S16](https://wjw.hubei.gov.cn/bmdt/ztzl/bmhqzcwjk/sjzc/202608/t20260828_6002909.shtml)[S13](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881875.shtml)[S19](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881770.shtml)

症状、健康档案和健康目的照片涉及敏感信息处理。建议默认不保存原始照片，用户选择保存时说明目的；服务所需处理与训练复用分别授权。实现撤回、更正、导出和删除，并留有验证记录。普通面色照片不自动等于人脸身份识别；若加身份识别，应另评估生物识别处理。[S20](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)

优先评估境内推理与数据存储，是降低依赖的设计选择；若向海外模型或服务发送可识别健康信息，应核实跨境要求。去掉姓名或加密不当然构成法律上的匿名化。[S21](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm)[S22](https://www.cac.gov.cn/2024-03/22/c_1712776611649184.htm)

公众生成式服务需核实适用的备案/登记及标识义务。直接调用已备案模型有应用登记路径，但自部署、微调及图像服务不能直接照搬另一服务的登记结论。2026年的医疗信息整治强调科学性、验证与数据合法来源。[S23](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)[S24](https://www.cac.gov.cn/2026-09/14/c_1791136833136332.htm)[S25](https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm)[S26](https://www.cac.gov.cn/2026-04/30/c_1779289298718765.htm)

不作概念层面的“一律禁止首诊”或“一律属于某类医疗器械”判断。2026年有特定儿童机构首诊试点；医用软件分类取决于用途和功能。2026年AI医用软件指导修订仍有征求意见稿，不能当生效规则引用。[S17](https://www.nhc.gov.cn/yzygj/c100067/202601/d14857660f89487d8de1572a1b0b08f6.shtml)[S18](https://wjw.beijing.gov.cn/xwzx_20031/xwfb/202602/t20260209_4503549.html)[S28](https://www.nmpa.gov.cn/xxgk/ggtg/ylqxggtg/ylqxqtggtg/20210708111147171.html)[S29](https://yjj.beijing.gov.cn/yjj/ztzl48/ylqxjgfwzn/zxwdzl68/743634809/index.html)[S30](https://www.ydcmdei.org.cn/article/975)

## 资源获取与实施门槛

| 阶段 | 可推进工作 | 完成证据 | 升级条件 |
|---|---|---|---|
| 需求收敛 | 确定首版输出边界、用户流程与假设 | 本文及需求草案 | 明确高频入口和用户实际任务 |
| 资源准备 | 固定候选版本、检查权重与数据、建立来源条目 | 资产清单、许可原文、校验与获取记录 | 权利通过；不能获取的候选淘汰 |
| 工程原型 | 主动询问、引用回答、摘要、照片记录、删除 | 实际可操作产品与端到端验证 | 数据隔离、失败处理、无编造引用 |
| 模型评估 | 通用底座与领域候选在相同任务上比较 | 任务样本、误差分类、专业审核、运行成本/延迟实测 | 根据输出风险确定标准，未通过能力保持关闭 |
| 受控试用 | 清权内容和已验证功能用于有限用户 | 用户任务完成、误导案例、反馈修复 | 完成上线必需登记、隐私与内容质量工作 |
| 医师服务 | 寻找合适机构及服务接口，逐步接入 | 真实合作与临床工作流 | 资质、责任、记录和药学服务实际落实 |

上线日期随这些门槛更新。AI可完成研究、软件与自动检查；授权、专业审核、真实数据标注、服务登记和医疗机构合作是外部依赖。不给尚未测量的模型延迟、准确率、费用和工期编造数字。医疗、数据与登记依赖参照相应来源落实。[S13](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881875.shtml)[S20](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)[S24](https://www.cac.gov.cn/2026-09/14/c_1791136833136332.htm)

## 研究方法与限制

采用项目发现、第一方README/许可证/论文核对、公开API目录核查及反证搜索。资产执行记录保存在 `.omo/ulw-research/20261010-232318/verification`；来源账本与观测记录同目录。本轮只获取说明和元数据，没有批量下载患者图像或模型权重，也没有执行第三方仓库代码。[S10](https://github.com/cshan-github/TongueSAM)[S31](https://huggingface.co/DigitalIntelligenceCenter-of-ICMM/Baize-Traditional-Chinese-Medicine-Large-Language-Model-V3-16bit)[S34](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-VL)[S41](https://huggingface.co/datasets/CMLM/ZhongJing-OMNI/tree/main)

三个并行研究方向覆盖文本/方药、图像与中国边界。文本成员终报前因使用额度中断，关键商业许可和资产由主任务补查；知识图谱与药物信息的逐条清权仍待实施。研究经历初始、两轮扩展及一轮剩余线索补检；未完成的下载、授权与临床验证保留为依赖，不把它们写成已完成。源页面截图存在不代表内容正确，关键资产以文本与API相互核对。

后续需要验证的产品假设：目标用户是否愿意持续记录；就诊摘要是否真正省事；用户能否理解可见特征与诊断的区别；知识解释是否有足够复用价值。技术资源决定可做范围，不能独自证明商业需求。

## 编号来源

来源链接由研究账本自动附在此处；访问时间及证据层级以账本和观测清单为准。

- [S1](https://github.com/tyang816/Awesome-TCM-LLM)：发现线索目录；不用于确证第三方项目能力。
- [S2](https://www.nhc.gov.cn/yzygj/c100068/202203/2072f0e8988249e59d942e1b2a933916.shtml)：互联网诊疗监管细则原文；搜索可见，直接抓取失败，待官方镜像交叉核对。
- [S3](https://huggingface.co/zsyjsld/Xinghe1.2-9B)：模型卡：Apache-2.0、作者说明尚无临床/第三方系统验证。
- [S4](https://huggingface.co/DigitalIntelligenceCenter-of-ICMM/Baize-Traditional-Chinese-Medicine-Large-Language-Model)：模型卡：0.6B，Apache-2.0；不能由机构名推定临床可靠性。
- [S5](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-Omni)：实际模型卡；由视觉研究成员继续核查。
- [S6](https://arxiv.org/abs/2602.01779)：LingLanMiDian 是知识与推理评测，不是同名多模态模型。
- [S7](https://huggingface.co/Qwen/Qwen3.5-9B)：通用底座第一方卡，Apache-2.0；未验证中医产品效果。
- [S8](https://github.com/pariskang/CMLM-ZhongJing/blob/120529288b44e0cb2fa2e90f289b2ca01b227fc1/README.md)：README商业须许可与临床限制，已通过raw实际抓取确认。
- [S9](https://github.com/michael-wzhu/ShenNong-TCM-LLM)：README明示非商业。
- [S10](https://github.com/cshan-github/TongueSAM)：原始项目，MIT，外部云盘资产待取。
- [S11](https://datadryad.org/dataset/doi%3A10.5061/dryad.1c59zw48r)：真实舌象存档，类别说明不一致。
- [S12](https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.1c59zw48r)：实际API核实CC0声明，publicationDate=2026-01-06。
- [S13](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881875.shtml)：2022监管细则官方完整转载，第十三、十八、二十一条。
- [S14](https://arxiv.org/html/2508.14706v1#Sx14)：ShizhenGPT限制与风险原文：临床未测，许可证与用途声明应区别。
- [S15](https://github.com/TCMAI-BJTU/Lingdan-V2/blob/main/README.md)：灵丹V2权重Apache-2.0，原始受限病历未公开。
- [S16](https://wjw.hubei.gov.cn/bmdt/ztzl/bmhqzcwjk/sjzc/202608/t20260828_6002909.shtml)：AI+医疗卫生2025政策完整官方镜像。
- [S17](https://www.nhc.gov.cn/yzygj/c100067/202601/d14857660f89487d8de1572a1b0b08f6.shtml)：2026特定儿童机构首诊试点反例。
- [S18](https://wjw.beijing.gov.cn/xwzx_20031/xwfb/202602/t20260209_4503549.html)：首诊试点实施官方解读。
- [S19](https://wjw.wuxi.gov.cn/doc/2023/02/13/3881770.shtml)：互联网医院2018规则完整转载。
- [S20](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)：个人信息保护法。
- [S21](https://www.cac.gov.cn/2024-03/22/c_1712776611775634.htm)：数据跨境规则。
- [S22](https://www.cac.gov.cn/2024-03/22/c_1712776611649184.htm)：数据跨境规则官方解读，匿名化区别。
- [S23](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)：生成式AI暂行办法。
- [S24](https://www.cac.gov.cn/2026-09/14/c_1791136833136332.htm)：2026模型服务与应用登记公告。
- [S25](https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm)：AI生成内容标识办法。
- [S26](https://www.cac.gov.cn/2026-04/30/c_1779289298718765.htm)：AI应用乱象整治医疗信息要求。
- [S27](https://app.www.gov.cn/govdata/gov/202305/09/500665/article.html)：非医疗中医养生规范，适用范围须区别。
- [S28](https://www.nmpa.gov.cn/xxgk/ggtg/ylqxggtg/ylqxqtggtg/20210708111147171.html)：AI医用软件分类指导原则。
- [S29](https://yjj.beijing.gov.cn/yjj/ztzl48/ylqxjgfwzn/zxwdzl68/743634809/index.html)：医疗软件分类官方解读。
- [S30](https://www.ydcmdei.org.cn/article/975)：2026指导原则修订草案，非已施行。
- [S31](https://huggingface.co/DigitalIntelligenceCenter-of-ICMM/Baize-Traditional-Chinese-Medicine-Large-Language-Model-V3-16bit)：白泽V3-8B第一方权重卡，根任务补查公开资产与Apache声明，2026-10-11。
- [S32](https://huggingface.co/datasets/DigitalIntelligenceCenter-of-ICMM/Baize-TCM-Corpus-for-Large-Language-Models-V3)：白泽问答数据，Apache声明；预览报错，未据此声称数据不可加载。
- [S33](https://github.com/Borororo/ZY-BERT)：TCM-SD数据非商业许可原文。
- [S34](https://huggingface.co/FreedomIntelligence/ShizhenGPT-7B-VL)：视觉权重存在，已API独立复核。
- [S35](https://huggingface.co/datasets/FreedomIntelligence/TCM-Vision-Benchmark/tree/main)：视觉评测公开资产。
- [S36](https://medinform.jmir.org/2026/1/e87237)：TongueVLM论文；数据需申请，未确认公开权重。
- [S37](https://doi.org/10.62762/bish.2026.303296)：TCM-Tongue发布论文，学术免费措辞和数据伦理声明。
- [S38](https://huggingface.co/orangeshushu/TOM/tree/main)：TOM实际checkpoint与桌面资产，MIT卡声明，根任务API补查。
- [S39](https://github.com/orangeshushu/TOM-Tongue-Segmentation-Model)：TOM代码权利文件需继续核实。
- [S40](https://github.com/BioHit/TongeImageDataset)：BioHit分割数据，权利未确认。
- [S41](https://huggingface.co/datasets/CMLM/ZhongJing-OMNI/tree/main)：只有说明和示意图，未公开所述评测目录，根任务API补查。
- [S42](https://github.com/au-han17/Suwen-CTM)：工程参考；缺许可与诊断权重。
- [S43](https://github.com/ansonlovecoding/tcm-ai-assistant)：演示参考；缺许可，README存在模拟结果路径。
- [S44](https://github.com/thuiar/TCM-CAS)：构成评估研究线索，主体仓库README-only。
- [S45](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296070)：医院舌象特征研究，数据受保密限制。
- [S46](https://arxiv.org/html/2609.25715v1)：2026 LingLan多模态记录模型，私有数据与待发布权重。
- [S47](https://github.com/NVlabs/ffhq-dataset)：面部数据上游非商业与各图片权利。
- [S48](https://arxiv.org/html/2512.21988v4)：手机面部颜色校准邻近研究，按v4固定，不等于中医诊断。
- [S49](https://github.com/hpicsk/regional-ccm)：校准代码与处理后RGB，原始数据需申请。
- [S50](https://zenodo.org/records/17557646)：TongueAtlas-4K受限获取，元数据CC-BY但匿名接口无文件。
- [S51](https://arxiv.org/abs/2511.10013)：MIRNet与TongueAtlas-4K原论文。
- [S52](https://github.com/tmai110605/TMC_TongueLab)：TongueDx关联仓库，检查实际树与占位引用。
- [S53](https://arxiv.org/html/2607.28148v1)：TongueDx2消融论文，未据此声称成套发布可商用。
- [S54](https://www.sciencedirect.com/science/article/pii/S2352340920310477)：住院老年舌象小样本研究线索，非首版成人手机场景证据。
