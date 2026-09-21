# s5b设计输入样例， 告诉 Agent 应用需求怎么映射到硬件

## 功能映射
- 电压检测：使用 ADC1 采样 PA1，阈值 2.5V
- 按键检测：使用 GPIO 输入 PA0，下拉
- LED 指示：使用 GPIO 输出 PB0

## 协议
- WiFi 模块：USART1 走 AT 协议，帧格式见附录 A
- 上位机通信：USART2，自定义二进制协议

## 任务划分（如启用 RTOS）
- task_sensor：100ms 周期，优先级中
- task_wifi：事件驱动，优先级高
