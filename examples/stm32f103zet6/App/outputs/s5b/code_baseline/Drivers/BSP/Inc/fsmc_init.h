/* fsmc_init.h - FSMC LCD 并口控制器初始化（S5a hardware-initializer 生成） */
#ifndef FSMC_INIT_H
#define FSMC_INIT_H

#include <stdint.h>

/* LCD 命令/数据地址（Bank1 NE4 区域，基址 0x6C000000）
 * RS = FSMC_A10（PG0）：低 = 命令，高 = 数据。
 * 16 位数据总线时 HADDR[25:1] → FSMC_A[24:0]，A10 对应 HADDR[11]：
 *   命令地址 = 0x6C000000（A10 = 0）
 *   数据地址 = 0x6C000800（A10 = 1）
 * 注：设计输入原文数据地址 0x6C0007FE 的 A10 = 0，电气上等同命令地址，
 * 疑为正点原子 lcd.h 中 LCD_BASE = 0x6C0007FE（结构体首成员命令 +2 后
 * 落在 0x6C000800）写法引起的笔误，此处按电气正确性取 0x6C000800。 */
#define FSMC_LCD_CMD_ADDR   (*(volatile uint16_t *)0x6C000000UL)
#define FSMC_LCD_DATA_ADDR  (*(volatile uint16_t *)0x6C000800UL)

void fsmc_lcd_init(void);

#endif /* FSMC_INIT_H */
