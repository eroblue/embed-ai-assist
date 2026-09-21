/* nvic_init.c - 全局中断框架初始化（S5a hardware-initializer 生成，FT61F143A-RB）
 *
 * FT61F 为 8 位机，中断控制器为 INTC（无 NVIC 优先级分组概念）：
 * - INTCON.GIE（bit7）：全局中断总开关
 * - INTCON.PEIE（bit6）：外设中断总开关
 *
 * 任务书规则：只搭全局框架，不使能任何具体中断源
 * （避免未注册 handler 时中断落入默认向量死循环）。
 */
#include "nvic_init.h"
#include "ft61f14x_sfr.h"

void nvic_init(void)
{
    /* 保持 GIE/PEIE 关闭（复位默认 0）——外设初始化期间不开总中断。
     * 注：位写法遵循手册"位清除专用指令"惯例，直接 AND 清零。 */
    INTCON &= ~(unsigned char)(INTCON_GIE | INTCON_PEIE);

    /* 使能建议（应用层注册好中断服务函数后按需打开）：
     * - UART 接收中断：URIER.URRXNE（bit0）→ INTCON |= INTCON_GIE;
     * - TIM1 更新/CC 中断：TIM1IER（0x215）对应位 → INTCON |= INTCON_GIE | INTCON_PEIE;
     * 具体中断向量号与入口写法以 datasheet 章节表（中断向量表）为准。
     */
}
