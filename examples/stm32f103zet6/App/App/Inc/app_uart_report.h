/**
 * @file    app_uart_report.h
 * @brief   串口上报模块（5s 周期 JSON 帧）
 *
 * 对应时序图 docs/flow/app_uart_report_sequence.md：
 * 初始化上报口 → 5s 周期组帧 → write（同步拷贝语义）→
 * 失败重试 2 次 → 连续 3 个周期失败置上报故障标志。
 */
#ifndef APP_UART_REPORT_H
#define APP_UART_REPORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 初始化上报串口（115200-8N1）。 @return PORT_OK 或负值错误码。 */
int32_t app_uart_report_init(void);

/** 10ms 节拍轮询：内部按 5s 周期上报。 */
void app_uart_report_poll(void);

/** 就绪标志（init 成功后置 1）。 */
uint8_t app_uart_report_is_ready(void);

/** 上报故障标志（连续 3 个周期发送失败置 1，任一成功清零）。 */
uint8_t app_uart_report_is_failing(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_UART_REPORT_H */
