# S7a toolchain-setup Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：toolchain-setup
- **Skill 用途**：检测并（可选）安装编译构建所需的开源工具链（arm-none-eabi-gcc / objcopy / make / cmake）。**已就绪时直接跳过**（`status: skipped`，不安装任何东西）；缺失时 Agent 引导安装并回填全局 `config.json` 的 `tool_paths`（**全项目唯一被允许写 config.json 的例外**，且仅限 `tool_paths` 段、写入前必须用户确认）。属于"编译构建"层的环境供给技能。
- **定位**：**可选的旁路技能**。用户已自行安装工具链时可完全跳过 S7a，直接运行 S7b build——S7b 不读取 `s7a.status`，只检查工具路径是否存在；两者仅通过 `tool_paths` 解耦。
- **触发时机**：S7b build 之前，由用户手动执行或 S12 workflow-runner 编排（可选步骤）。
- **执行模型**：三段式——`rule prepare（检测+计划）→ agent install（仅缺失时，安装需用户确认）→ rule validate（复验+回填）`。

### 商业工具红线

**Keil（UV4/fromelf）与 IAR（IarBuild/ielftool）是商业授权软件，厂家自研 IDE（辉芒微、和泰等，对应 S7b 的 `build_system = "vendor_ide"`）同属此列——S7a 一律不自动安装**。缺失时只在 `install_plan.md` 中提供官网下载与许可说明指引，由用户自行安装。S7a 的自动安装能力仅限以下开源工具白名单：

| 工具 | 用途（对应 build_system） | 最低版本 |
|---|---|---|
| `arm-none-eabi-gcc` + `arm-none-eabi-objcopy` | `gcc_make` / `gcc_cmake` | 10.0+ |
| `make` | `gcc_make` | 4.0+ |
| `cmake` | `gcc_cmake` | 3.20+ |

## 输入

### 从项目级 `config.json`（与全局 `config.json` 深合并后）读取

- `project.build_system`：构建系统（`keil` / `iar` / `gcc_make` / `gcc_cmake` / `null`）——决定检查哪些工具。为 `null` 时按与 S7b 相同的规则扫描目标工程根推断（`*.uvprojx` → keil、`*.ewp` → iar、`Makefile` → gcc_make、`CMakeLists.txt` → gcc_cmake；多候选/零候选报错）。**推断逻辑与 S7b 共享同一实现**（见 S7b `scripts/analysis.py`），避免两套规则漂移
- `project.build_target`：目标工程（决定扫描哪个工程根，缺省 `App`）

### 从全局 `config.json` 读取

- `tool_paths.*`：现有工具路径（`gcc` / `gcc_objcopy` / `make` / `cmake` / `keil` / `keil_fromelf` / `iar` / `iar_ielftool`）

## 输出

### 写入 `state.json`（仅 `s7a` 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s7a.status` | string | `skipped`（全部就绪，无需安装）/ `done`（安装成功或商业工具仅需手动指引）/ `error` |
| `s7a.build_system` | string | 本次检查的构建系统 |
| `s7a.checked_tools` | array | `[{name, path, present, version}]` 检测结果 |
| `s7a.installed_tools` | array | 本次实际安装的工具名（未安装为空） |
| `s7a.config_updated` | boolean | 是否回填了全局 config.json 的 tool_paths |
| `s7a.check_result` | string | `outputs/s7a/toolchain_check.json` 路径 |
| `s7a.install_report` | string/null | `outputs/s7a/install_report.md` 路径（无安装动作时为 null） |
| `s7a.error` | string/null | 错误信息 |
| `s7a.updated_at` | string | ISO 时间戳 |

### 写入 `outputs/s7a/`（数据）

| 产物 | 内容说明 |
|---|---|
| `toolchain_check.json` | 工具检测结果（工具名 / 路径 / 是否存在 / 版本 / 是否满足最低版本） |
| `install_plan.md` | Agent 任务书（仅缺失时）：缺失清单 / 安装方式 / 目标路径 / 需用户确认事项 / 商业工具手动指引 |
| `install_report.md` | 安装结果报告（安装了什么 / 版本 / 写入了哪些 tool_paths 键；无安装动作时不存在） |

## Skill 目录结构

```text
toolchain-setup/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（build_system + tool_paths 检查项）
│   ├── output.schema.json             # 输出契约（state.json 的 s7a 字段）
│   └── toolchain_check.schema.json    # 检测结果数据契约
├── scripts/
│   ├── analysis.py                    # 工具检测（路径存在性 / 可执行 / 版本探测）
│   ├── prepare.py                     # 阶段 1：检测 + 生成 install_plan.md
│   └── validate.py                    # 阶段 3：复验工具路径 + state 收口（config 回填由 Agent 在阶段 2 完成后触发本脚本复验）
└── references/
    ├── install_guides.md              # 各工具官方安装方式（winget / 官网 / MSYS2 pacman）
    └── tool_versions.md               # 最低版本要求与版本探测命令
```

> S7a 不复用 S7b 的 build 逻辑，但 build_system 推断必须 import S7b `scripts/analysis.py` 的共享函数（或抽取到公共模块），禁止复制两份规则。

## 执行步骤

### 阶段 A：prepare（rule）

1. 加载合并配置，判定 `build_system`（显式配置优先，否则共享推断）。
2. 按构建系统确定**检查清单**：
   - `keil` → `tool_paths.keil` + `tool_paths.keil_fromelf`（只检测，缺失给手动指引）
   - `iar` → `tool_paths.iar` + `tool_paths.iar_ielftool`（只检测，缺失给手动指引）
   - `gcc_make` → `tool_paths.gcc` + `tool_paths.gcc_objcopy` + `tool_paths.make`
   - `gcc_cmake` → `tool_paths.gcc` + `tool_paths.gcc_objcopy` + `tool_paths.cmake`
   - `vendor_ide` → `tool_paths.vendor_ide` 存在（只检测；厂家 IDE 不自动安装，缺失给手动指引）+ Python `intelhex` 包可用性（S7b GUI 机制 hex→bin 依赖；缺失列入开源安装清单：`pip install intelhex`）
3. 逐项检测：路径已配置且文件存在 → 尝试执行 `<tool> --version` 探测版本。
4. **全部就绪** → 写 `toolchain_check.json`，`state.s7a.status = skipped`，退出 0（不做任何安装动作）。
5. **有缺失** → 生成 `install_plan.md`：
   - 开源工具缺失项：安装方式（见下表）、目标路径、所需用户确认
   - 商业工具（Keil/IAR）缺失项：官网下载指引 + 许可说明，明确标注"需手动安装，S7a 不自动安装"
6. 更新 `state.s7a.status = running`（容忍并覆盖陈旧的 `running` 态——上次进程中断残留）。

### 阶段 B：install（agent，仅有开源工具缺失时）

7. `[agent]` 读 `install_plan.md` + `SKILL.md` + `references/install_guides.md`。
8. `[agent]` **在对话中列出安装清单（工具 + 版本 + 来源 + 目标路径），等待用户显式确认**——未确认前不得执行任何安装命令。
9. 用户确认后按官方源安装：

| 工具 | Windows 安装方式（默认平台） | Linux / macOS |
|---|---|---|
| ARM GNU Toolchain（gcc + objcopy） | `winget install Arm.GnuArmEmbeddedToolchain`，或 ARM 官网 `.exe` 静默安装 | `apt` / `brew` |
| make | `winget install MSYS2.MSYS2` 后 `C:/msys64/usr/bin/pacman -S make` | `apt` / `brew` |
| cmake | `winget install KitWare.CMake` | `apt` / `brew` |

   - 安装目标路径默认建议 `C:/gcc-arm/`、`C:/msys64/`、`C:/cmake/`（避免空格与用户目录权限问题），但**须先检测可写性**；C 盘不可写时请用户指定路径
10. `[agent]` 安装完成后**回填全局 `config.json`**——**本 skill 是"config.json 只读"红线的唯一明确例外**，且附加约束：
    - 只允许追加/更新 `tool_paths` 段的工具路径键，**禁止修改任何其他字段**
    - 写入前在对话中展示将要写入的键值对（diff），经用户确认
    - 不覆盖已有配置键，除非该键指向的路径已失效
11. 商业工具缺失但开源工具齐全：不进入本阶段，直接 `status: done` + `install_report.md` 中写明"Keil/IAR 需手动安装（指引见 install_plan.md）"。

### 阶段 C：validate（rule）

12. 复验 `tool_paths`（含 Agent 新写入的路径）：路径存在且 `--version` 可执行、版本满足最低要求（低于最低版本**警告不终止**，提示升级）。
13. 写 `toolchain_check.json`（复验结果）与 `install_report.md`（如有安装动作）。
14. state 收口：全部就绪/安装成功 → `status: done`；安装失败或用户拒绝 → `status: error` + `install_report.md` 写明失败原因与手动安装指引。
15. **不触发 S7b**——由用户或 S12 决定下一步。

## 使用方法

```bash
# 可选步骤（已装好工具链的用户可跳过，直接跑 S7b）
python skills/toolchain-setup/scripts/prepare.py --config examples/stm32f103zet6/config.json
# → 全部就绪：state.s7a.status = skipped，无任何安装动作
# → 有缺失：outputs/s7a/install_plan.md → Agent 与用户确认后安装 → 回填 tool_paths
python skills/toolchain-setup/scripts/validate.py --config examples/stm32f103zet6/config.json
```

## 依赖

- Python 3.10+、`jsonschema`
- 安装动作依赖 winget / 官网下载（Windows）或包管理器（Linux/macOS）

## 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 全部就绪（skipped）或安装成功（done） |
| 1 | 安装失败 / 用户拒绝安装（state 写 error） |
| 2 | 配置错误（build_system 无法判定等） |

## 禁止事项

**rule 脚本侧**：

- **不修改 config.json**（回填由 Agent 在用户确认后执行，rule 脚本只检测与复验）
- 不读写其他 Skill 的 state 字段（只写 `s7a`）
- 不安装任何商业软件（Keil / IAR）
- 不自动触发 S7b 或任何下游 Skill

**Agent 侧（install 阶段）**：

- **未经用户确认不得执行任何安装命令**
- 只从官方源安装（winget 官方源 / ARM 官网 / MSYS2 官方源 / Kitware 官网），不使用来源不明的安装包
- 写 config.json 仅限 `tool_paths` 段的工具路径键，写入前展示 diff 并经用户确认
- 不修改已存在的工具安装（路径存在但版本不匹配时只警告，不覆盖、不重装）
- 不修改 `state.s7a.status`（由 validate 收口）

## 演进路径（供实施参考）

1. **一期（与 S7b 一期同步）**：只做 prepare 检测 + 全就绪跳过（`skipped`）+ 缺失时输出手动安装指引（`install_plan.md` 含指引，但不执行安装）
2. **二期**：Agent 引导安装（开源工具白名单）+ 回填 `tool_paths`
3. **三期**：Linux / macOS 平台适配（一期仅 Windows）
