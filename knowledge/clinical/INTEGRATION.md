# 面诊、舌诊与脉诊结果接入约定

这是中立数据合同，尚未假定你的 API 字段或实现供应商适配器。明天的示例可以先去除姓名、电话、证件、照片 EXIF 定位及账户密钥；接口字段可用合成结果演示。

## 必须区分的三类结果

1. 特征或测量：例如颜色标签、设备数值、波形分析特征。
2. 外部服务推断：例如 API 已输出某证候或体质。
3. 材料质量：例如采集条件不足、照片失焦或记录不可用。

第三类不能变成第一类的“正常”，第二类不能伪装成独立测量。外部报告中的识别置信度不是患者诊断概率。相同图像产生的多个输出使用共同 evidence_group，不能重复计算为相互独立的证据。

## Observation 合同

见 [JSON Schema](schema/Observation.schema.json)。核心字段：

| 字段 | 含义 |
|---|---|
| observation_id | 本次观察唯一编号 |
| modality | inquiry / face / tongue / pulse / other |
| feature | 供应商字段映射后的观察名；未映射标签须保留原义 |
| value | 明确结果；未知、拒答、未测必须为 null |
| state | present / absent / unknown / not_measured / declined |
| observed_at | 带时区采集时间，不能拿上传时间冒充 |
| source_id | API/设备及版本标识，不放访问凭据 |
| evidence_group | 原图、同次测量或同段材料的共同组号 |
| unit | 测量单位；对有量纲数值必须在具体适配器中核验 |
| confidence | 可选来源置信度，范围 0—1；没有就保持 null |
| quality | unknown / acceptable / recollect |
| confirmed | 是否经过相应核对；false 不表示结果为阴性 |

示例只表示未采集状态，不是虚构你的 API 结果：

```json
{
  "observation_id": "synthetic-tongue-1",
  "modality": "tongue",
  "feature": "tongue_color",
  "value": null,
  "state": "not_measured",
  "observed_at": "2026-10-18T10:00:00+08:00",
  "source_id": "synthetic-provider",
  "evidence_group": "synthetic-capture-1",
  "unit": null,
  "confidence": null,
  "quality": "unknown",
  "confirmed": false
}
```

## 收到示例后的映射流程

先列原字段、类型、单位、枚举、置信度解释、采集时间和错误码，再逐项映射。找不到明确对应的值保持未映射，不由模型猜测。保留来源版本与原报告受控引用，但不把真实健康报告放进公开仓库。

随后验证超时、缺项、低质量、重复回调、同次材料多结果、患者更正和跨次就诊。确认旧结果失效规则，不能用昨日舌象和今日症状无条件拼成同一时刻状态。

现有 845 条数据词表不是供应商枚举表，更不保证符合国家标准代码。先建立精确映射，再做病例级融合；不能因为字符串相似就自动合并“病名、证型、体质、特征”。本包不包含可执行诊断概率或规则权重。
