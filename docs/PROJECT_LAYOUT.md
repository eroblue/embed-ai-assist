# PROJECT_LAYOUT

## 一、简介

本文档定义 EmbedAIAssist 工作流生成代码时的标准项目布局，适用于基于 Cortex-M0/M3 的 32 位 MCU 及主流 8 位 MCU。

**文档位置**：
- 框架级默认：`embed-ai-assist/docs/PROJECT_LAYOUT.md`
- 项目级覆盖：`Examples/<project>/docs/PROJECT_LAYOUT.md`

**用途**：
1. 用户查阅：了解标准布局，手动创建 IDE 工程时有据可循。
2. agent 读取：按此布局创建目录骨架，用户在此基础上增删改。
3. 设计参考：理解每层职责和 Skill 归属。

---

## 二、读取优先级与自定义

### 2.1 读取优先级

agent 读取本布局文档时，按以下优先级：

1. `Examples/<project>/docs/PROJECT_LAYOUT.md`（项目级，最高优先级）
2. `embed-ai-assist/docs/PROJECT_LAYOUT.md`（框架级）
3. skill 内置默认骨架（最低优先级，兜底）

### 2.2 如何自定义

**单个项目定制**：

1. 拷贝框架级文件到 `Examples/<project>/docs/PROJECT_LAYOUT.md`。
2. 在拷贝副本中修改。
3. agent 会优先读取项目级文件。

**全局定制**：

如果希望所有项目都用同一份定制布局，直接修改框架级文件 `embed-ai-assist/docs/PROJECT_LAYOUT.md` 即可。

### 2.3 目录选择逻辑（agent 如何识别）

agent 选择目录布局时，读取两个维度的信息：

**维度一：平台类型（决定骨架）**

按以下优先级判断：

| 优先级 | 来源 | 说明 |
|---|---|---|
| 1 | `config.json` 的 `project.arch_family` | 用户显式指定，最高优先级 |
| 2 | S3 输出的 `chip_data.arch_family` | S3 解析芯片手册得到 |
| 3 | 从 `project.target` 前缀推断 | 见下方映射表 |
| 4 | 兜底 `cortex_m` | Cortex-M 是主流，覆盖面更广 |

型号前缀 → 平台类型映射表：

| 型号前缀 | 平台类型 |
|---|---|
| `STM32`、`GD32`、`AT32`、`APM32`、`HC32`、`N32` | `cortex_m` |
| `LPC`、`MK`、`MKL` | `cortex_m` |
| `STC8`、`STC15`、`STC89` | `mcu8` |
| `FMD`、`FT61`、`FT62`、`HOLTEK`、`HT` | `mcu8` |
| `CMS`、`SC8` | `mcu8` |

**维度二：架构深度（决定是否有 Port 层）**

读 `config.json` 的 `project.architecture`（`flat` / `layered` / `full`）。未配置时由 agent 推荐。

**组合规则**：

| 平台类型 | architecture | 使用布局 |
|---|---|---|
| `cortex_m` | `flat` | 32 位骨架，无 Port |
| `cortex_m` | `layered` | 32 位骨架，有 Port |
| `cortex_m` | `full` | 32 位骨架，有 Port + 协议层 |
| `mcu8` | `flat` | 8 位骨架，无 Port |
| `mcu8` | `layered` | 8 位骨架，有 Port |
| `mcu8` | `full` | 8 位骨架，有 Port + 协议层 |

---

## 三、32 位 Cortex-M0/M3 项目布局

### 3.1 完整目录结构

> 根目录（`App/`）代表目标工程目录（`config.json` 的 `project.build_target`，即 `App/` 或 `BootLoader/`）。

```text
App/
├── Core/                                  # 内核相关（CubeMX 生成 / 用户手动放）
│   ├── Inc/
│   │   ├── main.h
│   │   ├── xxx_it.h                       # 中断服务函数声明
│   │   └── xxx_hal_conf.h                 # HAL 库配置文件
│   └── Src/
│       ├── main.c                         # 主入口
│       ├── xxx_it.c                       # 中断服务函数
│       └── system_xxx.c                   # 系统初始化
│
├── Drivers/
│   ├── CMSIS/                             # ARM 内核支持包（用户手动放）
│   │   ├── Device/
│   │   │   └── <厂商>/<系列>/
│   │   │       ├── Include/
│   │   │       └── Source/Templates/arm/  # 启动文件
│   │   └── Include/
│   ├── HAL_Driver/                        # 厂商 HAL 库（用户手动放，去平台化命名）
│   │   ├── Inc/
│   │   └── Src/
│   ├── BSP/                               # 板级支持包
│   │   ├── Inc/
│   │   │   ├── board_init.h               # S5a：硬件初始化总入口
│   │   │   ├── clock_init.h               # S5a：时钟初始化
│   │   │   ├── gpio_init.h                # S5a：GPIO 初始化
│   │   │   ├── nvic_init.h                # S5a：NVIC 优先级配置
│   │   │   ├── uart_init.h                # S5a：串口初始化
│   │   │   ├── i2c_init.h                 # S5a：I2C 初始化
│   │   │   ├── spi_init.h                 # S5a：SPI 初始化
│   │   │   ├── adc_init.h                 # S5a：ADC 初始化
│   │   │   ├── rtos_hw_init.h             # S5a：RTOS 硬件初始化（如启用）
│   │   │   ├── power_init.h               # S5a：低功耗初始化（如启用）
│   │   │   ├── driver_xxx.h               # S5b：板载器件驱动
│   │   │   └── ...
│   │   └── Src/
│   │       ├── board_init.c               # S5a
│   │       ├── clock_init.c               # S5a
│   │       ├── gpio_init.c                # S5a
│   │       ├── nvic_init.c                # S5a
│   │       ├── uart_init.c                # S5a
│   │       ├── i2c_init.c                 # S5a
│   │       ├── spi_init.c                 # S5a
│   │       ├── adc_init.c                 # S5a
│   │       ├── rtos_hw_init.c             # S5a
│   │       ├── power_init.c               # S5a
│   │       ├── driver_xxx.c               # S5b
│   │       └── ...
│   └── Port/                              # Ports & Adapters 核心层
│       ├── Inc/                           # S5b：Port 接口（平台无关）
│       │   ├── uart_port.h
│       │   ├── i2c_port.h
│       │   ├── spi_port.h
│       │   ├── gpio_port.h
│       │   ├── adc_port.h
│       │   ├── osal.h                     # 如启用 RTOS
│       │   └── power_port.h               # 如启用低功耗
│       └── Src/                           # S5c：Port 实现（平台相关）
│           ├── port_impl_uart_<平台>.c
│           ├── port_impl_i2c_<平台>.c
│           ├── port_impl_spi_<平台>.c
│           ├── port_impl_gpio_<平台>.c
│           ├── port_impl_adc_<平台>.c
│           ├── port_impl_osal_<rtos>.c    # 如启用
│           └── port_impl_power_<平台>.c   # 如启用
│
├── Middlewares/                           # 第三方中间件（用户手动放）
│   └── Third_Party/
│       ├── FreeRTOS/
│       ├── FatFs/
│       └── lwIP/
│
├── App/                                   # 应用逻辑（S5b 生成）
│   ├── Inc/
│   │   ├── app.h
│   │   ├── protocol_xxx.h                 # 协议层
│   │   └── app_xxx.h                      # 业务模块
│   └── Src/
│       ├── app.c                          # 汇总初始化 + 主循环 / 任务创建
│       ├── protocol_xxx.c                 # 协议层
│       └── app_xxx.c                      # 业务逻辑
│
├── MDK-ARM/                               # Keil 工程目录（用户创建，也可用 IAR/、GCC/）
│   ├── xxx.uvprojx
│   ├── xxx.uvoptx
│   └── xxx/
│       ├── Objects/
│       └── Listings/
│
└── README.md
```

### 3.2 各目录职责

| 目录 | 职责 | 归属 | 平台相关 |
|---|---|---|---|
| `Core/` | 内核相关：主入口、系统时钟、中断向量表、HAL 配置 | CubeMX / 用户 | 是 |
| `Drivers/CMSIS/` | ARM 内核支持包、启动文件 | 用户 | 是 |
| `Drivers/HAL_Driver/` | 厂商 HAL 库 | 用户 | 是 |
| `Drivers/BSP/`（初始化） | 外设初始化：时钟、GPIO、UART 等 | S5a | 是 |
| `Drivers/BSP/`（器件驱动） | 板载器件业务逻辑：AT 协议、寄存器操作 | S5b | 否 |
| `Drivers/Port/Inc/` | Port 接口定义 | S5b | 否 |
| `Drivers/Port/Src/` | Port 实现 | S5c | 是 |
| `Middlewares/` | 第三方组件 | 用户 | 视组件 |
| `App/` | 应用逻辑、协议层、任务化 APP | S5b | 否 |
| `MDK-ARM/` | IDE 工程目录 | 用户创建，`ide_sync.py` 同步 | — |

### 3.3 分层调用关系

```text
App/                      (平台无关)
  ↓ 调 Port 接口
Drivers/Port/Inc/         (平台无关)
  ↓ 由 Port 实现翻译
Drivers/Port/Src/         (平台相关)
  ↓ 调 HAL
Drivers/HAL_Driver/       (厂商提供)
  ↓ 调寄存器
芯片

Drivers/BSP/
  ├── 外设初始化 → 直接调 HAL
  └── 器件驱动 → 调 Port 接口
```

应用层往下看，只能看到 Port 接口。

---

## 四、8 位 MCU 项目布局

### 4.1 完整目录结构

> 根目录（`App/`）代表目标工程目录（`config.json` 的 `project.build_target`，即 `App/` 或 `BootLoader/`），下同。

```text
App/
├── App/                       # S5b：应用逻辑 + 协议层
│   ├── Inc/
│   └── Src/
├── Drivers/
│   ├── BSP/                   # S5a 初始化 + S5b 器件驱动
│   │   ├── Inc/
│   │   └── Src/
│   └── Port/                  # Port 抽象
│       ├── Inc/               # S5b：Port 接口
│       └── Src/               # S5c：Port 实现
└── Project/                   # IDE 工程目录（用户创建）
    ├── Objects/
    └── Listings/
```

### 4.2 各目录职责

| 目录 | 职责 | 归属 | 平台相关 |
|---|---|---|---|
| `Drivers/BSP/`（初始化） | 外设初始化 | S5a | 是 |
| `Drivers/BSP/`（器件驱动） | 板载器件业务逻辑 | S5b | 否 |
| `Drivers/Port/Inc/` | Port 接口定义 | S5b | 否 |
| `Drivers/Port/Src/` | Port 实现 | S5c | 是 |
| `App/` | 应用逻辑、协议层 | S5b | 否 |
| `Project/` | IDE 工程目录 | 用户创建，`ide_sync.py` 同步 | — |

### 4.3 与 32 位布局的对应关系

| 32 位目录 | 8 位目录 | 说明 |
|---|---|---|
| `Core/` | 无 | 8 位无 Cortex 内核概念 |
| `Drivers/CMSIS/` | 无 | CMSIS 是 ARM 专属 |
| `Drivers/HAL_Driver/` | 无 | 8 位通常直接操作寄存器或厂商宏 |
| `Drivers/BSP/` | `Drivers/BSP/` | 一致 |
| `Drivers/Port/` | `Drivers/Port/` | 一致 |
| `App/` | `App/` | 一致 |
| `Middlewares/` | 可选 | 大多数 8 位项目不跑 RTOS |
| `MDK-ARM/` | `Project/` | 8 位 IDE 多样，统一命名 |

**核心三层（BSP / Port / App）保持一致，32 位与 8 位的工作流是同一套。**

### 4.4 8 位下的两种架构

**layered 模式**（较强 8 位 MCU，如 STC8H、辉芒微部分型号）：

```text
App/
├── App/
│   ├── Inc/
│   └── Src/
├── Drivers/
│   ├── BSP/
│   │   ├── Inc/
│   │   └── Src/
│   └── Port/
│       ├── Inc/               # S5b：Port 接口
│       └── Src/               # S5c：Port 实现
└── Project/                   # IDE 工程目录（用户创建）
```

**flat 模式**（简单 8 位 MCU，资源极少）：

```text
App/
├── App/                       # S5b：所有应用逻辑混合放
│   ├── Inc/
│   └── Src/
├── Drivers/
│   └── BSP/                   # S5a 初始化 + S5b 器件驱动 + 应用混合
│       ├── Inc/
│       └── Src/
└── Project/                   # IDE 工程目录（用户创建）
```

`flat` 模式下不生成 `Drivers/Port/`，S5c 跳过。

---

## 五、为什么这样分目录

### 5.1 Core/ —— 只放内核相关

`Core/` 的语义是**芯片内核层面**的东西：主入口、系统时钟、中断向量表、HAL 配置。这些文件与芯片内核强绑定，换 MCU 时整个换掉，属于 CubeMX / 用户管理范畴，S5 不生成。

### 5.2 Drivers/CMSIS/ 和 Drivers/HAL_Driver/ —— 平台资料

ARM 官方内核支持包和厂商 HAL 库。**平台相关，但不属于任何 Skill 生成**，由用户从 SDK 复制。命名去平台化（`HAL_Driver` 而非 `STM32F1xx_HAL_Driver`），使目录骨架能跨平台复用。

### 5.3 Drivers/BSP/ —— 板级支持包

BSP 是**这块具体板子**的支持代码，包含：

- **外设初始化**（S5a）：把芯片外设配置好。
- **板载器件驱动**（S5b）：跟板子上挂的 WiFi 模块、传感器通信。

两类都属于"这块板子"，放一起符合 BSP 传统定义。

### 5.4 Drivers/Port/ —— Ports & Adapters 核心

- `Inc/`：Port 接口（平台无关），由 S5b 定义。
- `Src/`：Port 实现（平台相关），由 S5c 生成。

**接口和实现放同一父目录**，因为它们成对出现，改一个通常要同步改另一个。

**关键价值**：换 MCU 时，`Inc/` 不动，只重写 `Src/` 下的实现。应用层、驱动层完全不受影响。

### 5.5 Middlewares/ —— 第三方中间件

FreeRTOS、FatFs、lwIP 等放这里，与厂商 SDK 和业务逻辑分开。

### 5.6 App/ —— 应用逻辑

业务逻辑、协议层、任务化 APP，**全部平台无关**，由 S5b 生成。不 include 任何 HAL 头文件，也不 include 任何 RTOS 头文件。所有底层调用都通过 `Drivers/Port/Inc/` 下的接口。

### 5.7 MDK-ARM/ 或 Project/ —— IDE 工程目录

IDE 工程文件和编译输出集中在这里，与源码分离。用户手动创建，`ide_sync.py` 负责把新文件同步进来。

**命名差异**：
- 32 位常见 IDE 固定（Keil、IAR），用 `MDK-ARM/`、`IAR/`。
- 8 位 IDE 多样（SDCC、IAR 8051、Keil C51、厂商 IDE），统一用 `Project/`。

---

## 六、Skill 归属速查

| 目录 | 32 位 | 8 位 | Skill | 平台相关 |
|---|---|---|---|---|
| 内核相关 | `Core/` | 无 | CubeMX / 用户 | 是 |
| CMSIS | `Drivers/CMSIS/` | 无 | 用户 | 是 |
| HAL 库 | `Drivers/HAL_Driver/` | 无 | 用户 | 是 |
| 外设初始化 | `Drivers/BSP/` | `Drivers/BSP/` | S5a | 是 |
| 器件驱动 | `Drivers/BSP/` | `Drivers/BSP/` | S5b | 否 |
| Port 接口 | `Drivers/Port/Inc/` | `Drivers/Port/Inc/` | S5b | 否 |
| Port 实现 | `Drivers/Port/Src/` | `Drivers/Port/Src/` | S5c | 是 |
| 中间件 | `Middlewares/` | 可选 | 用户 | 视组件 |
| 应用逻辑 | `App/` | `App/` | S5b | 否 |
| IDE 工程 | `MDK-ARM/` | `Project/` | 用户创建，`ide_sync.py` 同步 | — |

---

## 七、如何创建工程

### 7.1 推荐流程

1. **用户手动创建基础工程**：
   - 32 位：用 STM32CubeMX / GD32 配置工具生成基础工程，或在 Keil / IAR 中新建空工程。
   - 8 位：在厂商 IDE（Keil C51、SDCC、IAR 8051）中新建空工程。
2. **用户手动放置平台资料**：
   - 从 SDK 复制 HAL 库到 `Drivers/HAL_Driver/`。
   - 从 SDK 复制 CMSIS 和启动文件到 `Drivers/CMSIS/`（仅 32 位）。
3. **agent 按本文档创建目录骨架**：
   - 扫描缺失的目录，创建空目录。
   - 不创建任何文件（`README.md` 可选）。
   - 不覆盖已存在的文件。
4. **S5a / S5b / S5c 生成代码**，落到对应目录。
5. **`ide_sync.py` 同步**：把布局中 Skill 产物目录（`layout_plan.scan_roots`，如 `Drivers/BSP/Src/`、`App/Src/`）下的新增文件加入 IDE 工程。

### 7.2 agent 行为约束

- **只创建目录，不创建文件**（`README.md` 例外）。
- **目录已存在则跳过**，不覆盖用户内容。
- **不修改用户已有的任何文件**。
- **不自动创建 IDE 工程文件**（`.uvprojx`、`.ewp` 等），由用户手动创建。

### 7.3 机器解析约定（layout_resolver.py 的读取契约）

本文档的目录树与注释是机器可读的（`skills/_shared/scripts/layout_resolver.py` 解析为
LayoutPlan：目录骨架 / Skill 产物目录 / IDE 工程目录 / 扫描根），修改本文档即全局生效，
无需改脚本。约定如下：

- **节点名**：带 `/` 后缀 = 目录；无 = 文件（不建骨架，注释仍参与归属推导）。
- **占位符**：目录名含 `<...>` 或为 `xxx` 时，该节点及其子树跳过（不建骨架、不参与归属）；
  文件占位符（如 `xxx_it.h`、`driver_xxx.h`）正常参与注释归属。
- **归属注释**：注释含 `S5a` / `S5b` / `S5c` → Skill 归属；含 `工程目录` → IDE 工程目录
  （注释中"也可用 `IAR/`、`GCC/`"式的备选目录名一并收入 IDE 目录候选）。
- **归属传播**：目录级注释向子树中所有以 `Src/` 或 `Inc/` 结尾的目录传播；
  文件级注释归属其最近的 `Src/Inc` 祖先目录；Skill 产物目录必须以 `Src/` 或 `Inc/` 结尾。
- **flat 组合规则**：`architecture = flat` 时剔除 `Port` 层目录与 S5c 归属（见 2.3 / 4.4）。
- **arch_family 判定**：按 2.3 节四级优先级；型号前缀映射表从 2.3 节表格解析
  （表格第二列为 `cortex_m` / `mcu8` 的行）。

---

## 八、覆盖范围

### 8.1 32 位布局适用平台

- STM32 全系（F0/F1/F4/L4/G0/G4 等）
- GD32 全系
- 国民技术、极海、华大、中微等国产替代
- NXP LPC / Kinetis
- 其他基于 Cortex-M0/M3 的厂商

### 8.2 8 位布局适用平台

- STC 全系（STC8、STC15、STC89 等）
- 辉芒微（FMD）
- 和泰（Holtek）
- 中微（CMS）
- 其他主流 8 位 MCU

### 8.3 需要单独适配的平台

- Nordic nRF52：SDK 有自己的布局。
- ESP32：使用 ESP-IDF 布局，不走本套。
- RISC-V 平台：待后续扩展。

---

## 九、扩展新平台

如需支持新平台（如 RISC-V、其他架构），在本文档中新增章节，说明：

- 目录结构
- 与现有布局的对应关系
- 平台资料放置方式
- Skill 归属

保持核心三层（BSP / Port / App）一致，是跨平台一致性的基础。