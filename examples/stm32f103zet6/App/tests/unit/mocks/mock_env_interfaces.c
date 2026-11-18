#include "mock_env_interfaces.h"
#include "driver_dht11.h"
#include "adc_port.h"
#include "app_alarm_control.h"

int mock_dht_read_result;
int16_t mock_temp;
uint8_t mock_humi;
uint16_t mock_light_mv;
int mock_dht_read_count;
int mock_fault_events;
int mock_recovery_events;

void mock_env_reset(void)
{
    mock_dht_read_result = PORT_ERR_TIMEOUT;
    mock_temp = 0;
    mock_humi = 0;
    mock_light_mv = 0;
    mock_dht_read_count = 0;
    mock_fault_events = 0;
    mock_recovery_events = 0;
}

int32_t driver_dht11_init(void) { return PORT_OK; }
int32_t driver_dht11_read(int16_t *temp, uint8_t *humi)
{
    mock_dht_read_count++;
    if (mock_dht_read_result == PORT_OK) {
        *temp = mock_temp;
        *humi = mock_humi;
    }
    return mock_dht_read_result;
}
int32_t adc_port_init(adc_port_id_t id, const adc_port_cfg_t *cfg)
{
    (void)id;
    (void)cfg;
    return PORT_OK;
}
int32_t adc_port_sample_mv(adc_port_id_t id, uint16_t *raw_mv)
{
    (void)id;
    *raw_mv = mock_light_mv;
    return PORT_OK;
}
void app_alarm_control_on_sensor_fault(void) { mock_fault_events++; }
void app_alarm_control_on_sensor_recovered(void) { mock_recovery_events++; }
