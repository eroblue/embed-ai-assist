/* port_impl_example.c - UART Port 实现示例（S5c port-implementer）
 *
 * 本文件是 assets/ 下的写法参考（STM32F10x 标准外设库 + 裸机），展示：
 *   - 文件头 hw_instance 映射登记（manifest 数据侧，不进接口签名）
 *   - static ctx 数组状态管理（按 instance id 索引，禁 malloc）
 *   - 错误码映射（port_err_t）
 *   - 同步拷贝语义的 write 实现
 *   - RX 环形缓冲 + ISR 回调判空（isr_safety_rules.md）
 * 真实实现以 outputs/s5c/generation_brief.md 的 manifest 接口清单为准。
 */

#include "uart_port.h"     /* S5b 接口头（唯一接口依据） */
#include "uart_init.h"     /* S5a 初始化成果（usart1_init 等，只读对接） */
#include "stm32f10x.h"     /* 厂商头（适配层允许） */
#include <string.h>        /* memset */

/* ---- 实例绑定（hw_instance 来自 manifest，换板只改此处与 manifest）----
 * report_uart → USART1（PA9=TX / PA10=RX，115200-8N1，hw_source=design_input）
 */
#define REPORT_UART_INST        USART1
#define REPORT_UART_IRQ         USART1_IRQn

#define TX_TIMEOUT_LOOPS        200000u   /* 轮询等待上限（72MHz 下 ~ms 级） */
#define RX_RING_SIZE            128u      /* 2 的幂 */

/* ---- 文件内私有上下文（static，不进头文件）---- */
typedef struct {
    uint8_t          bound;
    USART_TypeDef   *usart;
    uart_port_cb_t   rx_cb;       /* ISR 内调用，必须判空 */
    void            *rx_cb_user;
    struct {
        uint8_t          buf[RX_RING_SIZE];
        volatile uint16_t head;    /* ISR 写 */
        volatile uint16_t tail;    /* 任务读 */
    } ring;
} uart_impl_ctx_t;

static uart_impl_ctx_t s_uart_ctx[UART_PORT_COUNT];

/* ISR：读 DR 清 RXNE 标志 → 入环形缓冲 → 判空调回调（只做短事，长逻辑投主循环） */
void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(REPORT_UART_INST, USART_IT_RXNE) != RESET) {
        uint8_t byte = (uint8_t)USART_ReceiveData(REPORT_UART_INST);
        uart_impl_ctx_t *ctx = &s_uart_ctx[UART_PORT_REPORT];
        uint16_t head = ctx->ring.head;
        if ((uint16_t)(head - ctx->ring.tail) < RX_RING_SIZE) {  /* 未满才收 */
            ctx->ring.buf[head & (RX_RING_SIZE - 1u)] = byte;
            ctx->ring.head = (uint16_t)(head + 1u);
        }
        if (ctx->rx_cb != NULL) {                    /* 判空！未注册不裸调 */
            ctx->rx_cb(UART_PORT_REPORT, byte, ctx->rx_cb_user);
        }
    }
}

int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg)
{
    if ((int)id < 0 || (int)id >= UART_PORT_COUNT || cfg == NULL) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;      /* 重复 init */
    }
    switch (id) {                   /* 逻辑 id → 厂商实例绑定 */
    case UART_PORT_REPORT:
        ctx->usart = REPORT_UART_INST;
        usart1_init();              /* S5a 成果：时钟/GPIO/波特率/RXNE 中断 */
        NVIC_EnableIRQ(REPORT_UART_IRQ);
        break;
    default:
        return PORT_ERR_PARAM;
    }
    ctx->ring.head = 0u;
    ctx->ring.tail = 0u;
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t uart_port_write(uart_port_id_t id, const uint8_t *buf, uint16_t len)
{
    if ((int)id < 0 || (int)id >= UART_PORT_COUNT || buf == NULL) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* 同步拷贝语义：逐字节送完（或拷入内部缓冲）后返回，buf 即可复用 */
    for (uint16_t i = 0u; i < len; i++) {
        uint32_t guard = TX_TIMEOUT_LOOPS;
        while (USART_GetFlagStatus(ctx->usart, USART_FLAG_TXE) == RESET) {
            if (--guard == 0u) {
                return PORT_ERR_TIMEOUT;
            }
        }
        USART_SendData(ctx->usart, buf[i]);
    }
    return (int32_t)len;
}

int32_t uart_port_deinit(uart_port_id_t id)
{
    if ((int)id < 0 || (int)id >= UART_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    USART_Cmd(ctx->usart, DISABLE); /* 只停外设，不动 S5a 的引脚/时钟配置 */
    (void)memset(&ctx->ring, 0, sizeof(ctx->ring));
    ctx->rx_cb = NULL;
    ctx->rx_cb_user = NULL;
    ctx->usart = NULL;
    ctx->bound = 0u;
    return PORT_OK;
}
