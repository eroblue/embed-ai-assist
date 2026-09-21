# s5a设计输入样例， 告诉 Agent 外设怎么用.

## 时钟
- 主频：72 MHz，使用 HSE 8MHz + PLL×9

## 外设使用
- USART1：调试输出，PA9/PA10，波特率 115200
- SPI1：主机模式，PA5/PA6/PA7，模式 0
- ADC1：采样 PA1，12 位，单次转换
- TIM3：PWM 输出 CH1，频率 1kHz

## 特殊引脚
- PA0：作为 EXTI0 唤醒源
- PB2：BOOT1，配置为输入
