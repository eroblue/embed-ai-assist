---
name: "port-implementer"
description: "S5c Port 实现，三段式执行模型：rule 脚本 prepare.py 做 S5a/S5b 就绪与配置一致性检查、能力缺口前置检测（manifest 需求 × hardware_capabilities 供给，缺口即终止）、flat 判定、旧平台/旧 RTOS 残留清理与用户修改检测（skip-if-modified），并输出 Agent 任务书；Agent（LLM）按任务书实现 Port/OSAL/Power 接口到具体 HAL/RTOS 的适配代码（Drivers/Port/Src/，按 PROJECT_LAYOUT.md 解析，含中断回调判空规范）；rule 脚本 validate.py 校验产物（manifest 接口全覆盖/禁止向上依赖/ISR 判空抽查）、记录文件哈希，并调用公共工具 ide_sync.py 同步 IDE 工程。在 S5a 和 S5b 都完成后触发；flat 架构跳过生成。"
---

# port-implementer Port 实现（S5c）

## 用途

实现 S5b 定义的 Port / OSAL / Power 接口，将平台无关的调用翻译为具体
HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 **Adapter** 角色。
**flat 架构下跳过生成**（S5b 已直接对接厂商库，`s5c.status` 置 `skipped`）。

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
                       → outputs/s5c/generation_brief.md（任务书）
                       → state.s5c.status = "running"
[agent] Agent 生成代码  读 SKILL.md + 任务书 + references/（HAL/RTOS 映射指南、
                       实现模式、ISR 安全规范）+ manifest + capabilities +
                       SDK 头文件（核对 API/枚举名）→ 按 manifest 接口
                       逐外设编写 port_impl_<外设>_<平台>.c
[rule]  validate.py    产物校验（manifest 接口全覆盖 / include 对应 Port 头 /
                       禁止向上依赖 app*/protocol_*/driver* / ISR 回调判空抽查 /
                       mtime 守卫）→ 记录文件哈希（skip-if-modified 依据）
                       → 调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）
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
│   ├── output.schema.json           ← 输出契约（state.json 的 s5c 字段，含 skipped）
│   └── capability_gap.schema.json   ← 能力缺口报告契约
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                  ← 共享分析：一致性/能力缺口/残留检测/哈希
│   ├── prepare.py                   ← 第 1 段：检查 + 清理 + 任务书
│   └── validate.py                  ← 第 3 段：产物校验 + IDE 同步调用
├── references/
│   ├── hal_mapping_guide.md         ← HAL 映射指南（厂商 API ↔ Port 接口）
│   ├── rtos_mapping_guide.md        ← RTOS 映射指南（RTOS API ↔ OSAL 接口）
│   ├── port_impl_pattern.md         ← 实现模式（ctx 数组/环形缓冲/错误码/DMA 骨架）
│   └── isr_safety_rules.md          ← 中断安全规范（回调判空/临界区/ISR 约束）
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
| `generation_brief.md` | Agent 任务书（prepare 段）：manifest 接口清单 / 能力供给 / 映射要点 / ISR 规范 / 用户修改清单 / 禁止事项 |
| `capability_gap.json` | 可选，prepare 检测到 manifest 需要的硬件能力在 S5a 能力清单中不存在时输出，并**终止执行**（exit 2） |
| `file_hashes.json` | 生成文件哈希（skip-if-modified 依据） |
| `recommendations.json` | 可选，prepare 检出的待确认项（hw_instance=null 实例、能力清单退化） |

### 写入 state.json（仅 s5c 字段）

`status`（pending/running/done/error/skipped）、`rtos`、`architecture`、
`power_enabled`、`generation_brief`、`port_impl_sources`、`osal_impl`
（null=裸机）、`power_impl`（null=未启用）、`skipped_files`、`capability_gap`、
`error`、`updated_at`。

指针/数据分离：代码在 S5c 产物目录（布局解析确定），数据在 `outputs/s5c/`，
state.json 只存指针与清单。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare（配置分层加载 → S5a/S5b 就绪检查 → 一致性检查 →
   能力缺口前置检测 → flat 判定 → 残留清理 + 用户修改检测 → 任务书）：
   ```bash
   python skills/port-implementer/scripts/prepare.py --config <项目>/config.json
   ```
2. [agent] 读 `outputs/s5c/generation_brief.md`，通读本文件与
   `references/hal_mapping_guide.md`、`references/port_impl_pattern.md`、
   `references/isr_safety_rules.md`（RTOS 时加 `references/rtos_mapping_guide.md`）；
   写法参考 `assets/port_impl_example.c`
3. [agent] 读 manifest + capabilities + SDK 头文件，**核对将要用到的
   API 函数名/枚举名/时钟使能宏——不确定的留 `/* TODO: */` 注释，不臆造 API**
4. [agent] 读 `docs/s5c_design_input.md`：存在且非空时以其为准（低功耗方案、
   已有实现参考的命名/风格沿用）；**空/缺失时由 Agent 基于
   hardware_capabilities 与参考材料自主判断**
5. [agent] 遍历 manifest 接口，按外设编写实现（**每外设一个
   `port_impl_<外设>_<平台>.c`，跳过任务书标注"用户已修改"的文件**）；
   `rtos != none` 生成 OSAL 实现；`power.enabled` 生成 Power 实现
6. [agent] 遵守中断安全规范：**ISR 内调用回调前必须判断函数指针非 NULL**
   （未注册时清标志直接返回，不得裸调）；DMA 隐藏在 Port 实现内；
   实例状态用文件内 static 数组按 id 索引，禁动态分配
7. [rule] 运行校验：
   ```bash
   python skills/port-implementer/scripts/validate.py --config <项目>/config.json
   ```
   （validate 内部：接口全覆盖 → include 对应 Port 头 → 禁止向上依赖 →
   ISR 判空抽查 → mtime 守卫 → 记录文件哈希 → 调用公共工具 ide_sync.py
   同步 IDE 工程（失败不中断）→ state 写 done）
8. [agent] 校验失败（退出码 1）→ 按失败报告修复，重跑第 7 步直到通过
9. [workflow] 编译验证由 **S12 workflow-runner 在 S5c 之后编排调用 S7 build**
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

与 S5b 相同的整文件级哈希比对（目标形态：Agent 全自动生成、人工少改）：

1. validate.py 成功后把本轮生成文件哈希记入 `outputs/s5c/file_hashes.json`
   （用户手改过的文件**保留旧基线**，确保下次仍被识别为已修改）
2. prepare.py 重跑时逐文件比对：不一致 = 用户改过 → 任务书标注"跳过重写"；
   一致 = 正常重生成
3. 被跳过的文件不接收上游变化；**删除该文件即恢复自动生成**；
   跳过清单写入 `state.s5c.skipped_files`
4. **⚠️ 接口漂移风险**：跳过的文件与上游 manifest 会逐渐漂移（接口变了、
   实现没跟上），任务书在"用户修改文件清单"处标注，用户自行判断保留手改
   还是恢复自动生成

## 换平台 / 换 RTOS 的重跑规则

| 场景 | 重跑范围 |
|------|----------|
| 换 MCU | S3 → S4 → S5a → S5c（触发旧文件清理 + 重新生成 port_impl）；S5b 产物不变（layered/full） |
| 换 RTOS | S5a（rtos_hw_init）→ S5c（OSAL 实现替换 + 清理旧 RTOS 残留）；S5b 产物不变 |
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

## 使用方法

```bash
# 前置：S2、S3、S4、S5a、S5b 已在同一项目执行
python skills/port-implementer/scripts/prepare.py --config examples/<项目>/config.json
# → Agent 按任务书实现 Port/OSAL/Power →
python skills/port-implementer/scripts/validate.py --config examples/<项目>/config.json
```

## 依赖

- Python 3.10+，jsonschema（契约校验）
- IDE 工程同步：公共工具 `skills/_shared/scripts/ide_sync.py`（xml.etree 标准库）
- 交叉编译工具链：**不需要**（编译验证由 S12 workflow-runner 编排 S7 执行）

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功（含 flat skipped） |
| 1 | 产物校验失败（state 保持 running，Agent 修复后重跑） |
| 2 | 配置错误 / 就绪失败 / 能力缺口 / 一致性冲突（state 写 error） |

## 禁止事项

**rule 脚本侧**：不修改 config.json；不读写其他 Skill 的 state.json 字段；
不生成任何 C 代码。

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
- 不直接修改 IDE 工程文件——同步统一由公共工具
  `skills/_shared/scripts/ide_sync.py` 完成
