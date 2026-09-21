---
name: "port-implementer"
description: "S5c Port 实现，三段式执行模型：rule 脚本 prepare.py 做 S5a/S5b 就绪与配置一致性检查、能力缺口前置检测（manifest 需求 × hardware_capabilities 供给）、旧平台/旧 RTOS 残留清理，并输出 Agent 任务书；Agent（LLM）按任务书实现 Port/OSAL/Power 接口到具体 HAL/RTOS 的适配代码（src/port_impl/，含中断回调判空规范）；rule 脚本 validate.py 校验产物，并调用公共工具 ide_sync.py 同步 IDE 工程。在 S5a 和 S5b 都完成后触发；flat 架构跳过生成。"
---

# port-implementer Port 实现（S5c）

## 用途

实现 S5b 定义的 Port / OSAL / Power 接口，将平台无关的调用翻译为具体
HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 Adapter 角色。
**flat 架构下跳过生成**（状态置 `skipped`）。

**整体流程层级：S5c，代码生成层（平台相关）**。

- 上游依赖：S5a hardware-initializer（`s5a.*` + `outputs/s5a/hardware_capabilities.json`）、
  S5b port-contract-and-app（`s5b.*` + `outputs/s5b/port_interface_manifest.json`）
- 下游消费：S7 build 编译验证（由 **S12 workflow-runner 在 S5c 之后编排调用**，
  S5c 自身不执行编译）
- IDE 同步：由公共工具 `skills/_shared/scripts/ide_sync.py` 完成（S5a/S5b/S5c
  各自 validate 后调用，谁跑完谁同步），本 Skill 不再汇聚 IDE 更新

## 执行模型：rule 准备 → Agent 生成 → rule 校验

**策略（与 S5a/S5b 一致，用户拍板）**：确定性的规则用本地脚本实现；
Port/OSAL/Power 适配代码由 Agent（LLM）生成——新增平台/新增 RTOS 无需为本
Skill 编写任何适配脚本（平台 × RTOS 的模板组合正是要消灭的文件量爆炸）。

```
[rule]  prepare.py    S5a/S5b 就绪检查 + 配置一致性检查（防漂移）
                       → 能力缺口前置检测（manifest 需求 × capabilities 供给）
                       → flat 判定 → 旧平台/旧 RTOS 残留清理
                       → 用户修改检测（skip-if-modified）
                       → outputs/s5c/generation_brief.md（任务书）
                       → state.s5c.status = "running"
[agent] Agent 生成代码  读 SKILL.md + 任务书 + references/（HAL/RTOS 映射指南、
                       ISR 安全规范）+ manifest + capabilities + SDK 头文件
                       （确认 API/枚举名）→ 亲自编写 src/port_impl/*.c
[rule]  validate.py    校验产物（manifest 接口全覆盖 / 禁止 include 应用头 /
                       ISR 回调判空抽查）→ 记录文件哈希
                       → 调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）
                       → state.s5c.status = "done"
```

- **能力缺口在 prepare 前置检测**（exit 2 + `capability_gap.json` + state error）：
  缺口是契约层问题，修复要回 S5a/S5b——不让 Agent 白干一轮才发现
- validate 失败（退出码 1）→ Agent 按失败报告修复，**重跑 validate.py**
  （state 保持 running，不写 error）
- 配置/就绪失败（退出码 2）→ state 写 error

## 目录结构

> **实现状态（规划中）**：当前仅交付本文件；以下结构为实现规格，
> schemas/scripts/references/ 随实现补齐（接口语义约定见 S5b 的
> `skills/port-contract-and-app/references/port_design_principle.md`）。

```
port-implementer/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/
│   ├── input.schema.json            ← 输入契约（S5a/S5b 就绪性与一致性检查）
│   └── output.schema.json           ← 输出契约（state.json 的 s5c 字段，含 running）
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                   ← 共享分析：一致性/能力缺口/残留检测/哈希
│   ├── prepare.py                   ← 第 1 段：检查 + 清理 + 任务书
│   └── validate.py                   ← 第 3 段：产物校验 + IDE 同步调用
├── references/
│   ├── hal_mapping_guide.md         ← HAL 映射指南
│   ├── rtos_mapping_guide.md        ← RTOS 映射指南
│   └── isr_safety_rules.md          ← 中断安全规范（回调判空等）
└── assets/
    └── port_impl_example.c           ← 实现示例
```

> IDE 工程同步公共工具位于 `skills/_shared/scripts/ide_sync.py`
> （跨 Skill 共享，S5a/S5b/S5c 各自 validate 段调用）。

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| s5a.* | state.json（S5a 写入） | object | 是 | init_sources/hardware_capabilities/architecture/rtos/power_enabled 等 |
| s5b.* | state.json（S5b 写入） | object | 是 | port_manifest/port_headers/architecture/rtos/power_enabled 等 |
| outputs/s5a/hardware_capabilities.json | S5a 产物 | json | 是 | **实现 Port 的唯一硬件依据**（禁止直接读 S3/S4 数据） |
| outputs/s5b/port_interface_manifest.json | S5b 产物 | json | 是 | **实现 Port 的唯一接口依据**（禁止硬解析 C 头文件；含 version 字段） |
| platform | config.json（项目层） | string | 是 | 芯片平台名（定位 SDK/参考材料/残留清理判定） |
| project.target / .rtos / .architecture | config.json（项目层） | - | 否 | MCU 型号 / RTOS / 架构 |
| project.power.enabled | config.json（项目层） | bool | 否 | 是否启用低功耗 |
| project.inputs.ide_project | config.json（项目层） | string | 否 | 缺省按 IDE 工程目录（`MDK-ARM/`/`IAR/`/`Project/`，见 docs/PROJECT_LAYOUT.md）自动发现 |
| project.build_target | config.json（项目层） | enum | 否 | `App` / `BootLoader`，缺省 App——目标工程根（state.json / 源码目录 / outputs / IDE 工程目录所在）；docs / references 共享于项目根 |
| s5c.platform | config.json（项目层） | string | 否 | 平台标识（文件命名后缀） |
| docs/s5c_design_input.md | 项目 docs/ 目录 | markdown | 否 | **用户设计输入**，见下 |
| references/demos / .sdk / .existing_project | 项目 references/ | - | 否 | Agent 学习 API 写法与风格 |

> 配置契约统一由根目录 `schemas/config.schema.json` 定义。**三配置项只认
> config 显式值**（S5a/S5b/S5c 一致，缺省见 schema）：本 Skill 不做任何推断，
> 一致性检查只做"防漂移"（S5a/S5b 的 state 与当前 config 不一致 = 有 Skill
> 是旧配置跑的，提示重跑对齐）。

### 用户设计输入（docs/s5c_design_input.md）

用户向 Agent 传达实现约束的输入通道，**优先级高于自动推断**。**文件不存在、
内容为空或全部为 `none` 时，改由 Agent（LLM）基于 hardware_capabilities、
接口契约与参考材料（demo/SDK/已有项目）自主判断**（如低功耗模式选择、唤醒源
配置、时钟门控策略）。格式约定（填写示例见项目
`docs/demo/s5c_design_input_demo.md`）：

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

两段分别约束：低功耗策略（唤醒源/时钟门控/恢复流程，仅 `power.enabled` 时
生效）、已有实现参考（命名约定与代码风格沿用，避免 Agent 重造轮子）。

## 输出

### 写入 src/port_impl/（Agent 生成的代码）

| 产物 | 生成条件 |
|------|----------|
| `port_impl_<外设>_<平台>.c`（uart/i2c/spi/gpio/adc/timer/pwm） | manifest 中存在该外设 Port，按外设一文件 |
| `port_impl_osal_<rtos>.c` | `project.rtos != "none"`（含 flat 架构） |
| `port_impl_power_<平台>.c` | `project.power.enabled == true` 且非 flat |

未被使用的外设不生成；每个文件 include S5b 的 Port 头，只实现对应接口。
**接口语义（错误码/超时/线程安全）按 S5b 的
`references/port_design_principle.md` 同一约定实现**。

### 再生策略（skip-if-modified）

与 S5b 相同的整文件级哈希比对（目标形态：Agent 全自动生成、人工少改）：

1. validate.py 成功后把本轮生成文件哈希记入 `outputs/s5c/file_hashes.json`
2. prepare.py 重跑时逐文件比对：不一致 = 用户改过 → 任务书标注"跳过重写"；
   一致 → 正常重生成
3. 被跳过的文件不接收上游变化；**删除该文件即恢复自动生成**；跳过清单写入
   `state.s5c.skipped_files`

### 写入 outputs/s5c/（数据）

| 产物 | 内容说明 |
|------|----------|
| `generation_brief.md` | Agent 任务书（prepare 段）：manifest 接口清单/能力供给/映射要点/ISR 规范/禁止事项 |
| `capability_gap.json` | 可选，prepare 阶段检测到 S5b 需要的硬件能力在 S5a 能力清单中不存在时输出，并**终止执行**（exit 2） |
| `file_hashes.json` | 生成文件哈希（skip-if-modified 依据） |

### 写入 state.json（仅 s5c 字段）

`status`（pending/running/done/error/skipped）、`rtos`、`architecture`、
`power_enabled`、`generation_brief`（任务书路径）、`port_impl_sources`、
`osal_impl`（null=裸机）、`power_impl`（null=未启用）、`skipped_files`、
`error`、`updated_at`。

指针/数据分离：代码在 `src/port_impl/`，数据在 `outputs/s5c/`。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare（配置分层加载 → S5a/S5b 就绪检查 → **一致性检查**：
   比对 `s5a.rtos/architecture/power_enabled` 与 `s5b.*` 对应字段，不一致 →
   写 error（提示重跑其中一方使配置对齐）并终止 → **能力缺口前置检测**：
   manifest 需要的外设能力在 capabilities 中不存在 → 输出 `capability_gap.json`
   并终止（不得降级实现、不得改接口）→ `architecture == "flat"` → 跳过生成
   （S5b 已直接对接厂商库），`status` 置 `skipped`
   → **旧文件清理**：删除 `src/port_impl/` 下非当前平台/非当前 RTOS 的
   `port_impl_*.c`（换平台/换 RTOS 残留文件会导致编译失败）→ 用户修改检测
   → 任务书）：
   ```bash
   python skills/port-implementer/scripts/prepare.py --config <项目>/config.json
   ```
2. [agent] 读 `outputs/s5c/generation_brief.md`，通读本文件与
   `references/hal_mapping_guide.md`、`references/rtos_mapping_guide.md`、
   `references/isr_safety_rules.md`
3. [agent] 读 manifest + capabilities + 标准外设库头文件，核对将要用到的
   API 函数名/枚举名/时钟使能宏——**不确定的留 TODO 注释，不臆造 API**
4. [agent] 读 `docs/s5c_design_input.md`：存在且非空时以其为准（低功耗方案、
   已有实现参考的命名/风格沿用）；**空/缺失时由 Agent 基于
   hardware_capabilities 与参考材料自主判断**
5. [agent] 遍历 manifest 接口，按外设编写实现到 `src/port_impl/`
   （**跳过任务书标注"用户已修改"的文件**）；`rtos != "none"` 生成 OSAL
   实现；`power.enabled` 生成 Power 实现；接口语义（阻塞/超时/线程安全/
   错误码）按 S5b `port_design_principle.md` 同一约定
6. [agent] 遵守中断安全规范：**ISR 内调用回调前必须判断函数指针非 NULL**
   （回调未注册时清除中断标志直接返回，不得裸调）；DMA 隐藏在 Port 实现内
7. [rule] 运行校验：
   ```bash
   python skills/port-implementer/scripts/validate.py --config <项目>/config.json
   ```
   （validate 内部：manifest 接口全覆盖检查 → 禁止 include 应用头 →
   ISR 回调判空抽查 → 记录文件哈希 → 调用公共工具
   `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程（src/ 全量差异同步，
   含 S5a/S5b/S5c 产物；失败不中断）→ state 写 done）
8. [agent] 校验失败（退出码 1）→ 按失败报告修复，重跑第 7 步直到通过
9. [workflow] 编译验证由 **S12 workflow-runner 在 S5c 之后编排调用 S7 build**
   执行，S5c 自身不调用工具链

## IDE 工程同步（公共工具 ide_sync.py）

IDE 工程文件（`.uvprojx`/`.ewp`）的同步由公共工具
`skills/_shared/scripts/ide_sync.py` 完成，**S5a/S5b/S5c 各自 validate 段
自动调用**（谁跑完谁同步，不再由 S5c 统一汇聚）：

```bash
# 各 Skill validate 自动调用；也可单独手动运行
python skills/_shared/scripts/ide_sync.py --project examples/<项目> --target App --ide keil
```

- **差异同步**：扫描 `<目标工程>/src/` 全部源文件与工程条目比对——新增的
  添加（按 src/ 一级子目录分 group）、已删除的移除、include 路径追加
  （保留原工程配置：编译器选项/宏定义/已有条目）
- **并发安全**：全局文件锁（`<工程文件>.lock`），S5a/S5b 并行完成时互不覆盖
- **幂等**：重复调用不产生重复条目；无变化不写盘（不改 mtime）
- **备份/回滚**：修改前备份 `<工程文件>.bak`，写入失败自动恢复原文件
- **失败不中断**：工程文件缺失/解析失败/写盘失败时**不中断工作流**，
  输出 `outputs/_shared/ide_sync_manual.md` 手动同步清单（源文件列表 +
  group 建议 + include 路径 + 操作指引），修复后重跑即可
- IDE 工程由用户手动创建（选芯片/编译器等配置人工确认更可靠），工具只做
  src/ 增量同步；工程文件不存在时不自动创建

## 使用方法

```bash
# 前置：S2、S3、S4、S5a、S5b 已在同一项目执行
python skills/port-implementer/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 按任务书生成 src/port_impl/ →
python skills/port-implementer/scripts/validate.py --config examples/gd32f205vet6/config.json
```

## 换平台 / 换 RTOS 语义

- 换 MCU：重跑 S3/S4/S5a（硬件链）→ 重跑 S5c（触发旧文件清理 + 重新生成
  port_impl）；S5b 产物不变（layered/full）
- 换 RTOS：重跑 S5a（rtos_hw_init）→ 重跑 S5c（OSAL 实现替换 + 清理旧
  RTOS 残留）；S5b 产物不变
- flat 架构：S5c 生成部分跳过，换平台需重跑 S5b（其产物平台相关）

## 依赖

- Python 3.10+，jsonschema（契约校验）
- IDE 工程同步：公共工具 `skills/_shared/scripts/ide_sync.py`（xml.etree 标准库）
- 交叉编译工具链：**不需要**（编译验证由 S12 workflow-runner 编排 S7 执行）

## 禁止事项

**rule 脚本侧**：不修改 config.json；不读写其他 Skill 的 state.json 字段；
不生成任何 C 代码。

**Agent 侧**：
- 不修改 S5a/S5b 产出的文件（含 `port.h`/`osal_port.h`/`power_port.h` 接口定义）
- 不写任何应用业务逻辑，不生成 HAL 初始化代码（S5a 职责）
- 必须优先读取 `port_interface_manifest.json`，不得硬解析 C 头文件；
  硬件只依据 `hardware_capabilities.json`，禁止直接读取 S3/S4 数据
- 能力缺口必须报 `capability_gap` 终止（prepare 阶段），不得偷偷改接口或
  降级实现
- **ISR 内回调调用前必须判空**，不得裸调未注册的回调
- 不得把所有 Port 实现塞进一个文件，必须按外设拆分
- 不得把代码放在 `outputs/` 中，必须放在 `src/port_impl/`
- **不重写任务书标注"用户已修改"的文件**（skip-if-modified）
- 不直接修改 IDE 工程文件——同步统一由公共工具
  `skills/_shared/scripts/ide_sync.py` 完成（备份/回滚/手动清单降级内建）
