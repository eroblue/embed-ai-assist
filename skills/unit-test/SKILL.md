---
name: unit-test
description: "S8 嵌入式 C 单元测试：按配置选择有限的程序单元，编写主机侧用例和必要的 Mock，编译运行并记录可追溯结果。S5 代码就位后或修复后按需执行。"
---

# S8 unit-test

## 用途

验证一个函数、状态机或模块在给定参数和外部接口行为下是否符合已确认预期。主机测试结果不代表实机电气、时序或整机功能通过。需求依据见 `docs/skill_requirements/S8 requirement.md`。

## 目录结构

- `scripts/prepare.py`：扫描候选源模块、选择本轮范围，输出任务书。
- `scripts/run.py`：根据项目 `tests/unit/test_plan.json` 编译和运行选中测试。
- `scripts/validate.py`：核对结果、写报告、只更新 `state.s8`。
- `schemas/`：输入、测试计划、产物及状态契约。
- `references/test_design_rules.md`：编写测试和 Mock 时阅读。

## 输入

项目 `config.json`、目标工程源码、可用的需求/设计/接口依据。`s8.selection` 可设 `budget`、`ratio`、`explicit`、`changed`、`all`；缺省每批 Agent 最多新增或更新 20 个单元测试。测试程序与 Mock 放项目 `<build_target>/tests/unit/`。`changed` 模式需 `--baseline` 指向此前的 `unit_inventory.json`。

## 输出

每轮独立写入 `<build_target>/outputs/s8/<run_id>/`：候选清单、选择清单、源码快照、编译/运行日志、结果和中文报告。`state.json` 仅更新 `s8` 字段；有模块缺少测试计划时为 `partial`，只有本批全部可执行且通过时才为 `done`。候选清单是保守的源模块扫描结果，比例分母在报告中明确标为暂定值。

## 执行步骤

1. 运行 `python skills/unit-test/scripts/prepare.py --config <project-config>`；按需加 `--mode`、`--ratio`、`--units`、`--critical-units`、`--max-agent-units`、`--baseline`。
2. 阅读输出目录的 `generation_brief.md` 与 `selection.json`，只处理本批 `batch` 单元。阅读测试设计规则与相应需求、设计、头文件、源码。
3. 在目标工程 `tests/unit/` 编写或更新 `test_plan.json`、测试 C 文件和 Mock。用例预期必须有独立依据；缺失时标 `needs_clarification`。不要为测试通过修改生产代码。
4. 运行 `python skills/unit-test/scripts/run.py --config <project-config> --run-dir <prepare 输出目录>`。测试程序每个用例输出一行 `S8_CASE\t<case-id>\tPASS` 或 `FAIL`，退出码也须反映失败。
5. 运行 `python skills/unit-test/scripts/validate.py --config <project-config> --run-dir <同一目录>`。向用户报告实际执行范围、失败、延期和未选范围。

## 依赖

Python 3.10+、`jsonschema`、主机 C 编译器。默认探测 `gcc`、`clang`、`cc`；可用 `s8.host_compiler` 显式指定。

## 禁止事项

- 不把扫描出的源码模块数量称为准确的可测单元覆盖率。
- 不把延期、未选或待确认单元计为通过。
- 不把 Mock/测试入口放入目标固件编译清单，不自动烧录或触发 S5 修复。
