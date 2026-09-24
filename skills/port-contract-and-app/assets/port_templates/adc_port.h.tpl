/**
 * @file    adc_port.h.tpl
 * @brief   ADC Port 接口模板（平台无关）
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md）。
 * 逻辑通道按测量对象命名（NTC/VBAT），不是硬件通道号——
 * 硬件通道映射在 manifest 数据侧（hw_instance），由 S5c 翻译。
 */
#ifndef ADC_PORT_H
#define ADC_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,    /* 未 init / 转换进行中 */
    PORT_ERR_TIMEOUT = -3,  /* 转换超时（硬件异常） */
} port_err_t;

/* 逻辑通道（测量对象命名） */
typedef enum {
    ADC_PORT_NTC = 0,       /* 板载温度 NTC 分压 */
    ADC_PORT_VBAT = 1,      /* 电池电压检测 */
    ADC_PORT_COUNT
} adc_port_id_t;

typedef enum {
    ADC_PORT_REF_VDD = 0,   /* 基准 = VDD */
    ADC_PORT_REF_EXT = 1,   /* 外部基准（电压值进 cfg.ref_mv） */
} adc_port_ref_t;

typedef struct {
    adc_port_ref_t ref;     /* 基准源 */
    uint32_t       ref_mv;  /* 基准电压 mV（ref=EXT 时有效） */
    uint8_t        avg_count; /* 软件过采样次数（1=单次；奇数次中值/均值由实现定） */
} adc_port_cfg_t;

/**
 * 单次转换完成回调。
 * @context isr —— 转换结束中断直接调用，处理短小；数据处理放任务侧。
 */
typedef void (*adc_port_done_cb_t)(adc_port_id_t id, uint16_t raw, void *user_data);

int32_t adc_port_init(adc_port_id_t id, const adc_port_cfg_t *cfg);
int32_t adc_port_deinit(adc_port_id_t id);

/**
 * 同步单次采样（阻塞至转换完成；含 avg_count 次软件过采样处理）。
 * @param raw_mv 输出：换算后的毫伏值（基准换算在 Port 内完成，APP 不再算）
 * @return PORT_OK 或负值错误码。
 */
int32_t adc_port_sample_mv(adc_port_id_t id, uint16_t *raw_mv);

/**
 * 异步单次采样（发起即返回，完成回调通知原始值）。
 */
int32_t adc_port_sample_async(adc_port_id_t id, adc_port_done_cb_t cb, void *user_data);

/**
 * 周期自动采样（实现层定时器/连续转换触发；不需要的工程整段裁剪）。
 * @context isr 回调（周期尽量短小，建议只存值，APP 定期 read_mv）。
 */
int32_t adc_port_start_periodic(adc_port_id_t id, uint32_t period_ms,
                                adc_port_done_cb_t cb, void *user_data);
int32_t adc_port_stop_periodic(adc_port_id_t id);

/**
 * 读取最近一次周期采样值（无数据返回 PORT_ERR_STATE）。
 */
int32_t adc_port_read_mv(adc_port_id_t id, uint16_t *last_mv);

/* [扩展] 多通道序列扫描 / 阈值比较中断（window comparator）等按需扩展。 */

#ifdef __cplusplus
}
#endif

#endif /* ADC_PORT_H */
