---
name: "port-contract-and-app"
description: "S5b Port 契约与应用，三段式执行模型：rule 脚本 prepare.py 检查 S2/S4 就绪并输出 Agent 任务书（含 skip-if-modified 检测），Agent（LLM）按任务书定义平台无关的 Port/OSAL/Power 接口契约，编写 APP、任务化 APP、协议层、设备驱动与 main.c，并填写接口清单 port_interface_manifest.json；rule 脚本 validate.py 校验产物（禁止 include / 接口契约一致 / 骨架形态），并调用公共工具 ide_sync.py 同步 IDE 工程。在 S2 和 S4 都执行完成后触发，与 S5a 可并行；产物是 S5c 实现 Port 的接口依据。"
---

# port-contract-and-app Port 契约与应用（S5b）

## 用途

从功能规格书（S2）、软件规格书、参考材料和用户设计输入出发，定义平台无关的
Port / OSAL / Power 接口契约，并生成 APP、任务化 APP、协议层、设备驱动代码
与 main.c。**本 Skill 全部产物平台无关**。

**整体流程层级：S5b，代码生成层（平台无关）**。

- 上游依赖：S2 spec-reader（`spec.*` + `outputs/s2/spec.json`）、
  S4 circuit-investigator（`circuit.facts` + `outputs/circuit_facts.json`，
  仅作决策依据，见"S4 硬件事实的使用边界"）
- 并行关系：与 **S5a hardware-initializer 无数据依赖（互不读对方产物），
  可并行执行**
- 下游消费：**S5c port-implementer** 只依据 `outputs/s5b/port_interface_manifest.json`
  实现 Port 接口，禁止硬解析 C 头文件
- 架构模式：Ports & Adapters 中的 USER 层（平台无关）

## 执行模型：rule 准备 → Agent 生成 → rule 校验

**策略（与 S5a 一致，用户拍板）**：确定性的规则用本地脚本实现；C 代码与接口
契约由 Agent（LLM）生成——新增平台/新增 RTOS 无需为本 Skill 编写任何适配脚本。

```
[rule]  prepare.py    配置/就绪检查（S2+S4 均成功）→ 用户修改检测
                       （skip-if-modified，见"再生策略"）
                       → outputs/s5b/generation_brief.md（任务书）
                       → state.s5b.status = "running"
[agent] Agent 生成代码  读 SKILL.md + 任务书 + references/port_design_principle.md
                       + S2 规格摘要 + S4 硬件事实（决策依据）+ 软件规格书
                       + demo/SDK/已有项目（风格与 API 命名参考）
                       → 亲自编写 src/port/*.h、src/app|protocol|driver/*、main.c
                       → 填写 outputs/s5b/port_interface_manifest.json
[rule]  validate.py    校验产物（禁止 include HAL/RTOS 头 / manifest 与头文件
                       一致 / main.c 骨架形态）→ 记录文件哈希（再生策略依据）
                       → ide_pending_files.json → state.s5b.status = "done"
                       → 调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）
```

- validate 失败（退出码 1）→ Agent 按失败报告修复，**重跑 validate.py**
  （state 保持 running，不写 error）
- 配置/就绪失败（退出码 2）→ state 写 error，先解决 S2/S4/config 问题

## 目录结构

> **实现状态（规划中）**：当前仅交付本文件与
> `references/port_design_principle.md`；以下结构为实现规格，schemas/scripts
> 与其余 references 随实现补齐（与 README Skill 清单状态列一致）。

```
port-contract-and-app/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/
│   ├── input.schema.json             ← 输入契约（S2/S4 就绪性检查）
│   ├── output.schema.json            ← 输出契约（state.json 的 s5b 字段，含 running）
│   └── port_interface_manifest.schema.json ← 接口清单数据契约（含 version 字段）
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                   ← 共享分析：配置/就绪/材料清单/文件哈希
│   ├── prepare.py                    ← 第 1 段：就绪检查 + 任务书
│   └── validate.py                   ← 第 3 段：产物校验 + manifest 契约 + IDE 清单
├── references/
│   ├── port_design_principle.md      ← Port 设计原则 + 接口语义约定（错误码/阻塞/线程安全）
│   ├── osal_design_principle.md      ← OSAL 设计原则
│   ├── main_skeletons.md             ← main.c 标准骨架（裸机/RTOS）
│   ├── file_split_guide.md           ← 文件拆分规范
│   └── software_spec_guide.md        ← 软件规格书解析指南
└── assets/
    └── port_interface_manifest_example.json ← 接口清单示例
```

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| spec.* | state.json（S2 写入） | object | 是 | 功能规格数据路径 |
| circuit.facts | state.json（S4 写入） | object | 是 | `facts_path`（引脚角色/外设使用等硬件事实，仅作决策依据，见下"S4 硬件事实的使用边界"） |
| platform | config.json（项目层） | string | 是 | 芯片平台名（定位 SDK/已有项目参考材料） |
| project.architecture | config.json（项目层） | enum | 否 | `flat` / `layered` / `full`，缺省 layered |
| project.rtos | config.json（项目层） | enum | 否 | `none` / `FreeRTOS` / `RT-Thread` / `Zephyr`，缺省 none |
| project.power.enabled | config.json（项目层） | bool | 否 | 缺省 false |
| project.rtos_config.max_prio | config.json（项目层） | int | 否 | 最大任务优先级 |
| project.inputs.software_spec | config.json（项目层） | string | 否 | 缺省自动发现 `docs/software_spec.*` |
| project.inputs.demos / .sdk / .existing_project | config.json（项目层） | string | 否 | 缺省自动发现 `references/` 下对应目录 |
| project.inputs.ide_project | config.json（项目层） | string | 否 | 缺省按 IDE 工程目录（`MDK-ARM/`/`IAR/`/`Project/`，见 docs/PROJECT_LAYOUT.md）自动发现（只读，了解工程配置） |
| project.build_target | config.json（项目层） | enum | 否 | `App` / `BootLoader`，缺省 App——目标工程根（state.json / 源码目录 / outputs / IDE 工程目录所在）；docs / references 共享于项目根 |
| s5b.language | config.json（项目层） | string | 否 | 语言标准，缺省 c99 |
| s5b.port_split | config.json（项目层） | array | 否 | Port 拆分策略，缺省按应用需求推断（Agent 判断） |
| docs/s5b_design_input.md | 项目 docs/ 目录 | markdown | 否 | **用户设计输入**，见下 |

> 配置契约统一由根目录 `schemas/config.schema.json` 定义（含 `project` 段全部
> 枚举值），加载时统一拦截非法值。

**三配置项只认 config 显式值**（S5a/S5b/S5c 一致）：本 Skill 对
architecture/rtos/power **不做任何推断**。S2/S4 事实与显式值明显冲突时
（如规格要求多任务但 `rtos: "none"`），prepare 在任务书 constraints 中提示
用户确认 config——**不自行改判**，保证并行执行不产生推断漂移、S5c 一致性
检查不会因此失败。

### 用户设计输入（docs/s5b_design_input.md）

用户向 Agent 传达应用设计意图的输入通道，**优先级高于自动推断**。**文件不存在、
内容为空或全部为 `none` 时，改由 Agent（LLM）基于 S2 功能规格、S4 硬件事实
与软件规格书自主判断**（功能映射、协议选择、任务划分）。格式约定（填写示例
见项目 `docs/demo/s5b_design_input_demo.md`）：

```markdown
# s5b设计输入， 告诉 Agent 应用需求怎么映射到硬件

## 功能映射
- 电压检测：使用 ADC1 采样 PA1，阈值 2.5V
- LED 指示：使用 GPIO 输出 PC13

## 协议
- WiFi 模块：UART0 走 AT 协议，帧格式见附录 A

## 任务划分（如启用 RTOS）
- task_sensor：100ms 周期，优先级中
- task_wifi：事件驱动，优先级高
```

三段分别约束：功能→外设映射（决定 Port 接口形态与 driver 划分）、通信协议
（决定 protocol 层）、任务划分（决定任务化 APP 与优先级）。Agent 执行本 Skill
时必须读取并结合其校正推断结果。

### S4 硬件事实的使用边界

S5b 读取 `outputs/circuit_facts.json` 仅用于**提升决策准确率**：

- **功能映射**：S2 说"LED 指示"→ S4 facts 定位 LED1 网络的引脚角色（输出），
  APP/driver 的逻辑命名与功能划分更贴合实际电路
- **外设可用性**：定义 Port 前确认板上实际连接的外设实例数量（如 UART 个数、
  是否有 I2C 设备），避免定义出硬件不存在的能力
- **通信协议**：确认 S2 声明的通信外设真实存在且引脚角色匹配（如 TX/RX 齐全）

**边界铁律（产物保持平台无关）**：

- S4 facts 是**决策依据**，不得将厂商实例名（USART5/SPI2）、引脚号（PC6）、
  网络名硬编码进 Port 接口、APP、driver 产物（注释中的设计说明除外）
- 具体的硬件能力映射由 S5c 依据 `hardware_capabilities.json` 完成

## 输出

### 写入 src/port/（Port 接口，平台无关头文件）

| 产物 | 生成条件 |
|------|----------|
| `<外设>_port.h`（uart/i2c/spi/gpio/adc/timer/pwm） | 非 flat 架构且该外设有使用，按外设拆分 |
| `osal_port.h` | **`project.rtos != "none"` 时总是生成（含 flat 架构）** |
| `power_port.h` | `project.power.enabled == true` 且非 flat |

**OSAL 与外设 Port 层是两个正交维度**：Port 层管"外设无关"，OSAL 管"RTOS 无关"。
flat 架构只豁免外设 Port 层（APP 直接访问寄存器/厂商库）；8 位 MCU 跑 RTOS
（如 RT-Thread nano）是合法场景，此时仍生成 `osal_port.h`，APP 的 RTOS 调用
全部经 OSAL，不得直接 include RTOS 头。

Port 接口的**语义约定**（统一错误码 / 阻塞与超时 / 线程安全声明 / 回调规范 /
缓冲与 DMA 归属）强制遵守 `references/port_design_principle.md`，S5c 实现侧
遵守同一语义。

### 写入 src/app/、src/protocol/、src/driver/、src/mocks/

| 产物 | 生成条件 |
|------|----------|
| `src/app/app.c/h` | 总是（主入口，只做初始化和主循环/任务创建） |
| `src/app/app_<功能>.c/h` | 按功能模块拆分，一功能一对 |
| `src/app/app_<功能>_task.c/h` | `project.rtos != "none"` |
| `src/protocol/protocol_<名称>.c/h` | 按协议拆分（如有多协议） |
| `src/driver/driver_<设备>.c/h` | 按设备拆分（如 driver_esp32c2、driver_eeprom） |
| `src/mocks/mock_<外设>_port.c` | 可选，Mock Port 桩实现（单元测试用） |
| `src/main.c` | 如不存在则创建（标准骨架见下） |

**Mock Port 属于代码，必须放 `src/mocks/`，不得放 `outputs/`**（代码/数据分离铁律）。

### main.c 标准骨架

`src/main.c` 由 S5b 生成/维护，只允许两种标准形态（不得混写）：

```c
/* 裸机（rtos == "none"） */
#include "hal_init.h"      /* 或 flat 架构的 board_init.h */
#include "app.h"

int main(void)
{
    hal_init();            /* S5a 总入口（项目内部头，不算 HAL 头） */
    app_init();
    while (1) {
        app_loop();        /* 主循环，含低功耗 WFI 时由 app 层决定 */
    }
}

/* RTOS（rtos != "none"） */
#include "hal_init.h"
#include "app.h"
#include "osal_port.h"

int main(void)
{
    hal_init();
    app_init();            /* 内部经 osal_task_create 创建各任务 */
    osal_kernel_start();   /* 启动调度器，不返回 */
    return 0;
}
```

### 再生策略（skip-if-modified）

生成文件的人工修改保护。目标形态是 **Agent 全自动生成、人工少改**，因此不采用
USER CODE 保护域（那是为"人长期住在生成代码里"设计的），用整文件级哈希比对：

1. validate.py 成功后，把本轮生成文件的内容哈希记入 `outputs/s5b/file_hashes.json`
2. prepare.py 重跑时逐文件比对：哈希**不一致 = 用户改过** → 任务书标注
   "跳过重写，读取现状"；一致 → 正常重生成
3. 被跳过的文件不再接收上游变化（S2 规格变了不会自动同步）——**删除该文件即
   恢复自动生成**；跳过清单写入 `state.s5b.skipped_files`，对用户可见
4. 用户改过的 Port 头仍须保持 manifest 一致：Agent 读取该头文件**现状**，
   按实际接口更新 manifest（不得仍按任务书旧清单）

### 写入 outputs/s5b/（数据）

| 产物 | 内容说明 |
|------|----------|
| `generation_brief.md` | Agent 任务书（prepare 段）：项目信息/功能映射/接口清单要求/语义约定要点/禁止事项 |
| `port_interface_manifest.json` | 接口契约（`version` + interfaces[]/functions[]：name/return/args），S5c 实现 Port 的唯一接口依据 |
| `file_hashes.json` | 生成文件哈希（skip-if-modified 依据） |
| `ide_pending_files.json` | IDE 待添加清单（源文件 + group + include 路径，兜底参考）。IDE 工程同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成：validate 段自动调用（谁跑完谁同步，全局文件锁防并行冲突），失败不中断并输出 `outputs/_shared/ide_sync_manual.md` 手动清单 |

### 写入 state.json（仅 s5b 字段）

`status`（pending/running/done/error）、`rtos`、`architecture`、`power_enabled`、
`generation_brief`（任务书路径）、`port_manifest`、`port_headers`、`osal_header`
（null=裸机）、`power_header`（null=未启用）、`app_sources`/`app_headers`、
`app_task_sources`（裸机为空）、`protocol_sources`、`driver_sources`/`driver_headers`、
`main_source`、`skipped_files`（skip-if-modified 跳过清单）、`ide_pending_files`、
`error`、`updated_at`。

指针/数据分离：代码在 `src/`，数据在 `outputs/s5b/`，state.json 只存指针。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare（配置分层加载 → S2/S4 就绪检查 → 用户修改检测 →
   任务书）：
   ```bash
   python skills/port-contract-and-app/scripts/prepare.py --config <项目>/config.json
   ```
2. [agent] 读 `outputs/s5b/generation_brief.md`，通读本文件与
   `references/port_design_principle.md`（接口语义约定）、`references/main_skeletons.md`
3. [agent] 读输入材料：S2 规格摘要、S4 硬件事实（决策依据）、软件规格书、
   demo（代码风格）、SDK（API 命名）、已有项目（工程结构）、IDE 项目文件
   （只读，了解 include 路径与已有源文件）
4. [agent] 读 `docs/s5b_design_input.md`：存在且非空时以其为准校正推断结果；
   **空/缺失时由 Agent 基于 S2 规格与 S4 硬件事实自主判断**
   （功能映射/协议/任务划分）
5. [agent] 综合识别所需外设、业务功能、协议、设备（**对照 S4 facts 确认所需
   外设已实际连接且引脚角色匹配**，避免定义硬件不存在的能力）
6. [agent] 从应用需求出发定义 Port 接口：按应用能力拆分、只用基本类型和不透明
   句柄、生命周期 init/open/close/deinit；**语义约定强制执行**（port_err_t /
   timeout_ms / 线程安全声明 / 回调显式注册 + ISR 上下文标注，见
   `port_design_principle.md`）
7. [agent] 逐模块编写 `src/app/*`、`src/protocol/*`、`src/driver/*`、`src/main.c`
   （严格按标准骨架二选一）；**跳过任务书标注"用户已修改"的文件**，
   对这些文件读现状保持 manifest 一致
8. [agent] 填写 `outputs/s5b/port_interface_manifest.json`（含 `version`，
   函数签名与头文件一字不差）
9. [rule] 运行校验：
   ```bash
   python skills/port-contract-and-app/scripts/validate.py --config <项目>/config.json
   ```
   （validate 内部最后自动调用公共工具 `skills/_shared/scripts/ide_sync.py`
   同步 IDE 工程：src/ 差异同步 + 全局文件锁；工程文件缺失或同步失败时
   输出 `outputs/_shared/ide_sync_manual.md` 手动清单，不影响 S5b 产物）
10. [agent] 校验失败（退出码 1）→ 按失败报告修复，重跑第 9 步，直到通过
    （state 变为 done）

## 使用方法

```bash
# 前置：S2 已在同一项目执行（可与 S5a 并行）
python skills/port-contract-and-app/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 按任务书生成代码 →
python skills/port-contract-and-app/scripts/validate.py --config examples/gd32f205vet6/config.json
```

## 换平台语义（重要）

| 架构 | 换 MCU/换 RTOS 时 S5b 产物 |
|------|---------------------------|
| layered / full | 换 RTOS：**不变**（只影响 S5a 的 rtos_hw_init 与 S5c 的 OSAL 实现）。换 MCU：S4 facts 随之重跑更新，硬件连接语义不变（同角色拓扑）时产物语义稳定、可复用；拓扑变化（外设数量/角色变化）时需重跑 S5b |
| flat | **需重跑 S5b**（flat 下 APP 直接访问寄存器/厂商库，含平台相关代码） |

"S5b 产物哈希不变"的验收项**仅适用于 layered/full 架构且硬件连接语义不变**。

## 依赖

- Python 3.10+，jsonschema（契约校验）
- Agent 需可读取 S2/S4 产物、任务书指定的参考材料与 IDE 工程文件（只读）

## 禁止事项

**rule 脚本侧**：不修改 config.json；不读写其他 Skill 的 state.json 字段；
不修改 S2/S4 产出的文件；不生成任何 C 代码。

**Agent 侧**：
- 不得将 S4 facts 中的厂商实例名（USART5/SPI2）、引脚号（PC6）、网络名硬编码
  进 Port 接口、APP、driver 等平台无关产物（注释中的设计说明除外）
- 不依赖 S5a 的任何产物（S4 facts 仅作决策依据）
- **不要修改 IDE 项目工程文件**——同步由公共工具 skills/_shared/scripts/ide_sync.py
  完成，本 Skill 只输出待添加清单（兜底参考）
- 所有 APP/Driver/协议层源文件不得 include 任何 HAL 头文件与 RTOS 头文件
  （`hal_init.h`/`board_init.h` 为项目内部总入口头，允许在 main.c 中 include）
- RTOS 相关调用必须通过 `osal_port.h`
- Port 接口只使用基本类型和不透明句柄，语义约定见 `port_design_principle.md`
  （统一错误码/超时/线程安全声明）；DMA 不得单独暴露给 APP（隐藏在 UART 等
  Port 实现中）
- 不得把所有 APP 逻辑塞进一个 `app.c`，不得把所有 Port 接口塞进一个 `port.h`
- 不得把代码（含 Mock）放在 `outputs/` 中
- flat 架构下不生成外设 Port 层（`<外设>_port.h`），但 `rtos != "none"` 时
  仍须生成 `osal_port.h`
- **不重写任务书标注"用户已修改"的文件**（skip-if-modified）；manifest 必须
  与实际交付的头文件一致
