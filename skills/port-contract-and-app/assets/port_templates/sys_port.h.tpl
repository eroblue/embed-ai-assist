/**
 * @file    sys_port.h.tpl
 * @brief   System Port 接口模板（平台无关）——OTA App 向量表重定向
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md 第九节）。
 * 生成条件：config project.flash_offset > 0 且非 flat 架构（OTA App 场景；
 * flash_offset=0 不生成本头文件，main.c 也不含重定位调用）。
 *
 * 职责划分（应用策略 vs 硬件事实分置）：
 *   - 偏移量（flash_offset）是**应用/部署策略**，值来自 config
 *     project.flash_offset，由调用方（main.c 首句）显式传入——偏移量在
 *     代码中字面可见，不藏进编译宏或构建参数；
 *   - Flash 基址（如 0x08000000）、VTOR 对齐要求（M3 常为 512 字节）是
 *     **硬件事实**，由 S5c 实现层从厂商头文件（FLASH_BASE）与内核手册取得，
 *     不进本契约；
 *   - S7b 链接脚本消费同一 config 值（ORIGIN=基址+偏移，LENGTH=容量-偏移），
 *     S6/S9 合并/烧录同理——三处必须一致，本接口的字面量即锚点。
 *
 * 调用时机（硬约束）：必须在**任何中断使能之前**执行（通常为 main 首句、
 * hal_init 之前）；SystemInit 已将 VTOR 设为默认基址，本接口覆盖之。
 * S5c 实现须在写 VTOR 后加 DSB/ISB 屏障（ARM 推荐惯例）。
 */
#ifndef SYS_PORT_H
#define SYS_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,   /* 偏移量未对齐（对齐要求见实现文件头登记）/ 超出 Flash 容量 */
    PORT_ERR_STATE = -2,   /* 重复 init / 未 init */
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/**
 * 向量表重定位（OTA App：把 VTOR 从 Flash 基址指向 基址+flash_offset）。
 * @param flash_offset App 在 Flash 中的重定向偏移（字节，相对 Flash 基址）：
 *   与 config project.flash_offset、S7b 链接脚本的 ORIGIN 偏移必须一致；
 *   须满足芯片 VTOR 对齐要求（如 Cortex-M3 为 512 字节），否则 PORT_ERR_PARAM。
 * @note 须在任何中断使能之前调用（main 首句）；重复调用允许（幂等重设）。
 * @context task（仅启动早期）
 */
int32_t sys_port_relocate_vector(uint32_t flash_offset);

/* [扩展] 系统复位原因查询 / 低功耗模式入口等系统级接口按需扩展，
 * 仍须遵守平台无关约束（寄存器/厂商符号只进 S5c 实现）。 */

#ifdef __cplusplus
}
#endif

#endif /* SYS_PORT_H */
