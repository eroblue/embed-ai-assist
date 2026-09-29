# 中断安全规范（ISR 上下文约束 / 回调判空 / 临界区）

> S5c 硬约束：**ISR 内调用回调前必须判断函数指针非 NULL**——回调未注册时
> 清除中断标志后直接返回，不得裸调。validate.py 会对回调调用点做判空抽查。

## 1. 回调判空（最高优先级规则）

```c
/* 正确 */
void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) {
        uint8_t byte = (uint8_t)USART_ReceiveData(USART1);  /* 读 DR 顺带清标志 */
        uart_impl_ctx_t *ctx = &s_uart_ctx[UART_PORT_REPORT];
        if (ctx->rx_cb != NULL) {          /* 判空：回调未注册不裸调 */
            ctx->rx_cb(ctx->id, byte, ctx->rx_cb_user);
        }
    }
}

/* 错误（validate 拦截）：未判空直接调用
 * ctx->rx_cb(ctx->id, byte, ctx->rx_cb_user);   ✗
 */
```

- 判空保护须位于调用点上方 8 行内（validate 机械抽查范围）
- `if (ctx->cb)` / `if (ctx->cb != NULL)` / `if (!ctx->cb) return;` 均认可
- 回调指针与用户数据在 `init/start` 时成对写入，ISR 侧只读

## 2. ISR 上下文通用约束

1. **先清标志，后做事**：标志未清会导致重入风暴；读 DR 类硬件自清标志
   的外设，读操作即清（见库手册）。
2. **只做置标志/计数/短拷贝**：manifest 回调 `context: isr` 的约定是
   "长逻辑投主循环"——回调实现由 S5b 的 APP 侧遵守，Port 侧只透传。
3. **禁止阻塞**：不得轮询等待长事件、不得调用阻塞延时
   （`timer_port_delay_us` 全部标注"仅任务上下文"）、不得 malloc。
4. **volatile**：ISR 与任务共享的变量（head/tail、标志、计数）必须 volatile；
   多字节共享数据任务侧读写须关中断保护。
5. **FromISR 变体**：RTOS API 在 ISR 内必须用 FromISR 版本
   （`xQueueSendFromISR` + `portYIELD_FROM_ISR`；Zephyr 用天然中断安全的
   `k_sem_give` / `k_msgq_put(K_NO_WAIT)` 等），见 `references/rtos_mapping_guide.md`。
6. **不申请/持有互斥锁**：FreeRTOS 互斥锁带优先级继承，ISR 中禁止
   （返回 ERR_STATE 由 OSAL 透传）。

## 3. 临界区

- 优先级升/降（`taskENTER_CRITICAL` / PRIMASK）只用于**多字节共享数据的
  原子读写**，区域尽量短（≤ 数十指令），临界区内不得调用阻塞 API；
- 32 位对齐的原子量（单个 uint32_t 读写）Cortex-M 天然原子，无需临界区；
- 8 位 MCU（mcu8）无硬件嵌套中断时临界区=关总中断，窗口最小化。

## 4. ISR 命名与向量表

- ISR 函数名必须与启动文件向量表一致（`USART1_IRQHandler` /
  `TIM2_IRQHandler` / `SysTick_Handler`）——**先查启动文件/向量表确认名字**，
  不确定留 `/* TODO: */`；
- 不修改向量表（S5a nvic_init 职责）；若发现向量表未接出所需中断，
  报告用户回 S5a 处理，不在 Port 内私接。

## 5. isr_safe 标注的落实

manifest 中 `isr_safe: true` 的接口：实现不得含阻塞等待/关调度长临界区，
可在 ISR 中安全调用（如寄存器直写、环形缓冲入队）；
`isr_safe: false` 的接口入口若被 ISR 调用属上层契约违规，Port 侧不负责
运行时拦截，但实现中不得埋"ISR 调用也恰好能跑"的误导性路径。
