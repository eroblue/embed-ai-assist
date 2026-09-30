/**
 * @file    wdt_port.h.tpl
 * @brief   Watchdog Port 接口模板（平台无关）——通用必备外设
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md 第九节）。
 * 看门狗与具体应用需求无关（任何固件都需要存活监测），故本模板是**默认接口**：
 * 工程用到看门狗时直接取用，不必每次重新设计接口形态。
 *
 * 职责划分（应用策略 vs 硬件事实分置）：
 *   - 超时窗口（timeout_ms）是**应用策略**，由调用方（APP）在 wdt_port_init
 *     传入——APP 决定"多久未喂狗即复位"；
 *   - S5a 只提供**硬件事实**（时钟源/可用性/参数换算基），见
 *     hardware_capabilities；本模板不假设 S5a 已固化任何预分频/重装载值；
 *   - S5c 按 timeout_ms 换算并配置硬件（写 PR/RLR）+ 启动（Enable），
 *     超时换算基以 S5a 能力清单为准（如 IWDG 的 LSI 频率）。
 *
 * 注意：多数 MCU 的独立看门狗一旦启动不可关闭，故模板不提供 deinit。
 */
#ifndef WDT_PORT_H
#define WDT_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,   /* id 越界 / 出参为 NULL / timeout_ms 超量程 */
    PORT_ERR_STATE = -2,   /* 重复 init / 未 init */
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑看门狗实例（用途命名） */
typedef enum {
    WDT_PORT_SYSTEM = 0,   /* 系统看门狗：整个固件的存活监测 */
    WDT_PORT_COUNT
} wdt_port_id_t;

/**
 * 启动看门狗。
 * @param timeout_ms 超时窗口（毫秒）：**应用策略，由调用方决定**——
 *   "多久未喂狗即复位"；须大于实际喂狗间隔（通常数倍余量）。
 *   超出实现层量程返回 PORT_ERR_PARAM（换档/上限见实现文件头登记）。
 * @note 独立看门狗一旦启动不可关闭；重复调用返回 PORT_ERR_STATE。
 * @context task
 */
int32_t wdt_port_init(wdt_port_id_t id, uint32_t timeout_ms);

/**
 * 喂狗（刷新计数）。须在 timeout_ms 窗口内周期调用，否则触发复位。
 * @context isr/task 均可——只写硬件 Key 寄存器，无阻塞、无锁。
 */
int32_t wdt_port_feed(wdt_port_id_t id);

/**
 * 查询上次复位是否由看门狗引起（读并清复位标志）。
 * @param caused 出参：1=是，0=否（启动自检/日志用）
 * @context task
 */
int32_t wdt_port_reset_caused(wdt_port_id_t id, uint8_t *caused);

/* [扩展] 窗口看门狗（WWDG）/ 喂狗钩子按需扩展。
 * MCU 无看门狗硬件时由 S5c 报能力缺口（capability_gap），
 * 不得用软件计数假装实现。 */

#ifdef __cplusplus
}
#endif

#endif /* WDT_PORT_H */