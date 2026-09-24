# S2 规格书需求提取任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书把原始规格书转成结构化需求，
> 操作规范见 `skills/spec-reader/SKILL.md` 与 `references/`（提取要点
> spec_extraction_guide.md、分类规范 requirement_taxonomy.md、字段规范
> spec_json_format.md）。只提取'产品要什么'，不提取'技术上怎么实现'。

## 1. 项目信息

- 目标工程（build_target）：App
- 输出语言：zh-CN（仅影响描述字段语言）
- 严格模式：关闭（可合理假设默认值，同时登记 uncovered）
- 功能规格书：`docs/functional_spec.md`（格式：markdown）
- 软件规格书：未配置（无需处理）

## 2. 原文摘要

- 提取文本约 930 字符，13 个标题章节，4 行表格内容
- 提取文本已存档：`outputs/s2/raw_text.md`（人工核对与追溯用）

## 3. 输出要求（三个产物，写入 outputs/s2/）

1. `spec.json` —— 结构化需求（**核心产物**，S5b 消费）：
   - `meta`（source_file/source_type/extracted_at/spec_version）、`title`、`summary`
   - `requirements[]`：需求条目（`REQ-001` 起顺序编号不跳号），每条含
     id/title/description/priority(must|should|could)/
     category(functional|interface|performance|constraint)/source{section,page?}/acceptance?
   - `features[]`：业务域分组（`F-001` 起），每条含 id/name/description/requirements[]
   - `business_states[]`：业务级状态机（module_hint + states[] + transitions[]）
   - `business_timing[]`：业务级时序（period_ms 或 pattern + requirement 引用）
   - `error_handling[]`：业务级错误处理策略（scenario/strategy/requirement）
   - `thresholds[]`：业务阈值（name/value/unit/condition/requirement）
   - 结构契约：`skills/spec-reader/schemas/spec.schema.json`（写入前须通过校验）
   - 完整示例：`skills/spec-reader/assets/spec_example.json`
2. `spec_trace.json` —— 需求追溯：每条 REQ 一条记录（requirement/section/page?/quote 原文引用），
   须覆盖全部 REQ-ID，契约 `schemas/spec_trace.schema.json`
3. `uncovered.json` —— 未定项清单（模糊描述、缺失项）：items[] 可为空数组但文件必须存在，
   契约 `schemas/uncovered.schema.json`

## 4. 需求条目化规范

- **REQ 粒度 = 可独立验收的功能点**，不是规格书每句话一条：
  - 同一功能行为的不同侧面（如'采集 + 采集失败处理'）合并为一条
  - 能独立验收、且验收标准不同的功能点分开
  - 中等复杂度项目典型 10~20 条
- **category 判定**：functional=功能行为（默认）；interface=功能级接口/外设需求
  （'需要串口与上位机通信'，非波特率/引脚等技术细节）；performance=性能指标
  （响应时间/精度/吞吐量）；constraint=系统级约束（无动态内存/24h 连续可用）
- **来源标注**：`source.section` 填可定位的章节标题（如'2.1 环境采集'）；
  PDF 源填 `source.page`（对应 `<!-- page N -->` 标记）
- **验收标准**：`acceptance` 原文有则摘录，无则根据描述总结；纯约束类可留 null
- **feature 划分**：明显特征清楚即可，不追求完美；一条 REQ 至少归属一个 feature；
  横切关注点（工作状态管理/初始化与容错/系统约束）独立成 feature

## 5. 未定项处理原则（strict_mode 行为）

- 遇到模糊描述可采取合理默认假设（按行业惯例），但**必须**同时登记
  `uncovered.json`：description 写原文怎么说的，assumption 写采用的默认值，
  question 写需用户确认的问题
- 全文缺失的关键信息（如无错误处理章节）也登记 uncovered（source.section 为 null）
- uncovered 非空 → validate 收口为 `partial`，需用户确认后修订

## 6. 禁止事项（硬约束）

- 不提取技术实现细节：帧格式、命令码、波特率、校验方式、引脚映射、DMA、
  外设选择、消抖/调度/心跳实现方式——这些归 S5b 从 `s5b_design_input.md` 读取
- 不生成 `module_list.json`、不做 feature → module 映射（S5b 职责）
- 不解析 software_spec 内容（只登记路径）
- `spec.json` 中不内联'如何实现'的描述，只写'要什么'
- 不修改 config.json / state.json 其他字段

## 7. 原始文本（分章节，已 Markdown 化）

```markdown
# SmartEnvGuard 智能环境监测仪功能规格书

**版本**：V1.0
**日期**：2026-09-23

## 1. 产品概述

SmartEnvGuard 是一款室内环境监测仪，实时监测温度、湿度与光照强度，
本地 LCD 显示，环境异常时自动告警并联动通风，支持自动/手动两种控制
模式，并通过串口向上位机上报数据。

## 2. 功能需求

### 2.1 环境采集

系统每 2 秒采集一次温度（°C）、湿度（%RH）、光照（0~100%）数据，
采集结果保存在设备内部，供显示、上报与控制使用。

采集失败时保留上次有效值；连续 5 次失败判定传感器故障并告警，
恢复后自动清除故障标记与告警。

### 2.2 本地显示

LCD 实时显示温度、湿度、光照与工作模式，每 1 秒刷新一次。

### 2.3 按键交互

KEY1 切换自动/手动模式；KEY2 在手动模式下启停通风；按键需防误触。

### 2.4 自动控制

自动模式下温度超过 30℃ 或湿度超过 80%RH 时启动通风并蜂鸣告警
（1s 响 1s 停），恢复后自动停止。

### 2.5 数据上报

通过串口向上位机上报环境数据与设备状态，上报周期 10 秒。

### 2.6 运行指示

运行指示灯每 2 秒闪烁一次，故障时常亮。

### 2.7 初始化与自检

上电完成传感器、显示、存储自检，自检失败进入降级运行（仅保留可用
功能）。正常上电 3 秒内进入工作状态。

### 2.8 工作模式

设备具有自动/手动两种工作模式，上电默认自动模式；传感器故障告警
优先级高于环境阈值告警，高优先级告警触发时屏蔽低优先级告警提示。

## 3. 性能指标

| 指标 | 要求 |
|---|---|
| 按键响应时间 | 不超过 100ms |
| 周期任务 | 采集周期 2s、显示刷新 1s、上报周期 10s，各周期任务互不阻塞 |

## 4. 系统约束

- 温度有效范围 -40~85℃、湿度 0~100%RH、光照 0~100%，越界数据无效，
  不参与显示与控制。
- 系统不使用动态内存分配。
- 7×24 小时连续运行不死机。
```
