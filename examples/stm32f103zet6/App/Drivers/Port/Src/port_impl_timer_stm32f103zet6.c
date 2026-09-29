/* port_impl_timer_stm32f103zet6.c - Timer Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json）：
 *   TIMER_PORT_TICK_10MS → hw_instance=null（Agent 选定，在此登记）：
 *   **选定 SysTick**（HCLK 72MHz，TICKINT 使能）——TIM4 已被 S5a 蜂鸣器 PWM
 *   占用（hardware_capabilities 约束 + REC-005 建议），SysTick 不占通用定时器。
 *
 * delay_us 载体（Agent 选定，在此登记）：**TIM2 空闲通用定时器**
 * （APB1 倍频后 72MHz，PSC=71 → 1MHz 计数，自由运行 ARR=0xFFFF）——
 * 与 SysTick 节拍正交，delay_us 在节拍运行中可用；本 CMSIS 版本无 DWT 定义，
 * 不用校准 NOP 忙等（DHT11 位时序 26~70µs 需 µs 级精度）。
 *
 * 对接 S5a 成果：无（SysTick/TIM2 皆为本层自行配置；S5a tim_init 只管 TIM4 蜂鸣器）。
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "timer_port.h"
#include "stm32f10x.h"
#include "stm32f10x_tim.h"

/* ---- 文件内私有上下文（static，按 instance id 索引，禁动态分配） ---- */
typedef struct {
    uint8_t          bound;
    uint8_t          running;
    uint32_t         period_ms;
    timer_port_cb_t  cb;           /* ISR 内调用，必须判空 */
    void            *user_data;
} timer_impl_ctx_t;

static timer_impl_ctx_t s_timer_ctx[TIMER_PORT_COUNT];

/* TIM2 1µs 时基（PSC=71 → 72MHz/72 = 1MHz），free-run 单次延时基准 */
static uint8_t s_delay_ready;     /* TIM2 已配置标志（懒初始化） */

/* SysTick：10ms @ HCLK 72MHz = 720000 ticks（24 位上限 0xFFFFFF 内） */
#define SYSTICK_HZ         72000000u
#define TICKS_PER_MS       (SYSTICK_HZ / 1000u)

static void delay_timebase_init(void)
{
    TIM_TimeBaseInitTypeDef tim;
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);
    tim.TIM_Prescaler = 71u;              /* 72MHz / 72 = 1MHz（1µs 分辨率） */
    tim.TIM_CounterMode = TIM_CounterMode_Up;
    tim.TIM_Period = 0xFFFFu;              /* 自由运行（16 位回绕，unsigned 减法处理） */
    tim.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseInit(TIM2, &tim);
    TIM_Cmd(TIM2, ENABLE);
    s_delay_ready = 1u;
}

int32_t timer_port_init(timer_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)TIMER_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    timer_impl_ctx_t *ctx = &s_timer_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* delay_us 时基懒初始化前置到 init：app_init 中 timer_port_init 最先执行，
       driver_lcd 上电延时 / driver_dht11 位时序随后依赖 delay_us */
    if (!s_delay_ready) {
        delay_timebase_init();
    }
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t timer_port_start_periodic(timer_port_id_t id, uint32_t period_ms,
                                  timer_port_cb_t cb, void *user_data)
{
    if ((uint32_t)id >= (uint32_t)TIMER_PORT_COUNT || period_ms == 0u) {
        return PORT_ERR_PARAM;
    }
    timer_impl_ctx_t *ctx = &s_timer_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    if (ctx->running) {
        return PORT_ERR_STATE;      /* 同一 id 重复启动 */
    }
    ctx->period_ms = period_ms;
    ctx->cb = cb;
    ctx->user_data = user_data;
    /* SysTick 装载：ticks = period_ms × (HCLK/1000)；超过 24 位上限报错 */
    {
        uint32_t ticks = period_ms * TICKS_PER_MS;
        if (ticks > 0xFFFFFFu) {
            return PORT_ERR_PARAM;  /* 单次装载超 SysTick 24 位量程 */
        }
        if (SysTick_Config(ticks) != 0u) {
            return PORT_ERR_BUSY;
        }
    }
    ctx->running = 1u;
    return PORT_OK;
}

int32_t timer_port_stop(timer_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)TIMER_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    timer_impl_ctx_t *ctx = &s_timer_ctx[id];
    if (!ctx->running) {
        return PORT_OK;             /* 幂等 */
    }
    /* 关中断 + 关计数器（时钟源位保持 HCLK，下次 SysTick_Config 重配） */
    SysTick->CTRL &= ~(SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_ENABLE_Msk);
    ctx->running = 0u;
    ctx->cb = (timer_port_cb_t)0;
    ctx->user_data = (void *)0;
    return PORT_OK;
}

int32_t timer_port_delay_us(uint32_t delay_us)
{
    if (!s_delay_ready) {
        delay_timebase_init();      /* 兜底：init 未先行的调用路径 */
    }
    /* TIM2 自由运行 1µs 分辨率；16 位回绕用 unsigned 减法自然处理。
       大延时（LCD 上电 120ms）按 60000µs 分段防单次回绕歧义 */
    while (delay_us > 0u) {
        uint16_t chunk = (delay_us > 60000u) ? 60000u : (uint16_t)delay_us;
        uint16_t start = TIM_GetCounter(TIM2);
        while ((uint16_t)(TIM_GetCounter(TIM2) - start) < chunk) { }
        delay_us -= (uint32_t)chunk;
    }
    return PORT_OK;
}

int32_t timer_port_deinit(timer_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)TIMER_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    timer_impl_ctx_t *ctx = &s_timer_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    if (ctx->running) {
        (void)timer_port_stop(id);
    }
    ctx->bound = 0u;
    ctx->period_ms = 0u;
    return PORT_OK;
}

/* ---- SysTick 中断服务（周期 10ms）----
 * SysTick COUNTFLAG 由读 CTRL 清除 / 异常边界处理，ISR 内无标志清理动作。
 * 回调只做置标志/计数（长逻辑投主循环，manifest 回调约定 context=isr）。
 * ⚠ 判空：回调未注册时不得裸调（isr_safety_rules.md 硬约束）。 */
void SysTick_Handler(void)
{
    timer_impl_ctx_t *ctx = &s_timer_ctx[TIMER_PORT_TICK_10MS];
    if (ctx->cb != (timer_port_cb_t)0) {   /* 判空！未注册不裸调 */
        ctx->cb(TIMER_PORT_TICK_10MS, ctx->user_data);
    }
}
