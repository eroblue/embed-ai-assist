# S5c port-implementer Skill 需求（增量版）

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：port-implementer
- **Skill 用途**：实现 S5b 定义的 Port / OSAL / Power 接口，将平台无关的调用翻译为具体 HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 Adapter 角色。`flat` 架构下跳过生成。**支持 per-peripheral 增量生成**：manifest 局部演进时只重生成受影响的外设文件。
- **触发时机**：在 S5a 和 S5b 都完成后触发。
- **执行模型**：三段式（rule prepare → Agent generate → rule validate），与 S5a / S5b 一致。确定性的规则用本地脚本；Port/OSAL/Power 适配代码由 Agent 生成——新增平台/新增 RTOS 无需为本 Skill 编写任何适配脚本。
- **维护期分支入口**：`code-fix`（见后文），用于 manifest 未变、但实现行为不符合预期时的定点修复。

## 输入

### 从 `state.json` 读取

**S5a 字段**（来源：S5a hardware-initializer）：

- `s5a.init_sources`：S5a 产物源文件列表（`Drivers/BSP/Src/` 下）
- `s5a.init_headers`：S5a 产物头文件列表（`Drivers/BSP/Inc/` 下）
- `s5a.entry_source`：S5a 总入口源文件路径
- `s5a.rtos_hw_init`：RTOS 硬件初始化文件路径（可选）
- `s5a.power_init`：低功耗初始化文件路径（可选）
- `s5a.hardware_capabilities`：硬件能力清单路径
- `s5a.architecture` / `s5a.rtos` / `s5a.power_enabled`：本次使用的架构 / RTOS / 低功耗配置

**S5b 字段**（来源：S5b port-contract-and-app）：

- `s5b.port_manifest`：接口契约路径（`outputs/s5b/port_interface_manifest.json`）
- `s5b.port_headers`：Port 头文件路径列表（`Drivers/Port/Inc/` 下）
- `s5b.osal_header`：OSAL 头文件路径（可选，裸机为 null）
- `s5b.power_header`：Power 头文件路径（可选，未启用低功耗为 null）
- `s5b.architecture` / `s5b.rtos` / `s5b.power_enabled`：本次使用的配置

### 从项目级 `config.json`（与全局 `config.json` 合并后）读取

- `project.target`：MCU 型号
- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.rtos`：RTOS 类型
- `project.architecture`：架构
- `project.power.enabled`：是否启用低功耗
- `project.inputs.ide_project`：IDE 项目文件路径（可选，缺省按 IDE 工程目录自动发现）
- `s5c.platform`：平台标识（文件命名后缀）
- `s5c.hal_framework`：HAL 框架（用于定位参考材料）

### 可选参考材料

- `references/demos/`：demo 程序（学习 API 写法）
- `references/sdk/`：SDK 源码（确认函数名/枚举名）
- `references/existing_project/`：已有项目（代码风格参考）

### 历史产物（增量机制依据）

- `outputs/s5c/port_manifest_snapshot.json`：上轮 manifest 的 per-peripheral 签名摘要（可选，首次执行不存在 → 全量建基线）
- `outputs/s5c/file_hashes.json`：上轮生成文件的哈希基线（可选，首次执行不存在 → 全部视为"未改过"）

### 用户设计输入（`docs/s5c_design_input.md`）

用户向 Agent 传达实现约束的输入通道，**优先级高于自动推断**。文件不存在、内容为空或全部为 `none` 时，改由 Agent 基于 `hardware_capabilities`、接口契约与参考材料自主判断。

```markdown
# s5c设计输入， 告诉 Agent 实现约束.

## 低功耗方案
- 空闲时进入 STOP 模式
- 唤醒源：EXTI0 (PA0)、RTC 闹钟
- 睡眠前：关闭 UART、SPI 时钟

## 已有实现
- 参考 references/existing_project/power_mgmt.c
- 沿用 enter_sleep_before → enter_sleep → wakeup_after_sleep 命名
```

两段分别约束：低功耗策略（唤醒源/时钟门控/恢复流程，仅 `power.enabled` 时生效）、已有实现参考（命名约定与代码风格沿用）。

## 输出

### 文件拆分原则

S5c 生成的 Port 实现**必须按外设拆分成多个文件**，输出目录由 `docs/PROJECT_LAYOUT.md` 解析确定（32 位 layered 典型值为 `Drivers/Port/Src/`——与 S5b 的 Port 接口头目录 `Drivers/Port/Inc/` 对称）。

| 产物 | 生成条件 |
|---|---|
| `port_impl_uart_<平台>.c` | manifest 中存在 UART Port |
| `port_impl_i2c_<平台>.c` | manifest 中存在 I2C Port |
| `port_impl_spi_<平台>.c` | manifest 中存在 SPI Port |
| `port_impl_gpio_<平台>.c` | manifest 中存在 GPIO Port |
| `port_impl_adc_<平台>.c` | manifest 中存在 ADC Port |
| `port_impl_timer_<平台>.c` | manifest 中存在 Timer Port |
| `port_impl_pwm_<平台>.c` | manifest 中存在 PWM Port |
| `port_impl_osal_<rtos>.c` | `project.rtos != "none"`（含 flat 架构） |
| `port_impl_power_<平台>.c` | `project.power.enabled == true` 且非 flat |

**命名规范**：

- `<平台>`：小写字母，来自 `s5c.platform`（如 `gd32f205` / `stm32f103` / `ft61f14x`）
- `<rtos>`：全小写、连字符转下划线（如 `freertos` / `rtthread` / `zephyr`）
- `<外设>`：小写（uart / i2c / spi / gpio / adc / timer / pwm）

未被使用的外设不生成。每个实现文件 include S5b 的 Port 头文件，只实现对应接口。

### 写入 `state.json`（仅 `s5c` 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5c.status` | string | `pending` / `running` / `done` / `error` / `skipped` |
| `s5c.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5c.architecture` | string | 本次使用的架构 |
| `s5c.power_enabled` | bool | 是否启用低功耗 |
| `s5c.generation_brief` | string | 任务书路径（`outputs/s5c/generation_brief.md`） |
| `s5c.port_impl_sources` | array | Port 实现源文件相对路径列表 |
| `s5c.osal_impl` | string/null | OSAL 实现源文件相对路径，裸机时为 null |
| `s5c.power_impl` | string/null | Power 实现源文件相对路径，未启用低功耗时为 null |
| `s5c.skipped_files` | array | 因用户已修改而跳过的文件列表（skip-if-modified） |
| `s5c.port_manifest_snapshot` | string/null | 本轮写入的 manifest 快照路径（`outputs/s5c/port_manifest_snapshot.json`） |
| `s5c.port_diffs` | array | 本轮每外设 diff 结果文件路径列表（`outputs/s5c/port_diffs/*.json`） |
| `s5c.generation_modes` | object | 每外设生成模式映射 `{ "uart": "incremental", "i2c": "full", ... }` |
| `s5c.error` | string/null | 错误信息 |
| `s5c.updated_at` | string | ISO 时间戳 |

契约由 `schemas/output.schema.json` 约束。**首次执行（无 snapshot）时 `port_diffs` / `generation_modes` 可为空，全部按 full 建基线。**

### 写入 S5c 产物目录（Agent 生成的代码）

目录由 `docs/PROJECT_LAYOUT.md` 解析（prepare 段已幂等创建骨架），任务书给出确切路径。

### 写入 `outputs/s5c/`（数据）

| 产物 | 内容说明 |
|---|---|
| `generation_brief.md` | Agent 任务书（prepare 段）：manifest 接口清单 / 能力供给 / 映射要点 / ISR 规范 / 每外设生成模式 / 禁止事项 |
| `capability_gap.json` | 可选，prepare 阶段检测到 S5b 需要的硬件能力在 S5a 能力清单中不存在时输出，并**终止执行** |
| `file_hashes.json` | 生成文件哈希（skip-if-modified 依据；**用户手改检测维度**） |
| `port_manifest_snapshot.json` | 上轮 manifest 的 per-peripheral 签名摘要（**接口变化检测维度**，validate 成功后写入） |
| `port_diffs/<外设>_diff.json` | 每外设 diff 结果（变化明细 + generation_mode，prepare 阶段产出） |
| `diff_check_result.json` / `diff_anomaly.json` | 增量范围校验结果 / 异常报告（有 incremental 模块时产出） |
| `recommendations.json` | 可选，未指定项推荐清单 |

### 指针 / 数据分离规则

- 代码放 S5c 产物目录（`Drivers/Port/Src/`，由布局解析确定）
- 数据产物放 `outputs/s5c/`
- `state.json` 只存指针与统计，不存数据本体，不存代码本体

## Skill 目录结构（标准结构）

```text
port-implementer/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（S5a/S5b 就绪性 + 一致性检查）
│   ├── output.schema.json             # 输出契约（state.json 的 s5c 字段，含增量字段）
│   ├── capability_gap.schema.json     # 能力缺口报告契约
│   ├── port_diff.schema.json          # 【新增】per-peripheral diff 结果契约
│   └── port_manifest_snapshot.schema.json  # 【新增】manifest 快照契约
├── scripts/                            # rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                     # 共享分析（配置加载/manifest 解析/能力缺口/残留检测/哈希/manifest diff）
│   ├── prepare.py                      # 阶段 1：就绪检查 + 一致性检查 + 能力缺口 + manifest diff + 残留清理 + 任务书
│   ├── port_differ.py                  # 【新增】per-peripheral 生成模式判定（full/incremental/skip/blocked/deprecated）
│   ├── diff_range_checker.py           # 【新增】增量代码范围校验（与 S5b 复用，建议提升到 _shared）
│   └── validate.py                     # 阶段 3：产物校验 + 写快照 + IDE 同步调用
├── references/
│   ├── hal_mapping_guide.md            # HAL 映射指南（厂商 API ↔ Port 接口）
│   ├── rtos_mapping_guide.md           # RTOS 映射指南（RTOS API ↔ OSAL 接口）
│   ├── port_impl_pattern.md            # 实现模式（环形缓冲 / DMA 骨架 / 错误码映射）
│   ├── isr_safety_rules.md             # 中断安全规范（回调判空 / 临界区 / ISR 上下文约束）
│   ├── port_diff_rules.md              # 【新增】per-peripheral 变化率算法 / 版本管理 / blocked 判定
│   └── incremental_generation_rules.md # 【新增】定点修改原则 / 范围校验阈值 / 异常处置
└── assets/
    └── port_impl_example.c             # 实现示例
```

> IDE 工程同步公共工具位于 `skills/_shared/scripts/ide_sync.py`（跨 Skill 共享，S5a/S5b/S5c 各自 validate 段调用）。
>
> `diff_range_checker.py` 建议提升到 `skills/_shared/scripts/`，S5b/S5c 共用；若不提升，S5c 内部独立实现，接受轻度重复。
## 生成模式总览（新增）

生成模式由 `port_differ.py` **逐外设判定**（同一轮中 uart 可 full、i2c 可 incremental、gpio 可 skip）。

### per-peripheral 判定矩阵

**两个正交维度**：

| 维度 | 依据 | 由谁检测 |
|---|---|---|
| **用户手改** | 文件当前 hash vs `file_hashes.json` 基线 | prepare 阶段 |
| **接口变化** | 本轮 manifest 该外设签名 vs `port_manifest_snapshot.json` | prepare 阶段 |

交叉判定：

| 文件 hash | 外设签名 | 判定 | 处置 |
|---|---|---|---|
| 一致（未手改） | 一致（未变） | **skip** | 绝不动该文件 |
| 一致（未手改） | 不一致（变化率 ≤ 60%） | **incremental** | Agent 定点修改 |
| 一致（未手改） | 不一致（变化率 > 60% / 首次 / 快照缺失） | **full** | Agent 全量重生成该文件 |
| 不一致（用户手改） | 一致（接口未变） | **skip + 标注漂移** | 保留手改，任务书标注"该文件已与上游 manifest 脱钩" |
| 不一致（用户手改） | 不一致（接口变化） | **blocked** | 报告用户（冲突：手改 vs 上游变更），不自行处理 |
| 文件不存在 | 存在（新外设） | **full** | 首次生成 |
| 文件存在 | 不存在（外设删除） | **deprecated** | 移除文件（含 IDE 引用由 ide_sync 收口） |

### 变化率算法

对单个外设的 manifest 条目（`headers[].logical_instances / interfaces / callbacks`），做结构化字段级 diff：

- 总字段数 = 实例数 + 接口签名数 + 回调数 + 各字段属性数
- 变化率 = 有增/删/改的字段数 ÷ 总字段数

阈值：

- `> 60%` → `full`
- `≤ 60%` → `incremental`
- `= 0` 且 hash 一致 → `skip`

### 首次执行（无 snapshot）

`port_manifest_snapshot.json` 不存在 → **全部 full**，任务书标注"建立基线"。

### 与 S5b 的一致性

判定机制对标 S5b 的 `flow_differ.py`（full/incremental/skip/blocked/deprecated），命名和阈值保持一致，便于用户建立统一心智模型。

## 执行步骤

### 阶段 A：prepare（rule）

1. 从 `state.json` 读取 `s5a.*` 和 `s5b.*` 字段，确认 S5a 和 S5b 均已成功执行。
2. 读取项目级 `config.json`，与全局 `config.json` 深合并。
3. **配置一致性检查**（防漂移）：比对 `s5a.rtos/architecture/power_enabled` 与 `s5b.*` 对应字段，不一致 → 写 error（提示重跑其中一方使配置对齐）并终止（退出码 2）。
4. **能力缺口前置检测**：遍历 manifest 需要的硬件能力，在 `hardware_capabilities.json` 中查找；不存在 → 输出 `capability_gap.json` 并终止（退出码 2）。
5. **flat 判定**：`architecture == "flat"` → 跳过生成（S5b 已直接对接厂商库），`s5c.status` 置 `skipped`，终止。
6. **用户修改检测**：比对 `file_hashes.json`，标记哪些文件被用户改过。
7. **per-peripheral diff**（本次新增）：
   - 读 `outputs/s5c/port_manifest_snapshot.json`（如存在）
   - 调 `port_differ.py` 逐外设判定生成模式 → 产出 `outputs/s5c/port_diffs/<外设>_diff.json`
   - 判定结果写入任务书
8. **旧文件清理**：
   - 删除 S5c 产物目录下 **非当前平台/非当前 RTOS 的 `port_impl_*.c` 且未被标记为用户修改**的文件（换平台/换 RTOS 残留文件会导致编译失败）
   - 首跑（`file_hashes.json` 不存在）→ 所有文件视为"未改过"，正常清理
9. **生成任务书** `outputs/s5c/generation_brief.md`，内含：
   - 项目信息（平台、RTOS、架构、低功耗）
   - S5a 能力清单摘要（硬件实例、引脚、中断号）
   - S5b manifest 接口清单（每个外设的逻辑实例、接口签名、回调约定）
   - **每外设生成模式表**（外设 / mode / 原因 / 用户手改状态 / 接口变化摘要）
   - 映射要点（HAL API → Port 接口的对应关系）
   - ISR 安全规范引用
   - 用户修改文件清单（跳过重写，标注 ⚠️ 漂移风险）
   - 禁止事项
10. **生成推荐清单**（如有未指定项）：输出 `recommendations.json`（可选）。
11. 更新 `state.s5c.status = running`。

### 阶段 B：generate（agent）

12. 读任务书 + `SKILL.md` + `references/hal_mapping_guide.md` + `references/rtos_mapping_guide.md` + `references/port_impl_pattern.md` + `references/isr_safety_rules.md`；有 incremental 模块时加读 `references/incremental_generation_rules.md`。
13. 读 `docs/s5c_design_input.md`：存在且非空时以其为准；空/缺失时基于 `hardware_capabilities` 与参考材料自主判断。
14. 读 manifest + capabilities + 标准外设库头文件，**核对将要用到的 API 函数名/枚举名/时钟使能宏**——不确定的留 `/* TODO: */` 注释，不臆造 API。
15. **按任务书的生成模式表逐外设处理**：
    - `full`：全量生成该外设 `.c` 文件（首次 / 变化率 >60% / 快照缺失）
    - `incremental`：**只做定点修改**（`references/incremental_generation_rules.md`），不重写整个文件
    - `skip`：**绝对不动该文件**（含用户手改、接口未变两类）
    - `blocked`：报告用户（手改 + 上游变更冲突），不自行处理
    - `deprecated`：移除对应代码文件（含 IDE 引用由 ide_sync 收口）
16. 若 `project.rtos != "none"`，生成 `port_impl_osal_<rtos>.c`。
17. 若 `project.power.enabled == true`，生成 `port_impl_power_<平台>.c`。
18. 遵守中断安全规范：ISR 内调用回调前**必须判断函数指针非 NULL**（回调未注册时清除中断标志直接返回，不得裸调）；DMA 隐藏在 Port 实现内。

### 阶段 C：validate（rule）

19. 产物校验：
    - manifest 中每个接口在对应实现文件中都有定义（全覆盖）
    - 禁止 include 应用头文件（`app*.h` / `protocol_*.h`）
    - ISR 回调判空抽查（grep 回调调用点，检查前置判空）
    - mtime 守卫：full/incremental 模块代码须晚于任务书
20. **增量范围校验**（有 incremental 时）：调 `diff_range_checker.py`，异常（退出码 1）→ 报 `diff_anomaly.json`，按 `references/incremental_generation_rules.md` 处置，**不得自行修复后继续**。
21. 记录文件哈希到 `outputs/s5c/file_hashes.json`（validate 成功后写入；**用户手改过的文件保留旧基线**，确保下次仍被识别为已修改）。
22. **写入 manifest 快照**：把本轮 manifest 的 per-peripheral 签名摘要写入 `outputs/s5c/port_manifest_snapshot.json`（作为下轮 diff 基线）。
23. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程：
    - 扫描**目标工程根的源码目录**（`App/Src` + `Drivers/BSP/Src` + `Drivers/Port/Src` 等，由布局解析确定）
    - 差异同步（新增/删除/改 include 路径）
    - 失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单
24. 更新 `state.s5c` 字段：
    - 成功 → `status: done` + `port_manifest_snapshot` 路径 + `port_diffs` 列表 + `generation_modes` 映射
    - flat → `status: skipped`
    - 校验失败 → `status: running`（保持，Agent 修复后重跑 validate）
    - 环境/契约失败 → `status: error`

> **编译验证由 S12 workflow-runner 在 S5c 之后编排 S7 build 执行，S5c 自身不调用工具链。**
## 分支入口：code-fix（按需触发，默认不执行）

**用途**：manifest 未变、文件 hash 未变、但实现行为不符合预期时，由用户直接指定"文件 + 函数 + 症状"，Agent 定点修复。**不走 prepare 主流程**。

**设计依据**：S5b 已立下的"分支入口原则"——不走完整主流程的维护操作作为独立 Agent 入口新增章节，不改动主流程与散件脚本；按需触发、默认不执行；**禁止为预留而建空壳脚本或空壳参数**。

### 触发条件（用户显式发起）

- 用户在对话中指明：文件路径 + 函数名 + 预期行为 vs 实际行为
- 或用户提供日志/现象描述 + 定位线索

### 执行流程

1. `[agent]` 读指定文件 + 用户描述 + SKILL.md + references（hal_mapping_guide / port_impl_pattern / isr_safety_rules）
2. `[agent]` 定位问题 → 向用户确认修复方案（先方案后动手）
3. `[agent]` 定点修改，不做无关重构
4. `[rule]` 最小校验子集：include 规则（不 include app*/protocol*）+ ISR 回调判空（若改动涉及 ISR）；不跑全量 validate，不做 manifest 全覆盖检查
5. `[rule]` 更新 `outputs/s5c/file_hashes.json`：保留该文件的旧基线（让该文件进入"用户维护"状态），或直接标记 `skipped_files` 追加该文件
6. `[agent]` 向用户报告改动摘要（文件 / 函数 / 改动前后对比 / 未验证项）

### 不做

- 不跑 prepare（不做就绪/一致性/能力缺口检查）
- 不跑完整 validate（只跑增量相关子集）
- 不重新生成任何其他文件
- 不改动 `state.s5c.status`（主流程此前已 done，code-fix 是叠加维护，不改变状态）
- 不覆盖已有 `port_manifest_snapshot.json`（不影响下轮主流程 diff）
- 不修改 S5a/S5b 产物

### 与 skip-if-modified 的协同

code-fix 修完 → 更新 file_hashes.json → 下次主流程 prepare 检测到 hash 不一致 → 任务书标注"用户已修改" → Agent 主流程 skip 该文件 → **修复被保留**。

这是设计意图，不是副作用：**code-fix 天然产出"用户维护文件"**，无需额外机制。

### 后续可能的扩展入口（描述原则，不预建）

- `code-explain`：解释某段实现的意图（只读）
- `code-refactor`：重构某文件（不改行为，需要跑最小校验子集）
- `code-add`：手动新增一个 Port 实现（不走 manifest）

以上入口**只在 SKILL.md 描述原则，不预先建空壳脚本**，需要时按同一模式实现。

## 向后兼容

改造增量机制时，必须兼容已在跑的老项目：

### 1. 无 `port_manifest_snapshot.json` 的老项目

首次跑改造后的 S5c → snapshot 不存在 → **全部按 full 生成**，任务书标注"建立基线"。validate 成功后写入第一份 snapshot，之后进入增量模式。

### 2. 无 `port_diffs` / `generation_modes` 字段的老 state

prepare 读 state 时对这些新字段给默认值（空 array / 空 object），避免 schema 校验失败。

### 3. `file_hashes.json` 与 `port_manifest_snapshot.json` 的关系

- `file_hashes.json`：**用户手改检测**，schema 不变
- `port_manifest_snapshot.json`：**接口变化检测**，新增
- 两者是**正交维度**，交叉判定（见"生成模式总览"）
- `file_hashes.json` 中"用户手改过的文件保留旧基线"的现有逻辑**保持不变**

### 4. 改造顺序建议

1. **只观察不改行为**：先跑通"read snapshot → diff → 任务书写 mode"链路，但所有 mode 都执行 full
2. 对比几轮 diff 结果，确认判定逻辑正确
3. 再打开 full / incremental / skip 真实分支
4. 最后把 `diff_range_checker.py` 从 S5b 提升到 `_shared`
5. 更新 SKILL.md 和 references

每一步都可回退。

## 使用方法

```bash
# 前置：S2、S3、S4、S5a、S5b 已在同一项目执行
python skills/port-implementer/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → 检查任务书的"每外设生成模式表" →
# → Agent 按模式生成（full/incremental/skip/blocked/deprecated）→
python skills/port-implementer/scripts/diff_range_checker.py --config examples/gd32f205vet6/config.json   # 有 incremental 时
python skills/port-implementer/scripts/validate.py --config examples/gd32f205vet6/config.json

# 维护期分支入口（不进主流程）：
#   用户直接告诉 Agent：文件 + 函数 + 症状，走 code-fix 流程
```

## 依赖

- Python 3.10+
- `jsonschema`（契约校验）
- `xml.etree`（IDE 工程同步公共工具使用）
- **不需要交叉编译工具链**（编译验证移交 S7 build）

## 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 成功（含 skipped） |
| 1 | 产物校验失败 / 增量范围异常（state 保持 running，Agent 修复后重跑） |
| 2 | 配置错误 / 就绪失败 / 能力缺口 / 一致性冲突（state 写 error） |

## 禁止事项

**rule 脚本侧**：

- 不修改 `config.json`，不读写其他 Skill 的字段。
- 不生成任何 C 代码。
- 不修改 `port_manifest_snapshot.json` 的历史版本（只追加新版本；旧版本保留用于回溯）。

**Agent 侧**：

- 不要修改 S5a / S5b 产出的文件（含所有 `<外设>_port.h`、`osal.h`、`power_port.h` 接口定义）。
- 不得写任何应用业务逻辑。
- 不得生成 HAL 初始化代码（S5a 职责）。
- 必须优先读取 `port_interface_manifest.json`，不得硬解析 C 头文件。
- 硬件只依据 `hardware_capabilities.json`，**禁止直接读取 S3/S4 数据**。
- 能力缺口必须报 `capability_gap` 终止（prepare 阶段），不得偷偷改接口或降级实现。
- **ISR 内回调调用前必须判空**，不得裸调未注册的回调。
- 不得把所有 Port 实现塞进一个文件，必须按外设拆分。
- 不得把代码放在 `outputs/` 中，必须放在 S5c 产物目录（布局解析确定）。
- **不重写任务书标注"用户已修改"的文件**（skip-if-modified）。
- **`incremental` 模式无权重写整个文件**，只做定点修改；diff 范围异常时不得自行修复。
- **`blocked` 模式必须报告用户**（手改 + 上游变更冲突），不自行处理。
- **`skip` 模式绝对不动文件**（含用户手改与接口未变两类）。
- **首次执行（无 snapshot）时全部按 full 建基线**，不跳过任何文件。
- 不直接修改 IDE 工程文件——同步统一由公共工具 `skills/_shared/scripts/ide_sync.py` 完成。
- **code-fix 分支入口不做全量 validate**，只做最小校验子集；不改变 `state.s5c.status`；不动 `port_manifest_snapshot.json`。

## 补充说明

### 换平台 / 换 RTOS 的重跑规则

| 场景 | 重跑范围 |
|---|---|
| 换 MCU | S3 → S4 → S5a → S5c（触发旧文件清理 + manifest diff 判定全部 full）；S5b 产物不变（layered/full） |
| 换 RTOS | S5a（rtos_hw_init）→ S5c（OSAL 实现替换 + 清理旧 RTOS 残留）；S5b 产物不变；**OSAL diff 判定通常为 full（RTOS 名变化即触发）** |
| manifest 新增外设 | 只跑 S5c；该外设 full 生成，其他外设按 diff 判定 |
| manifest 改单外设接口 | 只跑 S5c；该外设 incremental（≤60%）或 full（>60%），其他外设 skip |
| flat 架构换平台 | S5c 跳过生成；需重跑 S5b（其产物平台相关） |

### 能力缺口处理

如果 S5b 定义的 Port 接口需要某硬件能力，但 S5a 的 `hardware_capabilities.json` 中没有提供，S5c 在 **prepare 阶段**输出 `capability_gap.json` 并终止（退出码 2）。**不得尝试修改接口或降级实现**——缺口是契约层问题，修复要回 S5a/S5b。

### skip-if-modified（用户修改检测）

与 S5b 相同的整文件级哈希比对：

1. validate 成功后把本轮生成文件哈希记入 `outputs/s5c/file_hashes.json`
2. prepare 重跑时逐文件比对：
   - 不一致 = 用户改过 → 任务书标注"跳过重写"
   - 一致 = 正常重生成
3. 被跳过的文件不接收上游变化；**删除该文件即恢复自动生成**
4. 跳过清单写入 `state.s5c.skipped_files`

**风险提示**：跳过的文件与上游 manifest 会逐渐漂移——接口变了、实现没跟上。任务书会在"用户修改文件清单"处标注 **⚠️ 接口漂移风险**，用户需自行判断是保留手改还是恢复自动生成。

**与 code-fix 的协同**：code-fix 修完的文件自动获得"用户维护"状态，无需额外操作。

### per-peripheral diff 细则

**snapshot 结构**（`port_manifest_snapshot.json`）：

```json
{
  "manifest_hash": "sha256:...",
  "captured_at": "2026-09-29T...",
  "peripherals": {
    "uart": {
      "signature_hash": "sha256:...",
      "instances": ["wifi", "debug"],
      "interface_count": 8,
      "callback_count": 1
    },
    "i2c": { }
  }
}
```

**diff 结果结构**（`port_diffs/<外设>_diff.json`）：

```json
{
  "peripheral": "uart",
  "generation_mode": "incremental",
  "signature_changed": true,
  "change_rate": 0.15,
  "file_hash_changed": false,
  "changes": [
    { "type": "interface_added", "name": "uart_send_dma" },
    { "type": "interface_modified", "name": "uart_recv", "field": "timeout_ms" }
  ],
  "reason": "接口签名变化率 15% ≤ 60%，且用户未手改该文件"
}
```

### Port 实现的状态管理

每个 Port 实例（如 UART 的两个逻辑实例 wifi/debug）需要保存自己的状态（接收缓冲、回调函数指针等）。**建议实现约定**：

- 文件内 `static` 数组，按 instance id 索引（如 `static uart_impl_ctx_t s_uart_ctx[UART_PORT_COUNT];`）
- 不动态分配（符合"不用动态内存"约束）
- 上下文结构体声明在实现文件内（`static` 类型），不进头文件

### IDE 工程同步

IDE 工程文件（`.uvprojx` / `.ewp`）由公共工具 `skills/_shared/scripts/ide_sync.py` 同步：

- **扫描范围**：目标工程根下的**源码目录**（`App/Src` + `Drivers/BSP/Src` + `Drivers/Port/Src` 等，由 `PROJECT_LAYOUT.md` 解析确定），不是硬编码 `src/`
- **差异同步**：新增/删除/改 include 路径，保留原工程配置
- **并发安全**：全局文件锁
- **幂等**：重复调用不产生重复条目；无变化不写盘
- **备份/回滚**：修改前备份 `.bak`，写入失败自动恢复
- **失败不中断**：输出 `outputs/_shared/ide_sync_manual.md` 手动清单
- IDE 工程由用户手动创建，工具只做增量同步

### 文件拆分示例

一个使用 UART、I2C、GPIO、FSMC（LCD）、ADC 的 GD32F205 项目：

```text
Drivers/Port/
├── Inc/                       # S5b 产出（接口头）
│   ├── uart_port.h
│   ├── i2c_port.h
│   ├── gpio_port.h
│   ├── adc_port.h
│   ├── timer_port.h
│   └── osal.h                 # RTOS 时
└── Src/                       # S5c 产出（实现）
    ├── port_impl_uart_gd32f205.c
    ├── port_impl_i2c_gd32f205.c
    ├── port_impl_gpio_gd32f205.c
    ├── port_impl_adc_gd32f205.c
    ├── port_impl_timer_gd32f205.c
    └── port_impl_osal_freertos.c
```

### 接口语义约定来源

接口语义（错误码、超时、线程安全）按 **S5b 的 `references/port_design_principle.md`** 同一约定实现。S5c 的 `references/hal_mapping_guide.md` 会引用该约定，不重复定义。

### 编译验证边界

S5c **不做编译验证**。编译（含链接）由 S12 workflow-runner 在 S5c 完成后编排 S7 build 执行。原因：

- S5c 执行时 IDE 工程可能尚未创建（用户手工建工程）
- 完整编译需要工具链就绪，属于 build 阶段职责
- 保持职责单一：S5c 管"代码写对"，S7 管"编译通过"

### 演进路径（供实施参考）

本次优化建议按如下顺序落地，每步可回退：

1. **观察期**：加 `port_manifest_snapshot.json` + `port_differ.py`，任务书写 mode，**所有 mode 都执行 full**——只观察 diff 判定是否合理
2. **打开增量**：确认判定正确后，打开 full / incremental / skip / blocked 真实分支
3. **加 code-fix**：在主流程稳定后，新增 code-fix 分支入口（SKILL.md 描述原则，不预建脚本）
4. **提升共享**：把 `diff_range_checker.py` 从 S5b 提升到 `_shared`，S5b/S5c 共用
5. **更新文档**：同步 SKILL.md、references、schemas
