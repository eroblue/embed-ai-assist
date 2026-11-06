# S10 serial-monitor Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：serial-monitor
- **Skill 用途**：连接目标设备的串口并采集 UART/USB CDC 输出，保存原始接收数据、可读日志和会话元数据，供用户查看或交给 S11 log-analyzer 分析。S10 是**采集工具**，不解释日志语义。
- **触发时机**：用户需要观察设备启动、运行或故障输出时手动启动；S9 烧录完成后可由用户启动。S9 不自动触发 S10，S10 不自动触发 S11。
- **执行模型**：规则层负责配置校验、串口操作、日志落盘和会话校验；首期提供 Windows 图形界面作为主要用户入口，CLI 作为可选入口（自动化、排错、开发者使用）。GUI 不承载串口驱动和采集逻辑，而调用共享采集服务。
- **运行方式**：GUI 前台持续运行，提供明确的“开始采集 / 停止采集”按钮和连接状态；采集期间允许用户随时停止。停止时 flush/close 串口与输出文件并写出最终会话状态。可选 `--duration` 自动停止；不后台隐藏运行。
- **适用范围**：提供串口设备且操作系统可访问的 MCU/嵌入式目标。首期只监听（RX-only），不发送命令、不控制 DTR/RTS 复位引脚。
- **界面技术**：首期使用 Python 标准库 Tkinter，避免新增 GUI 框架依赖；串口依赖仍为 pyserial。GUI 应可通过 Windows 启动器或文件资源管理器启动，不要求用户逐条输入 PowerShell 命令。
- **职责边界**：S10 保存采集事实；S11 分析已有日志。S11 可直接接收用户自行采集的文件，不要求 S10 状态或产物存在。S10 不依赖 S9 成功状态，也不要求日志必须来自本工具。

## 输入

### GUI 输入与交互

GUI 主窗口为 S10 默认入口。首次启动时提供项目 `config.json` 文件选择器；用户选择后加载全局配置与项目配置，并将最近使用的配置路径保存在用户级 S10 设置文件（不写入项目 config/state）。下次启动默认重开最近使用项目；项目配置不可读时显示错误对话框并允许重新选择。

主窗口至少包括：

| 控件 | 行为 |
|---|---|
| 项目配置 | 显示当前 config 路径；“选择项目”打开文件选择器 |
| 串口 | 可下拉选择枚举到的端口；“刷新”重新枚举，端口描述/硬件 ID 可用时作为辅助信息 |
| 串口参数 | 波特率、数据位、校验位、停止位、编码；以项目 `project.serial` 为初值，可在界面临时修改 |
| 持久化设置 | “保存为项目默认值”复选框，缺省不勾选；仅在用户明确勾选并点击保存时写 `project.serial`，保留 config 其他字段并原子更新。纯临时改动不得写 config |
| 开始/停止 | 未采集时显示“开始采集”；连接成功后切换为“停止采集”；采集中禁止重复开始 |
| 连接状态 | 至少显示 `未连接`、`正在连接`、`采集中`、`正在停止`、`已停止`、`错误`；显示当前端口和有效串口参数 |
| 实时日志 | 显示新收到的文本视图并自动滚动；提供暂停/恢复显示（仅暂停 UI 渲染，不暂停串口读取和落盘）及清空显示（只清屏，不删除文件） |
| 输出信息 | 显示当前会话目录、原始文件/可读日志路径、已接收字节数和已运行时长；提供“打开日志目录”按钮 |

端口选择不得根据名字自动猜；端口不存在或未选择时禁用开始按钮，并用界面提示要求刷新或选择端口。GUI 不在首期提供 TX 发送框、设备控制命令、DTR/RTS 控制、波形解析或日志语义分析。

### 连接错误提示

- 串口打开前参数校验失败：在对应输入控件附近显示具体字段错误，不弹出泛化异常栈。
- 串口打开失败：状态显示“连接失败”，同时弹出可关闭的错误对话框，包含端口名、串口参数、操作系统/pyserial 原始错误文本和可执行的排查建议（如端口占用时建议关闭其他串口工具）。不声称未验证的根因；不得自动换端口或波特率。
- 打开端口失败时采集尚未开始：不得创建标记为成功的会话或空日志；保留界面供用户修改参数后重试。
- 连接成功后状态即时更新；运行中断连/写盘失败时停止读取、保存已捕获内容、收口状态，并以醒目状态和对话框告知错误及已保存路径。

### 无终端启动

- 交付 Windows GUI 启动入口 `start_s10.pyw`（或等价 `.bat`/快捷方式方案）；直接启动窗口，不要求用户先开 PowerShell 或输入多条命令。
- GUI 启动器通过文件选择器选择项目 config；若使用 `.pyw`，致命启动错误必须写入可查看的启动错误日志并显示系统对话框，不能静默退出。
- CLI 命令保留用于自动化和开发者操作，README/Skill 使用说明将 GUI 列为普通用户默认路径，CLI 放在“高级/自动化用法”。

### 从项目级 `config.json` 读取

全局与项目配置按 README 的深合并规则加载，串口配置位于 `project.serial`：

```json
{
  "project": {
    "serial": {
      "port": null,
      "baudrate": 115200,
      "bytesize": 8,
      "parity": "N",
      "stopbits": 1,
      "encoding": "utf-8",
      "read_timeout_ms": 200
    }
  }
}
```

字段约束：

| 字段 | 类型 / 合法值 | 缺省 | 说明 |
|---|---|---|---|
| `project.serial.port` | string/null | `null` | 串口名，如 `COM5`、`/dev/ttyUSB0`；通常机器相关。缺省时须由 `--port` 提供或使用 `--list-ports` 后重跑，不猜测 |
| `project.serial.baudrate` | 正整数 | `115200` | 波特率；常见值可用但不得限制为固定枚举 |
| `project.serial.bytesize` | `5`/`6`/`7`/`8` | `8` | 数据位 |
| `project.serial.parity` | `N`/`E`/`O`/`M`/`S` | `N` | 无校验/偶/奇/标记/空格校验；底层库不支持的值在 prepare 报错 |
| `project.serial.stopbits` | `1`/`1.5`/`2` | `1` | 停止位；底层库不支持的组合在 prepare 报错 |
| `project.serial.encoding` | string | `utf-8` | 可读视图解码方式；原始字节文件不受此值影响 |
| `project.serial.read_timeout_ms` | 正整数 | `200` | 串口读取超时，避免停止信号长期阻塞 |

端口名可写在项目配置中作为本机默认值，但必须允许 GUI/CLI 单次覆盖；跨机器共享项目时，端口不存在不得静默退回到另一个端口。GUI 临时修改缺省不写配置；仅在用户明确勾选“保存为项目默认值”并确认后才写 `project.serial`。CLI 单次覆盖永不回写配置。

### 从 CLI 参数读取

CLI 是可选高级入口，遵循与 GUI 相同的配置、采集服务、输出契约和状态语义。

| 参数 | 缺省 | 说明 |
|---|---|---|
| `--config <path>` | 必填 | 项目级 config.json |
| `--port <name>` | config 值 | 覆盖串口端口名 |
| `--baudrate <n>` | config 值 | 覆盖波特率 |
| `--bytesize <5\|6\|7\|8>` | config 值 | 覆盖数据位 |
| `--parity <N\|E\|O\|M\|S>` | config 值 | 覆盖校验位 |
| `--stopbits <1\|1.5\|2>` | config 值 | 覆盖停止位 |
| `--encoding <name>` | config 值 | 仅影响可读日志视图 |
| `--duration <seconds>` | 不限时 | 采集指定时长后自动停止，必须大于 0 |
| `--output-dir <path>` | `<build_target>/outputs/s10/` | 指定会话目录的父目录；会在其下创建 `<session_id>/`；相对路径按项目根解析 |
| `--list-ports` | — | 列出可访问串口后退出，不打开端口、不创建采集会话 |
| `--session-dir <path>` | validate 必填 | 待校验的会话目录 |

### 状态前置条件

- `state.json` 可选：若存在则读取 `project.build_target` 对应目标的 state 作为会话上下文；没有 state 或尚未运行 S9 时仍允许采集。
- 不要求 `s9.status = done`，不要求 S7b/S6 产物存在。
- 若 state 中存在最近一次 S9 结果，可以在 `session.json` 记录其固件路径、SHA256 和烧录时间作为**可选上下文快照**；不将其作为采集成功判据。
- S10 不读取或修改 S11 状态。

### `input.schema.json` 的契约边界

该文件描述 S10 **可选读取的 state.json 上下文**，不重复描述 config.json 或 CLI 参数：

- 根对象允许为空；S10 无状态依赖。
- `s9` 可缺省或为 `null`；存在时只允许按 `s9_context` 白名单读取 `status`、`firmware_path`、`firmware_sha256`、`updated_at`。
- `s9` 内容格式与 `skills/flash/schemas/output.schema.json` 对齐；S10 不要求其状态为 `done`。
- `additionalProperties: true`，因为该 schema 校验的是全局 state 的投影，不得拒绝其他 Skill 字段。
- 项目配置字段由根 `schemas/config.schema.json` 校验；CLI 参数由 `argparse` 与本需求中的规则校验。不得把配置和 CLI 参数伪装成 state 输入 schema。

### 串口依赖

- 首期使用 Python `pyserial`（模块 `serial`）作为串口后端；`prepare.py` 检查依赖可导入。
- 不自动安装依赖。缺失时报告安装命令和当前 Python 路径，退出码为 2。
- 首期支持当前 pyserial 可用的串口端口；不自定义厂商驱动、不扫描网络串口。

## 输出

### 输出路径

默认会话目录：`<项目根>/<build_target>/outputs/s10/<session_id>/`，与 App / BootLoader 目标隔离。串口连接成功后 GUI/CLI 自动生成 `session_id` 并创建目录；无需用户手动运行 prepare。`session_id` 使用本地时间可读前缀加短随机后缀，避免同秒会话覆盖。CLI 显式 `--output-dir` 可覆盖会话目录的父目录；仍在其下新建 `<session_id>/`，不得覆盖已有目录；冲突时报错。

每个会话写入：

| 产物 | 内容说明 |
|---|---|
| `capture.bin` | 串口收到的原始字节，按接收顺序逐字节保存；不得注入时间戳、换行、转码或丢弃不可打印字节 |
| `capture.log` | UTF-8 JSON Lines，每个接收块一行，字段为 `record_type`、`ts_host`、`data_b64`、`text`；时间戳是主机接收时间，Base64 保留该块确切字节，`text` 是按配置编码解码的便利视图，解码错误用 U+FFFD 替代并计数。JSON 转义使设备内容中的换行不会伪造记录边界 |
| `session.json` | 会话元数据与最终状态，结构见下文 |

`capture.bin` 是原始数据权威副本；`capture.log` 是包含原始块 Base64 的可读/可解析副本，解码或时间戳格式变化不得改变原始副本。`ts_host` 使用 ISO 8601 含时区格式；首条记录为 `record_type="header"`，包含时间戳语义、编码与会话 ID；其余接收块为 `record_type="rx"`，每个非空块一条记录。增量解码器停止时产生的尾部字符可另写 `record_type="decode_tail"`，`data_b64` 为空、原始字节已在先前 RX 记录中。时间戳明确标注为主机接收时间，不是设备端时间。

### `session.json` 契约

至少包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 元数据格式版本 |
| `session_id` | string | 唯一会话标识 |
| `status` | string | `running` / `stopped` / `completed` / `error`；未正常收口由 validate 在 state 摘要中标为 `interrupted` |
| `target` | string | `App` / `BootLoader`；从项目配置的 `project.build_target` 取得，缺省 `App` |
| `port` | string | 实际打开的端口名 |
| `serial` | object | 实际 baudrate/bytesize/parity/stopbits/encoding/read_timeout_ms |
| `started_at` | string | 含时区 ISO 8601 时间戳 |
| `ended_at` | string/null | 含时区 ISO 8601 时间戳；运行中为 null |
| `duration_sec` | number/null | 实际会话时长 |
| `duration_limit_sec` | number/null | CLI `--duration` 的计划时长；不限时为 null |
| `stop_reason` | string/null | `duration_reached` / `user_interrupt` / `serial_disconnected` / `error` 等 |
| `bytes_received` | integer | 原始接收字节数 |
| `chunks_received` | integer | 实际读取到的非空接收块数，不含 header |
| `capture_bin` | string | 原始文件相对会话目录的路径 |
| `capture_log` | string | 可读文件相对会话目录的路径 |
| `encoding_errors` | integer | 可读视图发生解码替代/转义的次数 |
| `s9_context` | object/null | 若可用，记录本次采集启动时观察到的最近 S9 固件摘要；仅上下文，不证明当前运行固件未被更换 |
| `error` | string/null | 错误摘要；不得用来替代原始异常日志 |

字段约束：`schema_version` 首期固定为 `1.0`；`session_id` 匹配 `[0-9]{8}T[0-9]{6}-[a-f0-9]{8}`（本地时间前缀 + 随机后缀）；`target` 为 `App/BootLoader`；`port` 非空；`baudrate` 为正整数；`bytesize` 为 5–8；`parity` 为 `N/E/O/M/S`；`stopbits` 为 `1/1.5/2`；时间戳使用 RFC 3339/ISO 8601 且带 UTC offset；计数非负；路径为相对会话目录的 `capture.bin`、`capture.log`；`serial` 中固定包含实际生效参数；未知字段允许保留以便向前扩展。

状态转移：`prepare` 创建 `running`；捕获到至少一次字节后仍为 `running`；达到时长写 `completed` / `duration_reached`；用户 Ctrl+C 写 `stopped` / `user_interrupt`（尽力完整收口，退出码 0）；端口打开失败、运行中断连或写盘失败写 `error` / 对应原因（退出码 1 或 2）；进程被强制终止而未能收口时保留 `running`，validate 将其报告为未完成并在 state 摘要中标记 `interrupted`，但不得擅自篡改 session 文件为已正常结束。`ended_at` 与 `duration_sec` 在 `running` 时必须为 null，其余状态必须有值。`error` 状态必须提供 `error`；非错误状态 `error` 为 null。

状态写入应原子化（临时文件后替换），避免中断时留下半截 JSON。采集过程中定期 flush 原始数据与日志；Ctrl+C、串口断开或运行异常时尽量关闭端口、flush 文件并写最终元数据。进程被强制终止/断电时，允许 `status` 留在 `running`，validate 必须识别并报告为非正常结束，不得误标 `completed`。

### 写入 `state.json`（仅 `s10` 字段）

若目标 `state.json` 存在则只更新 `s10` 字段；不存在时不为采集强行创建不完整的项目状态文件，改由 `session.json` 作为会话权威记录。state 保存指针和摘要，不内嵌日志内容。

| 字段 | 类型 | 说明 |
|---|---|---|
| `s10.status` | string | `running` / `done` / `error` / `interrupted` |
| `s10.session_id` | string | 最近一次会话 ID |
| `s10.session_dir` | string | 会话目录路径 |
| `s10.capture_bin` | string | 原始日志路径 |
| `s10.capture_log` | string | 可读日志路径 |
| `s10.session_manifest` | string | `session.json` 路径 |
| `s10.port` | string | 实际端口名 |
| `s10.started_at` | string | 会话开始时间 |
| `s10.ended_at` | string/null | 结束时间 |
| `s10.bytes_received` | integer | 接收字节数 |
| `s10.stop_reason` | string/null | 停止原因 |
| `s10.error` | string/null | 错误摘要 |
| `s10.updated_at` | string | 最近更新时间 |

S10 是 append-only 会话产物：新会话创建新目录，不覆盖历史采集；state 仅指向最新会话。不得清理旧会话或修改 S9/S7b/S11 等其他字段。

### `output.schema.json` 的契约边界

描述 `state.json.s10` 单个对象（不是整个 state 根对象），供 validate 校验后写回。要求 `status`、`session_id`、`session_dir`、`capture_bin`、`capture_log`、`session_manifest`、`updated_at`；状态枚举为 `running/done/error/interrupted`。`done` 必须有 `ended_at`、`bytes_received`、`stop_reason`；`error` 必须有非空 `error`；`interrupted` 必须说明未正常收口的原因。其他摘要字段按前表定义，`additionalProperties: false`，便于发现拼写错误。validate 应先校验临时对象，通过后再原子更新 state。

### `session.schema.json` 的契约边界

描述每个会话目录中的 `session.json`，按上表字段定义必填项与状态条件；`status` 采用本节状态枚举，`serial` 对象字段固定且 `additionalProperties: false`，顶层允许 `additionalProperties: true` 以便版本演进。该 schema 是会话数据契约，不是 `state.json` 的替代品。

## 执行阶段

GUI 与 CLI 调用相同业务服务。GUI 的“开始采集”在后台线程中校验参数并打开串口；连接成功后才创建会话和日志。GUI 的“停止采集”触发有序关闭，收口后执行同等于 validate 的规则校验与 state 更新。GUI 不启动 PowerShell 子窗口。

### 阶段 A [rule] `prepare.py`（可选 CLI 预检查）

1. 加载全局与项目配置并深合并；解析目标工程和项目根。
2. 合并配置与 CLI 覆盖值；校验端口非空、波特率为正、数据位/校验/停止位合法、编码可识别、超时与时长合法。
3. 检查 pyserial 可用；验证输出目录可创建、目标目录无冲突、磁盘可写。
4. `--list-ports` 时列出端口名称/描述/硬件 ID（可用时），退出，不改变 state。
5. 检查端口名是否在当前系统枚举中；允许用户显式给出未枚举端口以兼容热插拔/驱动差异，但打开失败时返回清晰 OS/驱动错误，不静默改选。
6. 预检查只输出配置/端口信息；**不打开串口、不创建会话目录、不更新 state**。普通用户不需要运行该阶段。

### 阶段 B [rule] GUI “开始/停止”或 `capture.py`（单命令 CLI）

1. 加载并校验项目配置、可选 state 与串口参数；拒绝同一目标另有未收口 S10 会话的情况。
2. 先打开指定串口；打开失败时在 GUI 显示端口/参数/系统错误和建议，CLI 输出到 stderr，且不创建会话或空日志。
3. 串口打开成功后才生成独立会话目录、header、初始 `session.json`，并将 state `s10.status` 记为 `running`（state 存在时）。
4. 只读 RX；按接收块写原始字节、Base64 + 增量解码文本 JSONL 和有时区主机接收时间；固定最多 4096 bytes/次读取，不等待设备换行。
5. GUI“停止采集”、关闭窗口和 CLI Ctrl+C 都设置停止事件；时长到期正常结束。每 0.5 秒及收口时 flush；停止请求幂等。
6. 正常结束写 session `completed`（时长到期）或 `stopped`（用户主动），更新统计和 state `done`；断连/写盘故障写 `error`，尽量保存部分数据后告知路径。收口后自动执行 validate 逻辑。

### 阶段 C [rule] `validate.py`

1. 独立调用时 `--session-dir` 必填；GUI/CLI 正常收口时也调用同一校验函数。校验 `session.json` schema、会话 ID、实际参数、时间字段、停止原因和状态一致。
2. 确认 `capture.bin` 与 `capture.log` 存在且可读，按文件实际字节数复核 `bytes_received`；若实现定义日志统计字节数，需另字段，不混淆二者。
3. 检查非正常退出：`running` 状态视为强制中断/未收口；`error` 必须包含原因并不得归为 `done`。
4. 正常 `completed` 或用户主动 `stopped` 时，state 标记 `done`；连接成功后的设备断连/磁盘失败标记 `error`；连接失败没有会话/state 新写入；残留 `running` 的强制中止标记 `interrupted`（仅 state 摘要，不伪造 session 的结束信息）。
5. 若 state 存在，仅更新 `s10` 字段并校验指针存在；session 文件为会话事实权威，会话状态与 state 不一致时以 session 为准并报告。`validate --session-dir` 能在当前会话未被 state 指向（例如没有 state 文件）时独立工作。
6. 输出验证摘要：状态、端口、时长、字节数、原始日志路径、可读日志路径、停止原因。

## 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 当前阶段成功；capture 达到时长或用户 Ctrl+C 后正常收口均为成功 |
| `1` | capture 运行时错误、设备断连或写盘错误；已尽力保存部分数据 |
| `2` | 配置/参数/依赖/输出目录错误、端口打开失败、计划文件无效或 validate 发现契约错误 |

## Agent 参与与禁止事项

- 默认无 Agent 阶段。GUI/CLI 中的串口选择、端口连接、读取、保存和校验均由确定性代码执行；不为保持其他 Skill 的三段式而插入 Agent。
- 普通用户不需要在 PowerShell 中逐条输入 prepare/capture/validate 命令；GUI 是首期默认入口，CLI 只作为备用入口。
- 不分析日志中的错误含义、不推断设备状态、不生成修复建议；这些属于 S11。
- 不要求日志来源于 S10；不阻止用户将任意文本日志直接交给 S11。
- 不自动选择“看起来最像”的端口；多个端口存在时必须使用配置或 CLI 明确指定。
- 不自动扫描波特率、不尝试不同串口参数、不自动重连（一期）；连接断开后收口并报告。
- 不发送任何串口数据、不自动复位目标、不控制 DTR/RTS、不执行设备命令。
- 不自动修改项目配置、源代码、固件或历史会话；不覆盖已有会话目录。只有用户在 GUI 明确选择“保存为项目默认值”并确认后，才允许原子更新 `project.serial`；CLI 永不回写。
- 不自动安装 pyserial 或系统驱动。
- 不静默丢弃/改写原始字节；解码失败只能影响可读视图并在元数据中计数。
- 不把主机接收时间伪装成设备生成时间。
- 不自动触发 S11；由用户或未来 S12 工作流显式决定。

## Skill 目录结构

```text
serial-monitor/
├── SKILL.md
├── schemas/
│   ├── input.schema.json          # 可选读取的 state.json S9 上下文投影
│   ├── output.schema.json         # state.json 的 s10 字段
│   └── session.schema.json        # session.json 会话契约
├── scripts/
│   ├── analysis.py                # 配置加载、串口参数校验、端口枚举、会话路径与 state 原子更新
│   ├── prepare.py                 # 阶段 A：准备计划、检查依赖/目录、初始化会话
│   ├── capture.py                 # 阶段 B：串口读取、双格式落盘、统计与收口
│   ├── validate.py                # 阶段 C：产物校验、state 收口
│   ├── gui.py                     # Tkinter 主窗口；调用共享采集服务，不直接实现串口读写
│   ├── capture_service.py         # GUI/CLI 共用的串口会话服务、后台读取线程与有序停止
│   └── start_s10.pyw              # Windows GUI 启动入口（无控制台窗口）
├── references/
│   ├── serial_config_guide.md     # 常见系统端口名、串口参数说明与故障排查
│   └── log_format.md              # capture.bin / capture.log / session.json 约定
└── assets/
    └── serial_example.md          # 命令示例与样例会话
```

## 使用方法

```bash
# 普通用户：双击 skills/serial-monitor/scripts/start_s10.pyw，选择项目 config/串口后点击“开始采集”

# 高级用户/自动化：枚举串口，不打开、不采集
python skills/serial-monitor/scripts/prepare.py --config examples/stm32f103zet6/config.json --list-ports

# 单次覆盖端口/波特率，采集 60 秒（不回写 config）
python skills/serial-monitor/scripts/capture.py --config examples/stm32f103zet6/config.json --port COM5 --baudrate 115200 --duration 60

# 对已有会话做独立校验/收口
python skills/serial-monitor/scripts/validate.py --config examples/stm32f103zet6/config.json --session-dir examples/stm32f103zet6/App/outputs/s10/<session_id>
```

## 与其他 Skill 的关系

| Skill | 关系 |
|---|---|
| S9 flash | 可在烧录完成后由用户启动 S10；无状态硬依赖，S9 不自动启动串口会话 |
| S11 log-analyzer | 可读取 S10 的 `capture.log` 或用户提供的其他日志；S11 不依赖 S10 的 state/manifest，S10 不自动调用 S11 |
| S12 workflow-runner | 将来可编排“用户启动采集 → 用户停止 → 可选分析”；首期不设计无人值守的默认串口时长或自动分析 |

## 演进路径

1. **一期**：Windows Tkinter GUI 主入口 + CLI 高级入口；pyserial RX-only；项目 config 加载、界面临时覆盖和显式保存默认值；端口刷新/选择；连接状态、实时日志显示、暂停显示、停止并保存；原始二进制与 JSONL 可读日志双写；session 元数据、state 收口和 validate。
2. **二期**：支持断线后用户选择是否重连、可配置轮转/分段日志和更丰富的端口枚举信息；仍保持默认只读。
3. **后续可选**：按用户显式配置加入 TX 命令/协议交互或硬件流控；这类能力需独立权限与审计设计，不属于首期日志监控。

## 验收标准

- 配置与 CLI 覆盖优先级正确，参数不会写回 config。
- 端口缺失/多候选时不擅自选取；用户显式端口可用于连接。
- 原始串口字节按接收顺序完整落入 `capture.bin`；乱码不影响原始副本。
- 可读日志含明确的主机接收时间，解码失败有可见表示及计数。
- Ctrl+C、时长结束、连接失败、运行中断连、写盘失败分别正确收口并记录原因。
- 每次会话独立目录，不覆盖旧日志；`session.json` 可独立说明采集参数、状态和文件。
- 有项目 state 时只更新 `s10`，无 state 时仍可采集且不创建半成品 state。
- validate 能检测缺失文件、JSON 损坏、统计不一致和未收口的 `running` 会话。
- S10 不分析日志、不发送数据、不复位设备、不自动调用 S11。
- 普通用户可通过 Windows GUI 完成选择项目、选端口、设置参数、开始/停止和查看输出，不需要逐条输入命令。
- GUI 关闭窗口等同于请求停止：等待串口线程完成 flush/close 和会话收口后再退出；保存完成前不得直接销毁窗口或丢弃正在采集的数据。
- 实时日志 UI 必须使用有界队列/缓冲区，显示暂停或高流量时不得阻塞串口读取与文件落盘；UI 缓冲区满时只丢弃屏幕显示旧行并提示，不得丢弃文件数据。

## 实施时必须同步的全局契约

- `schemas/config.schema.json`：在 `project.properties` 增加 `serial` 对象及本需求列出的字段、类型、范围、默认值；`project.additionalProperties` 当前为 false，因此不更新会导致 config 校验拒绝配置。
- `schemas/state.schema.json`：新增 `s10` 对象说明，并将旧 `log` 字段标为 S10 早期兼容字段/弃用，不再由 S10 写入；新实现只写 `s10`。
- S10 自有 `input.schema.json`、`output.schema.json`、`session.schema.json` 必须按上文契约边界落成 JSON Schema Draft 2020-12；input 校验 state 中可选的 S9 投影，output 校验 state.s10，session 校验会话清单。
- GUI 的 Tk 事件线程不得执行阻塞串口读取或文件 I/O；采集线程通过线程安全队列发送状态/日志事件，UI 定时轮询更新。停止请求应是幂等操作，关闭窗口时等待收口但 UI 仍保持响应并显示“正在保存”。
- `start_s10.pyw` 从脚本位置定位 Skill 与根配置，从用户选定的项目 config 定位项目根；路径包含空格/中文时必须正确工作。用户级最近项目设置存放于 Windows 用户配置目录，不进入仓库。
- S10 所有路径写入 state 时采用相对当前目标工程根的正斜杠路径；命令输出可同时给绝对路径，方便用户打开文件。
- state.json 的更新必须保留未知顶层字段和其他 Skill 字段，禁止重建整个 state 对象；同一目标同一时刻只允许一个 S10 会话更新 state。若检测到 `s10.status=running` 且指向另一会话，prepare 报错并提示先对旧 `session_dir` 执行 validate 收口，不自动覆盖。

\n