/**
 * @file    power_port.h.tpl
 * @brief   Power 低功耗接口模板（平台无关，power.enabled=true 时生成）
 *
 * 命名来源优先级（见 references/port_design_principle.md 第八章）：
 *  1. 设计输入/已有方案指定的接口名（用户方案优先——与现有低功耗框架对接时
 *     【必须】改成本项目的命名，本模板只是无方案时的典型集）
 *  2. 本典型集（与主循环结构配套的三段式钩子）
 * 用户采纳/修改后，naming_source 与最终接口清单写入 manifest.power。
 *
 * 典型三段式（主循环空闲时）：
 *   power_port_enter_sleep_before();   ← 停外设/记录唤醒源（可含 __WFI）
 *   power_port_enter_sleep();
 *   power_port_wakeup_after_sleep();   ← 恢复时钟/补偿系统时间
 */
#ifndef POWER_PORT_H
#define POWER_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,   /* 时序错误（如未 init） */
} port_err_t;

/* 唤醒源（按项目实际裁剪；wakeup_after_sleep 回查用） */
typedef enum {
    POWER_PORT_WAKEUP_GPIO = 0,   /* 外部中断（按键等） */
    POWER_PORT_WAKEUP_UART = 1,   /* 串口起始位 */
    POWER_PORT_WAKEUP_RTC = 2,    /* RTC 定时到期 */
    POWER_PORT_WAKEUP_UNKNOWN = 3,
} power_port_wakeup_src_t;

int32_t power_port_init(void);
int32_t power_port_deinit(void);

/**
 * 睡前钩子：停用无关外设、配置唤醒源、保存需要恢复的状态。
 * @context task（主循环空闲分支调用）。
 */
int32_t power_port_enter_sleep_before(void);

/**
 * 进入睡眠（执行 WFI/WFE；实际睡眠深度由实现层按 MCU 能力定，
 * 深度约定写 manifest notes）。
 * @return 唤醒原因（POWER_PORT_WAKEUP_*）；浅睡实现可直接在钩子内不睡返回 UNKNOWN。
 */
int32_t power_port_enter_sleep(power_port_wakeup_src_t *wakeup_src);

/**
 * 醒后钩子：恢复时钟/外设状态。
 * 注意：多数 MCU 醒来先跑 HSI，实现层负责恢复主时钟再返回。
 */
int32_t power_port_wakeup_after_sleep(void);

/**
 * 睡眠补偿：睡眠期间的系统节拍修正（OSAL 时基不跳变的关键）。
 * @return 实际睡眠毫秒数（实现层按 RTC/LSI 计数估算）。
 */
uint32_t power_port_sleep_compensate_ms(void);

/* [扩展] 电源域开关（power_port_domain_on/off）、深度睡眠模式选择等按需扩展；
 * 若设计输入指定了别的方案（如 PM 组件钩子），本文件按方案重写而非套模板。 */

#ifdef __cplusplus
}
#endif

#endif /* POWER_PORT_H */
