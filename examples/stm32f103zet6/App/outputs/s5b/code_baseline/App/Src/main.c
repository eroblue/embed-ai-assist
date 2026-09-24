/**
 * @file    main.c
 * @brief   固件入口：S5a 硬件初始化总入口 + 应用初始化与主循环
 *
 * 标准骨架（不含业务逻辑）：
 *   hal_init()（S5a 总入口：时钟/外设/引脚等硬件初始化）
 *   → app_init()（模块初始化汇总）→ app_loop()（主循环，不返回）
 */
#include "app.h"

extern void hal_init(void); /* S5a 硬件初始化总入口（Drivers/BSP/Src/hal_init.c） */

int main(void)
{
    hal_init();
    (void)app_init();
    app_loop();
    return 0;
}
