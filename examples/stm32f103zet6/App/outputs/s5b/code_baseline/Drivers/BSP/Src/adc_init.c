/* adc_init.c - ADC3 光照采集初始化：IN6/PF8，12 位单次软件触发（S5a hardware-initializer 生成，stm32f103zet6） */
#include "adc_init.h"
#include "stm32f10x.h"
#include "stm32f10x_adc.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"

void adc3_init(void)
{
    GPIO_InitTypeDef gpio;
    ADC_InitTypeDef adc;

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

    /* 上电校准（执行一次，提升转换精度） */
    ADC_ResetCalibration(ADC3);
    while (ADC_GetResetCalibrationStatus(ADC3) != RESET) { }
    ADC_StartCalibration(ADC3);
    while (ADC_GetCalibrationStatus(ADC3) != RESET) { }
}
