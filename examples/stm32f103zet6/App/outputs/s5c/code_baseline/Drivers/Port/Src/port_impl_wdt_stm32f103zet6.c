/* port_impl_wdt_stm32f103zet6.c - Watchdog Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json）：
 *   WDT_PORT_SYSTEM → hw_instance="IWDG"（来源 design_input）。
 *
 * 超时换算（本层职责，基数据取 hardware_capabilities 的 wdt 能力标签
 * lsi-40khz / prescaler-4to256 / reload-12bit）：
 *   T = (4 × 2^PR) × (RLR + 1) / F_LSI；取**最小预分频**使 RLR 落进 12 位
 *   （精度最高）。量程 ≈ 0.1ms（div 4 × 1 拍）~ 26.2s（div 256 × 4096 拍），
 *   超出返回 PORT_ERR_PARAM。整数取整使实际超时略小于请求值（偏安全）。
 *   超时值由 APP 经 wdt_port_init(timeout_ms) 传入（**应用策略**）。
 *
 * 无 S5a 看门狗初始化可对接：IWDG 无时钟门控（LSI 由硬件在使能时自动开启）、
 * 无引脚、无 NVIC——S5a 只声明能力，配置与启动全部在本层。
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "wdt_port.h"
#include "stm32f10x.h"
#include "stm32f10x_iwdg.h"
#include "stm32f10x_rcc.h"

/* ---- 文件内私有上下文（static，按 instance id 索引，禁动态分配） ---- */
typedef struct {
    uint8_t bound;      /* 看门狗已由本层启动（IWDG 不可关闭，启动后恒为 1） */
} wdt_impl_ctx_t;

static wdt_impl_ctx_t s_wdt_ctx[WDT_PORT_COUNT];

/* IWDG 换算基（hardware_capabilities）：LSI ≈ 40kHz，PR 3 位（档位 4~256），RLR 12 位 */
#define WDT_LSI_HZ       40000u
#define WDT_RLR_MAX      4095u
#define WDT_PRESC_COUNT  7u

/* 档位表索引 = PR 位值（0..6）→ 实际分频 = 4 × 2^PR */
static const uint16_t s_wdt_presc[WDT_PRESC_COUNT] = {
    IWDG_Prescaler_4, IWDG_Prescaler_8, IWDG_Prescaler_16, IWDG_Prescaler_32,
    IWDG_Prescaler_64, IWDG_Prescaler_128, IWDG_Prescaler_256,
};

int32_t wdt_port_init(wdt_port_id_t id, uint32_t timeout_ms)
{
    uint8_t  sel;
    uint32_t ticks = 0u;

    if ((uint32_t)id >= (uint32_t)WDT_PORT_COUNT || timeout_ms == 0u) {
        return PORT_ERR_PARAM;
    }
    wdt_impl_ctx_t *ctx = &s_wdt_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;      /* IWDG 已启动且不可关闭（硬件特性） */
    }

    /* 计数拍数 = T × F_LSI / (4 × 2^PR) = timeout_ms × (F_LSI/4000) / 2^PR
       （F_LSI/4000 = 10，整除无损失）；选最小 PR 使拍数 ≤ 4096（RLR = 拍数-1） */
    for (sel = 0u; sel < WDT_PRESC_COUNT; sel++) {
        ticks = (timeout_ms * (WDT_LSI_HZ / 4000u)) / ((uint32_t)1u << sel);
        if (ticks == 0u) {
            ticks = 1u;             /* 兜底：低于最小刻度时按 1 拍 */
        }
        if (ticks <= (WDT_RLR_MAX + 1u)) {
            break;
        }
    }
    if (sel >= WDT_PRESC_COUNT) {
        return PORT_ERR_PARAM;      /* 超时超出 IWDG 量程（> ≈26.2s） */
    }

    IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable);      /* 解除 PR/RLR 写保护 */
    IWDG_SetPrescaler((uint8_t)s_wdt_presc[sel]);      /* 分频 4 × 2^PR */
    IWDG_SetReload((uint16_t)(ticks - 1u));            /* RLR = 拍数 - 1 */
    IWDG_ReloadCounter();                              /* 先装载，再启动 */
    IWDG_Enable();
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t wdt_port_feed(wdt_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)WDT_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    if (!s_wdt_ctx[id].bound) {
        return PORT_ERR_STATE;      /* 未启动，喂狗无意义 */
    }
    /* IWDG_ReloadCounter 只写 Key 寄存器（0xAAAA），无阻塞、无锁 → ISR 安全 */
    IWDG_ReloadCounter();
    return PORT_OK;
}

int32_t wdt_port_reset_caused(wdt_port_id_t id, uint8_t *caused)
{
    if ((uint32_t)id >= (uint32_t)WDT_PORT_COUNT || caused == (uint8_t *)0) {
        return PORT_ERR_PARAM;
    }
    /* 复位原因属**上电状态查询**，不依赖本层 init：典型的启动自检在
       wdt_port_init 之前读取"上一次复位原因"，故此处不检查 bound。 */
    *caused = (RCC_GetFlagStatus(RCC_FLAG_IWDGRST) != RESET) ? 1u : 0u;
    /* RCC 无单标志清除位：清除即清整组复位标志（RCC_CSR.RMVF），硬件语义如此 */
    RCC_ClearFlag();
    return PORT_OK;
}
