---
name: "port-contract-and-app"
description: "S5b Port 契约与应用，三段式执行模型 + 两阶段生成：rule 脚本 prepare.py 检查 S2/S4 就绪（均可选，缺失自动降级）并输出 Agent 任务书，Agent（LLM）阶段 A 先做功能模块拆分、逐模块编写 Mermaid 流程图（docs/flow/，用户审核 approved 后经 flow_differ 判定 full/incremental/skip 再按映射规则生成模块代码），阶段 B 完成顶层连接（app.c/main.c/任务创建）；Agent 定义平台无关的 Port/OSAL/Power 接口并生成 APP、协议层、设备驱动代码，填写 port_interface_manifest.json（S5c 实现 Port 的唯一依据）；rule 脚本 validate.py 校验产物（流程图一致性/禁止 include/mtime 守卫），并调用公共工具 ide_sync.py 同步 IDE 工程。与 S5a 可并行；产物全部平台无关。"
---

# port-contract-and-app Port 契约与应用（S5b）

## 用途

从功能规格书（S2，可选）、软件规格书、S4 硬件事实（可选）、用户设计输入及
参考材料出发，定义平台无关的 Port / OSAL / Power 接口契约，生成 APP、
任务化 APP、协议层、设备驱动代码与 main.c。核心是通过"功能模块拆分 →
单模块 Mermaid 流程图 → 用户审核 → 单模块代码 → 顶层连接逻辑"的分步生成
策略，保证应用逻辑代码的质量和可维护性。**本 Skill 全部产物平台无关**。

**整体流程层级：S5b，代码生成层（平台无关）**。

- 上游依赖：**S2 spec-reader 与 S4 circuit-investigator 均为可选**（S2 缺失
  降级为设计输入驱动模式；S4 缺失时 manifest 的 hw_instance 置 null）
- 并行关系：与 **S5a hardware-initializer 无数据依赖（互不读对方产物），
  可并行执行**
- 下游消费：**S5c port-implementer** 只依据 `outputs/s5b/port_interface_manifest.json`
  实现 Port 接口，禁止硬解析 C 头文件
- 架构模式：Ports & Adapters 中的 USER 层（平台无关）

## 执行模型：rule 准备 → Agent 两阶段生成 → rule 校验

**策略（与 S5a 一致，用户拍板）**：确定性的规则用本地脚本实现；流程图内容、
接口契约与 C 代码由 Agent（LLM）生成——新增平台/新增 RTOS 无需为本 Skill
编写任何适配脚本。

```
[rule]  prepare.py    配置/就绪检查（S2/S4 可选）→ ensure_layout 幂等建目录
                       → 设计输入/能力缺口机械分析 → 流程图现状盘点
                       → 镜像代码基线（code_baseline/，增量范围校验用）
                       → outputs/s5b/generation_brief.md（任务书）
                       → state.s5b.status = "running"

[agent] 阶段 A（~80%，模块级）
       ① 读任务书 + 本文件 + references/ → 读输入材料（提取要点见
         software_spec_guide.md）
       ② 功能模块拆分 → 模块清单（模块名/一句话职责/图类型/需求来源）
         **先给用户过目再画图**（拆分返工比画图返工贵十倍）
       ③ 逐模块画流程图 → <target>/docs/flow/<模块>_<state|flow|sequence>.md
         （status=draft；规范 mermaid_*_guide.md，骨架 assets/flow_skeletons/）
       ④ flow_validator.py 校验流程图规范 → 修正到通过
       ⑤ 用户审核（交互点 1）→ 用户确认后 Agent 代改 status=approved
         （approved_at/by + version）——**Agent 不得自行批准**
       ⑥ flow_differ.py → flow_diffs/*.json（full/incremental/skip/blocked）
       ⑦ 按 generation_mode 生成模块代码：full 全量 / incremental 定点修改
         （映射规则 flow_to_code_mapping.md + incremental_generation_rules.md）
         / skip 绝不动 / blocked 报告用户 / deprecated 移除代码
       ⑧ diff_range_checker.py（incremental 后）→ 异常则报告用户（交互点 2）
       ⑨ 填 port_interface_manifest.json + traceability.json（+可选
         recommendations/capability_gap）

[agent] 阶段 B（~20%，顶层连接）
       ⑩ app.c/h（初始化汇总 + 主循环/任务创建，任务创建统一收敛于此）
         + main.c（不存在时创建，标准骨架）+ 模块间调度连接
       ⑪ 可选：系统级流程图 docs/flow/system_state.md

[rule]  validate.py    6 项校验：流程图规范/一致性 + approved 模块代码存在
                       + manifest/traceability/gap 契约 + 引用文件存在
                       + 禁止 include（黑名单 + 分层白名单）
                       + mtime 守卫（full/incremental 模块代码须晚于任务书）
                       → ide_pending_files.json → state.s5b.status = "done"
                       → 调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）
```

- validate 失败（退出码 1）→ Agent 按失败报告修复产物，**重跑 validate.py**
  （state 保持 running，不写 error）
- 环境/契约失败（退出码 3）→ state 写 error，先解决环境/config 问题
- **增量核心**：流程图是代码的唯一蓝图——代码可手改，但手改后必须回填
  流程图（硬性规定）；流程图无变更的模块走 skip，**不重跑代码生成**

## 目录结构

```
port-contract-and-app/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/                          ← 7 个数据契约（jsonschema 2020-12）
│   ├── input.schema.json             ← 输入契约（S2/S4 可选就绪性）
│   ├── output.schema.json            ← 输出契约（state.json 的 s5b 字段）
│   ├── port_interface_manifest.schema.json ← 接口契约（S5c 唯一依据）
│   ├── traceability.schema.json      ← 追踪矩阵契约
│   ├── capability_gap.schema.json    ← 能力缺口契约
│   ├── flow_diff.schema.json         ← 流程图 diff 结果契约
│   └── flow_index.schema.json        ← 流程图清单契约
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                   ← 共享分析：配置/设计输入/S4 摘要/Mermaid 解析
│   ├── prepare.py                    ← 第 1 段：就绪检查 + 任务书 + 代码基线
│   ├── flow_validator.py             ← 流程图规范校验（画完即调，可单文件调试）
│   ├── flow_differ.py                ← 流程图 diff + 生成模式判定（approved 后）
│   ├── diff_range_checker.py         ← 增量代码范围校验（拦截异常重写）
│   ├── validate.py                   ← 第 3 段：终验 + state 收口 + IDE 同步
│   └── ide_pending_exporter.py       ← IDE 待添加清单导出（兜底参考）
├── references/                       ← Agent 生成质量锚点（11 个）
│   ├── port_design_principle.md      ← Port 接口设计原则（八章）
│   ├── osal_design_principle.md      ← OSAL 设计原则（硬约束/接口清单）
│   ├── file_split_guide.md           ← 文件拆分与命名规范
│   ├── software_spec_guide.md        ← 输入材料提取要点（优先级/降级模式）
│   ├── mermaid_state_guide.md        ← 状态机图规范（语法子集/命名）
│   ├── mermaid_flowchart_guide.md    ← 顺序流程图规范（flowchart TD）
│   ├── mermaid_sequence_guide.md     ← 时序图规范（参与者/消息语义）
│   ├── flow_to_code_mapping.md       ← 流程图 → C 代码映射规则（增量动作表）
│   ├── flow_diff_rules.md            ← diff 机制/变化率/版本管理
│   ├── incremental_generation_rules.md ← 定点修改原则/范围校验阈值
│   └── ide_project_formats.md        ← IDE 工程说明（Agent 不碰工程文件）
└── assets/
    ├── port_templates/               ← 8 个 Port 接口模板（挑选→裁剪→扩展）
    │   ├── uart_port.h.tpl / i2c_port.h.tpl / spi_port.h.tpl
    │   ├── gpio_port.h.tpl / adc_port.h.tpl / timer_port.h.tpl
    │   ├── osal.h.tpl（rtos != none 时生成）
    │   └── power_port.h.tpl（power.enabled 时生成）
    ├── flow_skeletons/               ← 3 个流程图骨架（front-matter + 围栏）
    ├── port_interface_manifest_example.json ← 示例（已过 schema 校验）
    ├── traceability_example.json
    └── flow_diff_example.json
```

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| spec.* | state.json（S2 写入） | object | **否** | S2 缺失/无 spec_path → 设计输入驱动模式（任务书标注） |
| circuit.facts | state.json（S4 写入） | object | **否** | 硬件事实摘要进任务书；缺失 → manifest hw_instance=null |
| platform | config.json（项目层） | string | 是 | 芯片平台名（定位参考材料） |
| project.build_target | config.json（项目层） | enum | 否 | `App` / `BootLoader`，缺省 App——目标工程根；流程图放 `<target>/docs/flow/`（App 与 BootLoader 各自独立） |
| project.architecture | config.json（项目层） | enum | 否 | `flat` / `layered` / `full`，缺省 layered；flat 无 Port 层 |
| project.rtos | config.json（项目层） | enum | 否 | `none` / `FreeRTOS` / `RT-Thread` / `Zephyr`，缺省 none |
| project.power.enabled | config.json（项目层） | bool | 否 | 缺省 false |
| project.inputs.* | config.json（项目层） | string/array | 否 | software_spec / demos / sdk / existing_project / ide_project / s5b_design_input |
| s5b.language / s5b.port_split | config.json（项目层） | string | 否 | 缺省 c99 / 按应用需求推断 |
| docs/s5b_design_input.md | 项目 docs/ 目录 | markdown | 否 | **用户设计输入**，见下 |

> 配置契约统一由根目录 `schemas/config.schema.json` 定义，加载时统一拦截非法值。
> **三配置项只认 config 显式值**（S5a/S5b/S5c 一致，不做任何推断）：S2/S4 事实
> 与显式值冲突时 prepare 在任务书中提示用户确认 config，不自行改判。

### 用户设计输入（docs/s5b_design_input.md）

用户向 Agent 传达应用设计意图的输入通道，**优先级最高**。**文件不存在、内容
为空或全部为 `none` 时，改由 Agent（LLM）基于 S2 规格、S4 硬件事实与经验
自主判断**（功能映射、协议选择、任务划分），未定项进 recommendations.json
让用户拍板。已知段（功能规格/状态机/时序/错误处理/硬件使用/功能映射/协议/
任务划分）的机械解析结果按段内嵌任务书；各段产出对照表见
`references/software_spec_guide.md` 第三节。填写示例见项目
`docs/demo/s5b_design_input_demo.md`：

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

### S4 硬件事实的使用边界

S5b 读取 `outputs/circuit_facts.json` 仅用于**提升决策准确率**（功能映射定位、
外设可用性确认、通信协议引脚角色核对；prepare 已做引脚级机械比对，缺口进
capability_gap.json 由 Agent 复核）。

**边界铁律（产物保持平台无关）**：S4 facts 是**决策依据**，不得将厂商实例名
（USART5/SPI2）、引脚号（PC6）、网络名硬编码进 Port/APP/driver 产物代码
（注释中的设计说明除外）——硬件映射只进 `port_interface_manifest.json`
数据侧（hw_instance/hw_source 字段，换平台只改 manifest 不改代码）。

## 输出

### 写入 S5b 产物目录（Agent 生成的代码，目录由 PROJECT_LAYOUT.md 解析）

> prepare 段已按 `docs/PROJECT_LAYOUT.md` 幂等创建骨架，任务书第 6 节给出
> 确切路径（32 位 layered 典型值如下；改布局文档即全局生效）。

| 产物 | 目录（典型） | 生成条件 |
|------|--------------|----------|
| `app_<功能>.c/h`、`protocol_<名称>.c/h`、`main.c` | `App/Src/` + `App/Inc/` | 按功能模块拆分 |
| `app_<功能>_task.c/h` | `App/Src/` | RTOS 且非 flat；任务创建统一在 app.c |
| `app.c/h` | `App/Src/` | 总是（初始化汇总 + 主循环/任务创建） |
| `driver_<设备>.c/h` | `Drivers/BSP/{Src,Inc}/` | 板载器件驱动（与 S5a 初始化同层不同名前缀） |
| `<外设>_port.h`（uart/i2c/spi/gpio/adc/timer…） | `Drivers/Port/Inc/` | **非 flat** 且该外设有使用（模板 assets/port_templates/） |
| `osal.h` | `Drivers/Port/Inc/` | **RTOS 时总是生成（含 flat）** |
| `power_port.h` | `Drivers/Port/Inc/` | power.enabled 且非 flat |

**OSAL 与外设 Port 层是两个正交维度**：Port 管"外设无关"，OSAL 管"RTOS 无关"。
flat 只豁免外设 Port 层（APP 直接调 S5a 的 BSP 初始化接口）；8 位 MCU 跑
RTOS 是合法场景，此时仍生成 `osal.h`，APP 的 RTOS 调用全部经 OSAL。

### 流程图（→ `<target>/docs/flow/`，S5b 核心中间表示）

| 产物 | 内容 |
|------|------|
| `<模块>_state.md` | 状态机（stateDiagram-v2 + front-matter） |
| `<模块>_flow.md` | 顺序流程（flowchart TD + front-matter） |
| `<模块>_sequence.md` | 时序（sequenceDiagram + front-matter） |

规则：**模块名 = 代码文件基名 = 流程图模块名；一模块只允许一张图**。
front-matter（name/status/version 必填 + created_at/approved_at/approved_by/
base_version）；status 生命周期 draft→review→approved（生成代码前提）；
approved 后修改须置 dirty 重新审核且 version 递增。版本快照自动存
`docs/flow/.history/<模块>/<版本>.md`（diff 基线，勿手改）。

### main.c 标准骨架（两种形态，不得混写）

```c
/* 裸机（rtos == "none"） */
#include "hal_init.h"      /* 或 flat 架构的 board_init.h */
#include "app.h"

int main(void)
{
    hal_init();            /* S5a 总入口（项目内部头，不算 HAL 头） */
    app_init();
    while (1) {
        app_loop();        /* 主循环，含低功耗 WFI 由 app 层决定 */
    }
}

/* RTOS（rtos != "none"） */
#include "hal_init.h"
#include "app.h"
#include "osal.h"

int main(void)
{
    hal_init();
    app_init();            /* 内部经 osal_task_create 创建各任务 */
    osal_kernel_start();   /* 启动调度器，不返回 */
    return 0;
}
```

### 写入 outputs/s5b/（数据）

| 产物 | 内容说明 |
|------|----------|
| `generation_brief.md` | Agent 任务书（9 节：项目信息/输入清单/硬件摘要/流程图现状/能力缺口/生成要求/增量模式/禁止事项/执行步骤） |
| `port_interface_manifest.json` | 接口契约（headers[].logical_instances/interfaces/callbacks + power），**S5c 实现 Port 的唯一依据** |
| `traceability.json` | 追踪矩阵（需求→流程图→文件→函数，含数据来源） |
| `capability_gap.json` | 能力缺口（rule 机械比对 + Agent 复核，无缺口时删除） |
| `recommendations.json` | 可选，Agent 推荐未定项清单（首轮全量生成；增量轮次不重复推荐已确认项） |
| `flow_index.json` | 流程图清单（只登记 approved/deprecated） |
| `flow_diffs/<模块>_diff.json` | 每模块 diff 结果（变化明细 + generation_mode） |
| `code_baseline/` + `code_snapshot.json` | prepare 段镜像的上轮代码基线（增量范围校验依据） |
| `diff_check_result.json` / `diff_anomaly.json` | 增量范围校验结果 / 异常报告 |
| `ide_pending_files.json` | IDE 待添加清单（分组 + include 路径，兜底参考）。实际同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成（validate 段自动调用，失败输出 `outputs/_shared/ide_sync_manual.md`） |

### 写入 state.json（仅 s5b 字段）

`status`（running/done/error）、`rtos`、`architecture`、`power_enabled`、
`generation_brief`、`incremental`、`flows`（流程图文件列表）、`flow_diffs`、
`port_manifest`、`port_headers`、`osal_header`（null=裸机）、`power_header`、
`app_sources`/`app_headers`（validate 从实际产物分类收集：main_source、
protocol_sources、task_sources）、`driver_sources`/`driver_headers`、
`main_source`、`ide_pending_files`、`error`、`updated_at`。

指针/数据分离：代码在产物目录（PROJECT_LAYOUT 解析），流程图在 docs/flow/，
数据在 `outputs/s5b/`，state.json 只存指针。

## 执行模式总览

生成模式由 flow_differ **逐模块判定**（同一轮中模块 A 可 full、模块 B 可 skip）：

| 模式 | 触发条件 | 来源 |
|---|---|---|
| `full` | 首次登记 / 变化率 > 60% / 基线快照缺失 | 已实现（flow_differ） |
| `incremental` | 变化率 ≤ 60% | 已实现（flow_differ） |
| `skip` | 内容 hash 与上轮一致 / 节点边无实质变更 | 已实现（flow_differ） |
| `blocked` | approved 后修改未重审 / 版本回退 / dirty / 基线快照 hash 与 index 不一致 | 已实现（flow_differ） |
| `deprecated` | 模块在 flow_index 登记为废弃 | 已实现（flow_differ，处置：移除代码） |

**分支入口原则**：不走完整主流程的维护操作（如未来的 code-fix、impact 分析）作为**独立 Agent 入口**新增章节，不改动上述主流程与散件脚本——按需触发、默认不执行（与 Mock 可选后处理同模式）。禁止为预留而建空壳脚本或空壳参数。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare：
   ```bash
   python skills/port-contract-and-app/scripts/prepare.py --config <项目>/config.json
   ```
   退出码 0=任务书就绪 / 1=输入问题（按报告解决后重跑）/ 2=环境错误。
2. [agent] 读 `outputs/s5b/generation_brief.md`（9 节全读），通读本文件；
   按任务书第 2 节清单逐份读输入材料（提取要点 `references/software_spec_guide.md`）。
   维护期（flow_index 已存在）任务书自动裁剪 demos/sdk/existing_project
   学习材料——首轮全量学习，增量轮次按任务书标注的路径按需查阅。
3. [agent] 功能模块拆分：按 `file_split_guide.md` 命名规范产出**模块清单**
   （模块名/一句话职责/图类型/需求来源），**先给用户过目确认再画图**。
4. [agent] 逐模块画流程图（骨架 `assets/flow_skeletons/` + 对应
   `references/mermaid_*_guide.md`；修改已有图时以现有文件为锚点定点修改，
   不重新生成），保存 `<target>/docs/flow/`，status=draft。
5. [rule] 校验流程图规范：
   ```bash
   python skills/port-contract-and-app/scripts/flow_validator.py --config <项目>/config.json
   ```
   失败 → 修正重跑（只校验单文件可加 `--file <target>/docs/flow/<模块>_state.md`）。
6. [agent→用户] **审核交互点 1**：请用户查看流程图（Mermaid Live Editor /
   Typora / IDE 插件渲染均可），逐模块确认。用户确认后 Agent 代改
   front-matter：`status: approved` + `approved_at`/`approved_by` 填写
   （**用户未确认不得自行批准**）。
7. [rule] 流程图 diff（approved 后）：
   ```bash
   python skills/port-contract-and-app/scripts/flow_differ.py --config <项目>/config.json
   ```
   产出每模块 generation_mode（判定规则 `references/flow_diff_rules.md`）。
8. [agent] 按模式生成模块代码（映射规则 `references/flow_to_code_mapping.md`）：
   - `full`：全量生成该模块（变化率 >60% 时先向用户说明重构范围）
   - `incremental`：**只做定点修改**（`references/incremental_generation_rules.md`）
   - `skip`：**绝对不动该模块任何文件**
   - `blocked`：报告用户（dirty/未定稿），等待处理
   - `deprecated`：移除对应代码文件（含 IDE 引用由 ide_sync 收口）
   flat 架构不生成 Port 头；Port 头从 `assets/port_templates/` 挑选→裁剪→扩展。
9. [rule] 增量范围校验（有 incremental 模块时）：
   ```bash
   python skills/port-contract-and-app/scripts/diff_range_checker.py --config <项目>/config.json
   ```
   异常（退出码 1）→ **交互点 2**：向用户报告 `diff_anomaly.json`，按
   incremental_generation_rules.md 第四节处置（定点恢复或经同意转全量），
   不得自行修复后继续。
10. [agent] 填数据产物：`port_interface_manifest.json`（接口签名与头文件
    一字不差，hw_instance 按 S4 facts / null）、`traceability.json`
    （需求来源标注 spec/software_spec/design_input/inferred）、可选
    `recommendations.json` / `capability_gap.json`。
11. [agent] 阶段 B 顶层连接：`app.c/h`（初始化汇总 + 主循环/任务创建，任务
    创建统一收敛在此）+ `main.c`（标准骨架，不存在时创建）+ 模块间调度连接；
    可选系统级 `docs/flow/system_state.md`。
12. [rule] 终验：
    ```bash
    python skills/port-contract-and-app/scripts/validate.py --config <项目>/config.json
    ```
    （内部自动调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程，
    失败不中断并输出手动清单）
13. [agent] 校验失败（退出码 1）→ 按失败报告修复产物，重跑第 12 步直到通过
    （state 变为 done）；退出码 3（环境/契约错误）→ state 已写 error，
    先解决环境问题。

## 使用方法

```bash
# 前置：S1 已建立工作区（S2/S4 可选；与 S5a 可并行）
python skills/port-contract-and-app/scripts/prepare.py --config examples/gd32f205vet6/config.json
# → Agent 阶段 A（拆分确认 → 画图 → 审核 → diff → 生成）+ 阶段 B（顶层连接）→
python skills/port-contract-and-app/scripts/flow_validator.py --config examples/gd32f205vet6/config.json   # 步骤 5（画完即调）
python skills/port-contract-and-app/scripts/flow_differ.py --config examples/gd32f205vet6/config.json      # 步骤 7（approved 后）
python skills/port-contract-and-app/scripts/diff_range_checker.py --config examples/gd32f205vet6/config.json  # 步骤 9（增量后）
python skills/port-contract-and-app/scripts/validate.py --config examples/gd32f205vet6/config.json        # 步骤 12（终验）
```

## 换平台语义（重要）

| 架构 | 换 MCU/换 RTOS 时 S5b 产物 |
|------|---------------------------|
| layered / full | 换 RTOS：**不变**（只影响 S5a 的 rtos_hw_init 与 S5c 的 OSAL 实现）。换 MCU：代码只含逻辑实例名（硬件映射在 manifest 数据侧），硬件连接语义不变（同角色拓扑）时产物复用；拓扑变化（外设数量/角色变化）时需重跑 S5b |
| flat | **需重跑 S5b**（flat 下 APP 直接访问寄存器/厂商库，含平台相关代码） |

"S5b 产物哈希不变"的验收项**仅适用于 layered/full 架构且硬件连接语义不变**。

## 依赖

- Python 3.10+，jsonschema（契约校验）
- Agent 需可读取任务书列出的参考材料与 IDE 工程文件（只读）
- 可选：mermaid-cli（流程图批量渲染预览；缺失时提示用户用 Mermaid Live Editor 查看）

## 禁止事项

**rule 脚本侧**：不修改 config.json；不读写其他 Skill 的 state.json 字段；
不修改 S2/S4 产出的文件；不生成任何 C 代码与流程图内容。
state.json 写入统一经公共工具 `skills/_shared/scripts/state_store.py`
（独占文件锁内完成读改写，陈旧锁自动清理——与 S5a 并行执行不丢字段）。

**Agent 侧**：
- **不得在流程图未定稿（status != approved）时生成对应模块的代码**
- **不得重新生成已有流程图，只能以现有文件为锚点做定点修改**；approved 后
  修改必须置 dirty 重新审核、version 递增
- **不得在流程图无变更（skip）时重跑对应模块的代码生成**
- **不得自行批准流程图**（status→approved 只能发生在用户确认之后）
- 增量生成**无权重写整个文件**，只做定点修改；diff 范围异常时不得自行修复
- 不得将厂商实例名/引脚号/网络名硬编码进 Port/APP/driver 产物代码
  （manifest 数据侧的 hw_instance 除外；注释中的设计说明除外）
- 不依赖 S5a 的任何产物（S4 facts 仅作决策依据）
- **不修改 IDE 项目工程文件**——同步由公共工具 skills/_shared/scripts/ide_sync.py
  完成，本 Skill 只输出待添加清单（兜底参考）
- 所有 APP/Driver/协议层源文件不得 include 任何 HAL 头与 RTOS 头
  （`hal_init.h`/`board_init.h` 为项目内部总入口头，允许在 main.c 中 include；
  flat 架构允许 APP include S5a 的 `*_init.h`）
- RTOS 相关调用必须通过 `osal.h`；Port 层头文件不 include 任何 app/driver 头
- Port 接口只使用 `<stdint.h>` 基本类型和不透明句柄；DMA 不得暴露给 APP
- 不得把所有 APP 逻辑塞进一个 `app.c`，不得把所有 Port 接口塞进一个 `port.h`
- 不得把代码（含 Mock）放在 `outputs/` 中；Mock Port 放 `outputs/s5b/mocks/`
  仅限纯桩数据文件，可编译 Mock 实现属代码、放产物目录并登记 ide 清单
- flat 架构不生成外设 Port 层，但 RTOS 时仍须生成 `osal.h`
