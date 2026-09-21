# s5c设计输入样例， 告诉 Agent 实现约束.

## 低功耗方案
- 空闲时进入 STOP 模式
- 唤醒源：EXTI0 (PA0)、RTC 闹钟
- 唤醒后：重新配置 PLL，恢复 USART 时钟
- 睡眠前：关闭 USART、SPI 时钟

## 已有实现
- 参考 references/existing_project/power_mgmt.c
- 沿用 `enter_sleep_before → enter_sleep → wakeup_after_sleep` 命名
