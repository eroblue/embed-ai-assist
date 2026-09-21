/* fsmc_init.c - 外设初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "fsmc_init.h"
#include "gd32f20x.h"

void fsmc_lcd_init(void)
{
    rcu_periph_clock_enable(RCU_EXMC);
    /* Bank1 子bank0（NE1，基址 0x60000000）—— LCD 并口，8 位数据宽度
       时序为保守默认值（慢速），请按 LCD 驱动手册调整 setup 时间 */
    exmc_norsram_parameter_struct exmc_norsram_init_struct;
    exmc_norsram_timing_parameter_struct rw_timing;
    rw_timing.asyn_address_setuptime = 0x0FU;
    rw_timing.asyn_data_setuptime = 0xFFU;
    rw_timing.bus_latency = 0x0FU;
    exmc_norsram_init_struct.norsram_number = EXMC_BANK0_NORSRAM_REGION0;
    exmc_norsram_init_struct.write_mode = ENABLE;
    exmc_norsram_init_struct.asyn_wait = DISABLE;
    exmc_norsram_init_struct.norsram_signal = EXMC_NORSRAM_ASYNC_NORSRAM;
    exmc_norsram_init_struct.databus_width = EXMC_NOR_DATABUS_WIDTH_8B;
    exmc_norsram_init_struct.read_write_timing = rw_timing;
    exmc_norsram_init(&exmc_norsram_init_struct);
    exmc_norsram_enable(EXMC_BANK0_NORSRAM_REGION0);
}

void fsmc_init(void)
{
    fsmc_lcd_init();
}
