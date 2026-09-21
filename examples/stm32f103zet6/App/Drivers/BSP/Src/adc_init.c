/* adc_init.c - ADC 初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "adc_init.h"

/**
 * @brief ADC1 初始化：12bit 右对齐，单次转换
 *        通道 stm_adc=PA1（CH1），引脚模拟模式在 gpio_init.c 配置
 *        通道选择/采样时间待 S5b 用例确定（暂按 CH1 最大采样时间）
 */
void adc1_init(void)
{
    ADC_InitTypeDef ADC_InitStructure;

    /* ADC1 挂 APB2 总线，使能外设时钟（ADCCLK 8MHz 由 clock_init.c 配置） */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1, ENABLE);

    /* 独立模式（单 ADC 工作） */
    ADC_InitStructure.ADC_Mode = ADC_Mode_Independent;
    /* 关闭扫描模式（单通道） */
    ADC_InitStructure.ADC_ScanConvMode = DISABLE;
    /* 单次转换（软件触发） */
    ADC_InitStructure.ADC_ContinuousConvMode = DISABLE;
    /* 无外部触发 */
    ADC_InitStructure.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    /* 数据右对齐（12bit） */
    ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;
    /* 转换通道数 1 */
    ADC_InitStructure.ADC_NbrOfChannel = 1;

    ADC_Init(ADC1, &ADC_InitStructure);

    /* TODO(S5b)：通道/采样时间按用例确定，暂按 PA1=CH1、最大采样时间 */
    ADC_RegularChannelConfig(ADC1, ADC_Channel_1, 1, ADC_SampleTime_239Cycles5);

    ADC_Cmd(ADC1, ENABLE);

    /* 上电校准（复位校准 → 等待 → 启动校准 → 等待） */
    ADC_ResetCalibration(ADC1);
    while (ADC_GetResetCalibrationStatus(ADC1))
    {
    }
    ADC_StartCalibration(ADC1);
    while (ADC_GetCalibrationStatus(ADC1))
    {
    }
}

/**
 * @brief ADC 模块汇总初始化：ADC1
 */
void adc_init(void)
{
    adc1_init();
}
