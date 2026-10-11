---
name: "toolchain-setup"
description: "S7a 环境供给（可选旁路）：检测并可选安装编译构建所需开源工具链（arm-none-eabi-gcc/make/cmake），全部就绪时直接跳过；商业工具（Keil/IAR/厂家 IDE）只给手动指引。S7b build 之前使用。"
---

# toolchain-setup 工具链环境供给（S7a）

## 用途

检测并（可选）安装编译构建所需的开源工具链（arm-none-eabi-gcc / objcopy /
make / cmake）。**已就绪时直接跳过**（`status: skipped`，不安装任何东西）；
缺失时 Agent 引导安装并回填全局 `config.json` 的 `tool_paths`。

**定位：可选的旁路技能**。用户已自行安装工具链时可完全跳过 S7a，直接运行
S7b build——S7b 不读取 `s7a.status`，只检查工具路径是否存在；两者仅通过
`tool_paths` 解耦。触发时机：S7b build 之前，由用户手动执行或 S12
workflow-runner 编排（可选步骤）。

### 商业工具红线

**Keil（UV4/fromelf）与 IAR（IarBuild/ielftool）是商业授权软件，厂家自研 IDE
（辉芒微、和泰等，对应 S7b 的 `build_system = "vendor_ide"`）同属此列——S7a
一律不自动安装**。缺失时只在 `install_plan.md` 中提供官网下载与许可说明指引，
由用户自行安装。S7a 的自动安装能力仅限开源工具白名单：

| 工具 | 用途（对应 build_system） | 最低版本 |
|---|---|---|
| `arm-none-eabi-gcc` + `arm-none-eabi-objcopy` | `gcc_make` / `gcc_cmake` | 10.0+ |
| `make` | `gcc_make` | 4.0+ |
| `cmake` | `gcc_cmake` | 3.20+ |
| Python `intelhex` 包 | `vendor_ide` hex→bin 及兜底 | - |

## 目录结构

```text
toolchain-setup/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（build_system + tool_paths 检查项）
│   ├── output.schema.json             # 输出契约（state.json 的 s7a 字段）
│   └── toolchain_check.schema.json    # 检测结果数据契约
├── scripts/
│   ├── analysis.py                    # 工具检测（复用 S7b analysis 的推断与探测，禁止两套规则）
│   ├── prepare.py                     # 阶段 1：检测 + 生成 install_plan.md
│   └── validate.py                    # 阶段 3：复验工具路径 + state 收口
└── references/
    ├── install_guides.md              # 各工具官方安装方式
    └── tool_versions.md               # 最低版本要求与版本探测命令
```

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `project.build_system` | 项目层 | string/null | 否 | 决定检查哪些工具；null 时按 S7b 共享规则扫描推断 |
| `project.build_target` | 项目层 | string | 否 | 目标工程（决定扫描哪个工程根，缺省 App） |
| `tool_paths.*` | 全局层 | string | 否 | 现有工具路径（gcc / gcc_objcopy / make / cmake / keil / keil_fromelf / iar / iar_ielftool / vendor_ide） |

检查清单（按构建系统）：`keil` → keil + keil_fromelf（推导）；`iar` → iar +
iar_ielftool（推导）；`gcc_make` → gcc + gcc_objcopy（推导）+ make；
`gcc_cmake` → gcc + gcc_objcopy + cmake；`vendor_ide` → vendor_ide +
intelhex 包。

## 输出

### 写入 state.json（仅 s7a 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s7a.status` | string | `skipped`（全部就绪）/ `running`（待安装）/ `done`（安装成功或商业工具仅需手动指引）/ `error` |
| `s7a.build_system` | string | 本次检查的构建系统 |
| `s7a.checked_tools` | array | `[{name, path, present, version}]` 检测结果 |
| `s7a.installed_tools` | array | 本次实际安装的工具名（未安装为空） |
| `s7a.config_updated` | boolean | 是否回填了全局 config.json 的 tool_paths |
| `s7a.check_result` | string | outputs/s7a/toolchain_check.json 路径 |
| `s7a.install_report` | string/null | outputs/s7a/install_report.md 路径（无安装动作为 null） |
| `s7a.error` | string/null | 错误信息 |
| `s7a.updated_at` | string | ISO 时间戳 |

### 写入 outputs/s7a/（数据）

| 产物 | 内容说明 |
|---|---|
| `toolchain_check.json` | 工具检测结果（路径/存在/版本/是否满足最低版本） |
| `install_plan.md` | Agent 任务书（仅缺失时）：缺失清单/安装方式/目标路径/需用户确认事项/商业工具手动指引 |
| `install_report.md` | 安装结果报告（安装了什么/版本/写入的 tool_paths 键；无安装动作时不存在） |

## 执行步骤

**三段式：rule prepare → agent install（仅缺失时）→ rule validate**

### 阶段 A：prepare（rule，prepare.py）

1. 加载合并配置，判定 build_system（显式优先，否则 S7b 共享推断）。
2. 按构建系统确定检查清单，逐项检测：路径已配置且存在 → 执行 `--version` 探测版本
   （商业工具不做版本探测）。
3. 全部就绪 → 写 toolchain_check.json，`state.s7a.status = skipped`，退出 0
   （不做任何安装动作）。
4. 有缺失 → 生成 `install_plan.md`（开源缺失项：安装方式/目标路径/需用户确认；
   商业缺失项：官网指引 + "需手动安装，S7a 不自动安装"），`status = running`。

### 阶段 B：install（agent，仅有开源工具缺失时）

5. `[agent]` 读 install_plan.md + SKILL.md + references/install_guides.md。
6. `[agent]` **在对话中列出安装清单（工具 + 版本 + 来源 + 目标路径），等待用户
   显式确认——未确认前不得执行任何安装命令。**
7. 用户确认后按官方源安装（Windows：`winget install Arm.GnuArmEmbeddedToolchain`
   / `winget install MSYS2.MSYS2` + pacman / `winget install KitWare.CMake`；
   Linux/macOS：apt/brew）。目标路径默认建议 `C:/gcc-arm/`、`C:/msys64/`、
   `C:/cmake/`（避免空格与用户目录权限问题），但须先检测可写性。
8. `[agent]` 安装完成后**回填全局 config.json 的 tool_paths**——全项目唯一
   "config.json 只读"红线例外，附加约束：
   - 只允许追加/更新 `tool_paths` 段的工具路径键，禁止修改任何其他字段
   - 写入前在对话中展示将要写入的键值对（diff），经用户确认
   - 不覆盖已有配置键，除非该键指向的路径已失效
9. 商业工具缺失但开源工具齐全：不进入本阶段，validate 直接收口为 `done` +
   报告中写明"商业工具需手动安装（指引见 install_plan.md）"。

### 阶段 C：validate（rule，validate.py）

10. 复验 tool_paths（含 Agent 新写入的路径）：路径存在且 `--version` 可执行、
    版本满足最低要求（低于最低版本**警告不终止**，提示升级）。
11. 写 toolchain_check.json（复验结果）与 install_report.md（如有安装动作）。
12. state 收口：开源清单全部就绪 → `done`（商业缺失视为仅需手动指引）；
    仍有开源缺失（安装失败/用户拒绝）→ `error` + 退出码 1。
13. **不触发 S7b**——由用户或 S12 决定下一步。

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
- 安装动作依赖 winget / 官网下载（Windows 一期）或包管理器（Linux/macOS，三期）

## 禁止事项

**rule 脚本侧**：

- 不修改 config.json（回填由 Agent 在用户确认后执行，rule 只检测与复验）
- 不读写其他 Skill 的 state 字段（只写 `s7a`）
- 不安装任何商业软件（Keil / IAR / 厂家 IDE）
- 不自动触发 S7b 或任何下游 Skill

**Agent 侧（install 阶段）**：

- **未经用户确认不得执行任何安装命令**
- 只从官方源安装（winget 官方源 / ARM 官网 / MSYS2 官方源 / Kitware 官网），
  不使用来源不明的安装包
- 写 config.json 仅限 tool_paths 段的工具路径键，写入前展示 diff 并经用户确认
- 不修改已存在的工具安装（路径存在但版本不匹配时只警告，不覆盖、不重装）
- 不修改 state.s7a.status（由 validate 收口）
