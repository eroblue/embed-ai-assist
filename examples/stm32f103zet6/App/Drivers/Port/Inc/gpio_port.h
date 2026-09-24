/**
 * @file    gpio_port.h
 * @brief   GPIO Port 接口（平台无关）
 *
 * 逻辑引脚按"用途"命名（LED_EXEC / KEY_MODE...），不按封装引脚号——
 * 引脚号/有效电平只存在于 manifest 数据侧（hw_instance + active_level），
 * 换板不改代码。
 *
 * 本工程用不到边沿中断（按键为 10ms 轮询去抖），EXTI 相关接口已裁剪。
 *
 * [扩展] 说明：
 *  - set_dir：运行时换向（DHT11 单总线时序需要 输出起始信号 → 输入读响应）
 *  - set_active / read_active：有效电平语义（"激活"=点亮/按下/鸣响），
 *    低有效 LED 与高有效蜂鸣器由 manifest 实例的 active_level 区分，
 *    APP/Driver 统一按 active 语义调用，不感知电平极性。
 */
#ifndef GPIO_PORT_H
#define GPIO_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑引脚（用途命名） */
typedef enum {
    GPIO_PORT_LED_EXEC = 0,    /* 执行器指示灯（自动模式告警联动） */
    GPIO_PORT_LED_RUN = 1,     /* 运行指示灯（心跳/故障闪烁） */
    GPIO_PORT_BUZZER = 2,      /* 蜂鸣器（告警提示音） */
    GPIO_PORT_KEY_MODE = 3,    /* 模式切换按键 */
    GPIO_PORT_KEY_SWITCH = 4,  /* 手动开关按键 */
    GPIO_PORT_KEY_MUTE = 5,    /* 静音切换按键 */
    GPIO_PORT_DHT11_DATA = 6,  /* DHT11 单总线数据引脚 */
    GPIO_PORT_COUNT
} gpio_port_id_t;

typedef enum {
    GPIO_PORT_DIR_INPUT = 0,
    GPIO_PORT_DIR_OUTPUT = 1,
} gpio_port_dir_t;

typedef enum {
    GPIO_PORT_PULL_NONE = 0,
    GPIO_PORT_PULL_UP = 1,
    GPIO_PORT_PULL_DOWN = 2,
} gpio_port_pull_t;

typedef enum {
    GPIO_PORT_LEVEL_LOW = 0,
    GPIO_PORT_LEVEL_HIGH = 1,
} gpio_port_level_t;

typedef struct {
    gpio_port_dir_t   dir;         /* 方向 */
    gpio_port_pull_t  pull;        /* 输入时的上下拉；输出忽略 */
    gpio_port_level_t init_level;  /* 输出初始电平；输入忽略 */
    gpio_port_level_t active_level;/* [扩展] 激活态电平：set_active/read_active 的极性依据 */
} gpio_port_cfg_t;

/** 绑定逻辑引脚与配置。 */
int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg);

/** 反初始化。 */
int32_t gpio_port_deinit(gpio_port_id_t id);

/** 读输入电平（输出引脚读回实际输出）。 */
int32_t gpio_port_read(gpio_port_id_t id, gpio_port_level_t *level);

/** 写输出电平。 */
int32_t gpio_port_write(gpio_port_id_t id, gpio_port_level_t level);

/** 翻转输出。 */
int32_t gpio_port_toggle(gpio_port_id_t id);

/** [扩展] 运行时切换方向（单总线器件时序用；pull 沿用 init 配置）。 */
int32_t gpio_port_set_dir(gpio_port_id_t id, gpio_port_dir_t dir);

/** [扩展] 按有效电平写：active != 0 写激活电平，否则写非激活电平。 */
int32_t gpio_port_set_active(gpio_port_id_t id, uint8_t active);

/** [扩展] 按有效电平读：激活返回 1，否则 0。 */
int32_t gpio_port_read_active(gpio_port_id_t id, uint8_t *active);

#ifdef __cplusplus
}
#endif

#endif /* GPIO_PORT_H */
