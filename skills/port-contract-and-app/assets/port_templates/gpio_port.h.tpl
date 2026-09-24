/**
 * @file    gpio_port.h.tpl
 * @brief   GPIO Port 接口模板（平台无关）
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md）。
 * 逻辑引脚命名按"用途"（LED_STATUS / KEY_OK），不按封装引脚号——
 * 引脚号只存在于 manifest 数据侧（hw_instance），换板不改代码。
 */
#ifndef GPIO_PORT_H
#define GPIO_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,
} port_err_t;

/* 逻辑引脚（用途命名） */
typedef enum {
    GPIO_PORT_LED_STATUS = 0,  /* 状态指示灯 */
    GPIO_PORT_LED_ERROR = 1,   /* 故障指示灯 */
    GPIO_PORT_KEY_OK = 2,      /* 确认按键 */
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

typedef enum {
    GPIO_PORT_EDGE_RISING = 0,   /* 上升沿 */
    GPIO_PORT_EDGE_FALLING = 1,  /* 下降沿 */
    GPIO_PORT_EDGE_BOTH = 2,     /* 双沿 */
} gpio_port_edge_t;

typedef struct {
    gpio_port_dir_t  dir;
    gpio_port_pull_t pull;       /* 输入时的上下拉；输出忽略 */
    gpio_port_level_t init_level;/* 输出初始电平；输入忽略 */
} gpio_port_cfg_t;

/**
 * 电平/边沿事件回调。
 * @context isr —— 由 EXTI 中断直接调用：只允许置标志/拷贝时间戳，
 *                 消抖等耗时处理放任务侧（OSAL 事件/队列投递）。
 */
typedef void (*gpio_port_event_cb_t)(gpio_port_id_t id, void *user_data);

int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg);
int32_t gpio_port_deinit(gpio_port_id_t id);

/** 读输入电平（输出引脚读回实际输出）。 */
int32_t gpio_port_read(gpio_port_id_t id, gpio_port_level_t *level);

/** 写输出电平。 */
int32_t gpio_port_write(gpio_port_id_t id, gpio_port_level_t level);

/** 翻转输出。 */
int32_t gpio_port_toggle(gpio_port_id_t id);

/** 使能边沿中断并注册回调（输入引脚专用；先消抖语义还是裸边沿由实现层定，
 *  约定写进 manifest notes）。 */
int32_t gpio_port_enable_irq(gpio_port_id_t id, gpio_port_edge_t edge,
                             gpio_port_event_cb_t cb, void *user_data);

/** 关闭边沿中断。 */
int32_t gpio_port_disable_irq(gpio_port_id_t id);

/* [扩展] 批量读/写（gpio_port_read_group 等）按需扩展。 */

#ifdef __cplusplus
}
#endif

#endif /* GPIO_PORT_H */
