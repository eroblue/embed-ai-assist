#ifndef __NVIC_INIT_H
#define __NVIC_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* NVIC 中断优先级分组（分组 2：2 位抢占 + 2 位响应；不使能具体 IRQ） */
void nvic_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __NVIC_INIT_H */
