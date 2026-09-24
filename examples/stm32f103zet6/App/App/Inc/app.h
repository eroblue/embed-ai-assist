/**
 * @file    app.h
 * @brief   应用总入口（初始化汇总 + 主循环调度）
 *
 * app.c 只做初始化汇总与主循环调度，不含业务逻辑；
 * 硬件初始化由 main.c 调用 S5a 总入口 hal_init 完成。
 */
#ifndef APP_H
#define APP_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 初始化全部 APP 模块与节拍定时器。 @return PORT_OK 或负值错误码。 */
int32_t app_init(void);

/** 主循环（10ms 节拍调度各模块，不返回）。 */
void app_loop(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_H */
