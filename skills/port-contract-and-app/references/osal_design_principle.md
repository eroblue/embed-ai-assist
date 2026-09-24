# OSAL 接口设计原则（S5b Agent 生成 osal.h 的规范）

> 适用条件：`project.rtos != "none"` 且 `architecture != "flat"`。
> 单文件 `Drivers/Port/Inc/osal.h`，不拆分（实际项目用到的 RTOS 接口通常不超过 5 个，
> 按应用需求裁剪模板 `assets/port_templates/osal.h.tpl`）。
> 裸机（rtos=none）不生成 osal.h；flat 架构不生成（如配置了 RTOS，prepare 会在
> 任务书提示改用 layered）。

## 一、硬约束

- **不出现任何 RTOS API 名**：`FreeRTOS.h`、`xTaskCreate`、`osThreadNew`、
  `rt_thread_create` 等一律禁止（这是 S5c 翻译层的事）。
- 只用 `<stdint.h>` 基本类型与不透明句柄（任务句柄/队列句柄用本层 typedef）。
- 统一错误码：`OSAL_OK=0 / OSAL_ERR_PARAM / OSAL_ERR_TIMEOUT / OSAL_ERR_RESOURCE`。
- 每个接口标注：**是否可在 ISR 调用**（ISR 版本独立命名 `*_from_isr`，
  不做"自动判断上下文"的魔法）。

## 二、接口清单（按需裁剪，够用即可）

| 类别 | 典型接口 | 说明 |
|---|---|---|
| 任务 | `osal_task_create(task_func, name, stack_size, prio, arg, *handle)` | 栈大小单位统一为字节（S5c 翻译成 RTOS 单位） |
| 任务 | `osal_task_delay(ms)` | 毫秒统一 |
| 队列 | `osal_queue_create(item_size, queue_len, *handle)` | 按值拷贝语义 |
| 队列 | `osal_queue_send(handle, item, timeout_ms)` / `osal_queue_send_from_isr` | |
| 队列 | `osal_queue_recv(handle, item, timeout_ms)` | timeout=0 非阻塞，OSAL_WAIT_FOREVER 永久 |
| 互斥 | `osal_mutex_create` / `osal_mutex_lock` / `osal_mutex_unlock` | 递归性在注释中声明（默认非递归） |
| 信号量 | `osal_sem_create(init, max)` / `osal_sem_take` / `osal_sem_give[_from_isr]` | 二值/计数统一 |
| 事件 | `osal_event_create` / `osal_event_wait(set, wait_all, timeout)` / `osal_event_set[_from_isr]` | 位事件 |
| 时间 | `osal_tick_ms()` | 系统毫秒节拍 |
| 临界区 | `osal_critical_enter()` / `osal_critical_exit()` | 嵌套语义注释声明（默认支持嵌套） |

裁剪原则：从任务书的功能模块清单出发——只有轮询无任务间通信 → 只留任务+延时；
有 ISR→任务数据流 → 队列 + `*_from_isr`；共享资源 → 互斥。**不要全量照抄模板**。

## 三、任务化 APP 的对接（app_<功能>_task.c）

- 任务入口函数 `void app_<功能>_task(void *arg)`（OSAL 签名，不出现 RTOS 类型）；
- 任务创建统一在 `app.c` 的 `app_init()` 中（顶层连接逻辑），不在模块内自建；
- 优先级从设计输入"任务划分"段取；未指定时 Agent 推荐并在
  `recommendations.json` 说明理由（周期短/实时高的优先级高）；
- 栈大小建议：最小 256 字节 + 局部缓冲，宁大勿小（注释标注可调）。

## 四、ISR 安全速查（生成 APP/driver 代码时对照）

| 场景 | 正确做法 |
|---|---|
| ISR 内向任务发数据 | `osal_queue_send_from_isr` / `osal_event_set_from_isr` |
| ISR 内取时间/延时 | 禁止 `osal_task_delay`（ISR 不可阻塞） |
| ISR 内打印 | 禁止 printf（除非确认重入安全），置标志位任务侧打印 |
| 临界区 | 任务侧 `osal_critical_enter/exit` 成对；保持极短 |

## 五、manifest 登记

osal.h 生成后，在 `port_interface_manifest.json` 登记：
`kind: "osal"` 的 header 条目，`interfaces` 逐条列出（含 `isr_safe` 字段），
`logical_instances` 为空数组。S5c 以此为唯一实现依据。
