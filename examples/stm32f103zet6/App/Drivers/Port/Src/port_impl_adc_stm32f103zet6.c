/* port_impl_adc_stm32f103zet6.c - ADC Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json）：
 *   ADC_PORT_LIGHT → hw_instance 登记为 "ADC1_IN1（PA1）"，但 S5a 实际初始化
 *   ADC3_IN6 / PF8（战舰板光敏电阻真实接法，见 hardware_capabilities 约束）——
 *   本实现按实际硬件对接 ADC3 通道 6（12 位右对齐，VDD 基准，55.5 周期采样）。
 *
 * 对接 S5a 成果：adc_init.c 的 adc3_init() 已完成通道/时钟/校准配置；
 * 本实现只做软件触发、EOC 轮询、均值与毫伏换算。
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "adc_port.h"
#include "adc_init.h"
#include "stm32f10x.h"
#include "stm32f10x_adc.h"

/* ---- 文件内私有上下文（static，按 instance id 索引，禁动态分配） ---- */
typedef struct {
    uint8_t   bound;
    ADC_TypeDef *adc;         /* 厂商句柄（实现层私有） */
    uint8_t   channel;        /* 规则通道号 */
    uint32_t  ref_mv;         /* 满量程锚点（sample_mv 换算用） */
    uint8_t   avg_count;      /* 软件过采样次数 */
} adc_impl_ctx_t;

static adc_impl_ctx_t s_adc_ctx[ADC_PORT_COUNT];

/* EOC 轮询上限：55.5+12.5 周期 @12MHz ADCCLK ≈ 5.7µs/次；
 * 上限取 72MHz 下 ~ms 级防硬件异常死锁 */
#define ADC_EOC_GUARD 100000u

int32_t adc_port_init(adc_port_id_t id, const adc_port_cfg_t *cfg)
{
    if ((uint32_t)id >= (uint32_t)ADC_PORT_COUNT || cfg == (const adc_port_cfg_t *)0) {
        return PORT_ERR_PARAM;
    }
    adc_impl_ctx_t *ctx = &s_adc_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* S5a 成果：RCC/GPIO(PF8 AIN)/ADC3 独立模式/通道 6/校准 一次性完成 */
    adc3_init();
    ctx->adc = ADC3;
    ctx->channel = ADC_Channel_6;      /* PF8（s5a_design_input + capabilities） */
    ctx->ref_mv = (cfg->ref_mv != 0u) ? cfg->ref_mv : 3300u;
    ctx->avg_count = (cfg->avg_count != 0u) ? cfg->avg_count : 1u;
    /* 基准源语义：本实现仅支持 VDD 基准（ADC_Vrefint 未用）；
       ADC_PORT_REF_EXT 传入时 ref_mv 仍作为满量程锚点参与换算 */
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t adc_port_sample_mv(adc_port_id_t id, uint16_t *raw_mv)
{
    if ((uint32_t)id >= (uint32_t)ADC_PORT_COUNT || raw_mv == (uint16_t *)0) {
        return PORT_ERR_PARAM;
    }
    adc_impl_ctx_t *ctx = &s_adc_ctx[id];
    if (!ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* 软件过采样均值：avg_count 次单次转换取平均（去抖动） */
    uint32_t acc = 0u;
    for (uint8_t n = 0u; n < ctx->avg_count; n++) {
        ADC_SoftwareStartConvCmd(ctx->adc, ENABLE);
        uint32_t guard = ADC_EOC_GUARD;
        while (ADC_GetFlagStatus(ctx->adc, ADC_FLAG_EOC) == RESET) {
            if (--guard == 0u) {
                return PORT_ERR_TIMEOUT;   /* 硬件异常（转换超时） */
            }
        }
        acc += ADC_GetConversionValue(ctx->adc);   /* 读 DR 顺带清 EOC */
    }
    acc /= ctx->avg_count;
    /* 满量程换算：12 位右对齐 → 毫伏（val * ref_mv / 4095）
       基准换算在 Port 内完成，APP 不感知分辨率/通道号 */
    uint32_t mv = (acc * ctx->ref_mv) / 4095u;
    if (mv > 65535u) {
        mv = 65535u;
    }
    *raw_mv = (uint16_t)mv;
    return PORT_OK;
}

int32_t adc_port_deinit(adc_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)ADC_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    adc_impl_ctx_t *ctx = &s_adc_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    ADC_Cmd(ctx->adc, DISABLE);      /* 只停外设，不动 S5a 的引脚/时钟配置 */
    ctx->adc = (ADC_TypeDef *)0;
    ctx->channel = 0u;
    ctx->ref_mv = 0u;
    ctx->avg_count = 0u;
    ctx->bound = 0u;
    return PORT_OK;
}
