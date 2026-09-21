/* ft61f14x_sfr.h - FT61F14X SFR 寄存器定义（S5a hardware-initializer 生成，FT61F143A-RB）
 * 地址与位名来自 outputs/chip_info/registers.json（datasheet ft61f14x_ds_rev1p09 提取）。
 * FT61F 无标准外设库，统一 volatile 指针访问；跨 bank 访问由编译器/启动代码处理。
 * 仅登记 S5a 用到的寄存器，未用寄存器不臆造。 */
#ifndef FT61F14X_SFR_H
#define FT61F14X_SFR_H

/* ---------------- 通用 SFR 访问 ---------------- */
#define SFR8(addr)  (*(volatile unsigned char *)(addr))

/* ---------------- 时钟（OSC，章节5） ---------------- */
#define OSCCON      SFR8(0x99)   /* TUN<7:0> HIRC 校准 */
#define PCKEN       SFR8(0x9A)   /* 外设时钟：bit0 ADCEN / bit1 TIM1EN / bit2 TIM2EN / bit3 TIM4EN / bit<5:4> UARTEN */
#define TCKSRC      SFR8(0x31F)  /* T1CKSRC<2:0> TIM1 时钟源 / T2CKSRC<6:3> TIM2 时钟源 / bit7 LFMOD */

/* PCKEN 位掩码 */
#define PCKEN_ADCEN     0x01u
#define PCKEN_TIM1EN    0x02u
#define PCKEN_TIM2EN    0x04u
#define PCKEN_TIM4EN    0x08u
#define PCKEN_UARTEN    0x30u   /* bit<5:4> 两字段，写 11 使能 UART */

/* TCKSRC：TIM1 时钟源选择（T1CKSRC<2:0>，手册 10.3：000=fMASTER/4? 以手册表格为准） */
#define T1CKSRC_HIRC    0x01u   /* TODO: 依据手册 10.3 时钟源表核对编码（示例代码 STR TCKSRC H'01 选 HIRC） */

/* ---------------- 中断（INTC，章节6） ---------------- */
#define INTCON      SFR8(0x0B)  /* bit7 GIE / bit6 PEIE / bit5 EEIE / bit4 LVDIE / bit3 OSFIE
                                 * bit2 EEIF / bit1 LVDIF / bit0 OSFIF */
#define PIE1        SFR8(0x91)  /* bit1 CKMIE / bit0 ADCIE */
#define PIR1        SFR8(0x11)  /* bit1 CKMIF / bit0 ADCIF */

#define INTCON_GIE      0x80u
#define INTCON_PEIE     0x40u

/* ---------------- GPIO（章节14，FT61F143A SOP16 使用 PA/PB/PC） ---------------- */
#define PORTA       SFR8(0x0C)
#define PORTB       SFR8(0x0D)
#define PORTC       SFR8(0x0E)
#define TRISA       SFR8(0x8C)  /* 1=输入（复位默认全 1），0=输出 */
#define TRISB       SFR8(0x8D)
#define TRISC       SFR8(0x8E)
#define WPUA        SFR8(0x18C) /* 弱上拉使能 */

/* ---------------- TIM1（章节10，高级定时器） ---------------- */
#define TIM1CR1     SFR8(0x211) /* bit0 T1CEN / bit7 T1ARPE */
#define TIM1CR2     SFR8(0x212)
#define TIM1SMCR    SFR8(0x213)
#define TIM1ETR     SFR8(0x214)
#define TIM1IER     SFR8(0x215)
#define TIM1SR1     SFR8(0x216)
#define TIM1SR2     SFR8(0x217)
#define TIM1EGR     SFR8(0x218) /* bit0 T1UG 产生更新事件 */
#define TIM1CCMR1   SFR8(0x219) /* bit<1:0> T1CC1S / bit3 T1OC1PE / bit<6:4> T1OC1M */
#define TIM1CCMR2   SFR8(0x21A)
#define TIM1CCMR3   SFR8(0x21B)
#define TIM1CCMR4   SFR8(0x21C)
#define TIM1CCER1   SFR8(0x21D) /* bit0 T1CC1E / bit1 T1CC1P / bit<3:2> T1CC1NE/NP */
#define TIM1CCER2   SFR8(0x21E)
#define TIM1CNTRH   SFR8(0x28C)
#define TIM1CNTRL   SFR8(0x28D)
#define TIM1PSCRH   SFR8(0x28E) /* 预分频高字节（仅低 4 位有效） */
#define TIM1PSCRL   SFR8(0x28F)
#define TIM1ARRH    SFR8(0x290) /* 自动重载高字节 */
#define TIM1ARRL    SFR8(0x291)
#define TIM1RCR     SFR8(0x292)
#define TIM1CCR1H   SFR8(0x293) /* 捕捉/比较 1 高字节 */
#define TIM1CCR1L   SFR8(0x294)
#define TIM1BKR     SFR8(0x29B) /* bit7 T1MOE 主输出使能 / bit6 T1AOE / bit5 T1BKP / bit4 T1BKE */
#define TIM1DTR     SFR8(0x29C)
#define TIM1OISR    SFR8(0x29D)

/* TIM1 位操作 */
#define TIM1CR1_CEN     0x01u
#define TIM1CR1_ARPE    0x80u
#define TIM1CCMR1_OC1M_PWM1      (0x06u << 4)  /* OC1M=110：PWM 模式 1 */
#define TIM1CCMR1_OC1PE          (0x01u << 3)  /* 输出比较 1 预装载 */
#define TIM1CCER1_CC1E  0x01u
#define TIM1CCER1_CC1P  0x02u
#define TIM1EGR_UG      0x01u
#define TIM1BKR_MOE     0x80u

/* ---------------- USART（章节13） ---------------- */
#define URDATAL     SFR8(0x48C) /* 数据低位（发送/接收共用？以手册 13.3.1 为准） */
#define URDATAH     SFR8(0x48D)
#define URIER       SFR8(0x48E) /* bit0 URRXNE / bit1 URTE / bit2 RXSE / bit3 IDELE / bit<5:4> TCIE */
#define URLCR       SFR8(0x48F) /* bit0 EXTEN / bit1 RWU */
#define URLCREXT    SFR8(0x490)
#define URMCR       SFR8(0x491) /* bit3 RXEN / bit4 TXEN / bit1 HDSEL / bit2 WAKE */
#define URLSR       SFR8(0x492) /* bit0 RXNEF / bit1 OVERF / bit2 PEF / bit3 FEF / bit4 BKF / bit5 TXEF / bit6 IDLEF / bit7 ADDRF */
#define URRAR       SFR8(0x493)
#define URDLL       SFR8(0x494) /* 波特率除数低字节 DL<7:0> */
#define URDLH       SFR8(0x495) /* 波特率除数高字节 DL<7:0> */
#define URABCR      SFR8(0x496) /* 自动波特率控制 */
#define URSYNCR     SFR8(0x497)
#define URLINCR     SFR8(0x498)
#define URSDCR0     SFR8(0x499) /* 波特率相关配置 0 */
#define URSDCR1     SFR8(0x49A)
#define URSDCR2     SFR8(0x49B)
#define URTC        SFR8(0x49C)

#define URMCR_RXEN     0x08u
#define URMCR_TXEN     0x10u

#endif /* FT61F14X_SFR_H */
