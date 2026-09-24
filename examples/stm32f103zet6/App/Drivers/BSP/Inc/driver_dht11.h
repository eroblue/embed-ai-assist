/**
 * @file    driver_dht11.h
 * @brief   DHT11 温湿度传感器驱动（平台无关，经 GPIO/Timer Port 访问硬件）
 *
 * 单总线时序协议（全双向）：
 *  主机起始 = 拉低 >=18ms → 释放总线；DHT11 响应 = 拉低 80us + 拉高 80us；
 *  之后连续输出 40 位（湿度整数/小数、温度整数/小数、校验和），
 *  位编码 = 50us 低 + (26~28us 高 = 0 / 70us 高 = 1)。
 */
#ifndef DRIVER_DHT11_H
#define DRIVER_DHT11_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 初始化：把单总线数据引脚置为输入（外部上拉），进入空闲态。
 * @return PORT_OK 或负值错误码（port_err_t）。
 */
int32_t driver_dht11_init(void);

/**
 * 读取温湿度（阻塞约 25ms：18ms 起始信号 + 时序收发，2s 周期采集可接受）。
 * @param temp  输出：温度整数（°C，DHT11 范围 0~50）
 * @param humi  输出：相对湿度整数（%，DHT11 范围 20~90）
 * @return PORT_OK；PORT_ERR_TIMEOUT（响应/位超时）；
 *         PORT_ERR_STATE（校验和错误，数据视为无效）。
 */
int32_t driver_dht11_read(int16_t *temp, uint8_t *humi);

/** 反初始化（引脚交还 Port 层管理）。 */
int32_t driver_dht11_deinit(void);

#ifdef __cplusplus
}
#endif

#endif /* DRIVER_DHT11_H */
