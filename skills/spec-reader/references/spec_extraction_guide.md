# 规格书提取要点（Agent 依据）

> S2 Agent 轨操作指南：如何把 `outputs/s2/raw_text.md` 转成
> `spec.json` + `spec_trace.json` + `uncovered.json`。
> 任务书（generation_brief.md）给出项目参数与原文，本指南给出提取方法。

## 1. 总体流程

1. 通读 `raw_text.md` 全文，识别文档结构（功能章节 / 状态说明 / 时序说明 /
   异常处理 / 参数表）。
2. 逐章节扫描，按第 2 节的识别模式提取六类信息。
3. 条目化需求（REQ 粒度见 `requirement_taxonomy.md`）。
4. 归类功能域（features）。
5. 填写追溯（spec_trace）与未定项（uncovered）。
6. 写入三个产物前，逐个用对应 schema 自检（`schemas/spec.schema.json` 等）。

## 2. 六类信息的识别模式

### 2.1 需求条目（requirements[]）

识别信号：
- "系统应当/需要/支持/提供……"
- 章节标题本身即功能点（如"2.1 环境采集"）
- 参数表中的行为行（"采集周期：2s"）

粒度判断：**REQ = 可独立验收的功能点**。
- 合并：同一功能行为的侧面（"采集" + "采集失败保留旧值" → 一条，失败策略
  同时登记 error_handling）
- 拆分：能独立验收、验收标准不同的功能点（"本地显示" vs "上位机上报"）

### 2.2 业务状态机（business_states[]）

识别信号：模式/状态词（"自动模式/手动模式"、"待机/运行/告警"）+
迁移条件（"按键切换"、"超时进入"）。

- `module_hint` 填状态机归属的功能域名（与 features[].name 一致）
- 状态名用业务语义（AUTO/MANUAL），不发明技术状态（如"TIMER_EXPIRED"）
- 迁移事件写触发源（key1_press、sensor_fault），不写实现（中断/轮询）

没有状态机描述的产品填空数组，**不要臆造**。

### 2.3 业务时序（business_timing[]）

识别信号："每 X 秒/分钟"、"周期"、"间隔"、"X 秒后"、"响 X 停 X"。

- 周期型：填 `period_ms`（如 2000），pattern 留 null
- 非周期型：`pattern` 填文字描述（如"1s 响 1s 停"），period_ms 留 null
- **只登记业务级时序**（用户可感知的），主循环周期/调度切片不登记
- 每条时序必须关联一个 REQ-ID（requirement 字段）

### 2.4 错误处理（error_handling[]）

识别信号："失败/异常/超时/掉线……时，重试/降级/保留/恢复"。

- 只登记**策略级**内容："重试 3 次"、"跳过本次保留上次值"
- 不登记实现细节：重试用什么定时器、状态标志怎么设计

规格书没有异常处理章节时：登记 uncovered（全文性缺失），
**不要替用户发明错误处理需求**——除非 strict_mode 关闭且行业惯例明确
（此时 assumption 里写清楚）。

### 2.5 阈值（thresholds[]）

识别信号：带单位与比较关系的数值（">30℃ 告警"、"湿度低于 20% 提醒"）。

- 数值型：value 填 number（30），unit 填 "°C"，condition 填 ">"
- 范围型：value 填字符串（"18~28"），condition 填"范围内"
- 业务阈值（用户可感知），不是 ADC 原始值/寄存器值

### 2.6 功能域（features[]）

- 按业务能力分组，名称用产品语言（"环境采集"、"本地显示"）
- 横切关注点独立成域：工作状态管理 / 初始化与容错 / 系统约束
- 明显特征清楚即可，不追求完美（S5b 会做模块拆分决策）
- 每条 REQ 至少归属一个 feature（validate 强制校验）

## 3. 来源标注规范

- `source.section`：填**原文标题**（如"2.1 环境采集"），可加父级路径
  （"2 功能需求 > 2.1 环境采集"）——保证可回溯定位
- `source.page`：仅 PDF 源填写（对应 raw_text.md 中的 `<!-- page N -->`
  标记）；markdown/docx 源留 null 或缺省
- `spec_trace.quote`：摘录支撑该 REQ 的原文关键句（可轻度压缩），
  不要整段照抄

## 4. 模糊与缺失的处理

模糊示例与处理（strict_mode=false 时）：

| 原文 | 处理 |
|---|---|
| "定期采集环境数据"（无周期） | REQ 正常提取；uncovered 登记 topic=采集周期，assumption=按 2s（行业惯例），question=确认采集周期 |
| "异常时告警"（无阈值） | 阈值未知：uncovered 登记 topic=告警阈值；assumption 仅在惯例明确时填 |
| 无错误处理章节 | uncovered 登记（source.section=null，全文性缺失） |
| "支持低功耗"（一句话，无细节） | REQ 提取（category=functional）；细节模糊登记 uncovered |

strict_mode=true 时：所有 assumption 留 null，只登记 question，不臆断。

## 5. 完成自检清单

- [ ] REQ-ID 从 REQ-001 起连续编号，不跳号不重复
- [ ] 每条 REQ 的 category 已按四枚举判定（默认 functional）
- [ ] 每条 REQ 归属至少一个 feature；feature 内 REQ 引用全部有效
- [ ] timing/error_handling/thresholds 的 requirement 引用全部有效
- [ ] 状态机 from/to 均在 states 列表；module_hint 在 features[].name 中
- [ ] spec_trace 恰好覆盖全部 REQ-ID
- [ ] uncovered.json 文件存在（无未定项时 items=[]）
- [ ] 三个产物均通过对应 schema 校验
