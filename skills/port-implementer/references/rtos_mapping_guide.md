# RTOS 映射指南（RTOS API ↔ OSAL 接口）

> rtos != none 时 S5c 生成 `port_impl_osal_<rtos>.c`（如
> `port_impl_osal_freertos.c`）。OSAL 接口头 `osal.h` 由 S5b 产出（只读），
> 本文件实现其全部接口。接口语义按 S5b
> `references/osal_design_principle.md` 同一约定。

## 1. 文件命名与总则

- `<rtos>` token：全小写、连字符/下划线/空格去除——`FreeRTOS→freertos`、
  `RT-Thread→rtthread`、`Zephyr→zephyr`（prepare 任务书已给出确切文件名）
- 错误码映射：OSAL 统一错误码 ← RTOS 返回值（pdPASS→OK；非阻塞获取失败
  →TIMEOUT/AGAIN；参数错→PARAM）
- **ISR 内必须用 FromISR 变体**（FreeRTOS）或中断安全 API（Zephyr
  `k_*_from_isr`）；OSAL 若提供 isr 后缀接口，透传对应变体
- 优先级/栈大小等参数从 osal.h 的入参映射，不硬编码

## 2. FreeRTOS 映射表

| OSAL 接口（典型） | FreeRTOS API | 备注 |
|---|---|---|
| osal_task_create | `xTaskCreate()` | 返回句柄；栈深度按入参 |
| osal_task_delay | `vTaskDelay()`（ms→ticks：`pdMS_TO_TICKS`） | tick 率非 1kHz 时必须换算 |
| osal_queue_create/send/receive | `xQueueCreate` / `xQueueSend` / `xQueueReceive` | receive 超时 ms→ticks；`xQueueSendFromISR` 供 ISR 场景 |
| osal_mutex_lock/unlock | `xSemaphoreTake` / `xSemaphoreGive`（`xSemaphoreCreateMutex`） | ISR 内禁止操作互斥锁（FreeRTOS 约束），返回 ERR_STATE |
| osal_sem_give/take | `xSemaphoreGive` / `xSemaphoreTake`（`xSemaphoreCreateBinary`） | ISR 用 `xSemaphoreGiveFromISR` + `portYIELD_FROM_ISR` |
| osal_tick_get | `xTaskGetTickCount()` | |
| osal_enter_critical / exit | `taskENTER_CRITICAL()` / `taskEXIT_CRITICAL()` | 调度器级临界区 |

## 3. RT-Thread 映射表

| OSAL 接口（典型） | RT-Thread API | 备注 |
|---|---|---|
| osal_task_create | `rt_thread_create` + `rt_thread_startup` | 动态创建（框架约束禁 malloc 时用 `rt_thread_init` 静态版，栈空间由静态数组提供） |
| osal_task_delay | `rt_thread_mdelay()` | |
| osal_queue_* | `rt_mq_create/send/recv` 或 `rt_mb_*` | 超时 ms 直传 |
| osal_mutex_* | `rt_mutex_take` / `rt_mutex_release`（`rt_mutex_create`） | |
| osal_sem_* | `rt_sem_release` / `rt_sem_take`（`rt_sem_create`） | ISR 中 `rt_sem_release` 天然安全 |
| osal_tick_get | `rt_tick_get()` | |
| osal_enter/exit_critical | `rt_enter_critical()` / `rt_exit_critical()` 或调度器锁 | |

## 4. Zephyr 映射表

| OSAL 接口（典型） | Zephyr API | 备注 |
|---|---|---|
| osal_task_create | `k_thread_create`（k_stack 静态栈） | 或 CONFIG 期静态线程，动态创建需栈对象 |
| osal_task_delay | `k_sleep(K_MSEC(ms))` | |
| osal_queue_* | `k_msgq_put` / `k_msgq_get`（`k_msgq_init` 静态缓冲） | |
| osal_mutex_* | `k_mutex_lock` / `k_mutex_unlock`（`k_mutex_init`） | |
| osal_sem_* | `k_sem_take` / `k_sem_give`（`k_sem_init`） | ISR 中 `k_sem_give` 安全 |
| osal_tick_get | `k_uptime_get()` / `k_cycle_get()` | |
| osal_enter/exit_critical | `k_sched_lock()` / `k_sched_unlock()` | |

## 5. RTOS 硬件初始化边界

- RTOS 内核的 SysTick/PendSV 初始化由 `s5a.rtos_hw_init`（S5a 产物）与
  RTOS 启动流程承担；OSAL 实现不碰中断向量与内核时钟配置。
- 应用入口如何启动调度器（`vTaskStartScheduler` / `rt_system_scheduler_start`）
  属于 S5b 生成的 main/app.c 职责，不在 OSAL 内。

## 6. 常见坑

- FreeRTOS `configTICK_RATE_HZ != 1000` 时所有 ms 入参必须 `pdMS_TO_TICKS`；
- `xQueueSendFromISR` 的 `pxHigherPriorityTaskWoken` 置真后须 `portYIELD_FROM_ISR`；
- RT-Thread 互斥锁可嵌套、信号量不可——映射时按 osal.h 声明的语义对号入座；
- Zephyr 线程栈对齐要求（`K_THREAD_STACK_DEFINE`），普通数组做栈会踩坑，
  不确定留 `/* TODO: */`。
