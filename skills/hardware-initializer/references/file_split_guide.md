# 文件拆分规范（S5a）

## 总原则

- 初始化代码**必须按功能模块拆分**，禁止单文件大杂烩
- 每模块一对 `<模块>_init.c/h`，命名一致
- 未使用的模块不生成
- 代码只放 S5a 产物目录（PROJECT_LAYOUT.md 解析，如 `Drivers/BSP/{Src,Inc}`），数据产物只放 `outputs/s5a/`

## 模块清单

| 模块 | 生成条件 |
|---|---|
| `clock_init.c/h` | 总是生成 |
| `gpio_init.c/h` | 存在已配置 GPIO 引脚 |
| `nvic_init.c/h` | 总是生成（分组 + IRQ 使能建议） |
| `dma_init.c/h` | S4/S5b 确认使用 DMA（当前 rule 模式不生成） |
| `uart_init.c/h` | S4 facts 存在串口引脚 |
| `spi_init.c/h` / `i2c_init.c/h` / `adc_init.c/h` | 同上按需 |
| `timer_init.c/h` / `pwm_init.c/h` | 存在定时器/PWM 引脚 |
| `rtos_hw_init.c/h` | `project.rtos != "none"` |
| `power_init.c/h` | `project.power.enabled == true` |
| `hal_init.c/h` | 总入口（layered / full） |
| `board_init.c/h` | 总入口（flat，替代 hal_init） |

## 总入口职责

`hal_init.c/h` / `board_init.c/h` 只做汇总调用，不含具体实现：

```c
void hal_init(void)
{
    clock_init();
    gpio_init();
    nvic_init();
    uart_init();
}
```

## 与其他 Skill 的边界

- S5a 不生成 `port_impl_*.c`（S5c 职责）、不定义 Port/OSAL 接口（S5b 职责）
- S5a 不 include `app.h` / `driver_*.h`，不包含业务逻辑
- `main.c` 由 S5b 生成，S5a 只提供 `hal_init()/board_init()` 供其调用
