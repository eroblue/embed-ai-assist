/* fsmc_init.c - FSMC LCD 并口控制器：Bank1/NE4，16 位，Mode B（S5a hardware-initializer 生成，stm32f103zet6） */
#include "fsmc_init.h"
#include "stm32f10x.h"
#include "stm32f10x_fsmc.h"
#include "stm32f10x_rcc.h"

void fsmc_lcd_init(void)
{
    FSMC_NORSRAMTimingInitTypeDef read_timing;
    FSMC_NORSRAMTimingInitTypeDef write_timing;
    FSMC_NORSRAMInitTypeDef fsmc;

    /* 引脚（D0~D15/NOE/NWE/A10/NE4，复用推挽）在 gpio_init.c 中配置，
       本函数只有 bank 与时序本体 */

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_FSMC, ENABLE);

    /* 读写独立时序（ExtendedMode + AccessMode B），参数为设计输入
       ILI9341 类典型值，请按实际 LCD 手册微调（docs/s5a_design_input.md） */
    read_timing.FSMC_AddressSetupTime = 0;
    read_timing.FSMC_AddressHoldTime = 0;
    read_timing.FSMC_DataSetupTime = 15;
    read_timing.FSMC_BusTurnAroundDuration = 0;
    read_timing.FSMC_CLKDivision = 2;
    read_timing.FSMC_DataLatency = 2;
    read_timing.FSMC_AccessMode = FSMC_AccessMode_B;

    write_timing = read_timing;

    /* Bank1 NOR/SRAM 区域 4（NE4 片选，基址 0x6C000000），SRAM 异步 16 位 */
    fsmc.FSMC_Bank = FSMC_Bank1_NORSRAM4;
    fsmc.FSMC_DataAddressMux = FSMC_DataAddressMux_Disable;
    fsmc.FSMC_MemoryType = FSMC_MemoryType_SRAM;
    fsmc.FSMC_MemoryDataWidth = FSMC_MemoryDataWidth_16b;
    fsmc.FSMC_BurstAccessMode = FSMC_BurstAccessMode_Disable;
    fsmc.FSMC_AsynchronousWait = FSMC_AsynchronousWait_Disable;
    fsmc.FSMC_WaitSignalPolarity = FSMC_WaitSignalPolarity_Low;
    fsmc.FSMC_WrapMode = FSMC_WrapMode_Disable;
    fsmc.FSMC_WaitSignalActive = FSMC_WaitSignalActive_BeforeWaitState;
    fsmc.FSMC_WriteOperation = FSMC_WriteOperation_Enable;
    fsmc.FSMC_WaitSignal = FSMC_WaitSignal_Disable;
    fsmc.FSMC_ExtendedMode = FSMC_ExtendedMode_Enable;
    fsmc.FSMC_WriteBurst = FSMC_WriteBurst_Disable;
    fsmc.FSMC_ReadWriteTimingStruct = &read_timing;
    fsmc.FSMC_WriteTimingStruct = &write_timing;
    FSMC_NORSRAMInit(&fsmc);

    FSMC_NORSRAMCmd(FSMC_Bank1_NORSRAM4, ENABLE);
}
