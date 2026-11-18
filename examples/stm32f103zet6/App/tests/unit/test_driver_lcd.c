#include "driver_lcd.h"
#include "par_port.h"
#include "timer_port.h"
#include "uart_port.h"
#include "s8_case.h"

static int init_result = PORT_ERR_STATE;
static int init_calls;
static int deinit_calls;
static uint16_t read_values[3];
static int read_pos;
int32_t par_port_init(par_port_id_t id) { (void)id; init_calls++; return init_result; }
int32_t par_port_deinit(par_port_id_t id) { (void)id; deinit_calls++; return PORT_OK; }
int32_t par_port_write_cmd(par_port_id_t id, uint16_t cmd) { (void)id; (void)cmd; return PORT_OK; }
int32_t par_port_write_data(par_port_id_t id, uint16_t data) { (void)id; (void)data; return PORT_OK; }
int32_t par_port_read_data(par_port_id_t id, uint16_t *data)
{
    (void)id;
    *data = read_values[read_pos++ % 3];
    return PORT_OK;
}
int32_t par_port_write_data_block(par_port_id_t id, const uint16_t *data, uint32_t len)
{
    (void)id; (void)data; (void)len; return PORT_OK;
}
int32_t timer_port_delay_us(uint32_t us) { (void)us; return PORT_OK; }
int32_t uart_port_write(uart_port_id_t id, const uint8_t *data, uint16_t len)
{
    (void)id; (void)data; return len;
}
int main(void)
{
    int fail = 0;
    uint16_t id = 0;
    fail += s8_case("lcd_init_bus_error", driver_lcd_init() == PORT_ERR_STATE && init_calls == 1);
    fail += s8_case("lcd_bad_arguments", driver_lcd_read_id(0) == PORT_ERR_PARAM &&
                    driver_lcd_show_line(4, "x") == PORT_ERR_PARAM &&
                    driver_lcd_show_line(0, 0) == PORT_ERR_PARAM);
    read_values[0] = 0; read_values[1] = 0x55; read_values[2] = 0x10; read_pos = 0;
    fail += s8_case("lcd_id_read", driver_lcd_read_id(&id) == PORT_OK && id == 0x5510);
    read_values[0] = read_values[1] = read_values[2] = 0; read_pos = 0;
    fail += s8_case("lcd_no_response_code", driver_lcd_read_id(&id) == PORT_OK &&
                    driver_lcd_get_diag_code() == 1);
    fail += s8_case("lcd_deinit", driver_lcd_deinit() == PORT_OK && deinit_calls == 1);
    return fail ? 1 : 0;
}
