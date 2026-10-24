# S9 flash Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：flash
- **Skill 用途**：调用烧录工具将固件写入目标 MCU Flash 并校验复位。**双烧录机制**：**CLI 机制**（J-Link Commander / J-Flash / STM32CubeProgrammer CLI / OpenOCD / pyOCD，命令行调用，纯 rule；选 J-Flash 时 `.jflash` 工程文件走"检查 → 自提供/自动生成"决策流程）与 **GUI 机制**（`vendor_ide`：厂家 IDE 无 CLI 时，Agent 按 vendor 指南操作下载按钮完成烧录，`flash.py --collect` 收口，8 位 MCU 场景）。烧录前按 `project.flash_offset`（唯一权威来源）计算目标地址，烧录后缺省执行 verify 校验 + 复位运行。烧录失败时 Agent 产出 `error_analysis.md`（连接 / 芯片 / 固件 / 工具四类根因），**不自动重试、不自动解锁**。烧录前将本次固件聚合**发布**到 `<项目根>/release/`（用户唯一需要关注的固件交付目录），并**从该目录副本执行烧录——烧的即发布的**。属于"烧录部署"层。
- **触发时机**：S7b build `done` 之后（或 S6 firmware-merger `done` 之后烧合并固件），由 S12 workflow-runner 编排或用户手动执行。
- **执行模型**：**与 S7b 相同的四段式**——`rule prepare → flash（CLI 机制为 rule；GUI 机制为 agent）→ agent analyze（仅失败时）→ rule validate`。CLI 烧录是确定性操作，不需要 Agent；GUI 烧录（厂家 IDE 按钮操作）与失败日志分析才需要 LLM。
- **执行策略**：**直接执行，不请求人工确认**（开发迭代场景；prepare 任务书完整展示固件 / 地址 / 芯片 / 探针信息供追溯，verify 缺省开启兜底）。
- **8 位 MCU 支持**：8 位平台（`arch_family = mcu8`，如 ft61f14x）使用厂家 IDE 烧录，机制二选一（与 S7b 对称）：
  - 厂家 IDE / 独立烧录器支持 CLI（少数）→ 走 CLI 机制，`flash_tool` 取对应值
  - 不支持 CLI（多数，辉芒微 / 和泰等自研 IDE）→ 走 **GUI 机制**（`flash_tool = "vendor_ide"`）
- **下游消费**：S10 serial-monitor（烧录成功后用户手动启动看运行日志；S9 **不自动触发**）。
- **上游依赖**：S7b（hex/bin 产物）、可选 S6（合并固件，优先消费）。与 S7a toolchain-setup 仅通过全局 `tool_paths` 解耦：**不读 `s7a.status`、不自动触发 S7a**。**烧录工具完全由用户自管理**——S9 与 S7a 均不自动下载安装任何烧录工具（理由见"补充说明"：探针偏好因人而异，且存在软件版本兼容、设备数据库支持、`.jflash` 等配置文件绑定问题，自动安装不可控）。prepare 检测到工具缺失时报错并附手动安装指引（references 各工具指南含官方下载渠道与版本建议）。
- **适用范围**：Cortex-M 平台（CLI 机制，一期起）+ 8 位平台（GUI 机制，见演进路径）。

## 输入

### 从 `state.json` 读取（就绪检查）

| 字段 | 要求 |
|---|---|
| `s7b.status` | 必须 `done`，且 `s7b.hex_path` / `s7b.bin_path` 至少一个非空（烧录单固件的来源） |
| `s9` 之外的固件相关字段 | 可选：S6 firmware-merger 产物字段（合并固件）存在且 `done` 时**优先消费**（S6 未实现时自然落到 s7b） |

### 从项目级 `config.json`（与全局 `config.json` 深合并后）读取

- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——决定读哪个工程的 state 与产物
- `project.flash_tool`：**新增**，枚举 `jlink` / `jflash` / `stlink` / `openocd` / `pyocd` / `vendor_ide` / `null`，缺省 `null`（智能推断）。`jlink` = J-Link Commander CLI（JLink.exe，脚本化烧录，推荐）；`jflash` = J-Flash CLI 自动化模式（绑定 `.jflash` 工程文件，见"J-Flash .jflash 配置决策流程"，不参与推断）；`vendor_ide` = 厂家 IDE 无 CLI，走 GUI 烧录机制（不参与推断）
- `project.flash_config`：**新增**（可选），`.jflash` 工程文件显式路径（`flash_tool = "jflash"` 时消费；搜索优先级 `--jflash-project` 参数 > 本配置项 > `release/*.jflash` 约定）
- `project.flash_offset`：App 重定向偏移（字节，缺省 0）——**烧录目标地址的唯一权威来源**（与 S5b 向量表重定位字面值、S7b 链接脚本、S6 bin 拼接共用同一 config 值，四处必须一致）
- `project.arch_family`：`mcu8` 时 `flash_tool` 必须显式配置（厂家烧录器格式各异，不自动推断）
- `project.vendor_ide`：厂家 IDE 标识（`flash_tool = "vendor_ide"` 时必填）。用于定位 `references/vendor_flash/<标识>.md` 操作指南（启动方式 / 下载按钮位置 / 完成判定特征 / 失败输出特征）
- `project.inputs.ide_project`：IDE 工程文件路径（`vendor_ide` 时必填——GUI 打开的目标）
- `platform`：芯片平台名（`platforms/` 下目录名）——设备名映射与平台惯例（Flash 基址 / 容量）的输入之一

### 从全局 `config.json` 读取（`tool_paths` 段）

| flash_tool | tool_paths 键 | 可执行文件 | 未配置时的推导 |
|---|---|---|---|
| `jlink` | `jlink` | JLink.exe（J-Link Commander） | **从既存 `jflash` 键同目录探测**（`tool_paths.jflash` 兼作 SEGGER 安装目录定位线索；`JLink.exe` 与 `JFlash.exe` 同在 `C:/Program Files/SEGGER/JLink/`） |
| `jflash` | `jflash` | JFlash.exe | 无推导，缺失报错（`flash_tool = "jflash"` 时直接消费本键；本键兼作 `jlink` 的目录探测线索） |
| `stlink` | `stlink_cli` | STM32_Programmer_CLI.exe | 无推导，缺失报错（附 ST 官网手动安装指引，**不自动下载**） |
| `openocd` | `openocd` | openocd.exe | 无推导，缺失报错 |
| `pyocd` | `pyocd` | pyocd.exe | 用 `tool_paths.python -m pyocd` 探测（pip 包） |
| `vendor_ide` | `vendor_ide` | 厂家 IDE / 独立烧录器 | 无推导，缺失报错 |

### J-Flash .jflash 配置决策流程（仅 `flash_tool = "jflash"` 时）

J-Flash 绑定 `.jflash` 工程文件（INI 文本：设备名 / 接口 / Flash 基址等）。搜索顺序：

| 优先级 | 来源 | 说明 |
|---|---|---|
| 1 | `--jflash-project <path>` 参数 | 用户显式指定 |
| 2 | `project.flash_config` 配置项 | 持久配置 |
| 3 | `<release>/*.jflash` 约定 | 含用户自放与 S9 生成的 `flash.jflash`；**多份匹配 → 报错（退出码 2）列出候选** |

**未找到 → prepare 以退出码 3 结束并附两个选项说明，由 Agent 转达用户决策**（AskUserQuestion）：

- **自提供** → 本次 S9 结束（非错误，state 保持 `pending`）：用户将 `.jflash` 放入 `release/` 或配置 `project.flash_config` 后重跑 S9
- **自动生成** → 重跑 `prepare.py --gen-jflash`：根据芯片配置信息（J-Link 设备名映射链、`--interface`、Flash 基址与容量——复用 S7b 来源链）自动生成 `release/flash.jflash`（INI 文本，带**生成标记**），继续后续步骤

**生成标记不覆盖**（对齐 S7b 生成 Makefile 惯例）：`release/flash.jflash` 仅在缺失时生成，生成后**不再覆盖**（含用户修改——覆盖会破坏其 J-Flash 工作流）；文件内设备名与当前目标不符（INI 可解析）时**仅警告不覆盖**，由用户决定是否删除重生成。

### 智能推断通道（`flash_tool == null` 时，仅 Cortex-M）

推断证据按优先级：

| 优先级 | 证据来源 | 说明 |
|---|---|---|
| 1 | **IDE 工程文件的调试器配置** | Keil：解析 `<IDE 目录>/*.uvoptx` 的 `<pMon>`（`STLink\ST-LINKIII-KEIL_SWO.dll` → `stlink`、`Segger\JL2CM3.dll` → `jlink`、`CMSIS_AGDI.dll` → CMSIS-DAP → `openocd`）；IAR：解析 `.ewp`/`.ewd` 的调试器选择。这是用户实际所用探针的最强证据 |
| 2 | `tool_paths` 可用性 + 平台惯例 | 证据 1 缺失时：已配置且存在的 CLI 工具中按平台惯例选（STM32 → `stlink` > `jlink` > `openocd` > `pyocd`） |
| — | 多候选 / 零候选 / **证据探针对应 CLI 工具不可用** | **报错**（退出码 2），列出候选与证据，提示在 config 显式配置 `project.flash_tool`（不猜） |

> **探针 ≠ 工具**：`flash_tool` 枚举的是**软件 CLI**，不是探针硬件。探针差异由工具内部的 interface 配置消化——J-Link 探针 → `jlink`；ST-Link → `stlink`（或 `openocd`）；GD-Link / DAPLink 等 CMSIS-DAP 类探针 → `openocd` / `pyocd`（cmsis-dap 接口 cfg），无需为每种探针单做适配器。uvoptx 中未识别的厂家调试器 DLL（如 GD-Link 专用驱动）→ 归零候选报错并列出 DLL 名，要求显式配置（不猜）。

> 示例：本机 `stm32f103zet6` 工程的 uvoptx 为 `STLink` 证据，但 `stlink_cli` 未安装 → 推断报错，提示用户显式配置 `flash_tool = "jlink"`（实际探针为 J-Link）。

### 固件选择通道

优先级从高到低：

| 优先级 | 来源 | 说明 |
|---|---|---|
| 1 | CLI 参数 `--firmware <path>` | 用户显式指定，跳过 state 检查（仍校验文件存在与格式） |
| 2 | S6 合并固件（state 固件字段 `done`） | Boot+App 已合并 / OTA 包，**烧录地址不应用 `flash_offset`**（合并固件自身管理布局） |
| 3 | S7b 产物（`s7b.hex_path`） | **hex 优先**：自带地址与校验和，烧录不传地址不易错 |
| 4 | S7b 产物（`s7b.bin_path`） | hex 为 null 时兜底：bin 无地址信息，**必须显式传烧录地址**（见下表） |

`--format hex|bin` 参数可强制格式（覆盖优先级 3/4 的选择）。

> **`release/` 发布目录永不作为固件发现来源**——发现永远走上表 state 指针（s7b/s6 权威位置），`release/` 只是发布镜像（防烧旧固件，见"补充说明·release/ 发布目录设计"）。

### 烧录地址规则（`flash_offset` 消费，config 唯一权威）

| 固件来源 | 格式 | 烧录地址 | 说明 |
|---|---|---|---|
| S7b（单 App 固件） | hex | **不传地址**（hex 自带，S7b 链接已偏移） | 防御性校验：解析 hex 首记录地址，`flash_offset > 0` 时应为 `flash_base + offset`，不匹配 → **警告"疑似未偏移固件"**（hex 起址等于裸基址时） |
| S7b（单 App 固件） | bin | `flash_base + flash_offset` | 显式传给烧录工具 |
| S6 合并固件 | hex | **不传地址**（hex 自带） | — |
| S6 合并固件 | bin | `flash_base`（合并固件从基址起含 Boot） | S6 state 若记录了合并基址则优先用之 |
| `--firmware` 显式 | bin | `--address <addr>` 必填 | 无来源信息，用户负责地址 |

**flash_base / Flash 容量来源链**（与 S7b 链接脚本生成一致，避免两套规则）：
1. 工程文件 IROM（uvprojx `IROM` 起址 / `.ld` 的 `ORIGIN`）
2. 平台惯例（`analysis.py` 的 `PLATFORM_INFO`，如 STM32 = `0x08000000`）
3. 均无 → 报错，要求 `--address` 显式指定（bin 时）或修复工程文件

**地址合法性校验**（prepare 阶段，报错即拦截）：
- `flash_base + flash_offset + 固件大小 ≤ Flash 容量`（越界报错）
- `flash_offset` 非 512 字节对齐 → 警告（与 S7b 同判据）
- 固件大小为 0 / 文件不存在 / 格式与内容不符（hex 解析失败）→ 报错

### CLI 参数（`flash.py`）

| 参数 | 缺省 | 说明 |
|---|---|---|
| `--config <path>` | 必填 | 项目级 config.json 路径 |
| `--firmware <path>` | 无 | 显式固件路径（bin 时需配合 `--address`） |
| `--format hex\|bin` | 自动 | 强制固件格式 |
| `--address <0x...>` | 按规则计算 | 显式烧录地址（`--firmware` + bin 时必填；正常流程无需提供） |
| `--device <name>` | 推断 | 显式烧录器设备名（J-Link 设备名，推断失败时兜底） |
| `--jflash-project <path>` | 无 | 显式指定 `.jflash` 工程文件（`flash_tool = "jflash"`，决策流程优先级 1） |
| `--gen-jflash` | — | `.jflash` 缺失时的决策选择：自动生成 `release/flash.jflash` 后继续（对应选项"自提供" = 结束 S9，放好文件后重跑） |
| `--interface SWD\|JTAG` | `SWD` | 探针接口 |
| `--no-verify` | verify 开启 | 跳过烧录后校验 |
| `--no-reset` | reset 开启 | 烧录后不复位运行 |
| `--chip-erase` | 关闭（按范围擦除） | 全片擦除（破坏性，显式 opt-in；缺省让工具按固件范围擦除） |
| `--retry <N>` | `0` | 失败自动重试次数（连接抖动场景；缺省不重试，靠 analyze 闭环） |
| `--timeout <秒>` | `300` | 烧录超时（超时杀进程按失败处理） |
| `--collect` | — | GUI 机制收口模式（同 S7b `build.py --collect`） |

## 输出

### 写入 `state.json`（仅 `s9` 字段）

> state 字段命名沿用 S5/S7 系列新惯例（`s5a`/`s7b` 同款），不用旧模板的 `flash` 键。

| 字段 | 类型 | 说明 |
|---|---|---|
| `s9.status` | string | `pending` / `running` / `done` / `error` |
| `s9.flash_tool` | string | 本次实际使用的烧录工具（`jlink` / `jflash` / `stlink` / `openocd` / `pyocd` / `vendor_ide`） |
| `s9.flash_mode` | string | `cli` / `gui`（`vendor_ide` 为 `gui`，S12 编排可据此区分） |
| `s9.firmware_path` | string | 烧录的固件路径（`release/` 内副本——实际烧录执行体） |
| `s9.firmware_format` | string | `hex` / `bin` |
| `s9.firmware_source` | string | `s7b` / `s6` / `manual`（`--firmware` 显式时为 manual） |
| `s9.firmware_size` | int | 固件字节数 |
| `s9.firmware_sha256` | string | 固件哈希（追溯"烧的是哪个固件"） |
| `s9.device` | string | 烧录器设备名（如 `STM32F103ZE`） |
| `s9.jflash_project` | string/null | 使用的 `.jflash` 工程文件路径（仅 `flash_tool = "jflash"` 时非 null） |
| `s9.interface` | string | `SWD` / `JTAG` |
| `s9.target_address` | int | 烧录目标地址（hex 时为解析出的首地址；`flash_offset` 已含在内） |
| `s9.verify` | bool | 本次是否执行了校验 |
| `s9.verify_passed` | bool/null | 校验结果（未校验为 null） |
| `s9.reset_done` | bool | 烧录后是否复位运行 |
| `s9.duration_sec` | number | 烧录耗时 |
| `s9.flash_log` | string | 日志路径（`outputs/s9/flash.log`） |
| `s9.flash_result` | string | 结果摘要路径（`outputs/s9/flash_result.json`） |
| `s9.release_dir` | string | 发布目录（`release/`，项目根，跨工程） |
| `s9.release_manifest` | string | 发布清单路径（`release/flash_info.json`） |
| `s9.error_analysis` | string/null | Agent 分析报告路径（仅失败时） |
| `s9.gui_flash_log` | string/null | GUI 操作记录路径（CLI 机制为 null） |
| `s9.error` | string/null | 错误信息 |
| `s9.updated_at` | string | ISO 时间戳 |

### 写入 `outputs/s9/`（数据）

| 产物 | 内容说明 |
|---|---|
| `generation_brief.md` | Agent 任务书（prepare 段）：**烧录信息清单**（固件路径/大小/SHA256/格式/来源、目标地址、设备名、接口、探针工具与完整命令、verify/reset/chip_erase 选项、超时、禁止事项摘要）；GUI 机制另含 vendor 指南要点与完成判定特征 |
| `flash.log` | 完整烧录日志（CLI：stdout+stderr，多编码解码 UTF-8→GBK→replace；GUI：Agent 抄录的 IDE 输出关键行） |
| `flash_result.json` | 结果摘要（工具/固件指纹/地址/verify 结果/耗时/退出码/日志关键行，schema 见 flash_result.schema.json） |
| `error_analysis.md` | 烧录失败时 Agent 产出的根因分析与修复建议（成功时不存在） |
| `gui_flash_log.md` | GUI 烧录操作记录（Agent 逐步记录：启动/按钮操作/完成判定依据/观察到的输出；CLI 机制不存在） |
| `gui_session.json` | GUI 机制会话数据（T0 等，prepare 写、`--collect` 读） |

### 写入 release/（发布目录，`<项目根>/release/`）

> 跨工程交付目录（合并固件属 Boot+App 组合产物，故位于项目根而非目标工程内）。S9 是唯一写者；**烧录从本目录副本执行——烧的即发布的**。发现来源永远是 state 指针，本目录只是镜像。

| 产物 | 内容说明 |
|---|---|
| `<固件名>.hex` / `<固件名>.bin` | 本次烧录固件的发布副本（已定位的全部格式一并发布）；按 SHA256 比对——与既有副本一致则复用不重复复制，不一致则覆盖（重编译后自动刷新，杜绝旧固件残留） |
| `flash_cmd.jlink` | J-Link Commander 脚本（`jlink` 工具时 prepare 生成；`loadfile`/`verify`/`r`/`g`/`qc` 命令序列，引用本目录固件）——自包含：生产人员仅凭 JLink.exe + 本目录即可复烧 |
| `flash.jflash` | J-Flash 工程文件（仅 `flash_tool = "jflash"` 时存在：S9 生成——用户选"自动生成"时，带生成标记不覆盖；或用户自放 `*.jflash` 被决策流程识别消费，不修改） |
| `flash_info.json` | 发布清单：固件 SHA256/大小/来源、目标地址、device、flash_tool、verify 结果、时间戳、复烧命令（schema 见 flash_info.schema.json）；flash 结束落盘，成败均写 |
| 用户自放文件 | release note 等——不识别不触碰；例外：用户自放 `*.jflash` 在 `flash_tool = "jflash"` 时被决策流程识别并消费（只读不改） |

### 指针 / 数据分离

- 固件本体留在工程目录（S7b/S6 产物原位置，state 指针为权威）；S9 另发布**副本**到 `release/`（镜像与烧录执行体，不回写权威位置）
- 数据产物在 `outputs/s9/`
- `state.json` 只存指针与统计（含固件指纹）

## Skill 目录结构

```text
flash/
├── SKILL.md
├── schemas/
│   ├── input.schema.json              # 输入契约（S7b/S6 就绪性 + 烧录工具检查项）
│   ├── output.schema.json             # 输出契约（state.json 的 s9 字段）
│   ├── flash_result.schema.json       # 烧录结果摘要契约
│   └── flash_info.schema.json         # 发布清单契约（release/flash_info.json）
├── scripts/                            # rule 轨（无代码生成，无业务逻辑）
│   ├── analysis.py                     # 共享分析（配置加载/烧录工具推断/固件定位/地址计算/设备名映射/日志解析）
│   ├── prepare.py                      # 阶段 1：就绪检查 + 工具判定 + 固件定位 + 地址校验 + 任务书
│   ├── flash.py                        # 阶段 2（CLI 机制）：执行烧录 + 日志解析 + 结果落盘；GUI 机制下为 --collect 模式
│   └── validate.py                     # 阶段 4：产物验证 + state 收口
├── references/
│   ├── jlink_flash_guide.md            # J-Link Commander 指南（-CommandFile 脚本/设备名映射/退出码/连接失败特征）【一期实现】
│   ├── jflash_flash_guide.md           # J-Flash CLI 指南（.jflash 工程文件 INI 格式与生成标记/自动生成模板/-openprj -open -auto -exit/退出码）【二期实现】
│   ├── stlink_flash_guide.md           # STM32_Programmer_CLI 指南（-c/-w/-v/-rst 参数/端口枚举）【演进项】
│   ├── openocd_flash_guide.md          # OpenOCD 指南（interface/target cfg 选法/program 命令）【演进项】
│   ├── pyocd_flash_guide.md            # pyOCD 指南（--target/包安装）【演进项】
│   ├── vendor_flash/                   # 厂家 IDE GUI 烧录指南（按 project.vendor_ide 标识一文件）
│   │   └── _template.md                # 新厂家 IDE 指南编写模板（启动/打开工程/下载按钮/完成判定/失败特征）
│   └── flash_log_parse_rules.md        # 日志解析规则（各工具成功/失败特征行/连接错误分类/编码尝试顺序）
└── assets/
    └── flash_example.md                # 烧录示例（各工具命令模板与 jlink 脚本样例）
```

> S9 是纯 rule + Agent 分析形态，不存在代码生成，`references/` 下均为烧录工具使用指南。`analysis.py` 的 Flash 基址/容量来源链与 S7b 共享同一实现（import S7b 函数或抽公共模块，**禁止两套规则**）。

## 执行步骤

### 阶段 A：prepare（rule）

1. 从 `state.json` 读取 `s7b` 字段：`status = done` 且 `hex_path`/`bin_path` 至少一个非空；可选检查 S6 固件字段。
2. 读取项目级 `config.json`，与全局 `config.json` 深合并。
3. **平台与烧录机制判定**（与 S7b 对称）：
   - `mcu8` 平台：`flash_tool` 必须显式配置（`vendor_ide` 或厂家烧录器 CLI 值）；未配置 → 报错。`vendor_ide` 时另要求 `project.vendor_ide` 与 `project.inputs.ide_project` 已配置，且 `references/vendor_flash/<标识>.md` 指南存在（无指南 → 报错，提示先编写指南）
   - Cortex-M 平台：`flash_tool = "vendor_ide"` → 报错（GUI 机制仅用于厂家自研 IDE；J-Link/ST-Link/OpenOCD/pyOCD 均有 CLI）
4. **烧录工具判定**：显式配置优先；为 `null` → 智能推断（见"智能推断通道"）；多候选/零候选/证据探针工具不可用 → 报错。
5. **固件定位与格式判定**：按固件选择通道确定；文件存在、大小 > 0、格式校验（hex 可解析 / bin 非空）不过 → 报错；计算 SHA256。已定位的全部格式（hex+bin）**发布同步到 `release/`**：SHA256 一致的既有副本跳过复制并记录"复用"，不一致则覆盖（重编译后旧副本自动刷新）。
6. **烧录地址计算**：按烧录地址规则表；`flash_base` 走来源链（与 S7b 共享实现）；执行越界/对齐/起址防御性校验。
7. **设备名推断**：`platform` → 烧录器设备名映射（如 `stm32f103zet6` → `STM32F103ZE`：剥离温度等级尾码；`gd32f205vet6` → `GD32F205VE`），映射表在 `references/jlink_flash_guide.md`；无法映射 → 报错，要求 `--device` 显式指定。
8. **烧录工具就绪检查**：按映射表检查 `tool_paths`（含推导规则，如 `jlink` 从既存 `jflash` 键同目录探测）；**工具缺失 → 报错（退出码 2）**，附手动安装指引（官方下载渠道 + `tool_paths` 配置示例），**不自动下载安装**——烧录工具用户自管理，版本兼容 / 设备数据库 / 配置文件绑定等环境差异由用户掌控最可靠。`flash_tool = "jflash"` 时另执行 **.jflash 配置决策流程**（见"输入"小节）：缺失且用户选"自提供" → 退出码 3 结束本次运行；选"自动生成" → 生成 `release/flash.jflash` 后继续。
9. 生成任务书 `outputs/s9/generation_brief.md`（烧录信息清单）；`jlink` 工具另生成 `release/flash_cmd.jlink` 脚本（引用 release/ 内固件，自包含可交付）；GUI 机制另写 `gui_session.json`（T0）。
10. 更新 `state.s9.status = running`（容忍并覆盖上次中断残留的 `running` 态）。

### 阶段 B：flash

#### 机制一：CLI（`jlink` / `stlink` / `openocd` / `pyocd`，rule 执行）

11. 按 `flash_tool` 构造烧录命令（固件路径一律指向 `release/` 内副本——烧的即发布的）：

| flash_tool | 命令模板 | 说明 |
|---|---|---|
| `jlink` | `JLink.exe -device <设备名> -if <SWD\|JTAG> -speed 4000 -autoconnect 1 -CommandFile release/flash_cmd.jlink` | 脚本内容：`loadfile <hex>`（hex 自带地址）或 `loadfile <bin> <0x地址>` → `verify ...` → `r`（复位）→ `g`（运行）→ `qc`（退出）；`--no-verify`/`--no-reset`/`--chip-erase` 映射为脚本行增删 |
| `jflash` | `JFlash.exe -openprj<xxx.jflash> -open<release/固件> -auto -exit` | CLI 自动化模式：`-auto` 自动编程+校验+退出（verify 含在内不可跳过，`--no-verify` 时警告仍执行）；`.jflash` 来自决策流程，固件指向 release/ 副本 |
| `stlink` | `STM32_Programmer_CLI.exe -c port=SWD -w <固件> <0x地址> -v -rst` | hex 时省略地址参数；`--no-verify` 去 `-v`，`--no-reset` 去 `-rst` |
| `openocd` | `openocd -f interface/<探针>.cfg -f target/<平台>.cfg -c "program <固件> <0x地址> verify reset exit"` | bin 时地址必填；hex 时 `program <hex> verify reset exit` |
| `pyocd` | `pyocd flash -t <设备名> <固件>` | pyOCD 自动校验；`--no-reset` 加 `--no-reset` 选项 |

12. 调用烧录工具，捕获 stdout/stderr/退出码；**带超时控制**（`--timeout` 缺省 300 秒，超时杀进程按失败处理）。失败且 `--retry N > 0` 时重试（N 次上限），每次重试记录到日志。
13. 保存完整日志到 `outputs/s9/flash.log`（多编码解码：UTF-8 → GBK → `errors='replace'`）。
14. **成功判定**（各工具语义不同，映射表写入 `references/flash_log_parse_rules.md`）：

| flash_tool | 成功判据 | 失败特征 |
|---|---|---|
| `jlink` | 退出码 0 且日志解析出 `Downloading file` + `Writing`/`O.K.`（+ verify 开启时 `Verifying`/`Verified` 行 O.K.）且无 `Cannot connect`/`Error`/`Failed` | `Connecting...FAILED`（探针/连接）、`Cannot connect to target`（芯片）、`Verify failed`（校验）、`Unknown device`（设备名错） |
| `jflash` | 退出码 0 且日志含 `Downloading`/`O.K.`（`-auto` 含校验：`Verified` O.K.） | `Failed`/`Error`/`Cannot connect` |
| `stlink` | 退出码 0 且日志含 `File download complete` / `Verification passed` | `Error:`/`No ST-LINK detected` |
| `openocd` | 退出码 0 且含 `verified`/`shutdown command invoked` | `Error:`/`failed`/`Target not examined yet` |
| `pyocd` | 退出码 0 且含 `Successfully loaded` | `Error`/`No debug probe` |

15. 解析 verify 结果、耗时、关键行 → 输出 `outputs/s9/flash_result.json`，并落盘 `release/flash_info.json` 发布清单（固件指纹/地址/device/工具/verify 结果/复烧命令；成败均写，schema 校验后写入）。
16. 烧录成功（且 verify 开启时校验通过）→ 进入阶段 D；失败 → 进入阶段 C（flash.py 以退出码 1 结束，提示进入 analyze）。**verify 失败不算烧录成功**（固件可能写入损坏，state 标 error）。

#### 机制二：GUI（`vendor_ide`，agent 执行 + rule 收口）

适用于厂家 IDE 无 CLI（8 位 MCU）场景。Agent 操作必须严格遵循 `references/vendor_flash/<project.vendor_ide>.md` 指南：

- **B1 `[rule]`** 记录烧录开始时刻 T0（写入 `gui_session.json` + 任务书）。
- **B2 `[agent]`** 启动厂家 IDE / 独立烧录器（`tool_paths.vendor_ide`），打开 `project.inputs.ide_project` 工程文件，等待就绪（按指南窗口特征判定）。
- **B3 `[agent]`** 确认目标固件为最新产物（核对任务书的固件指纹），按指南触发**下载/烧录按钮**（仅限指南列出的操作）。
- **B4 `[agent]`** 轮询烧录完成特征（进度窗口消失 / 成功提示 / 输出目录无新文件——按指南判定），超时（同 `--timeout` 缺省 300 秒）按失败处理。
- **B5 `[agent]`** 烧录结束后，从 IDE 输出窗口抄录烧录结果关键行写入 `outputs/s9/flash.log`；操作全程（启动/按钮/完成判定依据/观察到的输出）记录到 `outputs/s9/gui_flash_log.md`。
- **B6 `[agent]`** 关闭工程与 IDE（**不保存任何工程文件改动**，保存提示一律选"否"）。
- **B7 `[rule]`** 运行 `flash.py --collect` 收口：成功判定依据 Agent 抄录的成功特征行（GUI 工具自身完成 verify，`verify_passed` 按抄录内容判定，无法判定为 null）；结果落盘 `flash_result.json` 与 `release/flash_info.json`。
- **判定**：抄录到成功特征且无失败特征 → 阶段 D；无新产物/超时/有失败特征 → 阶段 C。

### 阶段 C：analyze（agent，仅烧录失败时）

17. `[agent]` 读 `flash.log` + `flash_result.json` + `SKILL.md` + `references/`（GUI 机制另读 `gui_flash_log.md`，区分"烧录失败"与"GUI 操作失败"——后者如按钮未生效、IDE 未响应，归为环境问题）。
18. `[agent]` 分析失败根因，归类为：
    - **连接问题**：探针未接/驱动未装/USB 被占用/线序错误（`Connecting...FAILED`/`No ST-LINK detected`/`No debug probe`）
    - **芯片问题**：识别失败/写保护/读保护 RDP/未上电/复位脚被拉住（`Cannot connect to target`/`Unknown device`）
    - **固件问题**：文件损坏/地址越界/格式错误/verify 失败（固件与 Flash 内容不符）
    - **工具问题**：工具版本过旧（设备数据库不含该芯片，如 J-Link 旧版对 GD32 等国产芯片 → `Device is unsupported`/`Unknown device`）/ 参数错误 / 设备名映射错误——版本类问题只建议用户自行升级软件，S9 不代装
19. `[agent]` 输出 `outputs/s9/error_analysis.md`：失败摘要（按根因分类）/ 详细分析（日志证据 / 可能原因 / 定位建议）/ 修复建议（**只建议，不执行**）/ 推荐路径（连接与芯片问题 → 建议用户检查硬件后重跑 S9；固件问题 → 建议重跑 S7b/S6；工具问题 → 建议配置修正）。
20. `[agent]` **不自动重试、不自动解锁芯片**（解除写保护/RDP 降级会触发全片擦除，破坏性操作必须用户手动执行）、不修改任何文件、不触发上游 Skill。

### 阶段 D：validate（rule）

21. **产物验证**：
    - `flash_result.json` 存在且 schema 合法
    - `release/` 发布文件齐备（本次固件副本 + `flash_info.json`；`jlink` 时含 `flash_cmd.jlink`）
    - 烧录成功时：`verify_passed` 非 false（verify 开启时必须为 true；未开启为 null）、`firmware_sha256` 存在
    - 烧录失败时：`error_analysis.md` 存在
    - GUI 机制（`flash_mode = gui`）时 `gui_flash_log.md` 存在（无论成败）
22. 更新 `state.s9` 字段：成功 → `status: done` + 固件指纹/地址/verify 结果/耗时；失败 → `status: error` + `error_analysis` 路径 + `error` 摘要。
23. **不触发下游 Skill**（S10 serial-monitor 由用户或 S12 决定下一步）。

## 与相邻 Skill 的边界

| Skill | 职责 |
|---|---|
| **S7b build** | 编译产出 hex/bin（`s7b.hex_path`/`bin_path`），不管烧录 |
| **S6 firmware-merger** | 合并 Boot+App 固件（消费 bin），产出合并固件；**先编译后合并后烧录**（实际执行顺序 S7b → S6 → S9） |
| **S9 flash** | 将 S7b/S6 固件写入 MCU（消费 hex 优先、bin 兜底；消费 `flash_offset` 计算地址），不管合并；烧录前聚合发布 `release/` 交付快照（release/ 唯一写者） |
| **S10 serial-monitor** | 烧录成功后的串口日志采集（用户手动启动；S9 不自动触发） |
| **S7a toolchain-setup** | 可选旁路技能，仅管编译工具链；**烧录工具不属 S7a 管辖**（用户自管理），S9 工具缺失时报错附手动指引，不触发 S7a |
| **S12 workflow-runner** | 决定何时烧录、失败后走什么分支；S9 只执行烧录这一件事 |

**flash_offset 四处一致**（config 唯一权威）：S5b main.c 向量表重定位字面值、S7b 链接脚本 `ORIGIN`、S6 bin 拼接位置、S9 烧录目标地址——全部读 `project.flash_offset`，禁止各自计算。

## 交付物：config schema 更新

S9 的 config 新增字段必须同步更新根目录 `schemas/config.schema.json`（与 S7b 交付物惯例一致）：

- `project.flash_tool`：enum `["jlink", "jflash", "stlink", "openocd", "pyocd", "vendor_ide", null]`；新增可选 `project.flash_config`（`.jflash` 工程文件路径，`flash_tool = "jflash"` 时消费）
- `tool_paths` 段补充键：`jlink`（含"未配置时从既存 `jflash` 键同目录探测"说明）/ `stlink_cli` / `openocd` / `pyocd`；既存 `jflash` 键在 `flash_tool = "jflash"` 时被直接消费，description 注明"兼作 `jlink` 的目录探测线索（两 exe 同目录）"
- `schemas/state.schema.json` 补 `s9` 键描述（旧 `flash` 键标注 deprecated、由 `s9` 取代——与 `s5a`/`s7b` 新惯例对齐）

## 使用方法

```bash
# 前置：S7b done（或 S6 done 烧合并固件）；烧录工具已配置（一期：jlink 可从 jflash 同目录自动探测）
python skills/flash/scripts/prepare.py --config examples/stm32f103zet6/config.json
# → 检查任务书（固件指纹/目标地址/设备名/探针/完整命令）
python skills/flash/scripts/flash.py --config examples/stm32f103zet6/config.json
# → 成功：release/ 内固件副本 + flash_info.json（交付快照）；outputs/s9/flash_result.json 含 verify 结果与耗时，直接 validate
# → 失败：Agent 读 flash.log 分析 → outputs/s9/error_analysis.md（阶段 C）
python skills/flash/scripts/validate.py --config examples/stm32f103zet6/config.json

# J-Link 探针（本机示例，uvoptx 为 ST-Link 证据但实际用 J-Link 探针，需显式配置）：
#   项目 config.json 显式 "flash_tool": "jlink"
# 固件格式/地址强制：
python skills/flash/scripts/flash.py --config examples/stm32f103zet6/config.json --format bin
python skills/flash/scripts/flash.py --config examples/stm32f103zet6/config.json --firmware outputs/merged.bin --address 0x08000000

# 8 位平台（GUI 机制）：config 显式 flash_tool="vendor_ide" + project.vendor_ide
# + inputs.ide_project；Agent 按任务书操作厂家 IDE（B1–B6）后：
python skills/flash/scripts/flash.py --config examples/ft61f14x/config.json --collect
python skills/flash/scripts/validate.py --config examples/ft61f14x/config.json

# 烧录失败后，Agent 分析报告判定根因 → 用户按推荐路径处理：
#   连接/芯片问题 → 检查探针与板子后重跑；固件问题 → 重跑 S7b/S6；工具问题 → 修正配置
```

## 依赖

- Python 3.10+、`jsonschema`
- `intelhex`（hex 首地址解析与防御性校验；**依赖降级**：缺失时跳过起址校验仅警告，不影响烧录）
- 烧录工具（按 `flash_tool` 选择，见"输入"映射表）；缺失时手动安装并配置 `tool_paths`
- `pyocd` 时：`pip install pyocd`（开源）

## 退出码（按脚本拆分）

**prepare.py / validate.py**：

| 退出码 | 含义 |
|---|---|
| 0 | 就绪检查 / 校验通过 |
| 2 | 配置错误 / 就绪失败 / S7b 未完成 / 烧录工具缺失 / 固件不存在或非法 / 地址越界 / release 内多份 `.jflash` 候选 |
| 3 | `flash_tool = "jflash"` 且 `.jflash` 缺失、用户选"自提供"——S9 本次结束（非错误，state 保持 `pending`）；用户放好文件后重跑（自动生成路径用 `--gen-jflash` 重跑 prepare） |

**flash.py**：

| 退出码 | 含义 |
|---|---|
| 0 | 烧录成功（含 verify 通过；GUI 机制下 `--collect` 检测到成功特征） |
| 1 | 烧录失败（连接/芯片/固件/verify 失败；日志与 flash_result.json 已产出；提示进入 analyze 阶段，error_analysis.md 由 Agent 后续生成，此时尚不存在） |
| 2 | 配置错误 / 无法调用烧录工具（超时按 1 处理） |

## 禁止事项

**rule 脚本侧**：

- **不修改 config.json**（含全局与项目级），不读写其他 Skill 的字段
- 不修改工程文件与固件文件（固件本体留在 S7b/S6 产物原位置不动；`release/` 只增发布副本，不回写）
- 不自动触发任何上下游 Skill（S6/S7b/S10/S7a）
- **不主动全片擦除**（缺省按固件范围擦除；`--chip-erase` 为显式 opt-in）
- **不自动解除芯片读保护/写保护**（RDP 降级 = 全片擦除，破坏性操作；analyze 只建议，由用户手动执行）
- 探针连接失败不盲试重试（仅 `--retry` 显式指定时重试，上限 N 次）

**Agent 侧（analyze 阶段）**：

- **不自动重试烧录、不自动解锁芯片**——只分析、报告、给建议
- 不修改任何源文件、固件文件与配置文件
- 不臆造失败原因——所有分析必须基于 `flash.log` 与 `flash_result.json` 的实际内容
- 不把失败简单归为"固件问题"——必须区分连接 / 芯片 / 固件 / 工具四类根因
- 不修改 `state.s9.status`——状态由 validate 收口

**Agent 侧（GUI 烧录阶段，`vendor_ide`）**：

- **只执行 vendor_flash 指南中列出的按钮 / 菜单操作**——不点击任何未在指南中的控件，不打开工程配置/选项对话框
- **不保存任何工程文件改动**——关闭工程与 IDE 时遇到保存提示一律选"否"
- 不在 IDE 中编辑任何源代码
- GUI 操作失败（按钮未生效 / IDE 未响应）不得反复盲试超过 2 次——记录现象进入 analyze，归为环境问题

## 补充说明

### hex 优先的理由

- hex 自带地址信息（S7b 链接已应用 `flash_offset`）与行校验和，烧录不传地址、不易错位
- bin 无地址信息必须显式计算 `flash_base + flash_offset`，地址链多一环多一分出错面
- bin 是 S6 合并的格式需求（按地址拼接），S9 只在 hex 缺失或用户强制 `--format bin` 时走 bin + 显式地址

### release/ 发布目录设计

- **痛点**：烧录产物散落各处——Keil 埋在 `MDK-ARM/Objects/`、GCC 在 `build/`、S6 合并固件在 outputs/；用户找固件、交付生产/同事都要到处翻
- **方案**：S9 prepare 把本次烧录的固件（hex+bin 全部已有格式）聚合发布到 `<项目根>/release/`，烧录从 release/ 副本执行——**烧的即发布的**；`flash_cmd.jlink` + `flash_info.json` 同在其中，`release/` 即完整交付快照（生产人员仅凭 JLink.exe + release/ 可复烧）
- **stale 防护 + SHA256 同步流程**（S9 prepare 每次执行时**现场计算**，固件仅 KB~MB、hash 毫秒级开销，无人预生成、无缓存可腐败）：
  1. 按固件选择通道定位**源固件**（state 指针，如 `MDK-ARM/Objects/app.hex`）→ 现算其 SHA256（`hashlib`；该值同时写入 `s9.firmware_sha256` 作烧录追溯）
  2. `release/` 同名副本存在 → **现算副本文件的 SHA256** 与源比对（直接哈希实际文件，**不信任 `flash_info.json` 记录值**——防用户手改过副本而清单未同步）
  3. hash 一致 → 跳过复制，任务书记录"复用"（即"已经有了就直接调用"）；不一致或缺失 → 覆盖复制（重编译后旧副本自动刷新）
  4. `flash_info.json` 中的 hash 仅作**交付追溯**（生产端离线校验收到的固件与发布时是否同一份），不参与复用判据
- **`release/` 永不作为固件发现来源**——发现永远走 state 指针（s7b/s6 权威位置），`release/` 只是镜像；即便有人往 release/ 手放一份固件，S9 也不会烧它
- **单一写者**：release/ 中 S9 管理的文件（固件副本/脚本/清单/生成的 flash.jflash）只由 S9 写；用户自放文件不触碰——例外：用户自放 `*.jflash` 在 `flash_tool = "jflash"` 时被决策流程识别消费（只读不改）；S9 仅在用户显式选"自动生成"时写 `flash.jflash`（带生成标记，生成后不覆盖）
- **命名与位置**：取 `release/`（发布/交付语义，开发自用与对外交付通吃）而非 `burn/`（偏临时操作目录）；位于项目根（跨工程：合并固件属 Boot+App 组合产物，不归属单一目标工程）

### 烧录工具为什么完全交给用户自管理

- **偏好差异**：探针与配套软件因人/因团队而异（J-Link / ST-Link / GD-Link / CMSIS-DAP 各有拥趸），S9 不替用户选
- **版本与设备数据库**：烧录工具对芯片的支持取决于其设备数据库（如 J-Link 需较新版本才收录 GD32 等国产芯片，旧版直接 `Device is unsupported`）；S9 装的版本 ≠ 用户习惯用的版本，自动安装反而制造不一致
- **配置文件绑定**：`.jflash` 工程、JLinkDevices 目录等配置与安装版本强绑定，自动安装的工具未必兼容用户既有环境
- **S9 的应对**：只检测、只指引（references 各工具指南含官方下载渠道与版本建议）、**不安装**——与 Keil/IAR"仅手动指引"同构，环境掌控权留给用户

### 烧录信息追溯

任务书与 `flash_result.json` 记录固件 SHA256、目标地址、设备名、工具与完整命令——失败复盘时可直接回答"烧了什么、烧到哪、用什么烧的"；`s9.firmware_sha256` 与 `s7b` 产物可交叉核对是否烧了旧固件。

### J-Link 设备名映射

J-Link 设备库命名与平台目录名不同（`stm32f103zet6` → `STM32F103ZE`，剥离温度等级尾码；`gd32f205vet6` → `GD32F205VE`）。映射表维护在 `references/jlink_flash_guide.md`，一期实测校准两个已有平台；新平台映射失败时报错要求 `--device` 显式指定，不猜。

### J-Link 命名辨析：Commander 与 J-Flash 的分工

- "J-Link" 既是探针（硬件）名，也是 SEGGER 软件套装名；套装内有两个能烧录的可执行程序
- **JLink.exe（J-Link Commander）**：命令行程序，`-CommandFile` 脚本化烧录（`loadfile`/`verify`/`r`/`g`/`qc`），无需工程文件，无人值守标准做法——**推荐**：智能推断的缺省方向、一期实现
- **JFlash.exe（J-Flash）**：图形界面烧录器，但有 CLI 自动化模式（`-openprj -open -auto -exit`），**绑定 `.jflash` 工程文件**——服务惯用 J-Flash 工作流/产线的用户：显式配置 `flash_tool = "jflash"` 选用，不参与智能推断；`.jflash` 缺失触发"自提供/自动生成"决策流程（见"输入"小节）
- 两者差异本质是"是否需要工程文件"：Commander 拿脚本即烧，J-Flash 离开 `.jflash` 不工作；`tool_paths.jflash` 键在 `flash_tool = "jflash"` 时被直接消费，兼作 `jlink` 的同目录探测线索（两 exe 同目录）

### 与 S7b 的机制对称性

S9 的双机制/四段式/`--collect` 收口/任务书/退出码拆分与 S7b 一一对应（编译 ↔ 烧录、vendor 编译快捷键 ↔ vendor 下载按钮、`error_analysis.md` 四分类根因、`gui_build_log.md` ↔ `gui_flash_log.md`），降低 S12 编排与用户心智负担。`analysis.py` 的 Flash 基址/容量来源链复用 S7b 实现，禁止两套规则。

### 演进路径（供实施参考）

1. **一期**：J-Link Commander CLI 机制全链路（本机 J-Link 探针 + JLink.exe 已装，从 `jflash` 同目录自动探测）——prepare（推断/定位/地址校验/任务书/jlink 脚本生成）→ flash（执行/日志解析/verify 判定）→ validate；实测 `stm32f103zet6`；同步更新 `schemas/config.schema.json` 与 `state.schema.json`（s9 键）
2. **二期**：J-Flash 适配——`.jflash` 决策流程（搜索/自提供/自动生成 + 生成标记不覆盖）与 `-openprj -open -auto -exit` CLI 烧录（本机 JFlash.exe 已装，可实测）
3. **三期**：OpenOCD + pyOCD 适配器（开源跨平台，顺带覆盖 GD-Link / DAPLink 等 CMSIS-DAP 探针；工具仍由用户自装，S9 只检测不安装）
4. **四期**：ST-Link（STM32CubeProgrammer CLI）适配器实测（用户手动安装后使用）
5. **五期**：8 位平台 GUI 烧录机制（`vendor_ide`）——ft61f14x（辉芒微）首个验证：编写 `references/vendor_flash/` 首份指南 + Agent GUI 操作 + `--collect` 收口
6. **六期**：`--retry` 智能化（仅连接类失败重试）、多探针并存探测（`--list-probes`）

每一步独立可验证，不影响其他 Skill。
