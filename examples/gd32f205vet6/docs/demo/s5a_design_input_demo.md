# s5a设计输入样例， 告诉 Agent 外设怎么用.

## 时钟
- 主频：120 MHz，使用 HSE 8MHz + PLL

## 外设使用
- UART0：使用 DMA 收发，波特率 115200
- UART1：仅调试输出，轮询模式
- I2C1：使用硬件 I2C，主模式，400kHz
- SPI0：使用 DMA，模式 0
- ADC1：采样 PA1，12 位，单次转换
- TIMER2：PWM 输出，频率 1kHz

## 特殊引脚
- PA0：作为 EXTI0 唤醒源
- PB2：BOOT1，配置为输入