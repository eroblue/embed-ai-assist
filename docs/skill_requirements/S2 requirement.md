# S2 spec-reader Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：spec-reader
- **Skill 用途**：从原始功能规格书（Word / PDF / Markdown）出发，把非结构化文本转成结构化需求 JSON（`spec.json`），供 S5b 消费。S2 只管"产品要什么"（需求侧），不管"技术上怎么实现"（设计侧）。
- **触发时机**：在 S1 建立工作区后触发；与 S3 / S4 / S5a 无数据依赖，可并行执行。**S5b 若需消费 spec.json（spec 驱动模式），必须后于 S2 收口执行**——若并行，S5b 将因 `state.spec` 缺失走设计输入驱动降级模式（S2 等于白跑）。

## 输入

### 从 `state.json` 读取

- 无（S2 是流水线早期 Skill，只依赖工作区存在）

### 从项目级 `config.json`（与全局 `config.json` 合并后）读取

- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / `outputs/` 位于 `<项目根>/<build_target>/`
- `project.inputs.functional_spec`：功能规格书路径（**必选**，相对项目根）
- `project.inputs.software_spec`：软件规格书路径（可选，**仅登记路径指针，S2 不解析内容**）
- `s2.language`：输出语言（可选，默认 `zh-CN`，仅影响描述字段）
- `s2.strict_mode`：严格模式（可选，默认 `false`）——严格模式下遇到模糊描述会写入 `uncovered` 而不臆断

### 输入格式支持

| 格式 | 解析方式 | 依赖 |
|---|---|---|
| `.md` / `.txt` | 直接读取 | 无 |
| `.docx` | `python-docx` 提取段落与标题层级 | `python-docx` |
| `.pdf` | `pdfplumber` 提取文本与页码 | `pdfplumber` |

格式无法识别或解析失败时，`status: failed` 并写明原因，不产出半成品。

## 输出

### 写入 `state.json`（仅 `spec` 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `spec.status` | string | `success` / `partial` / `failed` |
| `spec.spec_path` | string | `outputs/s2/spec.json` 相对路径（success/partial 时必填；failed 时为 null，不留半成品指针） |
| `spec.software_spec_path` | string/null | 软件规格书路径指针（若 config 指定则登记；仅供 Agent 查阅——S5b 实际以 config 的 `project.inputs.software_spec` 为准） |
| `spec.spec_summary` | object | 统计信息：`{total_requirements, feature_count, uncovered_count}` |
| `spec.source_file` | string | 原始规格书路径（相对项目根） |
| `spec.updated_at` | string | ISO 时间戳 |
| `spec.error` | string/null | 失败时的错误信息 |

契约由 `schemas/output.schema.json` 约束。

### 写入 `outputs/s2/`

| 产物 | 内容说明 |
|---|---|
| `outputs/s2/raw_text.md` | 原始规格书提取的纯文本（分章节，保留标题层级）——便于人工核对与 Agent 上下文注入 |
| `outputs/s2/spec.json` | 结构化需求（**S2 核心产物**，结构由 `schemas/spec.schema.json` 约束） |
| `outputs/s2/spec_trace.json` | 需求追溯（`REQ-ID` → 章节 / 页码 / 原文段落） |
| `outputs/s2/uncovered.json` | 未定项清单（模糊描述、缺失项，供用户确认） |

### `spec.json` 结构设计（v1）

```json
{
  "meta": {
    "source_file": "docs/functional_spec.md",
    "source_type": "markdown",
    "extracted_at": "2026-09-23T10:00:00",
    "spec_version": "1.0"
  },
  "title": "SmartEnvGuard 智能环境监测仪",
  "summary": "实时监测室内温湿度和光照，本地显示，异常告警，支持自动/手动控制和上位机上报。",

  "requirements": [
    {
      "id": "REQ-001",
      "title": "环境数据周期采集与保存",
      "description": "每 2 秒采集一次温度（°C）、湿度（%RH）、光照（0~100%）数据，保存在设备内部供显示、上报、控制使用。",
      "priority": "must",
      "category": "functional",
      "source": {"section": "2.1 环境采集"},
      "acceptance": "上电后每 2 秒完成一次采集，三条下游路径均可读取最近有效值。"
    }
  ],

  "features": [
    {
      "id": "F-001",
      "name": "环境采集",
      "description": "环境数据的周期采集、保存与失败处理。",
      "requirements": ["REQ-001", "REQ-002"]
    }
  ],

  "business_states": [
    {
      "module_hint": "work_mode",
      "states": [
        {"name": "AUTO", "description": "自动模式"},
        {"name": "MANUAL", "description": "手动模式"}
      ],
      "transitions": [
        {"from": "AUTO", "to": "MANUAL", "event": "key1_press"}
      ]
    }
  ],

  "business_timing": [
    {"name": "环境采集", "period_ms": 2000, "description": "每 2 秒采集一次", "requirement": "REQ-001"}
  ],

  "error_handling": [
    {"scenario": "采集失败", "strategy": "跳过本次，保留上次有效值", "requirement": "REQ-002"}
  ],

  "thresholds": [
    {"name": "高温告警阈值", "value": 30, "unit": "°C", "condition": ">", "requirement": "REQ-005"}
  ]
}
```

**字段说明**：

| 字段 | 内容 | 粒度原则 |
|---|---|---|
| `requirements[]` | 需求条目 | **功能点级**（可独立验收的功能点），不是规格书每句话一条 |
| `features[]` | 业务域分组 | **明显特征清楚即可**，不追求完美划分（见"补充说明"） |
| `business_states[]` | 业务级状态机 | 业务语义状态（"连接中"、"待机"），不是技术状态机 |
| `business_timing[]` | 业务级时序 | "每 2 秒采集"、"1s 响 1s 停"，不是主循环周期 |
| `error_handling[]` | 业务级错误处理策略 | "重试 3 次"、"降级"，不是技术细节 |
| `thresholds[]` | 业务阈值 | "温度 > 30℃ 报警"，不是 ADC 采样值 |

**`requirements[].category` 枚举**（支撑 S5b 消费端结构化提取外设需求与性能指标，而非从描述文本中猜测）：

- `functional`：功能行为（默认）
- `interface`：功能级接口/外设需求——"需要串口与上位机通信"、"WiFi 数据上报"（是"需要什么通信能力"，不是引脚映射/波特率/校验方式等技术细节，后者仍归 S5b 设计输入）
- `performance`：性能指标——响应时间、测量精度、吞吐量
- `constraint`：系统级约束——无动态内存、24h 连续可用

### 指针 / 数据分离规则

- 原始文本、结构化 JSON、追溯信息、未定项清单全部放 `outputs/s2/`
- `state.json` 只存指针与统计，不存数据本体
- 数据量大的产物（`spec.json` 等）放 `outputs/`，结构由 `schemas/<产物名>.schema.json` 约束

## Skill 目录结构

```text
spec-reader/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（state.json 就绪性检查）
│   ├── output.schema.json             # 输出契约（state.json 的 spec 字段）
│   ├── spec.schema.json               # spec.json 结构契约（核心）
│   ├── spec_trace.schema.json         # 追溯矩阵契约
│   └── uncovered.schema.json          # 未定项清单契约
├── scripts/
│   ├── analysis.py                    # 共享分析（配置加载/格式识别/文本提取）
│   ├── prepare.py                     # 阶段 1：提取原始文本 + 生成 Agent 任务书
│   ├── validate.py                    # 阶段 3：校验 spec.json + state 收口
│   └── extractors/                    # 各格式文本提取器（适配器模式）
│       ├── docx_extractor.py
│       ├── pdf_extractor.py
│       └── markdown_extractor.py
├── references/
│   ├── spec_extraction_guide.md       # 规格书提取要点（Agent 依据）
│   ├── requirement_taxonomy.md        # 需求分类与优先级规范
│   └── spec_json_format.md            # spec.json 字段规范
└── assets/
    ├── spec_example.json              # spec.json 示例
    └── spec_trace_example.json
```

## 执行步骤

S2 采用三段式执行（与 S5a / S5b 一致：rule 准备 → Agent 生成 → rule 校验）。

### 阶段 A：prepare（rule）

1. 从 `config.json` 读取 `project.inputs.functional_spec`，与全局 `config.json` 深合并。
2. 检查规格书文件存在；根据扩展名选择 `extractors/` 下对应提取器。
3. 提取原始文本到 `outputs/s2/raw_text.md`：
   - 保留标题层级（用 Markdown `#` 标记）
   - 保留页码信息（PDF 场景，以 `<!-- page N -->` 注释形式插入）
   - 保留表格（转 Markdown 表格）
4. 生成任务书 `outputs/s2/generation_brief.md`，内含：
   - 项目信息（build_target、language、strict_mode）
   - 输入材料路径与摘要
   - 原始文本（分章节嵌入）
   - 输出要求（spec.json 结构规范、字段含义、禁止项）
   - 需求条目化规范（`REQ-XXX` 编号、来源标注、验收标准提取）
   - 未定项处理原则（strict_mode 行为）
5. 更新 `state.spec.status = running`。

### 阶段 B：generate（agent）

6. 读任务书 + `references/spec_extraction_guide.md` + `references/spec_json_format.md`。
7. 提取需求条目：
   - 逐章节扫描，识别功能描述、状态迁移、业务时序、错误处理、数据项、阈值
   - 每条需求分配 `REQ-XXX` ID（顺序编号，不跳号）
   - 填写 `source.section` 与 `source.page`（可定位到原文）
   - 提取验收标准（原文有则填，无则根据描述总结）
8. 归类功能域：把需求按业务域分组到 `features[]`（`F-XXX`）。
9. 提取业务状态机（`business_states[]`）、业务时序（`business_timing[]`）、错误处理（`error_handling[]`）、阈值（`thresholds[]`）。
10. 生成 `spec.json` + `spec_trace.json` + `uncovered.json`：
    - `spec.json` 写入 `outputs/s2/`
    - `spec_trace.json` 记录每条需求的原文段落（`REQ-001` → 原文引用）
    - `uncovered.json` 记录模糊描述、缺失项（原文没写清楚的点）

### 阶段 C：validate（rule）

11. 用 `schemas/spec.schema.json` 校验 `spec.json` 结构。
12. 校验引用一致性：
    - 每个 `features[].requirements` 里的 `REQ-ID` 必须存在于 `requirements[]`
    - 每个 `error_handling[].requirement`、`thresholds[].requirement` 引用必须存在
    - `REQ-ID` 不重复
    - `spec_trace.json` 覆盖全部 `REQ-ID`
13. 统计：`total_requirements`、`feature_count`、`uncovered_count`。
14. 更新 `state.spec`：
    - 成功且无未定项 → `status: success`
    - 有未定项但 spec 完整 → `status: partial`
    - 校验失败 / 提取失败 → `status: failed` + `error`
15. **不修改** `config.json`，**不触碰**其他 Skill 字段。

## 使用方法

```bash
# 前置：S1 已建立工作区（state.json 存在）
# 在项目 config.json 中配置 project.inputs.functional_spec

# 1. 运行 prepare 提取原始文本 + 生成任务书
python skills/spec-reader/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 按 outputs/s2/generation_brief.md 生成 spec.json

# 2. 运行 validate 终验
python skills/spec-reader/scripts/validate.py --config examples/gd32f205vet6/config.json

# 3. 查看结果
#    examples/gd32f205vet6/App/state.json     -> spec 字段
#    examples/gd32f205vet6/App/outputs/s2/    -> raw_text.md + spec.json
#                                               + spec_trace.json + uncovered.json
```

## 依赖

- Python 3.10+
- `jsonschema`（契约校验）
- `python-docx`（可选，.docx 提取）
- `pdfplumber`（可选，.pdf 提取）
- 未安装可选依赖时：对应格式不支持，报错退出（不降级为乱码提取）

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- **不要提取技术实现细节**：
  - 帧格式、命令码、波特率、校验方式
  - 引脚映射、DMA、外设选择
  - 消抖实现方式、主循环调度方式、心跳实现方式
  - 这些都是 S5b 从 `s5b_design_input.md` 读取的，S2 不能越界。
- **不要生成 `module_list.json`**——这是 S5b 产物。S2 只输出功能域标签（`features[]`）。
- **不要做 feature → module 映射**——这是 S5b 的职责。S2 只负责 feature 划分。
- **不要解析 `software_spec` 内容**——只登记路径到 state，S5b 自己读。
- 不要在 `spec.json` 中内联"如何实现"的描述，只写"要什么"。
- 数据量大的产物放 `outputs/s2/`，`state.json` 只存指针与统计。
- `spec.status=failed` 时不留下半成品产物文件（清空或标记无效）。

## 补充说明

### S2 与 S5b 的职责边界

**分界线**：
- S2 管"产品要什么"（需求侧）
- S5b 管"技术上怎么实现"（设计侧）

| 内容 | 提取方 | 说明 |
|---|---|---|
| 功能清单、功能描述 | S2 | 规格书里明确写的 |
| 业务状态、状态迁移条件 | S2 | 业务级（"上电后待机"） |
| 业务级时序（每 2 秒采集、蜂鸣 1s 响 1s 停） | S2 | 业务级 |
| 错误处理策略（重试次数、降级方式） | S2 | 业务级策略 |
| 数据项、上报周期、上报内容 | S2 | 业务级 |
| 阈值范围、边界条件 | S2 | 业务级 |
| 帧格式、命令码、波特率、校验方式 | **S5b** | 技术细节，来自 `s5b_design_input.md` |
| 引脚映射、DMA、外设选择 | **S5b** | 技术细节 |
| 消抖实现方式、主循环调度方式、心跳实现方式 | **S5b** | 技术细节 |
| 模块拆分（`module_list.json`） | **S5b** | 技术决策 |
| 流程图、Port 接口、C 代码 | **S5b** | 技术产物 |

**关键区分**：
- `spec.json`（S2 输出）= 需求条目清单 + 业务域标签
- `module_list.json`（S5b 输出）= 功能模块清单（可映射到 `.c/.h` 文件）
- 两者是不同层的东西，不要混。

### REQ 粒度原则

**REQ = 可独立验收的功能点**，不是规格书的每句话一条。

判断标准：
- 一条 REQ 对应一个可以独立"测试通过/不通过"的功能行为
- 合并原则：同一个功能行为的不同侧面（如"采集 + 采集失败处理"）合成一条
- 拆分原则：能独立验收、且验收标准不同的功能点分开

**SmartEnvGuard 示例**（12 条 REQ）：
- REQ-001 环境数据周期采集与保存（合并采集频率 + 数据保存）
- REQ-002 采集失败处理（合并保留旧值 + 连续失败告警 + 恢复）
- REQ-005 自动控制逻辑（合并自动/手动 + 阈值告警 + 蜂鸣 + 恢复）
- REQ-009 工作模式与告警优先级（合并三种模式 + 优先级规则）
- REQ-011 系统时序约束（合并主循环 + 各周期）
- REQ-012 数据有效范围与系统级约束（合并范围 + 无动态内存 + 24h 可用性）

**典型数量**：一个中等复杂度的项目 10~20 条 REQ。

### feature 划分原则

**feature = 业务域分组**，用于给 S5b 提供拆模块的锚点。

判断标准：
- **明显特征清楚即可**，不追求完美划分
- 一个 feature 覆盖 1~N 条 REQ，一条 REQ 通常归属 1 个 feature
- 一个 feature 大概率对应 S5b 的 1 个模块（约 80% 的情况）
- 剩下 20% 因人而异：可能合并进相邻 feature，也可能被拆成多个模块

**SmartEnvGuard 示例**（9 个 feature）：
- F-001 环境采集、F-002 本地显示、F-003 按键交互、F-004 自动控制、F-005 数据上报、F-006 运行指示
- F-007 工作状态管理（横切关注点）
- F-008 初始化与容错（横切关注点）
- F-009 系统约束（横切关注点）

**为什么不做 feature → module 映射**：
- 模块划分是设计决策，属于 S5b 职责
- 同样的 feature 在不同项目里可能拆法不同（如"按键交互"可以独立成模块，也可以并入"HMI 模块"）
- S5b 若发现 feature 划分不合适，用户可以用自然语言让 Agent 微调，不需要回头改 S2

### S2 的价值

把非结构化规格书转成结构化 JSON，让 S5b 不用再读原始规格书。S5b 拿 `spec.json` 就能知道：
- 有哪些功能要做什么（`requirements[]`）
- 这些功能能按什么业务域分组（`features[]`）
- 有哪些业务级状态机、时序、错误处理、阈值

S5b 再结合 `s5b_design_input.md`（技术细节），就能生成模块清单、流程图、代码。

### 后续扩展（v1 不做，留接口）

- **`spec_diff.json`**：规格书变更时，与旧版对比输出 diff，S5b 只处理变更部分（维护期最短路径）
- **`acceptance_criteria.json`**：独立验收标准文件，供 S8 单元测试使用
- **`feature_groups.json`**：独立功能域清单（v1 先内嵌在 `spec.json` 的 `features[]`）
- **多规格书合并**：项目有多个规格书文件时合并处理

这些扩展不影响 v1 的骨架：
- 输入是路径式（`project.inputs.functional_spec`），加多规格书时改为路径数组即可
- 输出是 `spec.json`（单一核心产物），扩展产物作为独立文件添加
- state 字段可增补，不改动已有字段

### 为什么不做"软件规格书解析"

初版曾打算让 S2 也解析软件规格书，提取任务划分、通信协议、状态机等技术细节。后来推翻，原因：

1. **越界**：软件规格书里的技术细节（帧格式、命令码、波特率）本应属于 S5b 的设计输入。
2. **冲突**：软件规格书和 `s5b_design_input.md` 可能不一致，边界模糊。按之前的结论：`s5b_design_input.md` 优先级最高。
3. **简化**：S2 只做"需求侧"，S5b 做"设计侧"，职责单一清晰。

因此 S2 只登记 `software_spec` 路径，S5b 自己读。