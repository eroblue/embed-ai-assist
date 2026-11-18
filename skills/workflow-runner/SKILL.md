---
name: workflow-runner
description: "S12 工作流配置与执行入口。用户在 PyQt6 GUI 保存方案，然后要求 Agent 执行 S12；Agent 顺序调用已勾选 Skill 并记录实时进度和每步耗时。"
---

# S12 workflow-runner

## 用途

用户双击仓库根目录的 `tools/EmbedAI-S12.exe`，选择项目 `config.json`。通用配置显示项目名称、目标工程及全局工具路径；在工作流配置中，S7b 面板设置构建参数、S9 面板设置烧录工具、S10 面板设置串口参数。每个面板把“项目默认参数”和“仅当前方案覆盖”分开显示。勾选需要执行的 Skill，保存命名方案后，回到项目 Agent 对话框输入“执行 S12”或粘贴 GUI 复制的方案路径，由 Agent 按方案顺序调用 Skill。

各 Skill 仍可单独运行。S12 不修改其他 Skill 的 state 或产物；S12 的事件文件只记录运行进度。

## 目录结构

- `scripts/config_service.py`：项目配置、方案验证和保存。
- `scripts/gui.py`、`scripts/start_s12.pyw`：PyQt6 界面与启动器。
- `scripts/progress.py`：Agent 在步骤边界调用的进度记录 CLI。
- `schemas/`：方案及事件契约。
- `references/skill_parameters.md`：UI 字段到现有 Skill 入口的映射。
- `assets/`：示例方案和 QSS 样式。

## 输入

项目 `config.json`、保存的 `workflows/<方案>.json`。项目路径以 Agent 当前项目为准；若仅输入“执行 S12”且该项目有多个方案，列出方案请用户指定。指定方案必须属于当前项目。

## 输出

GUI 保存或更新项目方案。执行时在 `<项目根>/<build_target>/outputs/s12/<run_id>/events.jsonl` 写入运行和步骤事件。不写 `state.s12`；各 Skill 自己写状态和产物。

## 执行步骤

1. 确认当前项目 `config.json`，读取并校验方案。检查方案目标与 `project.build_target` 一致。
2. 阅读每个已勾选 Skill 的 `SKILL.md` 与本方案参数。只执行已勾选项；参数适配遵守 `references/skill_parameters.md`。遇到无法传递的参数，停止并说明，不得假装生效。
3. 运行 `python skills/workflow-runner/scripts/progress.py start --profile <方案绝对路径>`，记录输出的 run ID。
4. 对每个已勾选步骤，先记录 `step-start`，再按该 Skill 自身流程执行。人工等待期间记录 `wait-start` 和 `wait-end`。长时间操作期间使用 `heartbeat` 保持监控更新。
5. 每步完成后调用 `step-end --status done|failed --step-id <ID>`；失败则停止后续步骤。最后调用 `finish --status done|failed`。即使步骤失败，尽力记录结束事件。
6. 向用户报告各 Skill 自身的结果及 S12 的运行 ID。重跑同一方案时生成新 run ID。

示例命令：

```powershell
python skills/workflow-runner/scripts/progress.py start --profile examples/stm32f103zet6/workflows/仅编译.json
python skills/workflow-runner/scripts/progress.py step-start --profile <方案> --run-id <ID> --step-id S7b
python skills/workflow-runner/scripts/progress.py heartbeat --profile <方案> --run-id <ID> --step-id S7b
python skills/workflow-runner/scripts/progress.py step-end --profile <方案> --run-id <ID> --step-id S7b --status done
python skills/workflow-runner/scripts/progress.py finish --profile <方案> --run-id <ID> --status done
```

## 使用方法

普通用户双击 `tools/EmbedAI-S12.exe`。开发者可使用 `python skills/workflow-runner/scripts/gui.py <项目config.json>`；Windows 打包命令为 `python tools/build_gui.py s12`。保存方案后复制界面显示的执行指令到当前项目的 Agent 对话框。

## 依赖

Python 3.10+、PyQt6、jsonschema。安装 GUI 依赖：`python -m pip install PyQt6 jsonschema`。

## 禁止事项

- GUI 点击“确定”不执行 Skill。
- 同一项目目标有未结束 S12 运行时，不开始第二个运行。
- 不执行未勾选步骤，不自动添加修复步骤。
- 项目设置只有用户在 GUI 明确保存时才写项目 `config.json`。

需求依据：`docs/skill_requirements/S12 requirement.md`。
