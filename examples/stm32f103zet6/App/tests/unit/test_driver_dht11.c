#include "driver_dht11.h"
#include "gpio_port.h"
#include "timer_port.h"
#include "s8_case.h"

static gpio_port_level_t levels[3000];
static unsigned level_count;
static unsigned level_pos;
static int init_calls;
static int deinit_calls;
static int delay_calls;
static int dir_output_calls;
static int dir_input_calls;

int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg)
{
    (void)cfg; init_calls++; return id == GPIO_PORT_DHT11_DATA ? PORT_OK : PORT_ERR_PARAM;
}
int32_t gpio_port_set_dir(gpio_port_id_t id, gpio_port_dir_t dir)
{
    (void)id;
    if (dir == GPIO_PORT_DIR_INPUT) dir_input_calls++; else dir_output_calls++;
    return PORT_OK;
}
int32_t gpio_port_write(gpio_port_id_t id, gpio_port_level_t level)
{
    (void)id; (void)level; return PORT_OK;
}
int32_t gpio_port_read(gpio_port_id_t id, gpio_port_level_t *level)
{
    (void)id;
    *level = level_pos < level_count ? levels[level_pos++] : GPIO_PORT_LEVEL_HIGH;
    return PORT_OK;
}
int32_t gpio_port_deinit(gpio_port_id_t id)
{
    (void)id; deinit_calls++; return PORT_OK;
}
int32_t timer_port_delay_us(uint32_t us)
{
    (void)us; delay_calls++; return PORT_OK;
}
static void push(gpio_port_level_t level) { levels[level_count++] = level; }
static void frame(const uint8_t bytes[5])
{
    unsigned b, bit, i;
    level_count = level_pos = 0;
    push(GPIO_PORT_LEVEL_LOW); push(GPIO_PORT_LEVEL_HIGH); push(GPIO_PORT_LEVEL_LOW);
    for (b = 0; b < 5; ++b) {
        for (bit = 0; bit < 8; ++bit) {
            unsigned high = ((bytes[b] >> (7 - bit)) & 1u) ? 50u : 20u;
            push(GPIO_PORT_LEVEL_HIGH); /* low-period ending */
            for (i = 0; i < high; ++i) push(GPIO_PORT_LEVEL_HIGH);
            push(GPIO_PORT_LEVEL_LOW); /* high-period ending */
        }
    }
}
int main(void)
{
    int fail = 0;
    int16_t temp = -1;
    uint8_t humi = 0;
    const uint8_t valid[5] = {60, 0, 25, 0, 85};
    const uint8_t bad[5] = {60, 0, 25, 0, 0};
    fail += s8_case("dht_init", driver_dht11_init() == PORT_OK && init_calls == 1 && dir_input_calls == 1);
    fail += s8_case("dht_null_arg", driver_dht11_read(0, &humi) == PORT_ERR_PARAM);
    frame(valid);
    fail += s8_case("dht_valid_frame", driver_dht11_read(&temp, &humi) == PORT_OK &&
                    temp == 25 && humi == 60 && dir_output_calls == 1);
    frame(bad);
    fail += s8_case("dht_checksum", driver_dht11_read(&temp, &humi) == PORT_ERR_STATE);
    level_count = level_pos = 0;
    fail += s8_case("dht_timeout", driver_dht11_read(&temp, &humi) == PORT_ERR_TIMEOUT && delay_calls >= 90);
    fail += s8_case("dht_deinit", driver_dht11_deinit() == PORT_OK && deinit_calls == 1);
    return fail ? 1 : 0;
}
