# Port 实现模式（状态管理 / 缓冲 / 错误码 / DMA 骨架）

> S5c Agent 编写 `port_impl_*.c` 的代码组织规范。ISR 规则见
> `references/isr_safety_rules.md`，HAL API 对应关系见
> `references/hal_mapping_guide.md`。

## 1. 文件骨架

每个外设一个文件，结构固定：

```c
/* port_impl_uart_stm32f103zet6.c - UART Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（来自 outputs/s5b/port_interface_manifest.json）：
 *   report_uart → USART1（PA9/PA10，115200-8N1，hw_source=design_input）
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "uart_port.h"          /* S5b 接口头（唯一接口依据） */
#include "uart_init.h"          /* S5a 初始化成果（可选对接） */
/* + 厂商头（stm32f10x.h 等）与必要的 C 标准头 */

/* ---- 文件内私有上下文（static，不进头文件） ---- */
```

- 文件头注释登记 hw_instance 映射（hw_instance=null 的实例登记 Agent 选定结果）
- 只 include：对应 Port 头、S5a init 头、厂商/RTOS 头、C 标准头；
  **禁止 include `app*.h` / `protocol_*.h` / `driver_*.h`**（向上依赖）

## 2. 实例状态管理（static ctx 数组）

```c
typedef struct {
    uint8_t          bound;        /* 实例是否已 init 绑定 */
    USART_TypeDef   *usart;        /* 厂商句柄（实现层私有） */
    uart_port_cb_t   rx_cb;        /* 回调：注册后 ISR 内调用（判空！） */
    void            *rx_cb_user;   /* 回调用户数据 */
} uart_impl_ctx_t;

static uart_impl_ctx_t s_uart_ctx[UART_PORT_COUNT];  /* id 数组索引，禁 malloc */
```

- `*_port_init(id, cfg)`：越界→`PORT_ERR_PARAM`；已绑定→`PORT_ERR_STATE`（幂等
  场景可返回 PORT_OK，按 manifest notes 语义）；绑定成功写 ctx
- `*_port_deinit(id)`：清 ctx，`bound=0`；后续调用返回 `PORT_ERR_STATE`
- 所有接口入口先校验 `id < COUNT && ctx[id].bound`

## 3. 错误码映射约定（port_err_t，S5b port_design_principle 同一约定）

| HAL 返回/情形 | port_err_t |
|---|---|
| 成功 / 参数合法且状态就绪 | `PORT_OK` |
| id 越界 / cfg 为 NULL / 频率/占空比超范围 | `PORT_ERR_PARAM` |
| 未 init 先用 / 已 init 重复 init / 重复启动 | `PORT_ERR_STATE` |
| 轮询等待标志超时（配超时上限） | `PORT_ERR_TIMEOUT` |
| 外设忙（上次操作未完成） | `PORT_ERR_BUSY` |

## 4. 同步拷贝语义（write 类接口）

manifest 中标注"同步拷贝语义"的接口：**返回后调用方缓冲即可复用**。

- 无 DMA：直接写寄存器，天然同步；
- 有 DMA：若启动 DMA 立即返回，必须先拷入文件内 static 缓冲（按实例固定大小），
  或轮询 `DMA_GetFlagStatus` 等传输完成再返回——禁止把调用方 buf 挂在
  DMA 上返回（buf 生命周期不可控）。

## 5. 接收环形缓冲（RX 缓冲骨架）

```c
#define RX_RING_SIZE 128u                    /* 2 的幂，覆盖最长帧 + 2 倍余量 */
typedef struct {
    uint8_t buf[RX_RING_SIZE];
    volatile uint16_t head, tail;            /* head=ISR 写入；tail=任务读出 */
} ring_t;

/* ISR 内：ring->buf[ring->head & (RX_RING_SIZE - 1u)] = byte; ring->head++; */
/* 任务读：if (ring->head == ring->tail) 无数据; b = ring->buf[ring->tail & MASK]; ring->tail++; */
```

- 单生产者（ISR）单消费者（任务）无锁安全；head/tail 用 volatile
- 缓冲不足丢弃新数据 + 计数器（勿阻塞 ISR）

## 6. DMA 骨架（隐藏在 Port 实现内）

manifest 未声明 DMA 语义时默认轮询实现；确需 DMA（高吞吐 UART/ADC）时：

```c
static uint16_t s_dma_buf[UART_PORT_COUNT][DMA_BUF_LEN];  /* static，禁 malloc */
/* write: 校验 → 拷入 s_dma_buf[id] → 配 DMA 通道 → 等待/回调收尾 → 返回 */
```

- DMA 通道占用在文件头注释登记；多实例复用通道需加忙标志（ERR_BUSY）
- 对上层接口签名与语义不变（同步拷贝语义照旧）

## 7. 周期定时回调约定（timer_port_cb_t 模板）

```c
/* ISR 上下文（context=isr）：只做置标志/计数，长逻辑投主循环 */
void tim2_irq_handler(void)            /* 命名随平台启动文件 */
{
    if (TIM_GetITStatus(TIM2, TIM_IT_Update) != RESET) {
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);   /* 先清标志 */
        timer_impl_ctx_t *ctx = &s_timer_ctx[TIMER_PORT_TICK_10MS];
        if (ctx->cb != NULL) {                        /* 判空！未注册不裸调 */
            ctx->cb(ctx->id, ctx->user_data);
        }
    }
}
```

## 8. 不臆造 API

SDK 头文件核对过的函数直接用；不确定的写：

```c
/* TODO: 此处调用 <库> 的 <功能> API，函数名待核（查 stm32f10x_tim.h / 参考手册 15.3） */
```

编译验证归 S7；validate 只查接口覆盖率与规范，不查 API 真伪，因此 TODO
必须显式标注给人工复核。
