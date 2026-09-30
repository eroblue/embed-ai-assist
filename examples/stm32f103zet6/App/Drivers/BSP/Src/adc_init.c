/* adc_init.c - ADC3 光照采集初始化：IN6/PF8，12 位单次软件触发（S5a hardware-initializer 生成，stm32f103zet6） */
#include "adc_init.h"
#include "stm32f10x.h"
#include "stm32f10x_adc.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"

/* 校准等待上限：正常校准为 µs 级，此上限（72MHz 下约数十 ms）仅供硬件异常兜底 */
#define ADC_CAL_TIMEOUT   0x00FFFFFFu

void adc3_init(void)
{
    GPIO_InitTypeDef gpio;
    ADC_InitTypeDef adc;
    uint32_t guard;

    /* 幂等保护：本函数被 hal_init() 与 adc_port_init() 各调用一次。ADC 已使能
       （ADON=1）后再执行 ADC_Init 属未定义操作，且会打断已开始的校准 —— 实测
       第二次调用会让下面的校准等待永不返回（整机卡死在 app_env_sensor_init，
       UART/LCD/主循环全都不执行）。S5a init 按约定必须幂等，此处显式保证。 */
    static uint8_t s_initialized;
    if (s_initialized != 0u) {
        return;
    }

    /* PF8 - 板载光敏电阻分压（ADC3_IN6，模拟输入，基准 VDD 3.3V） */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOF | RCC_APB2Periph_ADC3, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_8;
    gpio.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_Init(GPIOF, &gpio);

    /* ADCCLK = PCLK2 72MHz / 6 = 12MHz（≤ 14MHz 上限） */
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);

    adc.ADC_Mode = ADC_Mode_Independent;
    adc.ADC_ScanConvMode = DISABLE;
    adc.ADC_ContinuousConvMode = DISABLE;
    adc.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    adc.ADC_DataAlign = ADC_DataAlign_Right;
    adc.ADC_NbrOfChannel = 1;
    ADC_Init(ADC3, &adc);

    /* 通道 6，规则序列第 1 位，采样 55.5 周期（docs/s5a_design_input.md）。
       单次软件触发模式，采样调度（2s 周期）归应用层 */
    ADC_RegularChannelConfig(ADC3, ADC_Channel_6, 1, ADC_SampleTime_55Cycles5);

    ADC_Cmd(ADC3, ENABLE);

    /* 上电校准（执行一次，提升转换精度）。等待加超时上限：校准是"提升精度"
       而非功能前提，硬件异常时宁可跳过也不能阻塞启动 */
    ADC_ResetCalibration(ADC3);
    for (guard = ADC_CAL_TIMEOUT; (ADC_GetResetCalibrationStatus(ADC3) != RESET)
                                  && (guard != 0u); guard--) { }
    ADC_StartCalibration(ADC3);
    for (guard = ADC_CAL_TIMEOUT; (ADC_GetCalibrationStatus(ADC3) != RESET)
                                  && (guard != 0u); guard--) { }
    s_initialized = 1u;
}
