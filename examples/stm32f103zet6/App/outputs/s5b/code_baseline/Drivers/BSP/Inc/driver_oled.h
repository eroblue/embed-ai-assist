/**
 * @file    driver_oled.h
 * @brief   OLED 显示驱动（SSD1306 128x64，I2C 接口，平台无关）
 *
 * 4 行文本布局：每行高 16 像素（占 2 个显示页），每行最多 16 个 8x16 字符。
 * 字符集为应用所需 ASCII 子集（内嵌字库），字符集外的字符显示为空格。
 */
#ifndef DRIVER_OLED_H
#define DRIVER_OLED_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 文本行数（每行 16 像素高）。 */
#define DRIVER_OLED_LINES       4u
/** 每行最大字符数（8x16 字体，128/8）。 */
#define DRIVER_OLED_LINE_CHARS 16u

/**
 * 初始化：I2C 总线 + SSD1306 上电序列（页寻址模式），并清屏。
 * @return PORT_OK 或负值错误码（port_err_t）。
 */
int32_t driver_oled_init(void);

/** 清屏（全灭）。 */
int32_t driver_oled_clear(void);

/**
 * 显示一行文本（在原行内容上整行覆盖，行尾以空格补齐 16 列）。
 * @param line 行号 0~3
 * @param text 以 '\0' 结尾的文本（超出 16 字符截断）
 */
int32_t driver_oled_show_line(uint8_t line, const char *text);

/** 反初始化（关闭显示，总线交还 Port 层管理）。 */
int32_t driver_oled_deinit(void);

#ifdef __cplusplus
}
#endif

#endif /* DRIVER_OLED_H */
