# S7b build Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：build
- **Skill 用途**：调用工具链编译目标工程，**双编译机制**：**CLI 机制**（Keil / IAR / GCC Make / GCC CMake，命令行调用，纯 rule）与 **GUI 机制**（`vendor_ide`：厂家自研 IDE 无 CLI 支持时，Agent 打开工程、发送编译快捷键完成编译，如辉芒微、和泰）。收集编译日志，解析错误/警告。编译成功后**必须产出 bin 格式产物**（供 S6 firmware-merger 合并 Boot+App 使用）。CLI 编译成功为纯 rule 执行；GUI 编译与失败日志分析引入 Agent。属于"编译构建"层。
- **触发时机**：在 S5 全部完成后触发（由 S12 workflow-runner 编排，或用户手动执行）。与 S7a toolchain-setup 的关系：S7a 是**可选的旁路环境供给技能**，S7b **不读取 `s7a.status`、不自动触发 S7a**——prepare 检测到工具路径缺失时报错并提示"先运行 S7a 或手动配置 `tool_paths`"。
- **执行模型**：**与 S5 系列不同的四段式**——`rule prepare → build（CLI 机制为 rule；GUI 机制为 agent）→ agent analyze（仅失败时）→ rule validate`。CLI 编译是确定性操作，不需要 Agent；GUI 编译（厂家 IDE 快捷键操作）与日志分析才需要 LLM。
- **8 位 MCU 支持**：8 位平台（`arch_family = mcu8`，如 ft61f14x，IDE 目录为 `Project/`）使用厂家 IDE 编译，机制二选一：
  - 厂家 IDE 支持 CLI（少数）→ 走 CLI 机制，`build_system` 取对应值
  - 厂家 IDE 不支持 CLI（多数，辉芒微/和泰等自研 IDE）→ 走 **GUI 机制**（`build_system = "vendor_ide"`）
- **下游消费**：S6 firmware-merger（合并 Boot+App，消费 bin 产物）、S9 flash（烧录，消费 hex 或 bin）。
- **与 S5c 的衔接**：编译失败时，Agent 只产出 `error_analysis.md`，**不自动触发 code-fix**。用户判断是 S5 代码问题后，用自然语言告诉 Agent "读 outputs/s7b/error_analysis.md，走 code-fix 分支修复 xxx"，Agent 进入 S5c 的 code-fix 入口。
- **适用范围**：Cortex-M 平台（CLI 机制，一期起）+ 8 位平台（GUI 机制，见演进路径）。

## 输入

### 从 `state.json` 读取（就绪检查）

**S5 系列字段**（编译需要全部源码就位，不只查 S5c）：

- `s5a.status`：必须为 `done`（初始化代码已生成）
- `s5b.status`：必须为 `done`（APP/Port 契约已生成）
- `s5c.status`：必须为 `done` 或 `skipped`（flat 架构时 skipped）

### 从项目级 `config.json`（与全局 `config.json` 合并后）读取

- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——决定编译哪个工程
- `project.build_system`：**新增**，枚举 `keil` / `iar` / `gcc_make` / `gcc_cmake` / `vendor_ide` / `null`，缺省 `null`（智能推断）。`vendor_ide` = 厂家自研 IDE 无 CLI，走 GUI 编译机制
- `project.build_config`：**新增**，构建配置名（`Debug` / `Release` / 自定义），缺省 `null`（推断）
- `project.vendor_ide`：**新增**，厂家 IDE 标识（`build_system = "vendor_ide"` 时必填，如 `fmd_ft`）。用于定位 `references/vendor_ide/<标识>.md` 操作指南（启动方式 / 编译快捷键 / 输出目录 / 完成判定特征）
- `project.vendor_ide_output_dir`：**新增**，厂家 IDE 编译输出目录（相对目标工程根；缺省按 vendor 指南推断，如 `Project/Output/`）
- `project.inputs.ide_project`：IDE 工程文件路径（可选，缺省按工程目录自动发现；该字段已存在于 config.schema.json，S7b 赋予编译语义；`vendor_ide` 时为必填——GUI 打开的目标）

### 从全局 `config.json` 读取

- `tool_paths.keil`：Keil UV4.exe 路径
- `tool_paths.keil_fromelf`：Keil fromelf.exe 路径。**注意：fromelf 不在 UV4.exe 同目录**，位于 `<Keil 根>/ARM/ARMCLANG/bin/` 或 `<Keil 根>/ARM/ARMCC/bin/`。未配置时 prepare 从 `tool_paths.keil` 推导 Keil 根（`UV4/UV4.exe` 的上一级），按上述两个候选目录自动探测；探测到多份时取 ARMCLANG 优先
- `tool_paths.iar`：IarBuild.exe 路径
- `tool_paths.iar_ielftool`：IAR ielftool.exe 路径（用于生成 bin；未配置时可从 IarBuild 同目录探测 `common/bin/ielftool.exe`）
- `tool_paths.gcc`：arm-none-eabi-gcc 路径
- `tool_paths.gcc_objcopy`：arm-none-eabi-objcopy 路径（用于生成 bin/hex；未配置时从 `tool_paths.gcc` 同目录探测）
- `tool_paths.cmake`：cmake 路径（可选）
- `tool_paths.make`：make 路径（可选）
- `tool_paths.vendor_ide`：厂家 IDE 可执行文件路径（`vendor_ide` 时必填）

### 智能推断通道（`build_system == null` 时）

prepare 阶段**递归扫描**目标工程根（限深度 3 层，排除 `outputs/`、`Listings/`、`Objects/`、`.history/`、备份目录）：

| 发现文件 | 推断结果 |
|---|---|
| `*.uvprojx` | `keil` |
| `*.ewp` | `iar` |
| `Makefile` 或 `makefile` | `gcc_make` |
| `CMakeLists.txt` | `gcc_cmake` |
| 多个同时存在 | **报错**，提示用户在 config 显式指定 |
| 一个都没有 | **报错**，提示用户创建工程文件或配置 `build_system` |

> `vendor_ide` **不参与自动推断**——厂家工程文件扩展名各异无法枚举。8 位平台（`mcu8`）未显式配置 `build_system` 时直接报错，要求显式指定（`vendor_ide` 或厂家 IDE 对应的 CLI 值）。

`build_config == null` 时的推断（与"不猜"原则对齐）：

| build_system | 推断规则 |
|---|---|
| `keil` | 解析 `.uvprojx`：**仅一个 target 时**取该 target 名；多个 target 时**报错**，要求显式配置 `build_config` |
| `iar` | 解析 `.ewp`：仅一个 configuration 时取其名；多个时**报错**，要求显式配置 `build_config` |
| `gcc_make` | 无 config 概念，使用默认 make target |
| `gcc_cmake` | 从 `CMakeLists.txt` / 首次 cmake 配置读默认配置（通常 `Debug`）；无法确定时报错要求显式配置 |

## 输出

### 工程产物（工具链生成 + S7b 转换）

**每种构建系统都必须产出 bin 格式**，供 S6 firmware-merger 合并使用：

| build_system | 调试产物 | 烧录产物 | **合并产物（必须）** |
|---|---|---|---|
| `keil` | `MDK-ARM/Objects/*.axf` | `MDK-ARM/Objects/*.hex` | `MDK-ARM/Objects/*.bin`（fromelf 生成） |
| `iar` | `IAR/<config>/Exe/*.out` | `IAR/<config>/Exe/*.hex` | `IAR/<config>/Exe/*.bin`（ielftool 生成） |
| `gcc_make` | `build/*.elf` | `build/*.hex` | `build/*.bin`（objcopy 生成） |
| `gcc_cmake` | `build/<config>/*.elf` | `build/<config>/*.hex` | `build/<config>/*.bin`（objcopy 生成） |
| `vendor_ide` | `<输出目录>/*.hex`（厂家 IDE 通常只出 hex，无独立调试产物） | `<输出目录>/*.hex` | `<输出目录>/*.bin`（intelhex hex→bin 转换，见下） |

> 注意：IAR 的 `.out` 最终产物在 `Exe/` 目录（`Obj/` 只有 `.o` 中间文件）；ielftool 的输入是 `Exe/*.out`。`vendor_ide` 的输出目录取 `project.vendor_ide_output_dir`（缺省按 vendor 指南推断，如 `Project/Output/`）。

**bin 生成规则**：

| build_system | 命令 |
|---|---|
| `keil` | `fromelf.exe --bin --output=<name>.bin <name>.axf` |
| `iar` | `ielftool.exe --bin <name>.out <name>.bin` |
| `gcc_make` | `arm-none-eabi-objcopy -O binary <name>.elf <name>.bin` |
| `gcc_cmake` | `arm-none-eabi-objcopy -O binary <name>.elf <name>.bin` |
| `vendor_ide` | Python `intelhex` 库 hex→bin 转换（**工具链无关**，不依赖 objcopy；厂家 IDE 几乎只输出 hex） |

> `intelhex` 转换同时作为其他构建系统的兜底：objcopy/fromelf/ielftool 均缺失时，若 hex 已生成，可用它转 bin（仅警告不终止的降级路径）。

**hex 补生成规则**（S7b 禁止修改工程文件，不能依赖工程内勾选项）：

| build_system | 规则 |
|---|---|
| `keil` | hex 仅在 `.uvprojx` 勾选"Create HEX file"时由工具链生成；日志解析未发现 hex 时用 `fromelf.exe --i32 --output=<name>.hex <name>.axf` 补生成 |
| `iar` | hex 仅在工程配置开启时生成；缺失时用 `ielftool.exe --ihex <name>.out <name>.hex` 补生成 |
| `gcc_make` / `gcc_cmake` | 用 `arm-none-eabi-objcopy -O ihex <name>.elf <name>.hex` 补生成 |
| `vendor_ide` | 厂家 IDE 自身输出 hex，无需补生成 |

### 写入 `state.json`（仅 `s7b` 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s7b.status` | string | `pending` / `running` / `done` / `error` |
| `s7b.build_system` | string | 本次实际使用的构建系统 |
| `s7b.build_mode` | string | `cli` / `gui`（`vendor_ide` 为 `gui`，其余为 `cli`；S12 编排与 S9 烧录可据此区分） |
| `s7b.build_config` | string | 本次实际使用的构建配置 |
| `s7b.build_target` | string | `App` / `BootLoader` |
| `s7b.artifact_path` | string/null | 主调试产物路径（`.axf` / `.out` / `.elf`） |
| `s7b.artifact_format` | string/null | `axf` / `out` / `elf` |
| `s7b.hex_path` | string/null | 烧录产物路径（`.hex`） |
| `s7b.bin_path` | string/null | **合并产物路径（`.bin`，S6 消费）**；bin 工具缺失时为 null 并附警告 |
| `s7b.error_count` | int | 编译错误数 |
| `s7b.warning_count` | int | 编译警告数 |
| `s7b.build_log` | string | 日志路径（`outputs/s7b/build.log`） |
| `s7b.build_result` | string | 结果摘要路径（`outputs/s7b/build_result.json`） |
| `s7b.makefile_generated` | bool | 阶段 A' 是否生成了 Makefile（非 gcc_make 或已存在时 false；skip-if-modified 跳过时 false 并警告） |
| `s7b.linker_script_generated` | bool | 阶段 A' 是否生成了 `.ld`（引用现成脚本或非 gcc_make 时 false） |
| `s7b.error_analysis` | string/null | Agent 分析报告路径（仅失败时） |
| `s7b.error` | string/null | 错误信息 |
| `s7b.updated_at` | string | ISO 时间戳 |

### 写入 `outputs/s7b/`（数据）

| 产物 | 内容说明 |
|---|---|
| `generation_brief.md` | Agent 任务书（prepare 段）：CLI 机制为失败分析路径准备；GUI 机制（`vendor_ide`）为编译执行路径准备（含 vendor 指南要点 / 工程文件 / 输出目录 / 超时 / 禁止事项） |
| `build.log` | 完整编译日志（CLI：stdout + stderr；GUI：Agent 抄录的 IDE 输出窗口关键行） |
| `gui_build_log.md` | GUI 编译操作记录（Agent 逐步记录：启动 / 快捷键操作 / 完成判定依据 / 观察到的 IDE 输出；CLI 机制不存在） |
| `build_result.json` | 结果摘要（error_count / warning_count / artifact_path / hex_path / bin_path / 错误列表） |
| `error_analysis.md` | 编译失败时 Agent 产出的根因分析与修复建议（成功时不存在） |

### 指针 / 数据分离

- 可执行文件在工程目录（工具链默认位置）
- 数据产物在 `outputs/s7b/`
- `state.json` 只存指针与统计

## Skill 目录结构

```text
build/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（S5 就绪性 + 工具链检查）
│   ├── output.schema.json             # 输出契约（state.json 的 s7b 字段）
│   └── build_result.schema.json       # 编译结果摘要契约
├── scripts/                            # rule 轨（无代码生成，无业务逻辑）
│   ├── analysis.py                     # 共享分析（配置加载/构建系统推断/工具链探测/日志解析/产物定位）——S7a 复用其中的推断与探测函数
│   ├── prepare.py                      # 阶段 1：就绪检查 + 工具链检测 + 构建系统判定 + 任务书（CLI 与 GUI 两种任务书模板）
│   ├── build.py                        # 阶段 2（CLI 机制）：调用工具链编译 + 生成 bin/hex + 收集日志 + 解析结果；GUI 机制下为 `--collect` 模式（产物检测/日志落盘/bin 转换/结果收口）
│   └── validate.py                     # 阶段 4：产物验证 + state 收口
├── references/
│   ├── keil_build_guide.md             # Keil 命令行编译指南（UV4/fromelf 参数/退出码/日志格式/GBK 编码处理）
│   ├── iar_build_guide.md              # IAR 命令行编译指南（IarBuild/ielftool/退出码/Exe-Obj 目录区分）
│   ├── gcc_build_guide.md              # GCC Make / CMake 编译指南（含 objcopy 生成 bin/hex）
│   ├── vendor_ide/                     # 厂家 IDE GUI 编译指南（按 project.vendor_ide 标识一文件）
│   │   └── <标识>.md                    # 如 fmd_ft.md：IDE 启动方式 / 打开工程参数 / 编译快捷键（菜单路径）/ 输出目录约定 / 编译完成判定特征 / 常见错误输出窗口特征
│   ├── binary_conversion_guide.md      # bin/hex 生成与转换指南（各工具链命令 + intelhex 转换 + 常见错误）
│   └── log_parse_rules.md              # 日志解析规则（错误/警告提取正则 / 编码尝试顺序 / 产物路径提取）
└── assets/
    └── build_example.md                # 编译示例（各构建系统的命令模板）
```

> S7b 是**纯 rule + Agent 分析**形态，不存在"代码生成"，因此 `references/` 下都是工具链使用指南而非生成规则。

## 执行步骤

### 阶段 A：prepare（rule）

1. 从 `state.json` 读取 S5 系列字段，确认 `s5a.status = done`、`s5b.status = done`、`s5c.status ∈ {done, skipped}`。
2. 读取项目级 `config.json`，与全局 `config.json` 深合并。
3. **平台与编译机制判定**：
   - `mcu8` 平台：`build_system` 必须显式配置（`vendor_ide` 或厂家 IDE 对应的 CLI 值）；未配置 → 报错（厂家工程文件格式各异，不自动推断）。`vendor_ide` 时另要求 `project.vendor_ide` 与 `project.inputs.ide_project` 已配置
   - Cortex-M 平台：`build_system = "vendor_ide"` → 报错（GUI 机制仅用于厂家自研 IDE；Keil/IAR/GCC 均有 CLI）
4. **构建系统判定**：显式配置优先；为 `null` → 递归扫描智能推断（见"智能推断通道"）；多候选/零候选 → 报错。
5. **构建配置判定**：显式配置优先；多 target/configuration 且未显式配置 → 报错，要求显式指定 `build_config`。`vendor_ide` 无 config 概念，跳过。
6. **工具链就绪检查**：
   - `keil` → `tool_paths.keil` 存在；`keil_fromelf` 按推导规则探测（见"输入"）
   - `iar` → `tool_paths.iar` 存在；`iar_ielftool` 按推导规则探测
   - `gcc_make` → `tool_paths.gcc` + `tool_paths.make` 存在；`gcc_objcopy` 同目录探测
   - `gcc_cmake` → `tool_paths.gcc` + `tool_paths.cmake` 存在；`gcc_objcopy` 同目录探测
   - `vendor_ide` → `tool_paths.vendor_ide` 存在 + `references/vendor_ide/<project.vendor_ide>.md` 操作指南存在（无指南 → 报错，提示先为该厂家 IDE 编写指南）
   - **编译工具缺失 → 报错（退出码 2），提示"先运行 S7a toolchain-setup 或手动配置 tool_paths"**（不自动触发 S7a）
   - **bin/hex 转换工具缺失 → 警告不终止**，任务书标注"bin 转换工具未配置，S6 合并时需用户手动提供"（`vendor_ide` 依赖 `intelhex`，见"依赖降级"）
7. **工程文件检查**：`keil` → `.uvprojx`；`iar` → `.ewp`；`gcc_make` → `Makefile`（缺失时进入 **Makefile 自动生成分支**，见下节）；`gcc_cmake` → `CMakeLists.txt`；`vendor_ide` → `project.inputs.ide_project` 存在。
8. 生成任务书 `outputs/s7b/generation_brief.md`（CLI 与 GUI 两种模板；GUI 任务书内嵌 vendor 指南要点）。
9. 更新 `state.s7b.status = running`（容忍并覆盖上次中断残留的 `running` 态）。

### 阶段 A'：Makefile 自动生成分支（仅显式 `gcc_make`）

**触发条件（三者同时满足，缺一不生成）**：

1. `project.build_system == "gcc_make"` 为**显式配置**（智能推断轨不生成本分支的任何文件——推断轨维持"零证据报错，不猜"，避免 gcc 变相成为兜底工具链）
2. 目标工程根递归扫描（同智能推断的扫描规则）**未发现 Makefile**
3. S5 就绪检查已通过（源码已生成，扫描有内容可编）

**生成策略（优先级从高到低）**：

| 优先级 | 数据来源 | 说明 |
|---|---|---|
| 1 | **解析已有 `.uvprojx`** | 工程内若存在 Keil 工程文件，解析其 XML 提取 defines / include paths / 源文件清单 / 编译选项 / CPU 型号——单一事实来源，与 Keil 编译行为一致（社区 keil2gcc 同思路） |
| 2 | **目录扫描 + 平台约定** | 无 uvprojx 时按 `docs/PROJECT_LAYOUT.md` 目录约定递归收集 `*.c` / `*.s`；`-mcpu` / `-D` 宏从 state.json 的 chip 字段（S3 产物）与平台惯例（如 `STM32F10X_HD` + `USE_STDPERIPH_DRIVER`）推导 |

**产物**（写入目标工程根，与 Makefile 同级）：

- `Makefile`：`TARGET` / `PREFIX=arm-none-eabi-` / `CC` `OBJCOPY` `SIZE` / `CPU` / `DEFS` / `INCLUDES` / `SRC`（按收集清单）/ `LDFLAGS` / all / clean / elf / hex / bin 目标；**编译输出目录 `build/`**（与产物路径表一致：`build/*.elf` / `build/*.hex` / `build/*.bin`）
- 链接脚本：优先级 **工程内用户自维护 `.ld`（无生成标记，最高，用户显式覆盖）> 平台库 `platforms/<platform>/linker_scripts/*.ld`（芯片级权威资产，`flash_offset == 0` 时直接引用；引用平台脚本时清理被取代的旧生成脚本）> 工程内本 skill 生成 `.ld`（有标记，按最新模板重新生成）> 从 S3 产物（FLASH/RAM 起址与大小）生成最小可用 `<target>.ld`**（ENTRY(Reset_Handler) + sections: text/data/bss/stack）。`flash_offset > 0` 时必定生成工程内脚本（平台脚本为固定基址，需偏移后布局）
- **flash_offset 应用（OTA App）**：`project.flash_offset > 0` 时（config 显式值，权威来源），链接脚本 `ORIGIN = Flash 基址 + 偏移`、`LENGTH = 总容量 - 偏移`（基址/容量取 uvprojx IROM 或平台惯例）；偏移非法（≥容量）报错，非 512 字节对齐警告（VTOR 对齐要求）；uvprojx IROM 起址已偏离平台基址时警告双重偏移风险。该值与 S5b main.c 的 `sys_port_relocate_vector` 字面值、S6/S9 的 bin 拼接/烧录地址必须一致（config 为唯一权威来源）

**skip-if-modified 约束（与 S5 系列惯例一致）**：

- 首次生成前检查 Makefile / `.ld` 是否已存在且非本 skill 生成（文件头含 `# Generated by S7b build` 标记行）
- 用户修改过（无标记或标记被改）→ **跳过生成，警告提示**"检测到用户自维护的 Makefile，S7b 不覆盖"；删除该文件即恢复自动生成
- `s7b` state 记录 `makefile_generated: true/false` 与 `linker_script_generated: true/false`

**失败处理**：源文件扫描为空 / CPU 信息无法推导 / 链接脚本无从生成 → 报错（退出码 2），提示用户手写 Makefile 或改用 keil/iar。

### 阶段 B：build

#### 机制一：CLI（`keil` / `iar` / `gcc_make` / `gcc_cmake`，rule 执行）

10. 按 `build_system` 构造编译命令：

| build_system | 命令模板 | 说明 |
|---|---|---|
| `keil` | `UV4.exe -b <project.uvprojx> -j0 -o build.log` | `-b` 增量编译；`--rebuild` 选项时改用 `-r` |
| `iar` | `IarBuild.exe <project.ewp> -build <config> -log info` | |
| `gcc_make` | `make -j4`（在工程 Makefile 目录执行） | `--rebuild` 时先 `make clean` |
| `gcc_cmake` | `cmake --build build/<config> -- -j4` | `--rebuild` 时加 `--clean-first` |

11. 调用工具链，捕获 stdout / stderr / 退出码；**带超时控制**（CLI `--timeout` 参数，缺省 600 秒，超时杀进程并按失败处理）。
12. 保存完整日志到 `outputs/s7b/build.log`（**多编码尝试解码**：UTF-8 → GBK → `errors='replace'`，Keil 在中文 Windows 上日志常为 GBK）。
13. **退出码判定**（各工具链语义不同，映射表写入 `references/`）：

| build_system | 成功 | 失败 |
|---|---|---|
| `keil` | 退出码 ∈ {0, 1}（**0=成功无警告，1=成功有警告**）且日志解析错误数 = 0 | 退出码 ≥ 2（含 fatal）或解析出错误 |
| `iar` | 退出码 0 且解析错误数 = 0 | 非 0 |
| `gcc_make` / `gcc_cmake` | 退出码 0 | 非 0 |

14. **日志解析**（规则在 `references/log_parse_rules.md`）：

| build_system | 错误行特征 | 警告行特征 |
|---|---|---|
| `keil` | `*** ERROR` / `Error: #` | `warning: #` |
| `iar` | `Error[` / `Fatal Error[` | `Warning[` |
| `gcc` | `error:` | `warning:` |

    - 提取错误/警告数、错误详情（文件 / 行号 / 消息）
    - 提取调试产物路径（Keil 从 `creating hex file...` 行；IAR 从 `Build complete` / `Exe` 输出行；GCC 从链接命令 `-o` 参数）
15. **生成 bin 产物**（编译成功时，按 `references/binary_conversion_guide.md`，命令见"输出"表）。
16. **补生成 hex 产物**（日志未发现 hex 时，按补生成规则表）。
17. 输出 `outputs/s7b/build_result.json`。
18. 编译成功（按第 13 步判据）且 bin 生成成功 → 直接进入阶段 D。
19. 编译失败 → 进入阶段 C（build.py 以退出码 1 结束，提示进入 analyze）。
20. bin 生成失败但编译成功 → **不算编译失败**，state 标 `status: done`，`bin_path = null` 并写警告，S6 需用户手动提供 bin。

#### 机制二：GUI（`vendor_ide`，agent 执行 + rule 收口）

适用于厂家自研 IDE 无 CLI 支持（辉芒微、和泰等）的场景。Agent 操作必须严格遵循 `references/vendor_ide/<project.vendor_ide>.md` 操作指南：

- **B1 `[rule]`** 记录编译开始时刻 T0（用于产物新旧判定），写入任务书。
- **B2 `[agent]`** 启动厂家 IDE（`tool_paths.vendor_ide`），打开 `project.inputs.ide_project` 工程文件，等待 IDE 就绪（按指南的窗口特征判定）。
- **B3 `[agent]`** 按 vendor 指南发送**编译快捷键 / 菜单操作**触发编译（仅限指南列出的操作）。
- **B4 `[agent]`** 轮询输出目录（`project.vendor_ide_output_dir`）文件 mtime 与 IDE 窗口状态，判断编译完成；超时（同 CLI 的 `--timeout`，缺省 600 秒）按失败处理。
- **B5 `[agent]`** 编译结束后，从 IDE 输出窗口抄录错误/警告关键行写入 `outputs/s7b/build.log`；将 GUI 操作全过程（启动 / 快捷键 / 完成判定依据 / 观察到的输出）记录到 `outputs/s7b/gui_build_log.md`。
- **B6 `[agent]`** 关闭工程与 IDE（**不保存任何工程文件改动**；IDE 弹出保存对话框时一律选"否"）。
- **B7 `[rule]`** 运行 `build.py --collect` 收口：
  - **产物检测**：输出目录中 mtime > T0 的 hex/bin 即本次产物；无新产物 → 判定编译失败
  - **bin 生成**：仅有 hex 时用 `intelhex` 转 bin（工具链无关）
  - **结果落盘**：`build_result.json`（错误数按 B5 抄录行统计，无法统计时为 -1 并标注"GUI 模式无法精确计数"）
- **判定**：产物已更新且无抄录错误 → 阶段 D；无新产物 / 超时 / 有错误 → 阶段 C（analyze 基于 `build.log` + `gui_build_log.md` 分析）。

### 阶段 C：analyze（agent，仅编译失败时）

21. `[agent]` 读 `build.log` + `build_result.json` + `SKILL.md` + `references/`（GUI 机制另读 `gui_build_log.md`，区分"编译失败"与"GUI 操作失败"——后者如快捷键未生效、IDE 未响应，归为环境问题并建议重试或人工介入）。
22. `[agent]` 分析错误根因，归类为：
    - **代码问题**：S5 生成的代码有缺陷（如漏 include、API 签名错误、类型不匹配）
    - **配置问题**：工程文件配置错误（如 include 路径缺失、宏定义缺失、链接脚本不匹配）
    - **环境问题**：工具链版本不匹配、路径错误、依赖缺失
    - **输入问题**：S5a/S5b/S5c 上游产物不一致
23. `[agent]` 输出 `outputs/s7b/error_analysis.md`：错误摘要（按根因分类）/ 每条错误的详细分析（错误消息 / 可能原因 / 定位建议）/ 修复建议（**只建议，不执行**）/ **推荐路径**（判定为 S5 代码问题 → 明确写出"建议走 S5c code-fix 分支，读取本报告修复 xxx"）。
24. `[agent]` **不自动修复**，不改动任何代码，不触发 code-fix。

### 阶段 D：validate（rule）

25. **产物验证**：
    - `build_result.json` 存在且 schema 合法
    - 编译成功时主调试产物路径存在
    - 编译成功时 `bin_path` 非空（除非 bin 转换工具缺失且已警告）
    - 编译失败时 `error_analysis.md` 存在
    - GUI 机制（`build_mode = gui`）时 `gui_build_log.md` 存在（无论成败）
26. 更新 `state.s7b` 字段：成功 → `status: done` + 三个产物路径；失败 → `status: error` + `error_analysis` 路径 + `error` 摘要。
27. **不调用 `ide_sync.py`**——S7b 只读工程文件，不修改。
28. **不触发下游 Skill**——由 S12 workflow-runner 根据 state 决定下一步。

> **烧录由 S9 flash 执行，固件合并由 S6 firmware-merger 执行（消费 bin），S7b 只负责编译 + 生成 bin。**

## 与 S5c code-fix 的衔接

编译失败后，用户看到 `error_analysis.md` 里的"推荐路径"。如果判定为 S5 代码问题，用户用自然语言告诉 Agent：

> "读 `outputs/s7b/error_analysis.md`，走 S5c code-fix 分支，修复 `port_impl_uart_stm32f103.c` 的 `uart_send` 函数。"

Agent 进入 S5c 的 code-fix 分支（见 S5c requirement），不走 S7b 的任何流程。**这是跨 Skill 的人工编排，不是自动触发。**

## 交付物：config schema 更新

S7b 的 config 新增字段必须同步更新根目录 `schemas/config.schema.json`（这是 S7b 交付物的一部分，缺失则枚举值拼错无法被拦截）：

- `project.build_system`：enum `["keil", "iar", "gcc_make", "gcc_cmake", "vendor_ide", null]`
- `project.build_config`：string（构建配置名，可选）
- `project.vendor_ide`：string（厂家 IDE 标识，`vendor_ide` 时必填）
- `project.vendor_ide_output_dir`：string（厂家 IDE 编译输出目录，可选）
- `tool_paths` 段补充键描述：`keil_fromelf` / `iar` / `iar_ielftool` / `gcc` / `gcc_objcopy` / `cmake` / `make` / `vendor_ide`
- `project.inputs.ide_project` 的 description 补充 S7b 编译语义（`vendor_ide` 时必填）

## 使用方法

```bash
# 前置：S5a/S5b done，S5c done 或 skipped（flat）；工具链已就绪（或先跑 S7a）
python skills/build/scripts/prepare.py --config examples/stm32f103zet6/config.json
# → 检查任务书（构建系统 / 工具链 / 工程文件 / bin 转换工具）
python skills/build/scripts/build.py --config examples/stm32f103zet6/config.json [--rebuild] [--timeout 600]
# → 成功：outputs/s7b/build_result.json 含 artifact / hex / bin 三个路径
# → 失败：Agent 读 build.log 分析 → outputs/s7b/error_analysis.md
python skills/build/scripts/validate.py --config examples/stm32f103zet6/config.json

# 8 位平台（GUI 机制，厂家 IDE 无 CLI）：
python skills/build/scripts/prepare.py --config examples/ft61f14x/config.json
# → config 需显式：build_system="vendor_ide" + project.vendor_ide + inputs.ide_project
# → Agent 按 generation_brief 启动 IDE、打开工程、发送编译快捷键（机制二 B1–B6）
python skills/build/scripts/build.py --config examples/ft61f14x/config.json --collect
# → rule 收口：产物检测（mtime>T0）/ intelhex 转 bin / build_result.json
python skills/build/scripts/validate.py --config examples/ft61f14x/config.json

# 编译失败后，判定为 S5 代码问题 → 用户告诉 Agent：
#   "读 outputs/s7b/error_analysis.md，走 S5c code-fix 分支修复 xxx"
```

## 依赖

- Python 3.10+、`jsonschema`
- `intelhex`（`vendor_ide` 机制的 hex→bin 转换，及其他构建系统 objcopy 类工具缺失时的兜底；**依赖降级**：缺失时 `vendor_ide` 报错退出 2，CLI 机制仅警告并置 `bin_path = null`）
- 工具链（按 `build_system` 选择，见"输入"）；缺失时先运行 S7a toolchain-setup 或手动配置

## 退出码（按脚本拆分）

**prepare.py / validate.py**：

| 退出码 | 含义 |
|---|---|
| 0 | 就绪检查 / 校验通过 |
| 2 | 配置错误 / 就绪失败 / S5 未完成 / 工具链缺失 / 工程文件缺失 |

**build.py**：

| 退出码 | 含义 |
|---|---|
| 0 | 编译成功（含 bin 生成失败但已警告的情况；GUI 机制下 `--collect` 检测到有效产物） |
| 1 | 编译失败（CLI：日志与 build_result.json 已产出；GUI：无新产物 / 超时；提示进入 analyze 阶段，error_analysis.md 由 Agent 后续生成，此时尚不存在） |
| 2 | 配置错误 / 无法调用工具链（超时按 1 处理） |

## 禁止事项

**rule 脚本侧**：

- **不修改 config.json**（含全局与项目级；工具链回填是 S7a 的专属例外），不读写其他 Skill 的字段。
- 不修改工程文件（`.uvprojx` / `.ewp` / `CMakeLists.txt`）。**例外**：`Makefile` 与生成的 `.ld` 允许在阶段 A' 分支生成（带 `# Generated by S7b build` 标记 + skip-if-modified），此为用户显式 `build_system=gcc_make` 表达的意图。
- 不生成任何 C 代码。
- 不修改 S5a/S5b/S5c 产物。
- 不自动触发任何下游 Skill 与 S7a（含 S5c code-fix）。
- 不调用 `ide_sync.py`（S7b 只读工程，不同步）。

**Agent 侧（analyze 阶段）**：

- **不自动修复代码**——只分析、报告、给建议。
- 不修改任何源文件与任何配置文件。
- 不触发 S5c code-fix 分支——由用户显式发起。
- 不把编译错误简单归类为"S5 代码问题"——必须区分代码 / 配置 / 环境 / 输入四类根因。
- 不臆造错误原因——所有分析必须基于 `build.log` 和 `build_result.json` 的实际内容。
- 不修改 `state.s7b.status`——状态由 validate 收口。

**Agent 侧（GUI 编译阶段，`vendor_ide`）**：

- **只执行 vendor 指南中列出的快捷键 / 菜单操作**——不点击任何未在指南中的控件，不打开工程配置 / 选项对话框。
- **不保存任何工程文件改动**——关闭工程与 IDE 时遇到保存提示一律选"否"。
- 不在 IDE 中编辑任何源代码（编译归编译，修复走 S5c code-fix）。
- GUI 操作失败（快捷键未生效 / IDE 未响应）不得反复盲试超过 2 次——记录现象进入 analyze，归为环境问题。

## 补充说明

### bin 产物为什么必须

BootLoader 合并 App 时，**bin 格式比 hex 格式更方便**：

- bin 是纯二进制镜像，合并时只需按地址拼接（`boot.bin + pad + app.bin`）
- hex 含地址信息、段记录、校验和，合并需解析 Intel HEX 格式，易出错
- 许多 OTA 包、BootLoader 跳转都是基于 bin 格式

因此 S7b **必须为所有构建系统生成 bin**，即使 Keil/IAR 默认只输出 hex/axf。

### bin 生成工具缺失的处理

如果 bin 转换工具（`keil_fromelf` / `iar_ielftool` / `gcc_objcopy`）探测失败：

- **不终止编译**（编译本身是核心）
- prepare 阶段**警告**，任务书里标注"bin 转换工具未配置，S6 合并时需用户手动提供"
- 编译成功后 `bin_path = null`，state 标 `status: done` 但附警告
- S6 firmware-merger 检测到 `bin_path = null` 时提示用户

### 产物路径的健壮性

不同工具链、不同配置下产物路径可能不同。S7b **不硬编码路径**，而是：

1. 优先从日志解析（最准确）
2. 日志解析失败时按 `build_system` + `build_config` 推断默认路径（含 IAR `Exe/` 目录修正）
3. 推断失败时置 `artifact_path = null`，由 S9 flash 阶段再定位

### 与 S6 firmware-merger 的边界

| Skill | 职责 |
|---|---|
| **S7b build** | 编译单个目标工程（App 或 BootLoader），产出 `.axf` / `.hex` / `.elf` + **`.bin`** |
| **S6 firmware-merger** | 合并 Boot + App 固件（如生成 OTA 包），**消费 bin 产物**，产出合并后固件 |

S6 在 S7b 之后执行（按编号 S7b 先于 S6 产出 bin，S6 消费）。S7b 不关心 Boot/App 如何合并，但**必须提供 bin**，否则 S6 无法工作。

### 与 S7a toolchain-setup 的边界

| Skill | 职责 |
|---|---|
| **S7a toolchain-setup** | 可选旁路技能：检测/安装开源工具链、回填 `tool_paths`（唯一 config 写入例外） |
| **S7b build** | 编译执行：只读 `tool_paths`，不读 `s7a.status`，不触发 S7a |

两者仅通过全局 `config.json` 的 `tool_paths` 解耦：已装用户跳过 S7a 直接跑 S7b；S7b prepare 发现工具缺失时报错并提示运行 S7a，**不自动执行**。

### 与 S12 workflow-runner 的边界

| Skill | 职责 |
|---|---|
| **S7b build** | 被调用时执行编译，产出结果 |
| **S12 workflow-runner** | 决定何时调用 S7a/S7b、编译失败后走什么分支（重试 / 报告 / 触发 code-fix） |

S7b **不编排任何流程**，只执行编译这一件事。

### 演进路径（供实施参考）

1. **一期**：只支持 Keil（`build_system = "keil"` 显式配置），跑通编译 + 日志解析（含 GBK）+ fromelf 生成 bin/hex + UV4 退出码映射；同步更新 `schemas/config.schema.json`
2. **二期**：支持 GCC Make（`build_system = "gcc_make"`），含 **Makefile 自动生成分支（阶段 A'：uvprojx 解析优先 + 目录扫描 fallback + `.ld` 生成）**，验证 VSCode + GCC 流程 + objcopy 生成 bin/hex
3. **三期**：支持 IAR + CMake，四种 CLI 构建系统全部覆盖
4. **四期**：加入 `build_system = null` / `build_config = null` 智能推断（多候选报错）
5. **五期**：加入 Agent 分析阶段（编译失败时产出 `error_analysis.md`）
6. **六期**：8 位平台 GUI 编译机制（`vendor_ide`）——以 ft61f14x（辉芒微）为首个验证平台：编写 `references/vendor_ide/` 首份指南 + Agent GUI 操作 + `--collect` 收口 + intelhex 转 bin

每一步都可独立验证，不影响其他 Skill。
