/**
 * @file    driver_lcd.h
 * @brief   TFT_LCD 显示驱动（ILI9341 类 240x320，16 位并口，平台无关）
 *
 * 竖屏 4 行文本布局：每行高 32 像素，每行最多 15 个 16x32 大字体字符
 * （8x16 基础字模 2 倍放大渲染，前景白、背景黑 RGB565）。
 * 字符集为应用所需 ASCII 子集（内嵌字库），字符集外的字符显示为空格。
 */
#ifndef DRIVER_LCD_H
#define DRIVER_LCD_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 文本行数（每行 32 像素高）。 */
#define DRIVER_LCD_LINES       4u
/** 每行最大字符数（16x32 字体，240/16）。 */
#define DRIVER_LCD_LINE_CHARS  15u

/**
 * 初始化：并口总线 + ILI9341 上电序列（厂商寄存器/Gamma/竖屏方向），并清屏。
 * @return PORT_OK 或负值错误码（port_err_t）。
 */
int32_t driver_lcd_init(void);

/** 清屏（黑色）。 */
int32_t driver_lcd_clear(void);

/**
 * 显示一行文本（整行覆盖，行尾以空格补齐 15 列）。
 * @param line 行号 0~3
 * @param text 以 '\0' 结尾的文本（超出 15 字符截断）
 */
int32_t driver_lcd_show_line(uint8_t line, const char *text);

/** 反初始化（关显示，总线交还 Port 层管理）。 */
int32_t driver_lcd_deinit(void);

#ifdef __cplusplus
extern "C" {
#endif

#endif /* DRIVER_LCD_H */
