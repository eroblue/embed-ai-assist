/* port_impl_par_stm32f103zet6.c - 16 位并行总线 Port 实现（S5c port-implementer 生成）
 *
 * 逻辑实例映射（outputs/s5b/port_interface_manifest.json）：
 *   PAR_PORT_LCD → FSMC Bank1-NE4（命令 0x6C000000 / 数据 0x6C000800，
 *   PG12=CS、PG0=RS，背光 PB0，hw_source=design_input）
 *
 * 对接 S5a 成果：fsmc_init.c 的 fsmc_lcd_init() 已完成总线控制器与时序配置
 * （含背光 PB0 点亮）；地址宏 FSMC_LCD_CMD_ADDR / FSMC_LCD_DATA_ADDR 同源。
 * 本实现只做地址映射与同步写直达——存储器映射写无"忙/超时"概念。
 *
 * 换板/换平台只改 manifest 数据侧与本文件，Port 头与 APP/Driver 不变。
 */
#include "par_port.h"
#include "fsmc_init.h"
#include "stm32f10x.h"

/* ---- 命令/数据地址（与 S5a fsmc_init.h 同源，manifest lcd_bus 实例登记） ----
 * 16 位总线 HADDR[25:1]→FSMC_A[24:0]，RS=A10 对应 HADDR[11]=0x800 */
#define PAR_LCD_CMD_ADDR   (*(volatile uint16_t *)0x6C000000UL)
#define PAR_LCD_DATA_ADDR  (*(volatile uint16_t *)0x6C000800UL)

/* ---- 文件内私有上下文（static，按 instance id 索引） ---- */
typedef struct {
    uint8_t bound;    /* 实例是否已 init 绑定（总线已由 S5a 初始化） */
} par_impl_ctx_t;

static par_impl_ctx_t s_par_ctx[PAR_PORT_COUNT];

int32_t par_port_init(par_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)PAR_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    par_impl_ctx_t *ctx = &s_par_ctx[id];
    if (ctx->bound) {
        return PORT_ERR_STATE;
    }
    /* S5a 成果：FSMC Bank1-NE4 总线控制器 + 16 位数据线 + PG12/PG0 + 背光 PB0 */
    fsmc_lcd_init();
    ctx->bound = 1u;
    return PORT_OK;
}

int32_t par_port_write_cmd(par_port_id_t id, uint16_t cmd)
{
    if ((uint32_t)id >= (uint32_t)PAR_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    if (!s_par_ctx[id].bound) {
        return PORT_ERR_STATE;
    }
    PAR_LCD_CMD_ADDR = cmd;         /* 同步写直达，无等待 */
    return PORT_OK;
}

int32_t par_port_write_data(par_port_id_t id, uint16_t data)
{
    if ((uint32_t)id >= (uint32_t)PAR_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    if (!s_par_ctx[id].bound) {
        return PORT_ERR_STATE;
    }
    PAR_LCD_DATA_ADDR = data;
    return PORT_OK;
}

int32_t par_port_write_data_block(par_port_id_t id, const uint16_t *buf,
                                  uint32_t len)
{
    if ((uint32_t)id >= (uint32_t)PAR_PORT_COUNT || buf == (const uint16_t *)0) {
        return PORT_ERR_PARAM;
    }
    if (!s_par_ctx[id].bound) {
        return PORT_ERR_STATE;
    }
    /* 同步拷贝语义：逐字写完返回（FSMC 写直达，无 DMA/缓冲语义） */
    for (uint32_t i = 0u; i < len; i++) {
        PAR_LCD_DATA_ADDR = buf[i];
    }
    return PORT_OK;
}

int32_t par_port_deinit(par_port_id_t id)
{
    if ((uint32_t)id >= (uint32_t)PAR_PORT_COUNT) {
        return PORT_ERR_PARAM;
    }
    par_impl_ctx_t *ctx = &s_par_ctx[id];
    if (!ctx->bound) {
        return PORT_OK;             /* 幂等 */
    }
    /* 总线控制器/背光归 S5a 管理，本层只解绑定（LCD 掉电序列归 driver_lcd） */
    ctx->bound = 0u;
    return PORT_OK;
}
