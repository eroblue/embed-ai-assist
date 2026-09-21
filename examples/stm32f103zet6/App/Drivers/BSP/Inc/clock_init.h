#ifndef __CLOCK_INIT_H
#define __CLOCK_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* 系统时钟初始化：HSE 8MHz×PLL4=32MHz；AHB/APB1/APB2 均 32MHz；
   ADCCLK=PCLK2/4；FLASH 1WS+预取；LSE 32.768kHz→RTC */
void clock_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __CLOCK_INIT_H */
