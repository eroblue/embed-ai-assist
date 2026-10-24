# 烧录日志特征行映射表

> S9 日志判定的唯一规则来源（`scripts/analysis.py` 的 `parse_jlink_log` 与本文件保持
> 同步；Agent 阶段 C 分析时以本表对照 flash.log / key_lines 分类根因）。
> 日志解码：UTF-8 → GBK → `errors='replace'`（烧录器在中文 Windows 上输出编码不定）。

## jlink（一期，V7.54 实测校准）

### 成功判据（全部满足）

| 判据 | 特征行 |
|---|---|
| 退出码 | JLink.exe 退出码 = 0（Commander 对脚本内失败也可能退 0，故还需下述特征） |
| 下载开始 | `Downloading file [...]` |
| Flash 写入段 | `J-Link: Flash download: Bank 0 @ 0x08000000:` 段头（实际写入与 `Skipped. Contents already match` 跳过均打印），段尾独立行 `O.K.` |
| 无失败特征 | 无任何失败特征行（见下表；瞬态 USB 连接失败除外，见注） |
| verify 通过（verify 开启时） | `Verify successful.`（verifybin 逐字节比对输出）；且无 `Verify failed` / `Verification failed` |

> **verify 失败不算烧录成功**（state 标 error）：下载完成但内容比对不一致，
> 多为 Flash 坏块/写保护/电源不稳。
>
> **瞬态 USB 连接**：首次 USB 连接可能瞬态失败（`Connecting to J-Link via
> USB...FAILED`），脚本首行 `connect` 前置吸收重试；日志后文出现
> `Connecting to J-Link via USB...O.K.` 时，早先的连接失败行不计致命。

### 失败特征行 → 四类根因

| 特征行（节选） | 根因类 | 说明 |
|---|---|---|
| `Connecting to J-Link via USB...FAILED` | 连接 | 探针未插 / USB 驱动问题（J-Link 软件未装或版本不匹配）；后文 USB O.K. 时为瞬态不计 |
| `Connecting to target via SWD...FAILED` | 连接 | 探针→目标板连接失败：接线/供电/接口类型错 |
| `Cannot connect to target` | 芯片 | 目标不可达：VCC/GND/SWDIO/SWCLK 线序、复位电路、芯片读保护（RDP）锁定 |
| `Init target failed` / `DP cannot be halted` | 芯片 | 时钟异常（外部晶振未起振）、复位脚被拉死 |
| `Verify failed` / `Verification failed` / `Contents differ` | 固件 | verifybin 比对不一致：Flash 坏块、写保护位、供电不稳 |
| `Downloading file failed` / `Failed to download` | 固件 | 文件路径错（release/ 副本被移走）或格式非法 |
| `Unknown command.` | 工具 | CommandFile 命令拼写错、使用了 `#` 注释行（V7.54 不支持）、或误用不存在的 `verify` 命令（应使用 verifybin）——检查 flash_cmd.jlink |
| `Unknown device` / `Device "X" is unsupported` | 工具 | 设备名映射错（--device 显式指定）或 J-Link 版本过旧缺设备数据库条目 |
| `Device name is ambiguous` | 工具 | 设备名不唯一，需按映射表精确命名 |
| `Script processing failed.` | 通用 | 脚本命令错误（命令拼写/顺序），检查 flash_cmd.jlink |

### 复位确认

- V7.54 复位输出（与 connect 后的初始化复位同段，无法从日志行严格区分归属）：
  `Reset type NORMAL: ...` / `Reset: Reset device via AIRCR.SYSRESETREQ.`
- 成功 + reset 开启 → `reset_done = true`（`r` 为内建命令，脚本跑通即已执行）

## stlink（STM32CubeProgrammer CLI，三期演进项——占位）

成功判据与失败特征待三期实测校准（参考命令预告：`STM32_Programmer_CLI -c port=SWD
-w <file> <addr> -v -rst`；`--connect`/`--download`/`--verify`/`--start` 子模式）。

## openocd（三期演进项——占位）

参考命令预告：`openocd -f interface/<cfg> -f target/<cfg> -c "program <file> verify
reset exit"`；日志特征待三期校准。

## pyocd（四期演进项——占位）

参考命令预告：`pyocd flash -t <target> --format bin <file>`；日志特征待四期校准。

## jflash（J-Flash CLI，二期演进项——占位）

J-Flash 自动化模式命令预告：`JFlash.exe -openprj <project.jflash> -open <file> -
auto -start -exit`；`.jflash` 决策流程（检查→自提供/自动生成，生成标记不覆盖）见
jflash_flash_guide.md（二期完善）。

## vendor_ide（GUI 机制，五期演进项——占位）

GUI 烧录无命令行日志——完成/失败判定特征（厂家 IDE 输出窗口关键词）登记在各
`references/vendor_flash/<标识>.md` 指南，由 Agent 操作时人机协同确认，
`flash.py --collect` 收口为 `gui_flash_log.md`。
