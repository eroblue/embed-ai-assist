# S9 flash 任务书（CLI 机制）

> 由 prepare.py 生成（rule 轨）。烧录由 `flash.py` 纯 rule 执行；
> 本任务书完整展示本次烧录决策供追溯，并为**烧录失败后的 Agent 分析路径**准备。

## 1. 烧录信息清单

| 项 | 值 |
|---|---|
| 目标工程 | `App`（工程根 `App`） |
| 固件来源 | `s7b`（s7b 产物 / S6 合并固件 / manual=--firmware 显式） |
| 固件格式 | `hex` |
| 固件源路径 | `E:\skills\EmbedSoftAutomaticProject\embed-ai-assist\examples\stm32f103zet6\App\MDK-ARM\Objects\Template.hex` |
| 烧录执行体 | `release/Template.hex`（release/ 副本——**烧的即发布的**） |
| 固件大小 | 41586 字节 |
| 固件 SHA256 | `432b33919a2443f73e42a47b53ad84119192476ab07b0a8b73affafa72693249` |
| 目标地址 | `0x08000000`（hex 自带地址，不传给工具） |
| flash_offset | `0x0`（config 唯一权威，已含在目标地址内） |
| 设备名 | `STM32F103ZE`（J-Link 设备库命名） |
| 探针接口 | `SWD` |
| 烧录工具 | `jlink`（从 tool_paths.jflash 同目录探测（C:\Program Files\SEGGER\JLink）） |
| verify | 开启（烧录后校验，失败不算成功） |
| 复位运行 | 开启（r + g） |
| 全片擦除 | 关闭（按固件范围擦除） |

## 2. 完整命令

```bash
cd E:\skills\EmbedSoftAutomaticProject\embed-ai-assist\examples\stm32f103zet6\release
C:\Program Files\SEGGER\JLink\JLink.exe -device STM32F103ZE -if SWD -speed 4000 -autoconnect 1 -CommandFile flash_cmd.jlink
```

命令脚本 `release/flash_cmd.jlink`（release/ 内，自包含可复烧）：

```
connect
loadfile Template.hex
verifybin Template_verify.bin 0x08000000
r
g
qc
```

## 3. release/ 发布文件

| 文件 | 大小 | SHA256（前 16 位） | 状态 |
|---|---|---|---|
| `release/Template.hex` | 41586 | `432b33919a2443f7…` | 复用（hash 一致） |
| `release/Template.bin` | 14768 | `46a8e2275e2f51b4…` | 复用（hash 一致） |
| `release/flash_cmd.jlink` | — | — | 每次按当前选项重新生成 |

## 4. 执行策略与禁止事项

- **直接执行烧录，不请求人工确认**（开发迭代场景；verify 缺省开启兜底，
  完整信息以本任务书为准供追溯）
- 失败**不自动重试**（`--retry` 缺省 0，连接抖动场景可显式开启）、
  **不自动解锁**芯片（读保护/写保护状态属用户决策）
- 烧录工具完全由用户自管理：**不自动下载安装任何烧录工具**（探针偏好、
  版本兼容、设备数据库支持因人而异）；缺失时仅报错并附手动指引
- `--timeout` 缺省 300s（flash.py 执行参数），超时杀进程按失败处理
- `release/` 永不作为固件发现来源（发现只走 state 指针，防烧旧固件）

## 5. 烧录失败时的 Agent 分析路径（阶段 C）

> 仅 flash.py 以退出码 1 结束时进入；产出 `outputs/s9/error_analysis.md`，
> 按四类根因（连接 / 芯片 / 固件 / 工具）定位，不自动修复。

1. 读 `outputs/s9/flash.log` 与 `outputs/s9/flash_result.json`（key_lines 已提取）
2. 按日志特征行分类（特征映射表见 `references/flash_log_parse_rules.md`）：
   连接类（`Connecting...FAILED` / 探针未插）、芯片类（`Cannot connect to target`、
   供电/复位电路、读保护锁定）、固件类（越界/起址不符/verify 失败）、
   工具类（`Unknown device` 设备名错、版本过旧不支持该芯片）
3. 结合本任务书的地址/设备名/工具版本信息给出结论与**用户手动**处置建议

## 6. 防御性校验警告（不阻断，请核对）

- 显式配置 project.flash_tool = 'jlink'
- release/Template.hex: 复用（hash 一致）
- release/Template.bin: 复用（hash 一致）
- release/Template_verify.bin: 由 hex 派生校验镜像（14768 字节 @ 0x08000000；间隙按 0xFF 比对，hex 含空洞且残留数据时会校验失败——可加 --chip-erase 全片擦除后再烧）

> 任务书生成于 2026-10-24T16:44:50，每次 prepare 按当前选项重新生成。
