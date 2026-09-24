/**
 * @file    app_lcd_display.h
 * @brief   LCD 显示模块（200ms 周期刷新，4 行文本画面）
 *
 * 对应流程图 docs/flow/app_lcd_display_flow.md：
 * 初始化失败跳过刷新（就绪标志）；告警激活时告警行 1Hz 闪烁；
 * 写失败仅计数不中断流程。
 */
#ifndef APP_LCD_DISPLAY_H
#define APP_LCD_DISPLAY_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 初始化 LCD（并口 + ILI9341 上电 + 清屏）。 @return PORT_OK 或负值错误码。 */
int32_t app_lcd_display_init(void);

/** 10ms 节拍轮询：内部按 200ms 周期渲染刷新。 */
void app_lcd_display_poll(void);

/** 就绪标志（init 成功后置 1；未就绪时 poll 跳过刷新）。 */
uint8_t app_lcd_display_is_ready(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_LCD_DISPLAY_H */
