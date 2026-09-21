/* uart_init.c - USART 初始化（S5a hardware-initializer 生成，FT61F143A-RB）
 *
 * 硬件连接（任务书第 3 节，S4 facts）：
 * - TX = PA6（net NetR3_2，经串口芯片连接上位机调试口）
 * - RX = PA7（net NetR2_2）
 * - 参数：115200-8N1（SYSCLK 16MHz HIRC）
 */
#include "uart_init.h"
#include "ft61f14x_sfr.h"

void uart_usart_init(void)
{
    /* PA6(TX) 输出、PA7(RX) 输入（TRISA 复位默认全 1=输入，仅把 TX 改输出） */
    TRISA &= ~(1u << 6);   /* TRISA.6 = 0：PA6 输出 */
    /* TRISA.7 保持 1：PA7 输入 */

    /* 波特率除数：DL = SYSCLK / baud = 16000000 / 115200 = 138.89 ≈ 139 (0x008B)
     * 实际波特率 16000000/139 = 115108Hz，误差 -0.08%。
     * TODO: 波特率公式以手册 13 章为准（若为 Fsys/DL 直除则上值正确；
     *       若有 16 分频模式需查 URSDCR0~2 采样配置后修正）。 */
    URDLH = 0x00u;
    URDLL = 139u;

    /* 帧格式 8N1：FT61F UART 复位默认 8 数据位/无校验/1 停止位。
     * TODO: 如需修改校验/停止位，查手册 13 章帧格式寄存器（URLCR/URSDCRx）。 */

    /* 收发使能（URMCR：bit3 RXEN / bit4 TXEN），中断不使能（任务书规则 5） */
    URMCR = URMCR_RXEN | URMCR_TXEN;
    /* 注：若需接收中断，先注册 handler 再置 URIER.URRXNE(bit0)
     * 并开 INTCON.GIE，见 nvic_init.c 使能建议。 */
}

void uart_init(void)
{
    uart_usart_init();
}
