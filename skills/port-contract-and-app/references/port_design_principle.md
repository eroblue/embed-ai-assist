# Port 接口设计原则与语义约定（S5b 生成 / S5c 实现共同遵守）

> 本文件是 S5b Agent 定义 Port 接口时的**强制语义约定**，S5c 实现 Port 时遵守
> 同一语义。语义不约定的接口，同一 Port 在两个平台会被实现出不同行为——
> 这正是 Port 层要消灭的问题。违反任一条 → validate.py 校验失败或人工评审打回。

## 1. 接口形态

- 按应用能力拆分（`uart_port.h` / `adc_port.h` / ...），不按 MCU 外设实例拆分
- 只使用基本类型（`uint8_t`/`uint16_t`/`uint32_t`/`size_t`/`bool`）和不透明
  句柄（如 `port_uart_t *`）；句柄内部结构由实现方定义，APP 不得解引用
- 生命周期统一：`init → open → （read/write/ioctl/...）→ close → deinit`
- 一对外设一对 `.h`；不把所有接口塞进一个 `port.h`

## 2. 统一错误码 port_err_t（所有接口的返回值）

```c
typedef enum {
    PORT_OK = 0,
    PORT_ERR_TIMEOUT,    /* 超时 */
    PORT_ERR_BUSY,       /* 忙（如上一笔 DMA 未完成） */
    PORT_ERR_INVAL,      /* 参数非法 */
    PORT_ERR_NO_MEM,    /* 缓冲不足 */
    PORT_ERR_NOT_OPEN,   /* 未 open 即使用 */
    PORT_ERR_HW          /* 硬件错误（含总线错误、过载） */
} port_err_t;
```

- **不得自造第二套错误码**；协议层/驱动层内部错误映射到上述七类
- 接口语义与 S5a `hardware_capabilities.json` 的能力约束冲突时（如波特率
  不支持），报 `PORT_ERR_INVAL`/`PORT_ERR_HW`，不静默取近似值

## 3. 阻塞与超时语义

- 同步接口一律带 `uint32_t timeout_ms` 参数：
  `0` = 不等待（未就绪立即返回 `PORT_ERR_BUSY`）；
  `PORT_WAIT_FOREVER`（`0xFFFFFFFF`）= 永久等待
- 中断/DMA 驱动的外设（UART 等）：非就绪数据由实现内部缓冲承接，接口层
  统一呈现**阻塞语义**，APP 不感知 ISR/DMA 细节
- 超时返回 `PORT_ERR_TIMEOUT`，**不得死等**（裸机下不得关中断死等）

## 4. 线程安全声明

- **默认**：同一句柄的所有接口可从多个任务并发调用，线程安全由 S5c 实现
  内部保证（RTOS 下用互斥锁/信号量；S5c 职责）
- **例外**接口（如连续采样流式读取）必须在头文件注释中显式标注
  "非线程安全"，并说明调用约束（如"仅单一任务可调用"）
- 裸机（`rtos == "none"`）下线程安全自动退化为重入安全（无抢占并发）

## 5. 回调规范

- 回调一律**显式注册**（`xxx_register_cb(handle, cb, user_data)`），
  不用 weak symbol（weak 在多实例/静态链接下行为不可控）
- 回调注释**必须标注**"ISR 上下文可调用 / 不可调用"；可 ISR 调用的回调，
  其实现不得做耗时操作（推荐置标志/入队）
- 实现方（S5c）在 ISR 内调用回调前**必须判空**；未注册时清中断标志直接返回

## 6. 缓冲与 DMA 归属

- 接收缓冲/ring buffer 归 **Port 实现内部**，APP 经 `read` 接口取数，
  不向 APP 暴露缓冲结构
- DMA 对 APP **完全隐藏**：不暴露 DMA 通道/句柄/完成标志等概念，
  收发完成由接口返回值或回调呈现

## 7. 接口清单（manifest）一致性

- `port_interface_manifest.json` 含 `version` 字段（初始 `"1.0"`），供 S5c
  做契约版本对齐；接口语义变更（超时语义/线程安全声明变化）必须递增
  minor 版本
- manifest 中每个函数的 name/return/args 必须与 `.h` 实际声明**一字不差**
- 用户修改过的 Port 头（skip-if-modified 跳过重生成）→ Agent 读其现状
  更新 manifest，保证两者不漂移；S5c 以 manifest 为准实现
