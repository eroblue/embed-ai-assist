# J-Link Commander（JLink.exe）烧录指南

> S9 flash 一期官方烧录通道。J-Link Commander 是 SEGGER J-Link 软件包自带的脚本化
> 命令行工具（`JLink.exe`），支持命令文件（CommandFile）批处理，适合纯 rule 自动化烧录。

## 1. 安装与路径配置（用户自管理）

- **官方下载渠道**：https://www.segger.com/downloads/jlink/ （J-Link Software and
  Documentation Pack；仅需免费的 "Software and Documentation pack"，无需烧录器授权）
- **版本建议**：V7.80+（GD32 等国产芯片设备数据库支持随版本更新；烧录 GD32F205
  需 JLinkDevices 支持包或较新版本内置条目，见 SEGGER 官网 Device Support）
- **默认安装路径**：`C:/Program Files/SEGGER/JLink/`（`JLink.exe` 与 `JFlash.exe` 同目录）
- **config.json 配置**（全局 config.json 的 `tool_paths` 段，二选一即可）：

```json
{
  "tool_paths": {
    "jlink": "C:/Program Files/SEGGER/JLink/JLink.exe"
  }
}
```

未配置 `tool_paths.jlink` 时，S9 自动从既存 `tool_paths.jflash` 同目录探测
`JLink.exe`（两 exe 同在 SEGGER 安装目录）。两者均缺失 → prepare 报错并指向本指南，
**不自动安装**（探针偏好、软件版本兼容、设备数据库支持因人而异，自动安装不可控）。

## 2. 设备名映射表（platform → J-Link 设备库命名）

映射规则：剥离封装/温度等级尾码（意法/兆民命名法：`<容量+引脚><封装><温度>`，
如 `ZET6` → `ZE`，T=LQFP 封装、6=-40~85°C）。**代码表**（`scripts/analysis.py`
的 `JLINK_DEVICE_MAP`）与本表必须同步维护。

| platform 目录名 | J-Link 设备名 | 说明 |
|---|---|---|
| `stm32f103zet6` | `STM32F103ZE` | STM32F103 512KB 大容量（本机示例，实测校准） |
| `gd32f205vet6` | `GD32F205VE` | 兆民 GD32F205 连接型（需 V7.80+ 或 JLinkDevices 支持包） |

新平台接入：在 `analysis.py` 的 `JLINK_DEVICE_MAP` 增加映射并在本表登记；
映射失败 → prepare 报错要求 `--device` 显式指定（**不猜**；设备名可在
J-Link Commander 交互模式中用设备选择器查询，或查 SEGGER 官网 Supported Devices）。

## 3. 命令行与 CommandFile

### 3.1 命令行（flash.py 实际执行，cwd = release/）

```
JLink.exe -device <设备名> -if <SWD|JTAG> -speed 4000 -autoconnect 1 -CommandFile flash_cmd.jlink
```

| 参数 | 说明 |
|---|---|
| `-device` | J-Link 设备库命名（见 §2 映射表） |
| `-if` | 探针接口（缺省 SWD） |
| `-speed` | 4000 kHz（4MHz；连接失败时可降至 1000 排除信号完整性问题） |
| `-autoconnect 1` | 启动后自动连接目标 |
| `-CommandFile` | 命令脚本（release/flash_cmd.jlink，S9 每次按当前选项生成） |

### 3.2 CommandFile 命令序列（flash_cmd.jlink，V7.54 实测校准）

实际生成内容（hex 固件、全缺省选项；CommandFile **不支持 `#` 注释行**——逐行报
`Unknown command.`，脚本只含纯命令）：

```
connect
loadfile Template.hex
verifybin Template_verify.bin 0x08000000
r
g
qc
```

| 命令 | 说明 |
|---|---|
| `connect` | **必须首行**：建立探针与目标连接。实测无 connect 时首次 USB 连接会瞬态失败（`Connecting to J-Link via USB...FAILED`），到后续命令才重试成功；`-autoconnect 1` 在 CommandFile 模式下不代劳连接。connect 失败时后续命令也会自动重试 |
| `erase` | 全片擦除（破坏性，仅 `--chip-erase` 显式 opt-in 时生成；缺省 loadfile 按固件范围自动擦除） |
| `loadfile <hex>` | hex 自带地址与校验和，不传地址不易错位 |
| `loadfile <bin> <0x地址>` | bin 无地址信息，必须显式传（flash_base + flash_offset） |
| `verifybin <bin> <0x地址>` | 校验 flash 内容与 bin 逐字节比对（实测输出 `Verify successful.`）。V7.54 **无 `verify` 命令**（裸/带参均 `Unknown command.`）；hex 固件由 plan_flash 派生 `<固件名>_verify.bin` 校验镜像（间隙按 0xFF 比对），bin 固件用自身 |
| `r` / `g` | 复位 / 运行（烧录后复位运行是缺省行为；复位经 AIRCR.SYSRESETREQ，实测正常） |
| `qc` | 退出 Commander（**必须**，否则进程不结束导致 flash.py 超时） |

## 4. 日志特征（V7.54 实测校准，详见 flash_log_parse_rules.md）

- **成功特征**：`Downloading file [...]` + `J-Link: Flash download: Bank 0 @
  0x08000000: ... O.K.`（板上已有相同内容时该段为 `Skipped. Contents already
  match`，同样算成功）+ verify 开启时 `Verify successful.`
- **连接类失败**：`Connecting to J-Link via USB...FAILED: Cannot connect to
  J-Link.`（探针未插/驱动；connect 前置后后文重试出现 `...USB...O.K.` 时按瞬态
  不计失败）；`Connecting to target via SWD...FAILED`（目标板）
- **芯片类失败**：`Cannot connect to target`（供电/SWD 引脚/复位电路/读保护锁定）
- **固件类失败**：`Verify failed` / `Verification failed`（verifybin 内容不一致）
- **工具类失败**：`Unknown command.`（脚本命令拼写错/使用了 `#` 注释行/误用不存在的
  `verify` 命令）；`Unknown device` / `Device name is ambiguous`（设备名错）；
  `Device "X" is unknown to this version`（版本过旧，升级或装 JLinkDevices 支持包）

> J-Link Commander 对脚本内部分命令失败仍可能以退出码 0 结束——S9 的成功判定以
> **日志特征为主判据**，退出码仅是必要条件。

## 5. 连接失败排查顺序（Agent analyze 参考）

1. **探针**：J-Link USB 是否插入（设备管理器看 "SEGGER J-Link"）；`Connecting to
   J-Link via USB...FAILED` 即此层
2. **目标供电与接线**：VCC/ GND / SWDIO / SWCLK /（nRESET）；LED 亮否；排查线序
3. **接口/速度**：`--interface JTAG` 交叉验证；`-speed` 降 1000
4. **读保护**：STM32 选项字节 RDP 启用时 `Cannot connect to target`——**不自动解锁**
   （解锁全片擦除，属用户决策）；用户可自行用 STM32CubeProgramper/ST-Link Utility 解锁
5. **设备数据库**：设备名核对 §2；GD32 需较新版本或 JLinkDevices 包
