/* port_impl_uart_stm32f103zet6.c - UART Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json）：
 *   UART_PORT_REPORT → USART1（PA9=TX / PA10=RX，115200-8N1，hw_source=design_input）
 *
 * 对接 S5a 成果：usart1_init() 完成时钟/引脚/波特率配置与外设级 RXNE 使能；
 * 本层补 NVIC 通道使能（USART1_IRQn 抢占 2 / 子 0 —— 按 nvic_init.c 使能建议，
 * S5a 只做优先级分组、把通道使能留给 handler 的拥有者）。
 *
 * 接收：USART1_IRQHandler 读 DR（顺带清 RXNE/ORE）入环形缓冲（满则丢弃新字节
 * 并计数，保护已在缓冲的帧），随后判空并通知已注册的 rx_cb。
 * 上层两种取数方式可并用：非阻塞 read 取缓冲，或注册 rx_cb 获通知。
 * 指令协议未定义，本层只打通接收通道，不做协议解析。
 *
 * 发送：write 轮询 TXE/TC（同步拷贝语义）。
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "uart_port.h"
#include "uart_init.h"
#include "stm32f10x.h"
#include "stm32f10x_usart.h"
#include "misc.h"

/* ---- 接收环形缓冲（ISR 写 rx_head / 任务写 rx_tail；容量取 2 的幂便于掩码取模）
 * 容量依据设计输入 docs/s5c_design_input.md"已有实现"：uart 缓存 1KB ---- */
#define UART_RX_RING_SIZE   1024u
#define UART_RX_RING_MASK   (UART_RX_RING_SIZE - 1u)

/* ---- 文件内私有上下文（static，按 instance id 索引，禁动态分配） ---- */
typedef struct {
    uint8_t          bound;     /* 实例是否已 init 绑定 */
    USART_TypeDef   *usart;     /* 厂商句柄（实现层私有） */
    uint32_t         baudrate;  /* 登记用（实际配置由 S5a 完成） */

    uart_port_rx_cb_t rx_cb;    /* ISR 内调用，必须判空 */
    void             *rx_user;

    uint8_t           rx_buf[UART_RX_RING_SIZE];   /* 1KB（设计输入约定） */
    volatile uint16_t rx_head;  /* ISR 写索引 */
    volatile uint16_t rx_tail;  /* 任务读索引 */
    volatile uint16_t rx_drops; /* 缓冲满丢弃计数（诊断用） */
} uart_impl_ctx_t;

static uart_impl_ctx_t s_uart_ctx[UART_PORT_COUNT];

/* ---- 逻辑 id → 厂商实例/中断向量绑定表 ---- */
static USART_TypeDef *uart_map_instance(uart_port_id_t id)
{
    switch (id) {
    case UART_PORT_REPORT: return USART1;
    default:               return (USART_TypeDef *)0;
    }
}

static IRQn_Type uart_map_irqn(uart_port_id_t id)
{
    switch (id) {
    case UART_PORT_REPORT: return USART1_IRQn;
    default:               return (IRQn_Type)0;
    }
}

/* NVIC 通道使能/关闭（参数与 S5a nvic_init.c 使能建议一致：抢占 2 / 子 0） */
static void uart_nvic_config(uart_port_id_t id, FunctionalState state)
{
    NVIC_InitTypeDef nvic;
    nvic.NVIC_IRQChannel = uart_map_irqn(id);
    nvic.NVIC_IRQChannelPreemptionPriority = 2;
    nvic.NVIC_IRQChannelSubPriority = 0;
    nvic.NVIC_IRQChannelCmd = state;
    NVIC_Init(&nvic);
}

int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg)
{
    if ((uint32_t)id >= (uint32_t)UART_PORT_COUNT || cfg == (const uart_port_cfg_t *)0) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;      /* 重复 init */
    }
    USART_TypeDef *usart = uart_map_instance(id);
    if (usart == (USART_TypeDef *)0) {
        return PORT_ERR_PARAM;
    }
    /* S5a 成果：时钟/GPIO 复用/115200-8N1 一次性配置（幂等由 S5a 保证） */
    usart1_init();

    /* 复位接收环与回调登记（清残留 RXNE/ORE） */
    ctx->rx_head = 0u;
    ctx->rx_tail = 0u;
    ctx->rx_drops = 0u;
    ctx->rx_cb = (uart_port_rx_cb_t)0;
    ctx->rx_user = (void *)0;
    (void)USART_GetFlagStatus(usart, USART_FLAG_ORE);  /* 先读 SR */
    (void)USART_ReceiveData(usart);          /* 再读 DR：清残留 RXNE 与 ORE（F1 序列） */

    /* 外设级接收中断使能（S5a 已使能，此处幂等重申）+ NVIC 通道使能 */
    USART_ITConfig(usart, USART_IT_RXNE, ENABLE);
    uart_nvic_config(id, ENABLE);

    ctx->usart = usart;
    ctx->baudrate = cfg->baudrate;
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t uart_port_write(uart_port_id_t id, const uint8_t *buf, uint16_t len)
{
    if ((uint32_t)id >= (uint32_t)UART_PORT_COUNT || buf == (const uint8_t *)0) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* 同步拷贝语义：逐字节送完后返回，buf 即可复用（115200 下 1 字节 ~87µs） */
    for (uint16_t i = 0u; i < len; i++) {
        uint32_t guard = 200000u;    /* 轮询上限：~ms 级（72MHz）防硬件异常死锁 */
        while (USART_GetFlagStatus(ctx->usart, USART_FLAG_TXE) == RESET) {
            if (--guard == 0u) {
                return PORT_ERR_TIMEOUT;
            }
        }
        USART_SendData(ctx->usart, (uint16_t)buf[i]);
    }
    /* 等最后一个字节移出移位寄存器（TC），保证调用方紧接着改 buf 不会截尾 */
    {
        uint32_t guard = 200000u;
        while (USART_GetFlagStatus(ctx->usart, USART_FLAG_TC) == RESET) {
            if (--guard == 0u) {
                return PORT_ERR_TIMEOUT;
            }
        }
    }
    return (int32_t)len;
}

int32_t uart_port_set_rx_cb(uart_port_id_t id, uart_port_rx_cb_t cb,
                            void *user_data)
{
    if ((uint32_t)id >= (uint32_t)UART_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* 先写 user_data 再写 cb：ISR 判空 cb 后才读 user_data，保证配对就绪 */
    ctx->rx_user = user_data;
    ctx->rx_cb = cb;                /* cb 传 NULL 即取消注册 */
    return PORT_OK;
}

int32_t uart_port_read(uart_port_id_t id, uint8_t *buf, uint16_t len)
{
    if ((uint32_t)id >= (uint32_t)UART_PORT_COUNT || buf == (uint8_t *)0) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* 非阻塞：读走当前可用数据即返回（0=暂无数据）；单生产者/单消费者免临界区 */
    uint16_t n = 0u;
    while (n < len) {
        uint16_t tail = ctx->rx_tail;
        if (tail == ctx->rx_head) {
            break;                  /* 环空 */
        }
        buf[n] = ctx->rx_buf[tail];
        n++;
        ctx->rx_tail = (uint16_t)((tail + 1u) & UART_RX_RING_MASK);
    }
    return (int32_t)n;
}

int32_t uart_port_deinit(uart_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)UART_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    uart_impl_ctx_t *ctx = &s_uart_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    /* 先断中断源（NVIC 通道 + 外设级 RXNE），再停外设 */
    uart_nvic_config(id, DISABLE);
    USART_ITConfig(ctx->usart, USART_IT_RXNE, DISABLE);
    USART_Cmd(ctx->usart, DISABLE);
    ctx->rx_cb = (uart_port_rx_cb_t)0;
    ctx->rx_user = (void *)0;
    ctx->usart = (USART_TypeDef *)0;
    ctx->baudrate = 0u;
    ctx->bound = 0u;
    return PORT_OK;
}

/* ---- USART1 接收中断服务（向量名与 startup_stm32f10x_hd.s 一致）----
 * 读 DR 顺带清 RXNE（F1：读 SR + 读 DR 亦清 ORE）。
 * 回调为 ISR 直接调用（manifest context=isr）：只做置标志/短拷贝。
 * ⚠ 判空：回调未注册时不得裸调（isr_safety_rules.md 硬约束）。 */
void USART1_IRQHandler(void)
{
    uart_impl_ctx_t *ctx = &s_uart_ctx[UART_PORT_REPORT];

    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) {
        uint8_t byte = (uint8_t)USART_ReceiveData(USART1);   /* 读 DR 清 RXNE/ORE */
        uint16_t head = ctx->rx_head;
        uint16_t next = (uint16_t)((head + 1u) & UART_RX_RING_MASK);
        if (next != ctx->rx_tail) {
            ctx->rx_buf[head] = byte;
            ctx->rx_head = next;
        } else {
            ctx->rx_drops++;        /* 环满：丢弃新字节，保护已在缓冲的帧 */
        }
        if (ctx->rx_cb != (uart_port_rx_cb_t)0) {   /* 判空！未注册不裸调 */
            ctx->rx_cb((uart_port_id_t)UART_PORT_REPORT, &byte, 1u, ctx->rx_user);
        }
    }
}
