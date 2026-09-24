/* adc_init.h - ADC3 光照采集初始化（S5a hardware-initializer 生成） */
#ifndef ADC_INIT_H
#define ADC_INIT_H

/* ADC3_IN6 / PF8：12 位右对齐，采样 55.5 周期，单次软件触发，基准 VDD。
 * 采样触发与换算（ADC3->DR → 光照值）归应用层 */
void adc3_init(void);

#endif /* ADC_INIT_H */
