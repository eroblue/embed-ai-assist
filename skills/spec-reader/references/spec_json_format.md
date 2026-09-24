# spec.json 字段规范

> `spec.json` 逐字段说明（结构契约见 `schemas/spec.schema.json`，
> 完整示例见 `assets/spec_example.json`）。

## 1. 顶层结构

```json
{
  "meta": {...},
  "title": "...",
  "summary": "...",
  "requirements": [...],
  "features": [...],
  "business_states": [...],
  "business_timing": [...],
  "error_handling": [...],
  "thresholds": [...]
}
```

- `meta` / `title` / `summary` / `requirements` / `features` 必填；
  其余四个数组无内容时填 `[]`（字段保留）
- 禁止添加 schema 之外的自定义字段（additionalProperties: false）

## 2. 字段说明

### meta

| 字段 | 说明 |
|---|---|
| source_file | 与 config 的 project.inputs.functional_spec 完全一致（validate 校验） |
| source_type | markdown / docx / pdf（与源文件扩展名对应） |
| extracted_at | ISO 时间戳（生成当时） |
| spec_version | "1.0"（本结构版本） |

### requirements[]（核心）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | REQ-001 起顺序编号，三位数字，不跳号 |
| title | 短语标题（≤20 字），如"环境数据周期采集与保存" |
| description | 需求描述：只写"要什么"；1~3 句 |
| priority | must / should / could |
| category | functional / interface / performance / constraint（判定见 requirement_taxonomy.md） |
| source.section | 原文标题定位（如"2.1 环境采集"） |
| source.page | 仅 PDF 源填写，其余 null 或缺省 |
| acceptance | 验收标准：原文有则摘录，无则总结；纯约束可 null |

### features[]

| 字段 | 说明 |
|---|---|
| id | F-001 起顺序编号 |
| name | 业务域名（产品语言，如"环境采集"）；business_states.module_hint 引用此名 |
| description | 一句话职责 |
| requirements[] | 归属 REQ-ID 列表（≥1 条，全部有效，validate 校验） |

### business_states[]

| 字段 | 说明 |
|---|---|
| module_hint | 归属功能域名（必须存在于 features[].name） |
| states[] | {name, description}，name 用业务语义（AUTO/MANUAL） |
| transitions[] | {from, to, event}；from/to 必须在 states[].name 中（validate 校验） |

### business_timing[]

| 字段 | 说明 |
|---|---|
| name | 时序名（如"环境采集"） |
| period_ms | 周期型填毫秒数；非周期 null |
| pattern | 非周期型填文字模式（"1s 响 1s 停"）；周期型 null |
| description | 时序说明 |
| requirement | 关联 REQ-ID（必须存在，validate 校验） |

### error_handling[]

| 字段 | 说明 |
|---|---|
| scenario | 错误场景（"采集失败"） |
| strategy | 业务策略（"跳过本次，保留上次有效值"） |
| requirement | 关联 REQ-ID（必须存在） |

### thresholds[]

| 字段 | 说明 |
|---|---|
| name | 阈值名（"高温告警阈值"） |
| value | 数值型 number（30）；范围/枚举型字符串（"18~28"） |
| unit | 单位（"°C"/"%RH"）；无量纲 null 或缺省 |
| condition | 触发条件（">"、"<"、"范围内"） |
| requirement | 关联 REQ-ID（必须存在） |

## 3. spec_trace.json

每条 REQ 一条记录，**恰好覆盖全部 REQ-ID**（缺一条或多一条都校验失败）：

```json
{"requirement": "REQ-001", "section": "2.1 环境采集",
 "page": null, "quote": "系统每 2 秒采集一次温度、湿度、光照数据……"}
```

- quote 摘录支撑该 REQ 的原文关键句（可轻度压缩），保证人工可核对
- section/page 与 REQ 的 source 对应

## 4. uncovered.json

文件**必须存在**（无未定项时 items=[]）：

```json
{"id": "UNC-001", "topic": "采集周期", "description": "原文'定期采集'未给出周期",
 "question": "采集周期确认为 2s？", "assumption": "按行业惯例取 2s",
 "source": {"section": "2.1 环境采集", "page": null}}
```

- UNC-001 起顺序编号
- strict_mode=true 时 assumption 恒为 null（不臆断）
- uncovered_count > 0 → state.spec.status = partial（用户确认后修订）
