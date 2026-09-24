/**
 * @file    driver_dht11.c
 * @brief   DHT11 温湿度传感器驱动实现（单总线时序）
 *
 * 实现 docs/flow/app_env_sensor_flow.md 中"读取 DHT11 温湿度"的时序要求：
 *  - 起始信号：主机输出拉低 >=18ms，随后释放总线（切回输入，上拉拉高）
 *  - 响应判定：等 DHT11 拉低(80us) 再拉高(80us)，全程序化轮询 + 超时保护
 *  - 位接收：每位先 ~50us 低，再 26~70us 高；高电平持续 >40us 判 1，否则判 0
 *  - 数据校验：5 字节，前 4 字节之和（低 8 位）== 第 5 字节
 *
 * 硬件访问全部经 Port：gpio_port（换向/读写）+ timer_port（µs 延时）。
 */
#include "driver_dht11.h"
#include "gpio_port.h"
#include "timer_port.h"

/* ---------------- 时序参数（DHT11 数据手册标称值 + 裕量） ---------------- */
#define DHT11_START_LOW_US      20000u /* 起始拉低 >=18ms，取 20ms */
#define DHT11_RELEASE_US           30u /* 释放后主机等待，DHT11 随即拉低响应 */
#define DHT11_RESP_TIMEOUT_US     90u /* 响应低/高各 80us，超时判 90us */
#define DHT11_BIT_LOW_TIMEOUT_US  60u /* 位起始低 ~50us，超时判 60us */
#define DHT11_BIT_HIGH_TIMEOUT_US 90u /* 位高最长 70us，超时判 90us */
#define DHT11_ONE_THRESHOLD_US    40u /* 高电平持续 >40us 判 1 */
#define DHT11_DATA_BYTES           5u

static int32_t dht11_wait_level(gpio_port_level_t want, uint32_t timeout_us,
                                uint32_t *elapsed_us);

int32_t driver_dht11_init(void)
{
    /* 上电稳定由 APP 侧时序保证（首次采集前已运行 >1s）；总线置输入即可 */
    return gpio_port_set_dir(GPIO_PORT_DHT11_DATA, GPIO_PORT_DIR_INPUT);
}

int32_t driver_dht11_read(int16_t *temp, uint8_t *humi)
{
    uint8_t data[DHT11_DATA_BYTES];
    uint32_t elapsed = 0;
    uint32_t bit_idx;
    int32_t r;
    uint8_t i;

    if ((temp == 0) || (humi == 0)) {
        return PORT_ERR_PARAM;
    }

    /* 1. 起始信号：输出拉低 >=18ms 后释放总线 */
    r = gpio_port_set_dir(GPIO_PORT_DHT11_DATA, GPIO_PORT_DIR_OUTPUT);
    if (r != PORT_OK) { return r; }
    r = gpio_port_write(GPIO_PORT_DHT11_DATA, GPIO_PORT_LEVEL_LOW);
    if (r != PORT_OK) { return r; }
    timer_port_delay_us(DHT11_START_LOW_US);
    gpio_port_write(GPIO_PORT_DHT11_DATA, GPIO_PORT_LEVEL_HIGH);
    timer_port_delay_us(DHT11_RELEASE_US);
    r = gpio_port_set_dir(GPIO_PORT_DHT11_DATA, GPIO_PORT_DIR_INPUT);
    if (r != PORT_OK) { return r; }

    /* 2. 响应：DHT11 拉低 80us → 拉高 80us → 拉低进入数据位 */
    r = dht11_wait_level(GPIO_PORT_LEVEL_LOW, DHT11_RESP_TIMEOUT_US, 0);
    if (r != PORT_OK) { return r; }
    r = dht11_wait_level(GPIO_PORT_LEVEL_HIGH, DHT11_RESP_TIMEOUT_US, 0);
    if (r != PORT_OK) { return r; }
    r = dht11_wait_level(GPIO_PORT_LEVEL_LOW, DHT11_BIT_LOW_TIMEOUT_US, 0);
    if (r != PORT_OK) { return r; }

    /* 3. 接收 40 位：5 字节 x 8 位，先高位后低位 */
    for (i = 0; i < DHT11_DATA_BYTES; i++) {
        data[i] = 0;
        for (bit_idx = 0; bit_idx < 8; bit_idx++) {
            /* 位起始低电平结束（进入高） */
            r = dht11_wait_level(GPIO_PORT_LEVEL_HIGH,
                                 DHT11_BIT_LOW_TIMEOUT_US, 0);
            if (r != PORT_OK) { return r; }
            /* 高电平持续期：等待回落，用时长区分 0/1 */
            r = dht11_wait_level(GPIO_PORT_LEVEL_LOW,
                                 DHT11_BIT_HIGH_TIMEOUT_US, &elapsed);
            if (r != PORT_OK) { return r; }
            data[i] <<= 1;
            if (elapsed > DHT11_ONE_THRESHOLD_US) {
                data[i] |= 1u;
            }
        }
    }

    /* 4. 校验和：前 4 字节之和低 8 位 == 第 5 字节 */
    if ((uint8_t)(data[0] + data[1] + data[2] + data[3]) != data[4]) {
        return PORT_ERR_STATE;
    }

    *humi = data[0];
    *temp = (int16_t)data[2];
    return PORT_OK;
}

int32_t driver_dht11_deinit(void)
{
    return gpio_port_deinit(GPIO_PORT_DHT11_DATA);
}

/**
 * 等待总线电平变化（1us 步进轮询，带超时保护）。
 * @param elapsed_us 输出可空：等待经历的时间（用于 0/1 位宽判定）。
 */
static int32_t dht11_wait_level(gpio_port_level_t want, uint32_t timeout_us,
                                uint32_t *elapsed_us)
{
    gpio_port_level_t level;
    uint32_t t = 0;
    int32_t r;

    for (;;) {
        r = gpio_port_read(GPIO_PORT_DHT11_DATA, &level);
        if (r != PORT_OK) { return r; }
        if (level == want) {
            if (elapsed_us != 0) { *elapsed_us = t; }
            return PORT_OK;
        }
        if (t >= timeout_us) {
            return PORT_ERR_TIMEOUT;
        }
        timer_port_delay_us(1u);
        t++;
    }
}
