#include <stdio.h>
#include "app_env_sensor.h"
#include "adc_port.h"
#include "mock_env_interfaces.h"

static int report(const char *name, int ok)
{
    printf("S8_CASE\t%s\t%s\n", name, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

static void advance_period(void)
{
    int i;
    for (i = 0; i < 200; ++i) app_env_sensor_poll();
}

int main(void)
{
    int failures = 0;
    const env_data_t *data;
    mock_env_reset();
    failures += report("initial_fault", app_env_sensor_init() == PORT_OK &&
                       app_env_sensor_is_fault() == 1 && mock_fault_events == 1 &&
                       mock_dht_read_count == 0);
    mock_dht_read_result = PORT_OK;
    mock_temp = 25;
    mock_humi = 60;
    mock_light_mv = 1650;
    advance_period();
    data = app_env_sensor_get_data();
    failures += report("first_valid_recovery", app_env_sensor_is_fault() == 0 &&
                       mock_recovery_events == 1 && mock_dht_read_count == 1 &&
                       data->temp == 25 && data->humi == 60 && data->light == 50);
    mock_dht_read_result = PORT_ERR_TIMEOUT;
    advance_period();
    data = app_env_sensor_get_data();
    failures += report("read_failure_retains", app_env_sensor_is_fault() == 0 &&
                       data->temp == 25 && data->humi == 60 && mock_dht_read_count == 2);
    return failures ? 1 : 0;
}
