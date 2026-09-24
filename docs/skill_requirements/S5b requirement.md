# S5b requirement.md

# S5b port-contract-and-app Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：port-contract-and-app
- **Skill 用途**：从 S2 功能规格书、软件规格书、S4 硬件事实、用户设计输入及参考材料出发，定义平台无关的 Port / OSAL / Power 接口，生成 APP、协议层、设备驱动代码。核心是通过“功能模块拆分 → 单模块 Mermaid 流程图 → 单模块代码 → 顶层连接逻辑”的分步生成策略，保证应用逻辑代码的质量和可维护性。
- **触发时机**：在 S2 执行完成后触发，与 S5a 并行；S5b 可选依赖 S4 的硬件事实用于精准定义 Port 实例，但不依赖 S5a 的任何产物。

## 输入

从 `state.json` 读取：

- `spec.*`：S2 输出的功能规格书数据路径（必选）
- `circuit.facts.facts_path`：S4 输出的硬件事实报告路径（可选，用于精准定义 Port 实例与 APP 引脚引用）

从项目级 `config.json`（与全局 `config.json` 合并后）读取：

- `project.target`：MCU 型号
- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.architecture`：`"flat"` / `"layered"` / `"full"`，未配置时由 Agent 推断
- `project.power.enabled`：是否启用低功耗
- `project.rtos`：RTOS 类型（可选，未配置时由 Agent 从 S2 推断）
- `project.rtos_config.max_prio`：最大任务优先级（可选）
- `project.inputs.software_spec`：软件规格书路径（可选）
- `project.inputs.s5b_design_input`：S5b 设计输入路径（可选，默认 `docs/s5b_design_input.md`）
- `project.inputs.demos`：demo 程序目录列表（可选）
- `project.inputs.sdk`：SDK 目录（可选）
- `project.inputs.existing_project`：已有项目目录（可选）
- `project.inputs.ide_project`：IDE 项目文件路径（可选，未配置时自动发现）
- `s5b.language`：语言标准（可选，默认 `c99`）
- `s5b.port_split`：Port 拆分策略（可选，按应用需求推断）

### 输入材料说明

| 输入 | 用途 |
|---|---|
| 功能规格书（S2 输出 spec.json） | 提取功能需求、外设需求、性能指标 |
| 软件规格书（software_spec.*） | `s5b_design_input.md` 的补充技术输入（非 S2 产物）；提取任务划分、时序约束、通信协议、状态机、错误处理、日志、配置项；两者冲突时以 `s5b_design_input.md` 为准 |
| S4 circuit_facts.json | 硬件实际连接，用于精准定义 Port 实例、APP 引脚引用 |
| s5b_design_input.md | 用户对外设使用、功能映射、状态机、时序、错误处理、协议细节的明确指定 |
| demo 程序 | 学习代码风格、初始化写法、外设使用方式 |
| SDK | 学习厂商 API 命名、数据结构、调用约定 |
| 已有项目 | 参考工程结构、代码风格、模块划分 |
| IDE 项目文件 | 了解工程配置、include 路径、已存在的源文件 |

**关于设计输入文件 `s5b_design_input.md`**：支持多个标记段，Agent 按标记提取内容。

```markdown
## 功能规格：
- （功能规格书统一由 S2 解析，本段不再承载功能需求；S5b 从 S2 输出的 spec.json 读取功能规格数据）

## 状态机：
- （可选，用户直接指定状态、事件、迁移条件）

## 时序：
- （可选，用户指定周期、超时、去抖时间）

## 错误处理：
- （可选，用户指定重试次数、降级策略）

## 硬件使用：
- UART0：WiFi 模块，115200-8N1
- I2C1：EEPROM，400kHz
- GPIO：LED 指示（PC13）、按键输入（PA0）

## 功能映射：
- 电压检测：ADC1 采样 PA1，阈值 2.5V
- 按键检测：GPIO 输入 PA0，下降沿触发
```

用户未写部分，Agent 按经验推荐最优方案，并输出 `outputs/s5b/recommendations.json` 供用户确认。

## 输出

### 文件拆分原则

S5b 生成的代码**必须按功能模块拆分成多个文件**，统一输出到 S5b 产物目录（由 `docs/PROJECT_LAYOUT.md` 解析确定）：

- Port 接口：`Drivers/Port/Inc/<外设>_port.h`（按外设拆分）
- OSAL 接口：`Drivers/Port/Inc/osal.h`（单文件，如启用 RTOS，含 flat 架构——OSAL 与外设 Port 层正交）
- Power 接口：`Drivers/Port/Inc/power_port.h`（单文件，如启用低功耗且 `architecture != "flat"`）
- APP 主入口：`App/Src/app.c/h`（只做初始化和主循环/任务创建）
- APP 功能模块：`App/Src/app_<功能>.c/h`
- 任务化 APP：`App/Src/app_<功能>_task.c/h`（如启用 RTOS 且非 flat 架构；flat + RTOS 时 APP 在主循环中经 osal 调用 RTOS 原语，不建任务）
- 协议层：`App/Src/protocol_<名称>.c/h`
- 设备驱动：`Drivers/BSP/Src/driver_<设备>.c/h` 和 `Drivers/BSP/Inc/driver_<设备>.h`
- 主入口：`App/Src/main.c`（如不存在则由 S5b 创建）
- 流程图：`docs/flow/<模块>_<类型>.md`（Mermaid 格式，含 YAML front-matter）
- 未被使用的模块不生成。

### 写入 state.json（仅 s5b 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5b.status` | string | `pending` / `running` / `done` / `error` |
| `s5b.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5b.architecture` | string | 本次使用的架构 |
| `s5b.power_enabled` | bool | 是否启用低功耗 |
| `s5b.port_manifest` | string | `outputs/s5b/port_interface_manifest.json` 相对路径 |
| `s5b.port_headers` | array | `Drivers/Port/Inc/` 下 Port 头文件相对路径列表 |
| `s5b.osal_header` | string/null | `Drivers/Port/Inc/osal.h` 相对路径，裸机时为 null |
| `s5b.power_header` | string/null | `Drivers/Port/Inc/power_port.h` 相对路径，未启用低功耗时为 null |
| `s5b.app_sources` | array | `App/Src/` 下源文件相对路径列表 |
| `s5b.app_headers` | array | `App/Inc/` 下头文件相对路径列表 |
| `s5b.app_task_sources` | array | 任务化 APP 源文件列表，裸机时可为空 |
| `s5b.protocol_sources` | array | `App/Src/` 下协议层源文件相对路径列表 |
| `s5b.driver_sources` | array | `Drivers/BSP/Src/` 下设备驱动源文件相对路径列表 |
| `s5b.driver_headers` | array | `Drivers/BSP/Inc/` 下设备驱动头文件相对路径列表 |
| `s5b.main_source` | string | `App/Src/main.c` 相对路径 |
| `s5b.flows` | array | `docs/flow/` 下流程图文件相对路径列表（含 status 字段） |
| `s5b.flow_diffs` | object | 本次执行中每个流程图的 diff 结果（见“流程图 diff 机制”章节） |
| `s5b.traceability` | string | `outputs/s5b/traceability.json` 相对路径 |
| `s5b.capability_gap` | string/null | `outputs/s5b/capability_gap.json` 路径，无缺口时为 null |
| `s5b.ide_pending_files` | string | `outputs/s5b/ide_pending_files.json` 路径（兜底参考；IDE 同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成） |
| `s5b.error` | string/null | 错误信息 |
| `s5b.updated_at` | string | ISO 时间戳 |

### 写入 S5b 产物目录

**Port 接口（→ `Drivers/Port/Inc/`）**：

| 产物 | 内容说明 |
|---|---|
| `uart_port.h` | UART Port 接口（如有使用） |
| `i2c_port.h` | I2C Port 接口（如有使用） |
| `spi_port.h` | SPI Port 接口（如有使用） |
| `gpio_port.h` | GPIO Port 接口（如有使用） |
| `adc_port.h` | ADC Port 接口（如有使用） |
| `timer_port.h` | Timer Port 接口（如有使用） |
| `osal.h` | OSAL 接口（如启用 RTOS，含 flat 架构——OSAL 与 Port 层正交） |
| `power_port.h` | Power 接口（如启用低功耗且非 flat） |

**APP 与协议（→ `App/Src/`、`App/Inc/`）**：

| 产物 | 内容说明 |
|---|---|
| `app.c/h` | APP 主入口，只做初始化和主循环/任务创建 |
| `app_<功能>.c/h` | APP 功能模块 |
| `app_<功能>_task.c/h` | 任务化 APP（如启用 RTOS 且非 flat 架构） |
| `protocol_<名称>.c/h` | 协议层模块 |
| `main.c` | 主入口 |

**设备驱动（→ `Drivers/BSP/Src/`、`Drivers/BSP/Inc/`）**：

| 产物 | 内容说明 |
|---|---|
| `driver_<设备>.c/h` | 板载器件驱动 |

**流程图（→ `docs/flow/`）**：

| 产物 | 内容说明 |
|---|---|
| `<模块>_state.md` | 状态机流程图（Mermaid stateDiagram-v2 + YAML front-matter） |
| `<模块>_flow.md` | 顺序流程图（Mermaid flowchart + YAML front-matter） |
| `<模块>_sequence.md` | 时序图（Mermaid sequenceDiagram + YAML front-matter） |

**流程图 YAML front-matter 格式**：

```yaml
---
name: app_wifi_state
status: draft
version: 1.0
created_at: 2026-09-21T10:00:00
approved_at: null
approved_by: null
base_version: null
---
```

**status 取值与 Agent 行为**：

| 状态 | 含义 | Agent 行为 |
|---|---|---|
| `draft` | 草稿，未审核 | 可以修改，不生成代码 |
| `review` | 待审核 | 可以修改，不生成代码 |
| `approved` | 定稿 | 不改，可以生成代码 |
| `dirty` | 已定稿后被修改 | 需要重新审核，暂不生成代码 |
| `deprecated` | 废弃 | 不处理 |

### 写入 outputs/s5b/

| 产物 | 内容说明 |
|---|---|
| `outputs/s5b/port_interface_manifest.json` | 接口契约，结构由 `schemas/port_interface_manifest.schema.json` 约束 |
| `outputs/s5b/traceability.json` | 追踪矩阵（需求 → 文件，函数级条目可选；增量轮次仅更新变更模块），结构由 `schemas/traceability.schema.json` 约束 |
| `outputs/s5b/capability_gap.json` | 可选，能力缺口报告 |
| `outputs/s5b/recommendations.json` | 可选，Agent 推荐的方案清单 |
| `outputs/s5b/flow_index.json` | 流程图清单（含版本、状态） |
| `outputs/s5b/flow_diffs/<模块>_diff.json` | 每个流程图的 diff 结果（见“流程图 diff 机制”章节） |
| `outputs/s5b/mocks/` | 可选，Mock Port 实现 |
| `outputs/s5b/tests/` | 可选，单元测试 |

### 指针/数据分离规则

- 代码放 S5b 产物目录（`App/Src`、`Drivers/Port/Inc`、`Drivers/BSP/Src` 等）。
- 流程图放 `docs/flow/`。
- 数据产物放 `outputs/s5b/`。
- `state.json` 中只存指针与统计计数，不存数据本体，不存代码本体。

## Skill 目录结构（标准结构）

```text
port-contract-and-app/
├── SKILL.md
├── schemas/
│   ├── input.schema.json
│   ├── output.schema.json
│   ├── port_interface_manifest.schema.json
│   ├── traceability.schema.json
│   ├── capability_gap.schema.json
│   ├── flow_diff.schema.json
│   └── flow_index.schema.json
├── scripts/                            # rule 侧散件脚本（无 generate.py 总入口；代码生成为 Agent 职责）
│   ├── analysis.py                     # 配置/输入加载、Mermaid 解析、diff 图计算、能力缺口比对
│   ├── prepare.py                      # rule 准备：环境检查 + 任务书 generation_brief.md 生成
│   ├── flow_validator.py               # 流程图规范校验（支持 --file 单文件校验）
│   ├── flow_differ.py                  # 流程图 diff（逐模块判定 full/incremental/skip/blocked）
│   ├── diff_range_checker.py           # 生成后 diff 范围校验（拦截异常重写）
│   ├── validate.py                     # 收尾校验（include 规范/产物存在/state 写入）
│   ├── ide_pending_exporter.py         # IDE 待添加清单导出（实际同步由公共工具 skills/_shared/scripts/ide_sync.py 完成）
│   └── functional_decomposer.py        # 【规划中】功能模块拆分（S2 spec.json 就绪后实现，产出 outputs/s5b/module_list.json）
├── references/
│   ├── port_design_principle.md         # Port 设计原则
│   ├── osal_design_principle.md         # OSAL 设计原则
│   ├── software_spec_guide.md           # 软件规格书解析指南
│   ├── mermaid_flowchart_guide.md       # 顺序流程规范
│   ├── mermaid_state_guide.md           # 状态机规范
│   ├── mermaid_sequence_guide.md        # 时序图规范
│   ├── flow_to_code_mapping.md          # 流程图到代码映射规则
│   ├── flow_diff_rules.md               # 流程图 diff 规则
│   ├── incremental_generation_rules.md  # 增量生成规则
│   ├── ide_project_formats.md           # IDE 项目文件格式说明
│   └── file_split_guide.md              # 文件拆分规范
└── assets/
    ├── port_templates/                  # Port 接口模板库
    │   ├── uart_port.h.tpl
    │   ├── i2c_port.h.tpl
    │   ├── spi_port.h.tpl
    │   ├── gpio_port.h.tpl
    │   ├── adc_port.h.tpl
    │   ├── timer_port.h.tpl
    │   ├── osal.h.tpl
    │   └── power_port.h.tpl
    ├── flow_skeletons/                  # 流程图骨架
    │   ├── state_skeleton.md
    │   ├── flowchart_skeleton.md
    │   └── sequence_skeleton.md
    ├── port_interface_manifest_example.json
    ├── traceability_example.json
    └── flow_diff_example.json
```

## 执行步骤

S5b 分为两阶段执行：**阶段 A（模块级生成）** 和 **阶段 B（顶层连接生成）**。

### 阶段 A：模块级生成（80% 工作量）

**A.1 prepare（rule）**

1. 从 `state.json` 读取 `spec.*` 字段，确认 S2 已成功执行。
2. 读取 `circuit.facts.facts_path`（可选），了解硬件实际连接。
3. 读取项目级 `config.json`，与全局 `config.json` 合并。
4. 读取输入材料：功能规格书（S2 已解析）、软件规格书、`s5b_design_input.md`、demo、SDK、已有项目、IDE 项目文件。
5. **检查流程图现状**：调用 `flow_index` 读取 `outputs/s5b/flow_index.json`，确定：
   - 哪些流程图已存在（有 `base_version`）。
   - 哪些流程图是本次新增的。
   - 哪些流程图在上次执行后被修改过（mtime 变化或 git diff）。
6. **功能模块拆分**：调用 `functional_decomposer.py`，从 S2 输出的 `spec.json` 和设计输入 `s5b_design_input.md` 中提取功能模块清单，输出 `outputs/s5b/module_list.json`。清单包含：模块名、来源章节、依赖关系、需要工程师确认的点。
7. **能力缺口检测**：如果 S4 硬件事实存在，检查需求所需外设是否被硬件支持。发现疑似缺口时输出 `outputs/s5b/capability_gap.json`（warning 级，Agent 逐条复核后再定级，可能是网络名未识别而非真缺口），**不终止流程**；仅当复核确认为真缺口（error 级）时由 validate 收尾拦截。
8. **生成任务书** `outputs/s5b/generation_brief.md`（rule 侧 `prepare.py` 生成）：环境与目录落点、输入材料清单、硬件事实摘要、流程图现状、能力缺口、生成要求、增量模式等 9 节；模块清单（模块名/职责/图类型/依赖）由 Agent 拆分后先给用户确认再画图。
9. **生成推荐清单**（如有未指定项）：输出 `outputs/s5b/recommendations.json`，列出 Agent 推荐方案供用户确认。增量轮次不重复推荐用户已确认的方案，仅推荐本轮新增的未定项。
10. **流程图 diff 判定**（关键新增步骤）：
    - 对本次任务涉及的每个模块，读取现有流程图（`base_version` 对应的旧版本 + 当前文件）。
    - 调用 `flow_differ.py`，识别变更点（详见“流程图 diff 机制”章节）。
    - 输出 `outputs/s5b/flow_diffs/<模块>_diff.json`。
    - 判定每个模块的生成模式：`full`（首次生成或大重构） / `incremental`（增量） / `skip`（无变更） / `blocked`（dirty 或未定稿，暂不生成代码） / `deprecated`（废弃，移除对应代码）。

**A.2 生成流程图初稿（agent）**

11. 对每个功能模块，根据功能类型选择图类型：
    - 状态迁移 → `stateDiagram-v2`
    - 顺序流程 → `flowchart TD`（竖向；历史 `LR` 兼容）
    - 模块交互 → `sequenceDiagram`
12. 读取对应骨架模板（`assets/flow_skeletons/`），在骨架上填充内容，**图类型和布局方向由系统决定，不由 Agent 选择**。
13. 生成的流程图保存到 `docs/flow/<模块>_<类型>.md`，front-matter 中 `status: draft`，`base_version: null`。
14. 调用 `flow_validator.py` 校验流程图是否符合规范（节点命名、图类型、方向、初始态/终态标注）。

**A.3 审核（人工）**

15. S5b 生成流程图后，自动调用 `mermaid-cli` 渲染：
    - 每张图生成 PNG（或 HTML）到 `outputs/s5b/flow_preview/`。
    - 生成索引页 `outputs/s5b/flow_preview/index.html`，一页看全部流程图。
    - 渲染失败（语法错误、工具缺失）时，降级提示工程师手动用 Mermaid Live Editor 查看。
    工程师查看渲染后的流程图（Mermaid Live Editor 或 Typora）。
16. 如需修改，用自然语言告诉 Agent，Agent **以现有文件为锚点做定点修改**，不重新生成。
17. 工程师确认后，将 front-matter 的 `status` 改为 `approved`，`approved_at` 填当前时间，`base_version` 保留，文件设为只读。
18. 更新 `outputs/s5b/flow_index.json`（流程图清单，记录每个模块的当前版本、状态、base_version）。

**A.4 生成模块代码（agent）**

19. 遍历 `flow_index.json`，对每个模块按 `status` 判定处理方式：
    - `approved` 且无变更：`skip`，不生成代码。
    - `approved` 且本次有修改：`incremental`，走增量生成。
    - `draft` 或 `review`：不生成代码，报警告。
    - 新增模块：`full`，走全量生成。
20. **全量生成路径**（首次或大重构）：
    - Agent 按 `references/flow_to_code_mapping.md` 的映射规则，从 Mermaid 生成对应模块的完整 C 代码。
    - 生成 APP 功能模块 `App/Src/app_<功能>.c/h`。
    - 生成协议层 `App/Src/protocol_<名称>.c/h`（如需要）。
    - 生成设备驱动 `Drivers/BSP/Src/driver_<设备>.c/h`（如需要）。
21. **增量生成路径**（已有代码，流程图有小改动）：
    - 读取 `outputs/s5b/flow_diffs/<模块>_diff.json`，获取变更点。
    - 读取现有代码文件。
    - Agent 把“现有代码 + 变更点 + 映射规则”作为输入（规则见 `references/incremental_generation_rules.md`），生成“修改后的代码”。
    - **关键约束**：只改动与变更点相关的部分，其他代码原样保留。
    - 生成后调用 `diff_range_checker.py`，对比新旧代码 diff，校验变更范围是否合理（详见“diff 范围校验”章节）。
22. **重命名/删除处理**：
    - 流程图节点被重命名 → 同步重命名对应函数/变量。
    - 流程图节点被删除 → 从代码中移除对应函数。
    - 流程图节点被新增 → 在代码中新增对应函数。

**A.5 生成 Port 接口（agent）**

23. 从 `assets/port_templates/` 挑选所需的 Port 接口模板。
24. 按应用需求裁剪模板（去掉用不到的接口）。
25. 必要时扩展应用特有接口。
26. 生成 `Drivers/Port/Inc/*.h`。
27. 如启用 RTOS，生成 `Drivers/Port/Inc/osal.h`。
28. 如启用低功耗，生成 `Drivers/Port/Inc/power_port.h`（命名由设计输入或 Agent 推荐决定）。
29. 生成 `outputs/s5b/port_interface_manifest.json`。

### 阶段 B：顶层连接生成（20% 工作量）

**B.1 生成顶层连接逻辑（agent）**

30. 生成 `App/Src/app.c/h`（APP 主入口，只做初始化和主循环/任务创建）。
31. 生成 `App/Src/app_<功能>_task.c/h`（如启用 RTOS）。
32. 生成或更新 `App/Src/main.c`。
33. **可选**：生成顶层系统状态机流程图 `docs/flow/system_state.md`，展示模块间的调度关系。

### 阶段 C：校验与收尾

**C.1 validate（rule）**

34. 用 Schema 校验输出结构（manifest、traceability、flow_diff）。
35. **可选后处理**：生成 Mock Port 实现（`outputs/s5b/mocks/`），让 APP/Driver 在 Mock Port 下独立编译——不阻塞主流程，默认不执行，按需手动触发。
36. grep 检查：所有 APP/Driver/协议层源文件不 include 任何 HAL 头文件和 RTOS 头文件。
37. 生成追踪矩阵 `outputs/s5b/traceability.json`（粒度到文件级，函数级条目可选；增量轮次仅更新变更模块的条目）。
38. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程（S5b 产物源文件与 include 路径自动入工程；失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单）。
39. 更新 `state.json` 的 `s5b` 字段，含 `s5b.flow_diffs`。

## 依赖

- Python 3.10+（`diff`、`re` 标准库用于 diff 分析）
- jsonschema 库
- xml.etree（IDE 工程同步公共工具 `skills/_shared/scripts/ide_sync.py` 解析工程文件）
- 可选：openai/anthropic SDK（用于软件规格书解析和代码风格学习）
- 可选：mermaid 校验工具（用于流程图语法校验）

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- 不要修改 S2/S4 产出的文件。
- 不得依赖 S5a 的任何产物（S5b 与 S5a 并行）。
- 所有 APP / Driver / 协议层源文件不得 include 任何 HAL 头文件。
- 所有 APP / Driver / 协议层源文件不得 include 任何 RTOS 头文件。
- RTOS 相关调用必须通过 `osal.h`。
- Port 接口只使用基本类型和不透明句柄。
- DMA 不得单独暴露给 APP，应隐藏在 UART 等实现中。
- 不得把所有 APP 逻辑塞进一个 `app.c`（除非 `flat` 架构）。
- 不得把代码放在 `outputs/` 中，必须放在 S5b 产物目录。
- **不得在流程图未定稿（`status != approved`）时生成对应模块的代码。**
- **不得重新生成已有流程图，只能以现有文件为锚点做定点修改。**
- **不得在流程图无变更时重跑对应模块的代码生成（必须走 `skip` 分支）。**
- **不得在增量生成时重写整个文件（必须走 diff 范围校验，超出范围报警并终止）。**
- 换平台时，S5b 产物哈希必须保持不变（**仅限 layered/full 架构且硬件连接语义不变**；flat 架构因产物与平台耦合，需重跑 S5b）。
- 换 RTOS 时，S5b 产物哈希必须保持不变（限定条件同上）。

## 补充说明

### 两阶段生成策略

S5b 的核心策略是“**先模块，后连接**”：

| 阶段 | 工作量 | 核心任务 | 质量控制 |
|---|---|---|---|
| 阶段 A | 80% | 模块拆分 + 流程图 + 模块代码 | 流程图审核 + 映射规则 |
| 阶段 B | 20% | 顶层连接逻辑 | 系统总流程图 + 静态检查 |

**为什么先模块后连接：**

- 模块内部逻辑闭环，5~15 个节点，Agent 生成准确率高。
- 模块之间通过 Port 接口解耦，即使连接出错，改起来快。
- 工程师审核流程图比审核代码快 5~10 倍。

### 流程图中间层

流程图是 S5b 的核心中间表示：

| 决策项 | 由谁决定 | 怎么定 |
|---|---|---|
| 图类型 | 系统 | 按功能类型固定映射 |
| 布局方向 | 系统 | 顺序流程固定 `LR`（横向），状态机默认纵向 |
| 节点命名风格 | 系统 | 状态名大写、事件名小写、动作名动词开头 |
| 参数表达 | 系统（软约束） | 节点不得内联魔法数值（阈值/周期/超时等），以参数名表达，并旁注当前值（如 `超时判断 /* timeout_ms=500 */`），保证审图时可读；调参只改代码常量，不改流程图结构 |
| 初始态与终态 | 系统 | 强制要求标注 `[*]` 开始和结束 |
| 内容（状态、事件、动作） | Agent | Agent 根据需求填充 |

**流程图与代码一致性保障：**

- 定稿后加锁（文件设为只读），防止误改。
- Agent 只处理 `approved` 状态的流程图。
- 代码可手改，但手改后必须回填流程图（硬性规定）。

### 流程图 diff 机制

**这是 S5b 增量生成的核心。** 没有 diff，每次改动就会重跑整个模块，代码全变，回到 Vibe Coding 的老路。

#### 一、diff 的输入与输出

**输入**：

- 现有流程图文件 `docs/flow/<模块>_<类型>.md`（含 YAML front-matter）
- `flow_index.json` 中记录的 `base_version` 对应的旧版本（如有）
- Git 历史中的旧版本（如有）

**输出**：

- `outputs/s5b/flow_diffs/<模块>_diff.json`，结构由 `schemas/flow_diff.schema.json` 约束

**diff 结果结构示例**：

```json
{
  "module": "app_wifi",
  "base_version": "1.0",
  "current_version": "1.1",
  "graph_type": "stateDiagram-v2",
  "changes": {
    "states": {
      "added": ["RECONNECTING"],
      "removed": [],
      "renamed": []
    },
    "transitions": {
      "added": [
        { "from": "ERROR", "to": "RECONNECTING", "event": "on_retry" },
        { "from": "RECONNECTING", "to": "CONNECTED", "event": "on_success" }
      ],
      "removed": [],
      "modified": []
    },
    "actions": {
      "added": ["reset_retry_counter"],
      "removed": [],
      "modified": []
    }
  },
  "change_summary": "新增 ERROR → RECONNECTING → CONNECTED 重连路径",
  "generation_mode": "incremental"
}
```

#### 二、diff 的粒度

对不同类型的图，diff 关注点不同：

| 图类型 | diff 关注点 |
|---|---|
| `stateDiagram-v2` | 状态（新增/删除/重命名）、迁移（from/to/event 变化）、动作 |
| `flowchart` | 节点（新增/删除/重命名）、边（连接变化）、判断条件变化 |
| `sequenceDiagram` | 参与者变化、消息（新增/删除/重命名）、返回变化 |

#### 三、生成模式判定

diff 完成后，按下表判定生成模式：

| diff 结果 | 生成模式 | Agent 行为 |
|---|---|---|
| 首次生成，无旧版本 | `full` | 全量生成模块代码 |
| 大重构（diff 变化率 > 60%） | `full` | 全量生成（提示工程师确认） |
| 小改动（diff 变化率 ≤ 60%） | `incremental` | 只生成变更点对应代码 |
| 无变更 | `skip` | 跳过，不重跑 |

**变化率计算**：`变更的节点数 + 变更的边数) / (总节点数 + 总边数)`。

#### 四、增量生成的工作方式

**Agent 的输入**：

```text
现有代码：App/Src/app_wifi.c（基于流程图 v1.0）
变更点：diff json（新增 ERROR → RECONNECTING → CONNECTED 路径）
映射规则：references/flow_to_code_mapping.md
```

**Agent 的任务**：

```text
在现有代码中，只添加这条路径对应的处理逻辑，
其他代码原样保留。
```

**Agent 的输出**：

```text
修改后的 app_wifi.c
只改动与变更点相关的部分
```

**关键约束**：Agent 无权重写整个文件。它只做定点修改。

#### 五、diff 范围校验（拦截异常重写）

增量生成后，调用 `diff_range_checker.py` 对比新旧代码：

| 指标 | 预期 | 异常判定 |
|---|---|---|
| 新增行数 | 与变更点数量成正比 | 超出预期 3 倍 → 报警 |
| 删除行数 | 与删除节点数量成正比 | 超出预期 3 倍 → 报警 |
| 修改行数 | 与修改节点数量成正比 | 超出预期 3 倍 → 报警 |
| 无关行改动 | 应为 0 | > 0 → 报警 |

**报警处理**：

- 输出 `outputs/s5b/diff_anomaly.json`，记录异常详情。
- `s5b.status` 置为 `error`。
- 不覆盖原代码，保留当前为 `draft` 状态供人工审核。
- 提示工程师：“增量生成 diff 范围异常，请人工审核。”

**这一步是防止 Agent 手抖重写全文件的关键防线。**

#### 六、版本管理

每次流程图定稿，`version` 递增（如 `1.0` → `1.1`），旧版本通过以下方式保留：

- **首选**：Git 提交历史（每次定稿后提交一次）。
- **备选**：`docs/flow/.history/<模块>/<version>.md` 快照目录。

`base_version` 字段记录当前流程图是基于哪个版本修改的，用于 diff 对比。

### Port 接口设计原则

- 从应用需求出发定义接口，不从硬件外设出发。
- 可按应用需求拆分为 `uart_port.h`、`gpio_port.h` 等。
- 只使用平台无关类型：基本类型、不透明句柄。
- 错误码统一。
- 生命周期明确：init / open / close / deinit。
- 回调上下文明确：中断上下文可调用什么，不可调用什么。
- DMA 是 UART 等实现细节，不暴露给 APP。

### OSAL 接口设计原则

- 只使用平台无关类型。
- 不出现 `FreeRTOS.h`、`xTaskCreate`、`osThreadNew` 等 RTOS API。
- 统一错误码。
- 提供任务、队列、互斥锁、信号量、事件、时间、临界区、ISR 安全接口。
- 单文件 `osal.h`，不拆分（实际项目用到的 RTOS 接口通常不超过 5 个）。

### Power 接口设计原则

- **不预先固化接口名**，由 `s5c_design_input.md` 指定或 Agent 推荐。
- 典型接口：`enter_sleep_before()`、`enter_sleep()`、`wakeup_after_sleep()`、`clock_compensate()`。
- 用户已有方案时，严格按用户方案生成。

### 软件规格书解析

软件规格书应包含以下内容，Agent 需要从中提取：

- 任务划分与优先级
- 时序约束与实时性要求
- 通信协议（帧格式、命令码、校验方式）
- 状态机定义
- 错误处理策略
- 日志与调试要求
- 配置项与默认值

### 与 S5c 的契约

S5b 生成的 `port_interface_manifest.json` 是 S5c 实现 Port 的唯一依据。S5c 以 manifest 为主、头文件为辅做二次校验，不一致时报冲突并终止。

### 顶层连接逻辑的静态检查

阶段 B 生成的顶层连接逻辑需要做静态检查：

| 检查项 | 说明 |
|---|---|
| 模块调用接口一致性 | 调用方参数类型与被调方签名匹配 |
| 任务栈大小合理性 | 任务栈大小与函数嵌套深度匹配 |
| 时序约束满足 | 任务周期与实时性要求匹配 |
| 中断上下文安全 | ISR 中调用非 ISR 安全函数时报警 |

### 文件拆分示例

一个使用 UART + ESP32C2 WiFi 模块、I2C + EEPROM、LED 指示的 GD32F205 项目，S5b 输出示例：

```text
App/
├── Src/
│   ├── main.c
│   ├── app.c/h
│   ├── app_led.c/h
│   ├── app_wifi.c/h
│   ├── app_wifi_task.c/h
│   ├── protocol_at.c/h
│   └── ...
├── Drivers/
│   ├── Port/Inc/
│   │   ├── uart_port.h
│   │   ├── i2c_port.h
│   │   ├── gpio_port.h
│   │   ├── osal.h
│   │   └── power_port.h
│   └── BSP/
│       ├── Src/
│       │   ├── driver_esp32c2.c
│       │   └── driver_eeprom.c
│       └── Inc/
│           ├── driver_esp32c2.h
│           └── driver_eeprom.h
└── docs/flow/
    ├── app_wifi_state.md
    ├── app_led_flow.md
    └── app_key_flow.md
```