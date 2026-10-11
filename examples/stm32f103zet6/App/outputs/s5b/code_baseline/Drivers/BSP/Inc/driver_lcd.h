/**
 * @file    driver_lcd.h
 * @brief   TFT_LCD 显示驱动（NT35510，480x800，16 位并口，平台无关）
 *
 * 竖屏 4 行文本布局：每行高 32 像素，每行最多 30 个 16x32 大字体字符
 * （8x16 基础字模 2 倍放大渲染，前景白、背景黑 RGB565）。
 * 字符集为应用所需 ASCII 子集（内嵌字库），字符集外的字符显示为空格。
 *
 * 联调诊断：driver_lcd.c 内 `DRIVER_LCD_DIAG_LOG` 打开时，初始化过程会经
 * uart_port 输出 ID/寄存器回读结果（与 5s JSON 上报共用 USART1，联调后置 0）。
 */
#ifndef DRIVER_LCD_H
#define DRIVER_LCD_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 文本行数（每行 32 像素高）。 */
#define DRIVER_LCD_LINES       4u
/** 每行最大字符数（16x32 字体，480/16）。 */
#define DRIVER_LCD_LINE_CHARS  30u

/**
 * 初始化：并口总线 + NT35510 上电序列（页 1 电源/伽马 → 页 0 显示控制 → SLPOUT → DISPON），
 * 并清屏。
 * @return PORT_OK 或负值错误码（port_err_t）。
 */
int32_t driver_lcd_init(void);

/** 清屏（黑色）。 */
int32_t driver_lcd_clear(void);

/**
 * 读取控制器 ID（NT35510：0xDB00 版本 ID 与 0xDC00 控制器 ID 组合）。
 * 面板型号探测用：NT35510 常见 0x5510（部分批次 0x8000，正点原子归一为 0x5510）；
 * 其它值说明面板型号与 NT35510 序列不匹配。
 * @param id 出参：控制器 ID（(0xDB00<<8)|0xDC00）
 * @return PORT_OK 或负值错误码。三条读指令全为 00/FF 表示总线无响应
 *         （时序/片选/数据线/面板供电），而非序列问题。
 */
int32_t driver_lcd_read_id(uint16_t *id);

/**
 * 初始化自检结果码（联调定位用，可用运行灯编码输出，不依赖串口）：
 *   0 = 正常
 *   1 = 总线无响应（ID 读回全 00 或全 FF）→ 查 FSMC 时序/片选/数据线/面板供电
 *   2 = ID 不符（面板控制器不是 NT35510）→ 需换对应型号的初始化序列
 *   3 = 寄存器回读异常（0x0C00 ≠ 0x55）→ 写通路未生效
 */
uint8_t driver_lcd_get_diag_code(void);

/** 输出一行自检摘要（经 uart_port；`DRIVER_LCD_DIAG_LOG` 关闭时为空操作）。 */
void driver_lcd_diag_dump(void);

/**
 * 显示一行文本（整行覆盖，行尾以空格补齐 30 列）。
 * @param line 行号 0~3
 * @param text 以 '\0' 结尾的文本（超出 30 字符截断）
 */
int32_t driver_lcd_show_line(uint8_t line, const char *text);

/** 反初始化（关显示，总线交还 Port 层管理）。 */
int32_t driver_lcd_deinit(void);

#ifdef __cplusplus
}
#endif

#endif /* DRIVER_LCD_H */
