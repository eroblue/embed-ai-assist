# Port 接口设计原则（S5b Agent 生成 Port 头文件的规范）

> 适用范围：`Drivers/Port/Inc/` 下全部 Port 头文件（`uart_port.h` 等）与
> `power_port.h`。flat 架构不生成 Port 层，本文档不适用。
> 模板基座：`assets/port_templates/`（挑选 → 裁剪 → 扩展，不是机械填充）。

## 一、核心原则：从应用需求出发，不从硬件外设出发

- 接口表达的是**应用想做什么**（"发一帧 AT 命令"），不是硬件怎么做的
  （"往 USART5 数据寄存器写字节"）。
- 先写 APP/Driver 代码怎么调用顺手，再定 Port 接口；顺序反了就会出现
  "HAL 换皮"式伪抽象。
- 按应用需求决定拆分粒度：单外设多场景（UART 同时接 WiFi 与调试口）时，
  用逻辑实例区分（`UART_PORT_WIFI` / `UART_PORT_DEBUG`），不要按硬件实例拆。

## 二、类型规范（平台无关的硬约束）

1. **只用 `<stdint.h>` 基本类型**：`uint8_t/int32_t/uint16_t...`；
   禁止 `unsigned int`、厂商类型（`uint32_t` 别名如 `FlagStatus`）、结构体透传厂商配置。
2. **不透明句柄**：实例用枚举 ID（`typedef enum { UART_PORT_WIFI = 0, UART_PORT_COUNT } uart_port_id_t;`），
   不暴露任何寄存器/配置结构体内部。
3. **配置用自家结构体**：需要参数的接口定义本层配置结构
   （`uart_port_cfg_t { baudrate, data_bits, parity, stop_bits }`），
   字段只含应用语义，不含硬件语义（无"时钟分频系数"）。
4. **禁止 include**：HAL 头、RTOS 头、`app*.h`、`driver_*.h`（Port 是最底层，
   只能依赖 C 标准库与同层 Port 头）。
5. **错误码统一**：`PORT_OK=0 / PORT_ERR_PARAM / PORT_ERR_STATE / PORT_ERR_TIMEOUT / PORT_ERR_BUSY`
   （各 Port 头自定义同名枚举，值域不冲突时直接复用 `port_common` 风格前缀注释说明）。

## 三、生命周期与命名

统一生命周期：`init → (open → 使用 → close)* → deinit`。

| 阶段 | 命名 | 语义 |
|---|---|---|
| 初始化 | `<peri>_port_init(id, cfg)` | 绑定实例与配置（实现层调 S5a 初始化成果） |
| 打开 | `<peri>_port_open(id)` | 可选；申请缓冲/使能中断 |
| 使用 | `<peri>_port_read/write/ioctl...` | 数据面 |
| 关闭 | `<peri>_port_close(id)` | 与 open 配对 |
| 反初始化 | `<peri>_port_deinit(id)` | 释放全部资源 |

命名规则：`<peri>_port_<动词>`（动词小写下划线）；回调类型 `<peri>_port_<事件>_cb_t`；
回调注册 `<peri>_port_set_<事件>_cb`。

## 四、回调与中断上下文（必须显式约定）

- 每个回调在头文件注释中**明确标注调用上下文**：`ISR`（中断直接调用）/
  `task`（投递到任务上下文）——S5c 实现与 APP 注册都要遵守。
- ISR 上下文回调内禁止阻塞、禁止调用非 ISR 安全接口（含 OSAL 非
  `FromISR` 系接口）；建议 ISR 回调只置事件/拷贝数据，处理放任务侧。
- 回调带 `void *user_data`（注册时传入，调用时透传），避免全局变量耦合。

## 五、DMA 与缓冲（隐藏在实现内）

- DMA 是 UART/SPI 等的**实现细节**，接口层不得出现 `dma` 字样、DMA 通道号、
  缓冲对齐要求（对齐需求由 S5c 实现自行处理或在 manifest notes 中说明）。
- 缓冲归属写进头文件注释：`write` 语义（同步拷贝 / 引用发送），
  `read` 语义（返回长度 / 缓冲注册制）。模板默认：write 同步拷贝、
  read 非阻塞返回可用长度，回调驱动接收。

## 六、逻辑实例与 manifest 映射（数据与代码分离）

- Port 头文件中只出现**逻辑实例名**（应用语义，如 `UART_PORT_WIFI`）；
- 逻辑名 → 硬件实例（`USART5`）/引脚的映射**只写进
  `outputs/s5b/port_interface_manifest.json`** 的 `logical_instances`
  （`hw_instance` + `hw_source`），S5c 据此实现；
- S4 硬件事实缺失时 `hw_instance: null`（S5c 按 hardware_capabilities 匹配），
  代码不变——这是"换平台 S5b 产物哈希不变"的关键机制。

## 七、Power 接口（power_port.h）

- **不预先固化接口名**：用户已有方案（设计输入/已有项目）严格按用户方案；
  否则按典型集裁剪推荐：`power_enter_sleep_before()` / `power_enter_sleep()` /
  `power_wakeup_after_sleep()` / `power_clock_compensate()`，
  输出 `outputs/s5b/recommendations.json` 供用户确认。
- 接口语义从 APP 视角描述（"睡前保存什么/醒后恢复什么"），
  不出现时钟寄存器/停机模式名（实现细节归 S5c）。
- 每个接口标注可调用上下文（任务/ISR）与时钟补偿前置条件。

## 八、模板使用流程（Agent 操作）

1. 从 `assets/port_templates/` 挑选对应外设模板（uart/i2c/spi/gpio/adc/timer）；
2. **裁剪**：删除应用用不到的接口（如不用 DMA 相关回调、不用 ioctl）；
3. **扩展**：应用特有需求（如 UART 帧协议裁剪回调）加在本层语义上；
4. 逻辑实例枚举按应用需求命名（见第六节）；
5. 同步登记 `port_interface_manifest.json`（每个接口一条 `interfaces` 记录，
   签名/ISR 安全/回调上下文完整）；
6. 校验：不含厂商名/引脚号/网络名；include 只有标准库与 Port 层。
