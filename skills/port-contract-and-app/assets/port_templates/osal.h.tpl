/**
 * @file    osal.h.tpl
 * @brief   OSAL 操作系统抽象层模板（平台无关，RTOS 工程专用）
 *
 * 硬约束（见 references/osal_design_principle.md）：
 *  - 接口名不得出现任何 RTOS 原生 API 名（xTask/rt_thread/k_ 等前缀禁止）
 *  - ISR 上下文可调的版本独立命名（*_from_isr 后缀），与任务版并存
 *  - 裸机（rtos=none）工程不生成本文件；flat+RTOS 组合由任务书提示
 *  - 任务创建统一收敛在 app.c（阶段 B），各模块不自行建任务
 *
 * 按需裁剪：整类能力（如事件组）未用 → 整段删除；登记 manifest 时只列保留项。
 */
#ifndef OSAL_H
#define OSAL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- 通用定义 ---------------- */
typedef void *osal_task_t;    /* 任务句柄（不透明指针） */
typedef void *osal_queue_t;  /* 队列句柄 */
typedef void *osal_mutex_t;  /* 互斥锁句柄 */
typedef void *osal_sem_t;    /* 信号量句柄 */
typedef void *osal_event_t;  /* 事件组句柄 */

typedef enum {
    OSAL_OK = 0,
    OSAL_ERR_PARAM = -1,
    OSAL_ERR_TIMEOUT = -2,   /* 等待超时 */
    OSAL_ERR_RESOURCE = -3,  /* 资源不足/创建失败 */
} osal_err_t;

#define OSAL_WAIT_FOREVER 0xFFFFFFFFU  /* 无限等待 */

/* ---------------- 任务 ---------------- */

/** 任务入口（原型与底层 RTOS 无关）。 */
typedef void (*osal_task_func_t)(void *arg);

typedef struct {
    const char      *name;      /* 任务名（调试用） */
    uint32_t         stack_size;/* 栈大小（字节；实现层按 RTOS 单位换算） */
    uint8_t          priority;  /* 优先级 0(最低)~255(最高)；实现层线性映射 */
} osal_task_cfg_t;

int32_t osal_task_create(osal_task_t *task, const osal_task_cfg_t *cfg,
                         osal_task_func_t entry, void *arg);
int32_t osal_task_delete(osal_task_t task);
void    osal_task_yield(void);

/* ---------------- 队列（定长消息，元素大小固定） ---------------- */

int32_t osal_queue_create(osal_queue_t *queue, uint16_t item_size, uint16_t depth);
int32_t osal_queue_send(osal_queue_t queue, const void *item, uint32_t timeout_ms);
/** ISR 上下文版本（不允许阻塞，队列满直接失败）。 */
int32_t osal_queue_send_from_isr(osal_queue_t queue, const void *item);
int32_t osal_queue_recv(osal_queue_t queue, void *item, uint32_t timeout_ms);

/* ---------------- 互斥锁（任务间共享资源保护；禁止 ISR 使用） ---------------- */

int32_t osal_mutex_create(osal_mutex_t *mutex);
int32_t osal_mutex_lock(osal_mutex_t mutex, uint32_t timeout_ms);
int32_t osal_mutex_unlock(osal_mutex_t mutex);

/* ---------------- 信号量（事件计数 / 二值同步） ---------------- */

int32_t osal_sem_create(osal_sem_t *sem, uint32_t init_count);
int32_t osal_sem_take(osal_sem_t sem, uint32_t timeout_ms);
int32_t osal_sem_give(osal_sem_t sem);
int32_t osal_sem_give_from_isr(osal_sem_t sem);

/* ---------------- 事件组（多事件按位等待）【未用整段删】 ---------------- */

int32_t osal_event_create(osal_event_t *event);
int32_t osal_event_set(osal_event_t event, uint32_t bits);
int32_t osal_event_set_from_isr(osal_event_t event, uint32_t bits);
/** 等待任意 bits 置位；clear_on_exit=1 时满足条件自动清除。 */
int32_t osal_event_wait(osal_event_t event, uint32_t bits, uint8_t clear_on_exit,
                        uint32_t timeout_ms, uint32_t *out_bits);

/* ---------------- 时间 ---------------- */

uint32_t osal_now_ms(void);          /* 系统节拍毫秒（与 timer_port_now_ms 语义一致） */
void     osal_delay_ms(uint32_t ms); /* 任务延时（让出 CPU；ISR 禁用） */

/* ---------------- 临界区【短小区域专用，禁止嵌套调用非本项目函数】 ---------------- */

void osal_enter_critical(void);
void osal_exit_critical(void);

/* [扩展] 静态任务/低功耗 tickless 钩子等按需扩展，命名 osal_<能力>_<动词>。 */

#ifdef __cplusplus
}
#endif

#endif /* OSAL_H */
