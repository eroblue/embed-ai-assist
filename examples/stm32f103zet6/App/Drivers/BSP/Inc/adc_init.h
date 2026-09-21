#ifndef __ADC_INIT_H
#define __ADC_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* ADC1 初始化：12bit 右对齐单次转换（stm_adc=PA1=CH1，采样时间待 S5b 确定） */
void adc1_init(void);

/* ADC 模块汇总初始化：依次初始化 ADC1 */
void adc_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __ADC_INIT_H */
