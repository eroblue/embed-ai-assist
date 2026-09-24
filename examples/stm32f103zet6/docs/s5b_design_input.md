# S5b 设计输入文件

**项目**：SmartEnvGuard 智能环境监测仪
**平台**：正点原子战舰 STM32F103ZET6 开发板
**用途**：S5b 的 prepare 阶段读取本文件，提取技术实现细节，生成功能模块清单和流程图。

---

## 硬件资源

| 外设 | 接口 | 用途 |
|---|---|---|
| DHT11 温湿度传感器 | 单总线（PG11） | 采集温度和湿度 |
| 光敏传感器 | ADC1_IN1（PA1） | 采集光照强度 |
| TFT_LCD 显示屏（240x320，ILI9341 类，以实际模块为准） | FSMC 16 位并口（NE4：PG12=CS，PG0=RS，背光 PB0） | 本地显示 |
| LED0 | GPIO 输出（PB5） | 模拟执行器（继电器/风扇） |
| LED1 | GPIO 输出（PE5） | 运行状态指示 |
| 蜂鸣器 | GPIO 输出（PB8） | 告警提示 |
| KEY0 | GPIO 输入（PE4，上拉） | 模式切换 |
| KEY1 | GPIO 输入（PE3，上拉） | 手动开关 |
| WK_UP | GPIO 输入（PA0，下拉） | 静音切换 |
| USART1 | PA9=TX，PA10=RX，115200-8N1 | 上位机上报 |

---

## 架构配置

- **架构**：`layered`（有 Port 层，不强制拆分协议层）
- **RTOS**：不使用
- **低功耗**：不启用
- **主循环**：10ms 软定时器 + 状态机轮询

---

## 功能规格（技术要求）

### 环境采集
- 周期 2 秒读取 DHT11 温湿度、光敏光照。
- DHT11 使用单总线协议，两次读取间隔至少 1 秒。
- 光照通过 ADC1_IN1 读取，换算公式 `light = (adc_value * 100) / 4095`。
- DHT11 读取失败：跳过本次，保留上次值，失败计数 +1，连续 5 次失败触发告警。
- 采集数据存入共享结构体 `env_data_t { int temp; int humi; int light; }`。

### 本地显示
- 使用 FSMC 并口 TFT_LCD，竖屏 4 行文本布局（信息项与行序沿用）：
  - 行 1：模式（AUTO / MANUAL / MUTED）
  - 行 2：温度 xx°C   湿度 xx%
  - 行 3：光照 xx%
  - 行 4：告警（NORMAL / HIGH_TEMP / LOW_TEMP / LOW_LIGHT / SENSOR ERR）
- 大字体文本（如 16x32 点阵），前景白色、背景黑色（RGB565）。
- 告警激活时，对应行 1Hz 闪烁。
- 分层约定：FSMC 总线/控制线/背光由 S5a `fsmc_lcd_init` 保证；LCD 初始化序列（厂商寄存器、Gamma、显示方向）与字符渲染由 S5b `driver_lcd` 承载。

### 按键交互
- KEY0 / KEY1 / WK_UP 通过 GPIO 输入读取。
- 软件去抖 50ms，短按在释放时刻响应。

### 自动控制
- 控制逻辑在 AUTO 模式生效。
- LED0 由自动逻辑控制：高温开、低温关、其他保持。
- 蜂鸣器：有告警时 1s 响 1s 停，MUTED 模式下不响。

### 串口上报
- USART1，115200-8N1，周期 5 秒。
- JSON 帧格式：
  ```
  {"temp":25,"humi":60,"light":75,"mode":"AUTO","alarm":"NORMAL"}\r\n
  ```
- 上报失败重试 2 次，连续 3 次失败记录日志。

---

## 状态机

### 工作模式
- 状态列表：AUTO、MANUAL、MUTED
- 初始状态：AUTO
- 迁移：
  - AUTO → MANUAL : KEY0 短按
  - MANUAL → AUTO : KEY0 短按
  - AUTO → MUTED : WK_UP 短按
  - MANUAL → MUTED : WK_UP 短按
  - MUTED → AUTO : WK_UP 短按

### 告警状态
- 状态列表：NORMAL、HIGH_TEMP、LOW_TEMP、LOW_LIGHT、SENSOR_FAULT
- 初始状态：NORMAL
- 优先级：HIGH_TEMP > LOW_TEMP > LOW_LIGHT > SENSOR_FAULT
- 多告警同时满足时，只取优先级最高的。

### 执行器状态
- LED0：开 / 关
- 蜂鸣器：响 / 停

---

## 时序

| 项目 | 周期 / 时间 |
|---|---|
| 主循环 | 10ms |
| DHT11 采集 | 2s |
| 光照采集 | 2s |
| LCD 刷新 | 200ms |
| 串口上报 | 5s |
| 按键去抖 | 50ms |
| 蜂鸣器告警 | 1s 响 / 1s 停 |
| LED1 心跳 | 1Hz（500ms 亮 / 500ms 灭） |
| LCD 告警闪烁 | 1Hz |

---

## 错误处理

### 采集失败
- DHT11 读取失败：跳过本次，保留上次值，失败计数 +1。
- 连续 5 次失败：触发 SENSOR_FAULT 告警，LCD 显示 "SENSOR ERR"。
- 一次成功后清零失败计数。

### 串口上报失败
- 发送失败重试 2 次。
- 连续 3 次上报失败：记录日志，LED1 快闪 3 次，继续工作。

### 初始化失败
- LCD 初始化失败：LED1 慢闪，跳过显示，其他功能继续。
- USART1 初始化失败：LED1 快闪，跳过上报，其他功能继续。

---

## 模块清单（S5b 预计拆分）

| 模块 | 类型 | 依赖 |
|---|---|---|
| `env_sensor` | 顺序流程 | gpio_port, adc_port |
| `lcd_display` | 顺序流程 | par_port, timer_port |
| `key_handler` | 状态机 | gpio_port |
| `auto_control` | 状态机 | gpio_port |
| `uart_report` | 时序图 | uart_port |

---

## 用户备注

- 本文件用于验证 S5b 流程图中间层，规模控制在 5 个模块。
- 允许 Agent 对未明确的部分推荐最优方案，输出 `recommendations.json`。
- 首次跑通后，会基于实际结果优化设计输入。