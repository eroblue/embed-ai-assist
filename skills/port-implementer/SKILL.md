---
name: "port-implementer"
description: "S5c Port 实现，三段式执行模型 + per-peripheral 增量生成：rule 脚本 prepare.py 做 S5a/S5b 就绪与配置一致性检查、能力缺口前置检测（manifest 需求 × hardware_capabilities 供给，缺口即终止）、flat 判定、旧平台/旧 RTOS 残留清理与用户修改检测（skip-if-modified）、per-peripheral diff（port_differ 逐单元判定 full/incremental/skip/blocked/deprecated）与代码基线镜像，并输出 Agent 任务书（含每单元生成模式表）；Agent（LLM）按生成模式实现 Port/OSAL/Power 接口到具体 HAL/RTOS 的适配代码（Drivers/Port/Src/，按 PROJECT_LAYOUT.md 解析，含中断回调判空规范）；rule 脚本 validate.py 校验产物（manifest 接口全覆盖/禁止向上依赖/ISR 判空抽查）、复跑增量范围校验（diff_range_checker）、写 manifest 快照、记录文件哈希，并调用公共工具 ide_sync.py 同步 IDE 工程。在 S5a 和 S5b 都完成后触发；flat 架构跳过生成。维护期支持 code-fix 分支入口（manifest 未变时的定点修复，不走主流程）。"
---

# port-implementer Port 实现（S5c）

## 用途

实现 S5b 定义的 Port / OSAL / Power 接口，将平台无关的调用翻译为具体
HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 **Adapter** 角色。
**flat 架构下跳过生成**（S5b 已直接对接厂商库，`s5c.status` 置 `skipped`）。

**支持 per-peripheral 增量生成**：manifest 局部演进（改单外设接口 / 新增外设）时
只重生成受影响的外设实现文件（`port_differ.py` 逐单元判定），其余走 skip——
避免"改一处接口、全部实现文件重写"。维护期另有 **code-fix 分支入口**（见后文），
用于 manifest 未变但实现行为不符预期时的定点修复。

**整体流程层级：S5c，代码生成层（平台相关）**。

- 上游依赖：S5a hardware-initializer（`s5a.*` +
  `outputs/s5a/hardware_capabilities.json`）、
  S5b port-contract-and-app（`s5b.*` +
  `outputs/s5b/port_interface_manifest.json`）——两者都完成后触发
- 下游消费：S7 build 编译验证（由 **S12 workflow-runner 在 S5c 之后编排调用**，
  S5c 自身不执行编译）
- IDE 同步：由公共工具 `skills/_shared/scripts/ide_sync.py` 完成（S5a/S5b/S5c
  各自 validate 后调用，谁跑完谁同步）

## 执行模型：rule 准备 → Agent 生成 → rule 校验

**策略（与 S5a/S5b 一致）**：确定性的规则用本地脚本实现；
Port/OSAL/Power 适配代码由 Agent（LLM）生成——**新增平台/新增 RTOS 无需为
本 Skill 编写任何适配脚本**（平台 × RTOS 的模板组合正是要消灭的文件量爆炸）。

```
[rule]  prepare.py    S5a/S5b 就绪检查 + 配置一致性检查（防漂移）
                       → 能力缺口前置检测（manifest 需求 × capabilities 供给，
                         缺口 → capability_gap.json + 终止 exit 2）
                       → flat 判定（skipped）
                       → 旧平台/旧 RTOS 残留清理 + 用户修改检测
                       → 代码基线镜像（outputs/s5c/code_baseline/，Agent 修改前）
                       → per-peripheral diff（读 port_manifest_snapshot.json →
                         逐单元判定 full/incremental/skip/blocked/deprecated →
                         outputs/s5c/port_diffs/<单元>_diff.json）
                       → outputs/s5c/generation_brief.md（任务书，含生成模式表）
                       → state.s5c.status = "running"
[agent] Agent 生成代码  读 SKILL.md + 任务书 + references/（HAL/RTOS 映射指南、
                       实现模式、ISR 安全规范；有 incremental 时加读增量规则）+
                       manifest + capabilities + SDK 头文件（核对 API/枚举名）
                       → 按任务书**生成模式表逐单元处理**（full 全量生成 /
                       incremental 定点修改 / skip 绝对不动 / blocked 报告用户 /
                       deprecated 移除文件）
[rule]  validate.py    产物校验（manifest 接口全覆盖 / include 对应 Port 头 /
                       禁止向上依赖 app*/protocol_*/driver* / ISR 回调判空抽查 /
                       mtime 守卫）→ 增量范围校验（diff_range_checker，拦截
                       异常重写）→ 记录文件哈希（skip-if-modified 依据）→
                       写 manifest 快照（下轮 diff 基线）→ 调用公共工具
                       ide_sync.py 同步 IDE 工程（失败不中断）
                       → state.s5c.status = "done"
```

- **能力缺口在 prepare 前置检测**（exit 2 + `capability_gap.json` + state error）：
  缺口是契约层问题，修复要回 S5a/S5b——不让 Agent 白干一轮才发现
- validate 失败（退出码 1）→ Agent 按失败报告修复，**重跑 validate.py**
  （state 保持 running，不写 error）
- 配置/就绪/缺口失败（退出码 2）→ state 写 error

## 目录结构

```
port-implementer/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/
│   ├── input.schema.json            ← 输入契约（S5a/S5b 就绪性与一致性检查）
│   ├── output.schema.json           ← 输出契约（state.json 的 s5c 字段，含增量字段）
│   ├── capability_gap.schema.json   ← 能力缺口报告契约
│   ├── port_diff.schema.json        ← per-peripheral diff 结果契约
│   └── port_manifest_snapshot.schema.json ← manifest 快照契约
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                  ← 共享分析：一致性/能力缺口/残留检测/哈希/manifest 签名 diff
│   ├── prepare.py                   ← 第 1 段：检查 + 清理 + diff + 基线镜像 + 任务书
│   ├── port_differ.py               ← per-peripheral 生成模式判定（full/incremental/skip/blocked/deprecated）
│   ├── diff_range_checker.py        ← 增量代码范围校验（拦截异常重写）
│   └── validate.py                  ← 第 3 段：产物校验 + 范围校验 + 快照 + IDE 同步调用
├── references/
│   ├── hal_mapping_guide.md         ← HAL 映射指南（厂商 API ↔ Port 接口）
│   ├── rtos_mapping_guide.md        ← RTOS 映射指南（RTOS API ↔ OSAL 接口）
│   ├── port_impl_pattern.md         ← 实现模式（ctx 数组/环形缓冲/错误码/DMA 骨架）
│   ├── isr_safety_rules.md          ← 中断安全规范（回调判空/临界区/ISR 约束）
│   ├── port_diff_rules.md           ← per-peripheral 变化率算法/判定链/版本管理
│   └── incremental_generation_rules.md ← 定点修改原则/范围校验阈值/异常处置
└── assets/
    └── port_impl_example.c          ← 实现示例（UART Port 全流程写法参考）
```

> IDE 工程同步公共工具位于 `skills/_shared/scripts/ide_sync.py`
> （跨 Skill 共享，S5a/S5b/S5c 各自 validate 段调用）。

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| s5a.* | state.json（S5a 写入） | object | 是 | init_sources/init_headers/entry_source/rtos_hw_init/power_init/hardware_capabilities/architecture/rtos/power_enabled |
| s5b.* | state.json（S5b 写入） | object | 是 | port_manifest/port_headers/osal_header/power_header/architecture/rtos/power_enabled |
| outputs/s5a/hardware_capabilities.json | S5a 产物 | json | 是 | **实现 Port 的唯一硬件依据**（禁止直接读 S3/S4 数据） |
| outputs/s5b/port_interface_manifest.json | S5b 产物 | json | 是 | **实现 Port 的唯一接口依据**（禁止硬解析 C 头文件） |
| outputs/s5c/port_manifest_snapshot.json | S5c 历史产物 | json | 否 | **接口变化检测基线**（增量机制依据）；首次执行不存在 → 全部单元 full 建基线 |
| outputs/s5c/file_hashes.json | S5c 历史产物 | json | 否 | **用户手改检测基线**（skip-if-modified）；首次执行不存在 → 全部视为未改过 |
| s5c.platform | config.json（项目层） | string | 否 | 平台标识（文件命名后缀）；缺省取顶层 `platform`，小写化 |
| s5c.hal_framework | config.json（项目层） | string | 否 | HAL 框架（如 `std_periph` / `hal` / `ll`，用于定位参考材料） |
| project.build_target | config.json（项目层） | enum | 否 | `App` / `BootLoader`，缺省 App——目标工程根（state.json/源码/outputs/IDE 目录所在），docs/ 与 references/ 为项目根共享 |
| project.inputs.ide_project | config.json（项目层） | string | 否 | IDE 工程文件路径；缺省按 IDE 工程目录自动发现 |
| docs/s5c_design_input.md | 项目 docs/ 目录 | markdown | 否 | **用户设计输入**，见下 |
| references/demos / .sdk / .existing_project | 项目 references/ | - | 否 | Agent 学习 API 写法与风格 |

> 配置契约统一由根目录 `schemas/config.schema.json` 定义。**rtos/architecture/
> power_enabled 三配置项只认 S5a/S5b state**（S5c 按上游产物生成）；
> 一致性检查做"防漂移"：s5a 与 s5b 不一致 → error 终止（重跑其中一方对齐）；
> 当前 config 与 state 不一致 → 任务书登记漂移警告。

### 用户设计输入（docs/s5c_design_input.md）

用户向 Agent 传达实现约束的输入通道，**优先级高于自动推断**。文件不存在、
内容为空或全部为 `none` 时，改由 Agent（LLM）基于 hardware_capabilities、
接口契约与参考材料自主判断（如低功耗模式选择、唤醒源配置、时钟门控策略）：

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

两段分别约束：低功耗策略（唤醒源/时钟门控/恢复流程，仅 `power.enabled`
时生效）、已有实现参考（命名约定与代码风格沿用）。

## 输出

### 写入 S5c 产物目录（Agent 生成的代码）

目录由 **PROJECT_LAYOUT.md 解析**确定（`layout_resolver.skill_dirs["s5c"]`，
32 位 layered/full 典型值为 `Drivers/Port/Src/`，与 S5b 的 Port 接口头目录
`Drivers/Port/Inc/` 对称）；prepare 任务书给出确切路径。

| 产物 | 生成条件 |
|------|----------|
| `port_impl_<外设>_<平台>.c`（uart/i2c/spi/gpio/adc/timer/pwm/par/…，按 manifest 的 peripheral 字段数据驱动） | manifest 中存在该外设 Port |
| `port_impl_osal_<rtos>.c`（freertos / rtthread / zephyr） | `project.rtos != "none"`（含 flat 架构）※ |
| `port_impl_power_<平台>.c` | `project.power.enabled == true` 且非 flat |

※ flat + RTOS 组合：OSAL 接口头由 S5b 生成，但 flat 布局无 Port 目录且
S5c 整体跳过——该组合的 OSAL 实现无法由 S5c 提供，需改 layered 或人工补齐
（布局树 flat 剔除 Port 层，见 docs/PROJECT_LAYOUT.md）。

**命名规范**：`<平台>` = `s5c.platform` 小写化（非字母数字字符去除，如
`stm32f103zet6`）；`<rtos>` 全小写、连字符/空格/下划线去除（`FreeRTOS→freertos`、
`RT-Thread→rtthread`、`Zephyr→zephyr`）。未被使用的外设不生成；每个实现文件
include S5b 的 Port 头，只实现对应接口。**接口语义（错误码/超时/线程安全）
按 S5b 的 `references/port_design_principle.md` 同一约定实现**。

### 写入 outputs/s5c/（数据）

| 产物 | 内容说明 |
|------|----------|
| `generation_brief.md` | Agent 任务书（prepare 段）：manifest 接口清单 / 能力供给 / 映射要点 / ISR 规范 / **每单元生成模式表** / 用户修改清单 / 禁止事项 |
| `capability_gap.json` | 可选，prepare 检测到 manifest 需要的硬件能力在 S5a 能力清单中不存在时输出，并**终止执行**（exit 2） |
| `file_hashes.json` | 生成文件哈希（**用户手改检测维度**，skip-if-modified 依据） |
| `port_manifest_snapshot.json` | manifest 的 per-peripheral 签名快照（**接口变化检测维度**，validate 成功后写入，作下轮 diff 基线；旧版本追加到 `port_manifest_snapshot_history/`） |
| `port_diffs/<单元>_diff.json` | 每单元 diff 结果（变化明细 + generation_mode，prepare 段产出） |
| `code_baseline/` + `code_snapshot.json` | 上轮实现文件镜像 + sha256 索引（增量范围校验的对照基线，prepare 段重建） |
| `diff_check_result.json` / `diff_anomaly.json` | 增量范围校验结果 / 异常报告（有 incremental 单元时产出） |
| `recommendations.json` | 可选，prepare 检出的待确认项（hw_instance=null 实例、能力清单退化） |

### 写入 state.json（仅 s5c 字段）

`status`（pending/running/done/error/skipped）、`rtos`、`architecture`、
`power_enabled`、`generation_brief`、`port_impl_sources`、`osal_impl`
（null=裸机）、`power_impl`（null=未启用）、`skipped_files`、`capability_gap`、
`port_manifest_snapshot`（本轮快照路径）、`port_diffs`（本轮每单元 diff 路径列表）、
`generation_modes`（`{ "uart": "incremental", ... }`）、`error`、`updated_at`。
**首次执行（无快照）时 `port_diffs` / `generation_modes` 可为空**（全部按 full 建基线）。

指针/数据分离：代码在 S5c 产物目录（布局解析确定），数据在 `outputs/s5c/`，
state.json 只存指针与清单。

## 生成模式总览

生成模式由 `port_differ.py` **逐单元判定**（同一轮中 uart 可 full、gpio 可 skip、
adc 可 incremental）：

| 模式 | 触发条件 | 处置 |
|---|---|---|
| `full` | 首次执行（无快照）/ 该单元无签名基线 / 变化率 > 60% / 实现文件不存在 | 全量重生成该文件 |
| `incremental` | 接口签名变化率 ≤ 60% | Agent 定点修改（无权整文件重写） |
| `skip` | 接口未变且文件未改；或**用户手改且接口未变**（+漂移标注） | **绝对不动该文件** |
| `blocked` | **用户手改 + 上游接口变化**（冲突） | **报告用户**，不自行处理 |
| `deprecated` | 外设已从 manifest 删除 | 移除对应实现文件 |

**判定维度**（前两个决定生成模式，第三个只提示）：

| 维度 | 依据 | 检测时机 | 作用 |
|---|---|---|---|
| **用户手改** | 文件当前 sha256 vs `file_hashes.json` 基线 | prepare 段 | 决定 `skip`（+漂移）/ `blocked` |
| **接口变化** | 本轮 manifest 单元签名 vs `port_manifest_snapshot.json` | prepare 段 | 决定 `skip` / `incremental` / `full` |
| **设计输入变化** | 本轮 `docs/s5c_design_input.md` sha256 vs 快照 `design_input_hash` | prepare 段 | **仅提示**：任务书标注"设计输入已变化"，**不自动改文件**（用户确认受影响单元后，删除文件触发 `full` 或走 `code-fix`） |

> 第三维度只做提示的原因：设计输入是**全局约束**（不分单元），无法机械映射到具体实现文件；
> 且其变化未必需要改代码（可能是补充说明）。`port_diffs/*.json` 的 `design_input_changed`
> 字段与任务书提示段承载这一信息。

**变化率** = 有增/删/改的字段数 ÷ 当前字段总数（字段 = 实例/接口/回调的属性原子）；
阈值 `> 60% → full`（对标 S5b `flow_differ` 的 `FULL_RATIO_THRESHOLD`，命名与阈值
保持一致，便于建立统一心智模型）。判定链与算法详见 `references/port_diff_rules.md`。

**用户手改保护优先于"首次执行全 full"**：`skip-if-modified` 是硬约束，用户改过的
文件不得被自动重写——即使本轮无签名基线（首次执行/新增单元）也判 skip。

**分支入口原则**（与 S5b 一致）：不走完整主流程的维护操作（`code-fix` 等）作为
**独立 Agent 入口**新增章节，不改动主流程与散件脚本——按需触发、默认不执行；
禁止为预留而建空壳脚本或空壳参数。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare（配置分层加载 → S5a/S5b 就绪检查 → 一致性检查 →
   能力缺口前置检测 → flat 判定 → 残留清理 + 用户修改检测 → 代码基线镜像 →
   per-peripheral diff → 任务书）：
   ```bash
   python skills/port-implementer/scripts/prepare.py --config <项目>/config.json
   ```
2. [agent] 读 `outputs/s5c/generation_brief.md`（**重点看第 5 节生成模式表**），
   通读本文件与 `references/hal_mapping_guide.md`、`references/port_impl_pattern.md`、
   `references/isr_safety_rules.md`（RTOS 时加 `references/rtos_mapping_guide.md`；
   有 incremental 单元时加 `references/incremental_generation_rules.md`）；
   写法参考 `assets/port_impl_example.c`
3. [agent] 读 manifest + capabilities + SDK 头文件，**核对将要用到的
   API 函数名/枚举名/时钟使能宏——不确定的留 `/* TODO: */` 注释，不臆造 API**
4. [agent] 读 `docs/s5c_design_input.md`：存在且非空时以其为准（低功耗方案、
   已有实现参考的命名/风格沿用）；**空/缺失时由 Agent 基于
   hardware_capabilities 与参考材料自主判断**
5. [agent] **按生成模式表逐单元处理**（模式见 `outputs/s5c/port_diffs/<单元>_diff.json`）：
   - `full`：全量生成该外设 `.c`（首次 / 变化率 >60%；>60% 时先向用户说明重构范围）
   - `incremental`：**只做定点修改**（`references/incremental_generation_rules.md`），
     无权重写整个文件
   - `skip`：**绝对不动该文件**（含用户手改与接口未变两类）
   - `blocked`：**报告用户**（手改 + 上游变更冲突），不自行处理
   - `deprecated`：移除对应实现文件（IDE 引用由 ide_sync 收口）
   `rtos != none` 时按模式生成/更新 OSAL 实现；`power.enabled` 时生成 Power 实现
6. [agent] 遵守中断安全规范：**ISR 内调用回调前必须判断函数指针非 NULL**
   （未注册时清标志直接返回，不得裸调）；DMA 隐藏在 Port 实现内；
   实例状态用文件内 static 数组按 id 索引，禁动态分配
7. [rule] 增量范围校验（有 incremental 单元时；validate 内部也会复跑，
   本步用于生成后即刻自检）：
   ```bash
   python skills/port-implementer/scripts/diff_range_checker.py --config <项目>/config.json
   ```
   异常（退出码 1）→ 报 `diff_anomaly.json`，按
   `references/incremental_generation_rules.md` 第四节处置，**不得自行修复后继续**
8. [rule] 运行校验：
   ```bash
   python skills/port-implementer/scripts/validate.py --config <项目>/config.json
   ```
   （validate 内部：接口全覆盖 → include 对应 Port 头 → 禁止向上依赖 →
   ISR 判空抽查 → mtime 守卫 → 增量范围校验 → 记录文件哈希 → 写 manifest 快照 →
   调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）→ state 写 done）
9. [agent] 校验失败（退出码 1）→ 按失败报告修复，重跑第 8 步直到通过
10. [workflow] 编译验证由 **S12 workflow-runner 在 S5c 之后编排调用 S7 build**
    执行，S5c 自身不调用工具链

## 能力缺口处理

prepare 阶段机械比对（manifest 需求 × capabilities 供给）：

- manifest 每个外设 Port 的**类型**须出现在 `hardware_capabilities.peripherals[].type`
  中，否则 error 级缺口 → `capability_gap.json` + 终止（exit 2）
- 启用低功耗但 capabilities 缺 `power` 能力段 → 同上
- `hw_instance=null` 的实例不报缺（实例选定是 Agent 职责，登记进
  recommendations.json 供用户确认）
- **不得尝试修改接口或降级实现**——缺口是契约层问题，修复要回 S5a/S5b
  （能力清单为空通常意味着 S1/S4 网表退化，需重跑硬件链）

## 再生策略（skip-if-modified）

与 S5b 相同的整文件级哈希比对，**与"接口变化"维度交叉判定**（见"生成模式总览"）：

1. validate.py 成功后把本轮生成文件哈希记入 `outputs/s5c/file_hashes.json`
   （用户手改过的文件**保留旧基线**，确保下次仍被识别为已修改）
2. prepare.py 重跑时逐文件比对：不一致 = 用户改过（`port_differ` 按接口是否
   也变，判 `skip`+漂移 或 `blocked`）；一致 = 按接口变化率判
   `skip` / `incremental` / `full`
3. 被跳过的文件不接收上游变化；**删除该文件即恢复自动生成**；
   跳过清单写入 `state.s5c.skipped_files`
4. **⚠️ 接口漂移风险**：跳过的文件与上游 manifest 会逐渐漂移（接口变了、
   实现没跟上），任务书在"用户修改文件清单"处标注，用户自行判断保留手改
   还是恢复自动生成
5. **与 code-fix 的协同**：code-fix 修完的文件自动获得"用户维护"状态
   （哈希不一致 → 下轮判 `skip`+漂移），**修复被保留**——这是设计意图，
   不是副作用（见"分支入口：code-fix"）

## 换平台 / 换 RTOS 的重跑规则

| 场景 | 重跑范围 |
|------|----------|
| 换 MCU | S3 → S4 → S5a → S5c（触发旧文件清理 + diff 判定全部 full）；S5b 产物不变（layered/full） |
| 换 RTOS | S5a（rtos_hw_init）→ S5c（OSAL 实现替换 + 清理旧 RTOS 残留）；S5b 产物不变；**OSAL diff 判定通常为 full（RTOS 名变化即触发）** |
| manifest 新增外设 | 只跑 S5c；该外设 full 生成，其他外设按 diff 判定 |
| manifest 改单外设接口 | 只跑 S5c；该外设 incremental（≤60%）或 full（>60%），其他外设 skip |
| flat 架构换平台 | S5c 跳过生成；需重跑 S5b（其产物平台相关） |

残留清理只删 `port_impl_*.c` 中**非当前平台/非当前 RTOS 且未被用户修改**的
文件（换平台/换 RTOS 残留文件会导致编译失败）；首跑（无哈希记录）全部视为
"未改过"，正常清理。

## IDE 工程同步（公共工具 ide_sync.py）

IDE 工程文件（`.uvprojx`/`.ewp`）的同步由公共工具
`skills/_shared/scripts/ide_sync.py` 完成，S5c validate 段自动调用：

- **扫描范围**：布局解析的 scan_roots（`App/Src` + `Drivers/BSP/Src` +
  `Drivers/Port/Src` 等），非硬编码
- **差异同步**：新增/删除/改 include 路径，保留原工程配置
- **并发安全**：全局文件锁；**幂等**：无变化不写盘
- **备份/回滚**：修改前备份 `.bak`，写入失败自动恢复
- **失败不中断**：输出 `outputs/_shared/ide_sync_manual.md` 手动清单
- IDE 工程由用户手动创建，工具只做增量同步

## 分支入口：code-fix（按需触发，默认不执行）

**用途**：manifest 未变、文件 hash 未变、但实现行为不符合预期时，由用户直接指定
"文件 + 函数 + 症状"，Agent 定点修复。**不走 prepare 主流程**。

**设计依据**（与 S5b 一致的"分支入口原则"）：不走完整主流程的维护操作作为独立
Agent 入口新增章节，不改动主流程与散件脚本；按需触发、默认不执行；
**禁止为预留而建空壳脚本或空壳参数**。

### 触发条件（用户显式发起）

- 用户在对话中指明：文件路径 + 函数名 + 预期行为 vs 实际行为
- 或用户提供日志/现象描述 + 定位线索

### 执行流程

1. `[agent]` 读指定文件 + 用户描述 + 本 SKILL.md + `references/hal_mapping_guide.md`
   / `port_impl_pattern.md` / `isr_safety_rules.md`
2. `[agent]` 定位问题 → **向用户确认修复方案**（先方案后动手）
3. `[agent]` 定点修改，不做无关重构
4. `[rule]` 最小校验子集：include 规则（不 include `app*` / `protocol_*`）+
   ISR 回调判空（若改动涉及 ISR）；**不跑全量 validate**，不做 manifest 全覆盖检查
5. `[rule]` 更新 `outputs/s5c/file_hashes.json`：**保留该文件的旧基线**（让该文件
   进入"用户维护"状态，下轮 prepare 判 `skip`+漂移），或直接把该文件追加进
   `state.s5c.skipped_files`
6. `[agent]` 向用户报告改动摘要（文件 / 函数 / 改动前后对比 / 未验证项）

### 不做

- 不跑 prepare（不做就绪/一致性/能力缺口检查）
- 不跑完整 validate（只跑增量相关子集）
- 不重新生成任何其他文件
- **不改动 `state.s5c.status`**（主流程此前已 done，code-fix 是叠加维护）
- **不覆盖已有 `port_manifest_snapshot.json`**（不影响下轮主流程 diff）
- 不修改 S5a/S5b 产物

### 与 skip-if-modified 的协同

code-fix 修完 → 哈希与基线不一致 → 下次主流程 prepare 判 `skip`+漂移 →
**修复被保留**。这是设计意图：**code-fix 天然产出"用户维护文件"**，无需额外机制。

### 后续可能的扩展入口（描述原则，不预建）

`code-explain`（解释实现意图，只读）/ `code-refactor`（重构不改行为，需最小校验子集）/
`code-add`（手动新增一个 Port 实现，不走 manifest）——**只在本文档描述原则，
不预先建空壳脚本**，需要时按同一模式实现。

## 向后兼容

改造增量机制时兼容已在跑的老项目：

1. **无 `port_manifest_snapshot.json` 的老项目**：首次跑 → snapshot 不存在 →
   全部单元按 `full` 生成（建基线），validate 成功后写入第一份 snapshot，
   之后进入增量模式。
2. **无 `port_diffs` / `generation_modes` 字段的老 state**：prepare 读 state 时
   对这些新字段给默认值（空 array / 空 object），避免 schema 校验失败。
3. **两个哈希文件的关系**：`file_hashes.json`（用户手改检测，schema 不变）与
   `port_manifest_snapshot.json`（接口变化检测，新增）是**正交维度**，
   交叉判定生成模式；`file_hashes.json` 的"用户手改保留旧基线"逻辑保持不变。
4. **新字段全部可选**：`output.schema.json` 只在 `status=done` 时要求
   `port_manifest_snapshot` / `port_diffs` / `generation_modes` 三个字段存在
   （running/skipped/error 不要求）。

## 使用方法

```bash
# 前置：S2、S3、S4、S5a、S5b 已在同一项目执行
python skills/port-implementer/scripts/prepare.py --config examples/<项目>/config.json
# → 检查任务书"生成模式表" →
# → Agent 按模式生成（full / incremental / skip / blocked / deprecated）→
python skills/port-implementer/scripts/diff_range_checker.py --config examples/<项目>/config.json   # 有 incremental 时
python skills/port-implementer/scripts/validate.py --config examples/<项目>/config.json

# 维护期分支入口（不进主流程）：
#   用户直接告诉 Agent：文件 + 函数 + 症状，走 code-fix 流程
```

## 依赖

- Python 3.10+，jsonschema（契约校验）
- IDE 工程同步：公共工具 `skills/_shared/scripts/ide_sync.py`（xml.etree 标准库）
- 交叉编译工具链：**不需要**（编译验证由 S12 workflow-runner 编排 S7 执行）

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功（含 flat skipped） |
| 1 | 产物校验失败 / 增量范围异常（state 保持 running，Agent 修复后重跑） |
| 2 | 配置错误 / 就绪失败 / 能力缺口 / 一致性冲突（state 写 error） |

## 禁止事项

**rule 脚本侧**：不修改 config.json；不读写其他 Skill 的 state.json 字段；
不生成任何 C 代码；**不修改 `port_manifest_snapshot.json` 的历史版本**
（只追加新版本，旧版本保留到 `port_manifest_snapshot_history/` 供回溯）。

**Agent 侧**：
- 不修改 S5a/S5b 产出的文件（含所有 `<外设>_port.h` / `osal.h` /
  `power_port.h` 接口定义）
- 不写任何应用业务逻辑，不生成 HAL 初始化代码（S5a 职责，Port 实现只做
  绑定与读写下层操作）
- 必须优先读取 `port_interface_manifest.json`，不得硬解析 C 头文件；
  硬件只依据 `hardware_capabilities.json`（及设计输入/S5a init 产物核对），
  **禁止直接读取 S3/S4 数据**
- 能力缺口必须报 `capability_gap` 终止（prepare 阶段），不得偷偷改接口或
  降级实现
- **ISR 内回调调用前必须判空**，不得裸调未注册的回调
- 不得把所有 Port 实现塞进一个文件，必须按外设拆分
- 不得把代码放在 `outputs/` 中，必须放在布局解析的 S5c 产物目录
- **不重写任务书标注"用户已修改"的文件**（skip-if-modified）
- **`incremental` 模式无权重写整个文件**，只做定点修改；diff 范围异常时
  不得自行修复后继续（先报告用户）
- **`blocked` 模式必须报告用户**（手改 + 上游变更冲突），不自行处理
- **`skip` 模式绝对不动文件**（含用户手改与接口未变两类）
- **首次执行（无 snapshot）时未手改的文件全部按 full 建基线**，不跳过
- **code-fix 分支入口不做全量 validate**，只做最小校验子集；
  不改变 `state.s5c.status`；不动 `port_manifest_snapshot.json`
- 不直接修改 IDE 工程文件——同步统一由公共工具
  `skills/_shared/scripts/ide_sync.py` 完成
