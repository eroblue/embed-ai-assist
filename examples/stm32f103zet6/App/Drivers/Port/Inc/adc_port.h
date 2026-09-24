/**
 * @file    adc_port.h
 * @brief   ADC Port 接口（平台无关）
 *
 * 逻辑通道按测量对象命名：ADC_PORT_LIGHT（光照传感器分压网络）。
 * 分辨率/通道号等硬件细节在 manifest 数据侧，由 S5c 翻译。
 *
 * 换算约定：sample_mv 在 Port 内完成基准换算，APP 不再感知分辨率——
 * 应用侧光照百分比 = raw_mv * 100 / ref_mv（ref_mv 由 cfg 传入）。
 *
 * 本工程只用同步单次采样：异步/周期接口已裁剪。
 */
#ifndef ADC_PORT_H
#define ADC_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,    /* 未 init / 转换进行中 */
    PORT_ERR_TIMEOUT = -3,  /* 转换超时（硬件异常） */
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑通道（测量对象命名） */
typedef enum {
    ADC_PORT_LIGHT = 0,     /* 光照传感器模拟量输入 */
    ADC_PORT_COUNT
} adc_port_id_t;

typedef enum {
    ADC_PORT_REF_VDD = 0,   /* 基准 = VDD */
    ADC_PORT_REF_EXT = 1,   /* 外部基准（电压值进 cfg.ref_mv） */
} adc_port_ref_t;

typedef struct {
    adc_port_ref_t ref;     /* 基准源 */
    uint32_t       ref_mv;  /* 基准电压 mV（满量程锚点，APP 百分比换算用） */
    uint8_t        avg_count; /* 软件过采样次数（1=单次；均值处理由实现定） */
} adc_port_cfg_t;

/** 绑定逻辑通道与配置。 */
int32_t adc_port_init(adc_port_id_t id, const adc_port_cfg_t *cfg);

/**
 * 同步单次采样（阻塞至转换完成；含 avg_count 次软件过采样处理）。
 * @param raw_mv 输出：换算后的毫伏值（基准换算在 Port 内完成，APP 不再算）
 * @return PORT_OK 或负值错误码。
 */
int32_t adc_port_sample_mv(adc_port_id_t id, uint16_t *raw_mv);

/** 反初始化。 */
int32_t adc_port_deinit(adc_port_id_t id);

#ifdef __cplusplus
}
#endif

#endif /* ADC_PORT_H */
