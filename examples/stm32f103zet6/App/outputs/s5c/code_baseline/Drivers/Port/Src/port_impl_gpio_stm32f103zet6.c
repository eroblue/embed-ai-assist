/* port_impl_gpio_stm32f103zet6.c - GPIO Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json，hw_source=design_input）：
 *   GPIO_PORT_LED_EXEC    → PB5（低电平点亮，active_level=0）
 *   GPIO_PORT_LED_RUN     → PE5（低电平点亮，active_level=0）
 *   GPIO_PORT_BUZZER      → PB8（有源高电平导通，active_level=1）
 *                            ⚠ S5a 将 PB8 配置为 TIM4_CH3 PWM（2kHz）而非 GPIO——
 *                            set_active 映射 TIM_SetCompare3（响 250 / 停 0），
 *                            不直写 PB8（复用模式下直写无效）
 *   GPIO_PORT_KEY_MODE    → PE4（上拉输入，按下=低，active_level=0）
 *   GPIO_PORT_KEY_SWITCH  → PE3（上拉输入，按下=低，active_level=0）
 *   GPIO_PORT_KEY_MUTE    → PA0（下拉输入，按下=高，active_level=1）
 *                            ⚠ S5a gpio_init 未配置 PA0，本层 init 时补配
 *   GPIO_PORT_DHT11_DATA  → PG11（外部上拉，运行时 set_dir 换向，active_level=1）
 *
 * 对接 S5a 成果：gpio_init.c 已配置 PB5/PE5/PE3/PE4/PB0/PA4 与 FSMC 复用；
 * tim_init.c 的 tim4_init() 已配置 PB8 蜂鸣器 PWM。
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "gpio_port.h"
#include "gpio_init.h"
#include "tim_init.h"
#include "stm32f10x.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_tim.h"

/* ---- 文件内私有上下文（static，按 instance id 索引，禁动态分配） ---- */
typedef struct {
    uint8_t              bound;
    uint8_t              is_pwm;      /* 蜂鸣器：TIM4_CH3 PWM 特殊路径 */
    GPIO_TypeDef        *port;        /* 厂商端口句柄（实现层私有） */
    uint16_t             pin;         /* GPIO_Pin_x */
    gpio_port_dir_t      dir;         /* 当前方向（set_dir 换向用） */
    gpio_port_pull_t     pull;
    gpio_port_level_t    active_level;/* set_active/read_active 极性依据 */
} gpio_impl_ctx_t;

static gpio_impl_ctx_t s_gpio_ctx[GPIO_PORT_COUNT];

/* ---- 逻辑 id → 厂商引脚绑定表（manifest 数据侧） ---- */
static const struct {
    GPIO_TypeDef *port; uint16_t pin; uint8_t is_pwm;
} s_gpio_map[GPIO_PORT_COUNT] = {
    [GPIO_PORT_LED_EXEC]   = { GPIOB, GPIO_Pin_5,  0u },  /* PB5 */
    [GPIO_PORT_LED_RUN]    = { GPIOE, GPIO_Pin_5,  0u },  /* PE5 */
    [GPIO_PORT_BUZZER]     = { GPIOB, GPIO_Pin_8,  1u },  /* PB8 = TIM4_CH3 PWM */
    [GPIO_PORT_KEY_MODE]   = { GPIOE, GPIO_Pin_4,  0u },  /* PE4 */
    [GPIO_PORT_KEY_SWITCH] = { GPIOE, GPIO_Pin_3,  0u },  /* PE3 */
    [GPIO_PORT_KEY_MUTE]   = { GPIOA, GPIO_Pin_0,  0u },  /* PA0 */
    [GPIO_PORT_DHT11_DATA] = { GPIOG, GPIO_Pin_11, 0u },  /* PG11 */
};

/* 蜂鸣器响/停占空比（S5a tim_init.c 约定：50% 响 = 250，停 = 0） */
#define BUZZER_CCR_ON    250u
#define BUZZER_CCR_OFF   0u

static void gpio_apply_dir(gpio_impl_ctx_t *ctx)
{
    GPIO_InitTypeDef gpio;
    gpio.GPIO_Pin = ctx->pin;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    if (ctx->dir == GPIO_PORT_DIR_OUTPUT) {
        gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    } else {
        /* 输入：pull 语义（DHT11 外部上拉 → none 也安全） */
        gpio.GPIO_Mode = (ctx->pull == GPIO_PORT_PULL_UP)   ? GPIO_Mode_IPU
                       : (ctx->pull == GPIO_PORT_PULL_DOWN) ? GPIO_Mode_IPD
                       : GPIO_Mode_IN_FLOATING;
    }
    GPIO_Init(ctx->port, &gpio);
}

int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT || cfg == (const gpio_port_cfg_t *)0) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;
    }
    ctx->port = s_gpio_map[id].port;
    ctx->pin = s_gpio_map[id].pin;
    ctx->is_pwm = s_gpio_map[id].is_pwm;
    ctx->dir = cfg->dir;
    ctx->pull = cfg->pull;
    ctx->active_level = cfg->active_level;

    switch (id) {
    case GPIO_PORT_KEY_MUTE:
        /* ⚠ S5a gpio_init 未覆盖 PA0：本层补配（manifest config pull=down） */
        RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
        gpio_apply_dir(ctx);
        break;
    case GPIO_PORT_BUZZER:
        /* S5a tim_init 成果：PB8 复用 + TIM4 2kHz PWM 已配，占空比 0（停）。
           不重配 GPIO（复用模式），只登记绑定 */
        break;
    case GPIO_PORT_DHT11_DATA:
        /* S5a dht11_init 成果：PG11 上拉输入已配；外部上拉，pull=none 亦可 */
        gpio_apply_dir(ctx);   /* 按 manifest config 重申方向（幂等） */
        break;
    default:
        /* LED_EXEC/LED_RUN/KEY_MODE/KEY_SWITCH：S5a gpio_init 成果已配，
           按 manifest config 重申（幂等，保持与本实例声明一致） */
        gpio_apply_dir(ctx);
        break;
    }
    /* 输出初始电平（输入忽略）：按非激活电平置初值，避免上电误激活 */
    if (ctx->dir == GPIO_PORT_DIR_OUTPUT && !ctx->is_pwm) {
        gpio_port_level_t inactive =
            (ctx->active_level == GPIO_PORT_LEVEL_LOW) ? GPIO_PORT_LEVEL_HIGH
                                                       : GPIO_PORT_LEVEL_LOW;
        (void)gpio_port_write(id, inactive);
    }
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t gpio_port_deinit(gpio_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    if (ctx->is_pwm) {
        TIM_SetCompare3(TIM4, BUZZER_CCR_OFF);   /* 蜂鸣器置停 */
    }
    ctx->port = (GPIO_TypeDef *)0;
    ctx->pin = 0u;
    ctx->bound = 0u;
    return PORT_OK;
}

int32_t gpio_port_read(gpio_port_id_t id, gpio_port_level_t *level)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT || level == (gpio_port_level_t *)0) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    if (ctx->is_pwm) {
        /* 蜂鸣器：读回当前 CCR 状态（>0 = 输出中 = 高） */
        *level = (TIM_GetCapture3(TIM4) > BUZZER_CCR_OFF)
                 ? GPIO_PORT_LEVEL_HIGH : GPIO_PORT_LEVEL_LOW;
        return PORT_OK;
    }
    /* 输出引脚读回实际输出（ODR），输入引脚读 IDR */
    {
        uint8_t bit = (ctx->dir == GPIO_PORT_DIR_OUTPUT)
                      ? GPIO_ReadOutputDataBit(ctx->port, ctx->pin)
                      : GPIO_ReadInputDataBit(ctx->port, ctx->pin);
        *level = (bit == Bit_SET) ? GPIO_PORT_LEVEL_HIGH : GPIO_PORT_LEVEL_LOW;
    }
    return PORT_OK;
}

int32_t gpio_port_write(gpio_port_id_t id, gpio_port_level_t level)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    if (ctx->is_pwm) {
        /* 蜂鸣器：写高 = 响（50%），写低 = 停（active_level=1 语义直通） */
        TIM_SetCompare3(TIM4, (level == GPIO_PORT_LEVEL_HIGH)
                               ? BUZZER_CCR_ON : BUZZER_CCR_OFF);
        return PORT_OK;
    }
    if (ctx->dir != GPIO_PORT_DIR_OUTPUT) {
        return PORT_ERR_STATE;
    }
    GPIO_WriteBit(ctx->port, ctx->pin,
                  (level == GPIO_PORT_LEVEL_HIGH) ? Bit_SET : Bit_RESET);
    return PORT_OK;
}

int32_t gpio_port_toggle(gpio_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    if (ctx->is_pwm) {
        uint32_t ccr = TIM_GetCapture3(TIM4);
        TIM_SetCompare3(TIM4, (ccr > BUZZER_CCR_OFF) ? BUZZER_CCR_OFF : BUZZER_CCR_ON);
        return PORT_OK;
    }
    if (ctx->dir != GPIO_PORT_DIR_OUTPUT) {
        return PORT_ERR_STATE;
    }
    {
        uint8_t cur = GPIO_ReadOutputDataBit(ctx->port, ctx->pin);
        GPIO_WriteBit(ctx->port, ctx->pin,
                      (cur == Bit_SET) ? Bit_RESET : Bit_SET);
    }
    return PORT_OK;
}

int32_t gpio_port_set_dir(gpio_port_id_t id, gpio_port_dir_t dir)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    if (dir != GPIO_PORT_DIR_INPUT && dir != GPIO_PORT_DIR_OUTPUT) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    if (ctx->is_pwm) {
        return PORT_ERR_STATE;      /* 蜂鸣器为 PWM 复用，不支持换向 */
    }
    if (ctx->dir == dir) {
        return PORT_OK;             /* 幂等 */
    }
    ctx->dir = dir;
    gpio_apply_dir(ctx);            /* pull 沿用 init 配置 */
    return PORT_OK;
}

int32_t gpio_port_set_active(gpio_port_id_t id, uint8_t active)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* active 语义 → 电平：active=1 写激活电平，active=0 写非激活电平 */
    gpio_port_level_t level = (active != 0u)
        ? ctx->active_level
        : ((ctx->active_level == GPIO_PORT_LEVEL_LOW)
           ? GPIO_PORT_LEVEL_HIGH : GPIO_PORT_LEVEL_LOW);
    return gpio_port_write(id, level);
}

int32_t gpio_port_read_active(gpio_port_id_t id, uint8_t *active)
{
    if ((uint32_t)id >= (uint32_t)GPIO_PORT_COUNT || active == (uint8_t *)0) {
        return PORT_ERR_PARAM;
    }
    gpio_impl_ctx_t *ctx = &s_gpio_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    gpio_port_level_t level;
    int32_t r = gpio_port_read(id, &level);
    if (r != PORT_OK) {
        return r;
    }
    *active = (level == ctx->active_level) ? 1u : 0u;
    return PORT_OK;
}
