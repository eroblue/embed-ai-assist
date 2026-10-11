---
name: "build"
description: "S7b 编译构建：调用工具链编译目标工程（Keil/IAR/GCC Make/CMake CLI 机制 + 厂家 IDE GUI 机制），收集解析日志，产出 bin/hex 供 S6 合并与 S9 烧录。S5 全部完成后触发。"
---

# build 编译构建（S7b）

## 用途

调用工具链编译目标工程（App / BootLoader），**双编译机制**：

- **CLI 机制**（`keil` / `iar` / `gcc_make` / `gcc_cmake`）：命令行调用，纯 rule 执行
- **GUI 机制**（`vendor_ide`）：厂家自研 IDE 无 CLI（辉芒微/和泰等）时，Agent 打开
  工程、发送编译快捷键完成编译，`build.py --collect` 收口

编译成功后**必须产出 bin 格式产物**（S6 firmware-merger 合并 Boot+App 消费）。
编译失败时 Agent 只产出 `error_analysis.md`（不自动修复，与 S5c code-fix 的衔接
由用户显式发起）。

层级与上下游：属于"编译构建"层，在 S5 全部完成后触发（S12 workflow-runner 编排
或用户手动执行）。上游 S5a/S5b/S5c（源码就位）；下游 S6（消费 bin）、S9（烧录
hex/bin）。与 S7a toolchain-setup 仅通过全局 `tool_paths` 解耦：**不读
`s7a.status`、不自动触发 S7a**——prepare 检测到工具缺失时报错提示"先运行 S7a
或手动配置 tool_paths"。

## 目录结构

```text
build/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（state.json 的 S5 系列就绪性）
│   ├── output.schema.json             # 输出契约（state.json 的 s7b 字段）
│   └── build_result.schema.json       # 编译结果摘要契约
├── scripts/                            # rule 轨（无代码生成，无业务逻辑）
│   ├── analysis.py                     # 共享分析（配置加载/构建系统推断/工具链探测/日志解析/产物定位）
│   ├── prepare.py                      # 阶段 1：就绪检查 + 构建系统/配置判定 + 任务书
│   ├── build.py                        # 阶段 2：CLI 编译 / GUI --collect 收口
│   └── validate.py                     # 阶段 4：产物验证 + state 收口
├── references/
│   ├── keil_build_guide.md             # Keil 命令行编译指南（UV4/fromelf/退出码/GBK）
│   ├── iar_build_guide.md              # IAR 命令行编译指南（IarBuild/ielftool/Exe-Obj）
│   ├── gcc_build_guide.md              # GCC Make / CMake 编译指南（objcopy 生成 bin/hex）
│   ├── vendor_ide/                     # 厂家 IDE GUI 编译指南（按 project.vendor_ide 一文件）
│   │   └── _template.md                # 新厂家 IDE 指南编写模板
│   ├── binary_conversion_guide.md      # bin/hex 生成与转换指南
│   └── log_parse_rules.md              # 日志解析规则
└── assets/
    └── build_example.md                # 编译示例（各构建系统命令模板）
```

> S7b 是纯 rule + Agent 分析形态，不存在代码生成，`references/` 下均为工具链
> 使用指南。`analysis.py` 的构建系统推断与工具探测函数被 S7a toolchain-setup
> 复用（禁止两套规则）。

## 输入

### 从 state.json 读取（就绪检查）

| 字段 | 要求 |
|---|---|
| `s5a.status` | 必须 `done`（初始化代码已生成） |
| `s5b.status` | 必须 `done`（APP/Port 契约已生成） |
| `s5c.status` | 必须 `done` 或 `skipped`（flat 架构 skipped） |

### 从 config.json 读取（项目级与全局深合并）

| 参数 | 来源 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `project.build_target` | 项目层 | string | 否 | `"App"` / `"BootLoader"`，缺省 `App` |
| `project.build_system` | 项目层 | string/null | 否 | `keil`/`iar`/`gcc_make`/`gcc_cmake`/`vendor_ide`/`null`（缺省 null 智能推断；vendor_ide 不参与推断） |
| `project.build_config` | 项目层 | string | 否 | 构建配置名，缺省推断（多 target 报错不猜） |
| `project.vendor_ide` | 项目层 | string | vendor_ide 时必填 | 厂家 IDE 标识（定位 references/vendor_ide/<标识>.md） |
| `project.vendor_ide_output_dir` | 项目层 | string | 否 | 厂家 IDE 输出目录（相对工程根，缺省按 vendor 指南如 `Project/Output/`） |
| `project.arch_family` | 项目层 | string | 否 | `mcu8` 时 build_system 必须显式配置 |
| `project.inputs.ide_project` | 项目层 | string | vendor_ide 时必填 | IDE 工程文件路径 |
| `tool_paths.keil` / `keil_fromelf` | 全局层 | string | keil 时 | fromelf 未配置时从 keil 根推导（ARMCLANG 优先） |
| `tool_paths.iar` / `iar_ielftool` | 全局层 | string | iar 时 | ielftool 未配置时从 IarBuild 同目录 common/bin/ 探测 |
| `tool_paths.gcc` / `gcc_objcopy` / `make` / `cmake` | 全局层 | string | gcc 系时 | objcopy 未配置时从 gcc 同目录探测 |
| `tool_paths.vendor_ide` | 全局层 | string | vendor_ide 时 | 厂家 IDE 可执行文件路径 |

## 输出

### 写入 state.json（仅 s7b 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s7b.status` | string | `pending` / `running` / `done` / `error` |
| `s7b.build_system` | string | 本次实际使用的构建系统 |
| `s7b.build_mode` | string | `cli` / `gui`（vendor_ide 为 gui） |
| `s7b.build_config` | string/null | 本次实际使用的构建配置 |
| `s7b.build_target` | string | `App` / `BootLoader` |
| `s7b.artifact_path` | string/null | 主调试产物（`.axf`/`.out`/`.elf`） |
| `s7b.artifact_format` | string/null | `axf` / `out` / `elf` |
| `s7b.hex_path` | string/null | 烧录产物（`.hex`，S9 消费） |
| `s7b.bin_path` | string/null | **合并产物（`.bin`，S6 消费）**；转换工具缺失时 null 并附警告 |
| `s7b.error_count` / `s7b.warning_count` | int | 编译错误/警告数（GUI 无法精确计数为 -1） |
| `s7b.build_log` | string | 日志路径（outputs/s7b/build.log） |
| `s7b.build_result` | string | 结果摘要路径（outputs/s7b/build_result.json） |
| `s7b.error_analysis` | string/null | Agent 分析报告路径（仅失败时） |
| `s7b.gui_build_log` | string/null | GUI 操作记录路径（CLI 机制为 null） |
| `s7b.bin_warning` | string/null | bin 转换工具缺失警告 |
| `s7b.error` | string/null | 错误信息 |
| `s7b.updated_at` | string | ISO 时间戳 |

### 写入 outputs/s7b/（数据）

| 产物 | 内容说明 |
|---|---|
| `generation_brief.md` | Agent 任务书（CLI 为失败分析路径准备；GUI 含 vendor 指南要点/T0/超时/禁止事项） |
| `build.log` | 完整编译日志（多编码解码 UTF-8→GBK→replace） |
| `gui_build_log.md` | GUI 编译操作记录（仅 vendor_ide，Agent 逐步记录） |
| `build_result.json` | 结果摘要（schema 见 build_result.schema.json） |
| `error_analysis.md` | 编译失败时 Agent 产出的根因分析与修复建议 |
| `gui_session.json` | GUI 机制 T0/输出目录会话数据（prepare 写、--collect 读） |

可执行产物（axf/hex/bin）在工程目录（工具链默认位置），state 只存指针与统计
（指针/数据分离）。

## 执行步骤

**四段式：rule prepare → build（CLI=rule / GUI=agent）→ agent analyze（仅失败）→ rule validate**

### 阶段 A：prepare（rule，prepare.py）

1. S5 系列就绪检查（s5a/s5b done，s5c done 或 skipped）。
2. 平台与编译机制判定：mcu8 必须
   显式配置 build_system；cortex_m 配 vendor_ide 报错。
3. 构建系统判定：显式优先；null 时递归扫描推断（深度 3，排除 outputs/Listings/
   Objects/.history/备份目录；`*.uvprojx`→keil、`*.ewp`→iar、`Makefile`→gcc_make、
   `CMakeLists.txt`→gcc_cmake；多候选/零候选报错）。
   **阶段 A'（Makefile 自动生成，仅显式 `build_system=gcc_make`）**：工程根无 Makefile
  时自动生成 Makefile + 链接脚本（uvprojx 解析优先，目录扫描 + 平台惯例 fallback；
  Keil 启动文件自动替换为平台库 GNU 语法同名文件）。链接脚本优先级：工程内用户
  自维护 `.ld` > 平台库 `linker_scripts/*.ld`（零偏移时引用，并清理被取代的旧生成
  脚本）> 工程内生成 `.ld`（重生成）> 按内存布局生成。生成文件首行含
  `# Generated by S7b build` 标记，可重新覆盖；用户自维护文件（无标记）不覆盖
  （skip-if-modified，删除生成文件即恢复自动生成）。推断轨（build_system=null）不生成。
  **flash_offset（OTA App）**：`project.flash_offset > 0` 时必定生成工程内链接脚本
  （平台脚本为固定基址不可直接用），
  `ORIGIN = 基址 + 偏移`、`LENGTH = 容量 - 偏移`（config 权威；非法报错、
  未对齐/疑似双重偏移警告）；与 S5b main.c 重定位字面值、S6/S9 消费值一致。
4. 构建配置判定：显式优先；keil/iar 多 target/configuration 且未配置 → 报错（不猜）。
5. 工具链就绪检查：编译工具缺失 → **退出码 2，提示先运行 S7a**（不自动触发）；
   bin/hex 转换工具缺失 → **警告不终止**（intelhex 兜底）。
6. 生成任务书 `generation_brief.md`；GUI 机制另写 `gui_session.json`（T0）。
7. `state.s7b.status = running`（容忍覆盖上次中断残留）。

### 阶段 B：build

**机制一 CLI（build.py，纯 rule）**：

8. 构造命令并执行（`UV4 -b|-r <uvprojx> -j0 -o <log>` / `IarBuild <ewp> -build
   <config> -log info` / `make -j4` / `cmake --build build -- -j4`；`--rebuild`
   全量重编；`--timeout` 缺省 600s，超时杀进程按失败处理）。
9. 日志落盘 build.log（UTF-8→GBK→replace 多编码解码）。
10. 判定：keil 成功 = 退出码 ∈ {0,1}（1=成功有警告）且解析错误数 0；iar/gcc 成功 =
    退出码 0 且解析错误数 0。
11. 编译成功：定位产物（优先日志解析，缺省按约定路径推断）→ fromelf/ielftool/
    objcopy 生成 bin（工具缺失时 intelhex 从 hex 降级转换）→ hex 缺失时补生成。
12. 输出 build_result.json；state 收口：成功 `done`（bin 失败不算编译失败，
    `bin_path=null` + 警告）；失败保持 `running` → 进入阶段 C。

**机制二 GUI（vendor_ide，Agent 按 vendor 指南 + rule 收口）**：

B1 `[rule]` prepare 记录 T0（gui_session.json + 任务书）。
B2 `[agent]` 启动厂家 IDE（tool_paths.vendor_ide），打开 ide_project，按指南窗口
特征判定就绪。
B3 `[agent]` 按指南发送编译快捷键/菜单操作（仅限指南列出的操作）。
B4 `[agent]` 轮询输出目录 mtime 与 IDE 状态判断完成（超时按失败）。
B5 `[agent]` 抄录 IDE 输出关键行 → build.log；操作全程 → gui_build_log.md。
B6 `[agent]` 关闭工程与 IDE（**不保存任何工程文件改动**，保存提示一律选"否"）。
B7 `[rule]` `build.py --collect`：产物检测（mtime > T0）→ intelhex 转 bin →
build_result.json（错误数按抄录行统计，无法统计为 -1）。

### 阶段 C：analyze（agent，仅编译失败时）

13. 读 build.log + build_result.json + SKILL.md + references/（GUI 另读
    gui_build_log.md，区分"编译失败"与"GUI 操作失败"——后者归环境问题）。
14. 根因四分类：**代码问题**（S5 生成缺陷）/ **配置问题**（工程文件配置错）/
    **环境问题**（工具链版本/路径/依赖）/ **输入问题**（上游产物不一致）。
15. 产出 `error_analysis.md`：错误摘要（按根因分类）/ 每条错误详细分析（消息/
    可能原因/定位建议）/ 修复建议（**只建议不执行**）/ 推荐路径（判定为 S5 代码
    问题时明确写"建议走 S5c code-fix 分支"）。
16. **不自动修复**、不改动任何代码、不触发 code-fix。

### 阶段 D：validate（rule，validate.py）

17. 产物验证：build_result.json 存在且 schema 合法；成功时主产物存在、bin_path
    非空（除非已警告）；失败时 error_analysis.md 存在；GUI 时 gui_build_log.md 存在。
18. state 收口：成功 `done` + 三个产物路径；失败 `error` + error_analysis 路径。
19. 不调用 ide_sync.py（S7b 只读工程文件）；不触发任何下游 Skill。

## 使用方法

```bash
# 前置：S5a/S5b done，S5c done 或 skipped；工具链就绪（或先跑 S7a toolchain-setup）
python skills/build/scripts/prepare.py --config examples/stm32f103zet6/config.json
python skills/build/scripts/build.py --config examples/stm32f103zet6/config.json [--rebuild] [--timeout 600]
# → 成功：build_result.json 含 artifact / hex / bin 三个路径，直接 validate
# → 失败：Agent 读 build.log 产出 error_analysis.md（阶段 C），再 validate
python skills/build/scripts/validate.py --config examples/stm32f103zet6/config.json

# 8 位平台（GUI 机制）：config 显式 build_system="vendor_ide" + project.vendor_ide
# + inputs.ide_project；Agent 按任务书操作厂家 IDE（B1–B6）后：
python skills/build/scripts/build.py --config examples/ft61f14x/config.json --collect
python skills/build/scripts/validate.py --config examples/ft61f14x/config.json
```

## 依赖

- Python 3.10+、`jsonschema`
- `intelhex`（vendor_ide 机制 hex→bin 及其他构建系统转换工具缺失时的兜底；
  依赖降级：缺失时 vendor_ide 在 S7a 报错、CLI 机制仅警告并 `bin_path = null`）
- 工具链（按 build_system 选择，见"输入"）；缺失时先运行 S7a 或手动配置 tool_paths

## 禁止事项

**rule 脚本侧**：

- 不修改 config.json（工具链回填是 S7a 的专属例外）；不读写其他 Skill 的 state 字段
- 不修改工程文件（.uvprojx / .ewp / CMakeLists.txt）；不调用 ide_sync.py
  （例外：阶段 A' 生成/重新生成含标记的 Makefile 与 .ld——用户自维护文件仍不覆盖）
- 不生成任何 C 代码；不修改 S5a/S5b/S5c 产物
- 不自动触发任何下游 Skill 与 S7a（含 S5c code-fix）

**Agent 侧（analyze 阶段）**：

- 不自动修复代码——只分析、报告、给建议；不修改任何源文件与配置文件
- 不触发 S5c code-fix（由用户显式发起："读 outputs/s7b/error_analysis.md，走
  S5c code-fix 分支修复 xxx"）
- 不把编译错误简单归为"S5 代码问题"——必须区分代码/配置/环境/输入四类根因
- 不臆造错误原因——分析必须基于 build.log 与 build_result.json 的实际内容
- 不修改 state.s7b.status（由 validate 收口）

**Agent 侧（GUI 编译阶段，vendor_ide）**：

- 只执行 vendor 指南中列出的快捷键/菜单操作；不打开工程配置/选项对话框
- 不保存任何工程文件改动（关闭时保存提示一律选"否"）
- 不在 IDE 中编辑任何源代码；GUI 操作失败不得盲试超过 2 次（记录现象进入 analyze）
