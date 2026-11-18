#include "app_key_handler.h"
#include "gpio_port.h"
#include "s8_case.h"

static uint8_t active[GPIO_PORT_COUNT];
int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg)
{
    (void)cfg; active[id] = 0; return PORT_OK;
}
int32_t gpio_port_read_active(gpio_port_id_t id, uint8_t *value)
{
    *value = active[id]; return PORT_OK;
}
static void poll_n(int n) { while (n-- > 0) app_key_handler_poll(); }

int main(void)
{
    int fail = 0;
    app_key_handler_init();
    active[GPIO_PORT_KEY_MODE] = 1;
    poll_n(2);
    active[GPIO_PORT_KEY_MODE] = 0;
    poll_n(2);
    fail += s8_case("bounce_ignored", app_key_handler_get_event() == APP_KEY_EVENT_NONE);
    active[GPIO_PORT_KEY_MODE] = 1;
    poll_n(5);
    active[GPIO_PORT_KEY_MODE] = 0;
    poll_n(5);
    fail += s8_case("short_press", app_key_handler_get_event() == APP_KEY_EVENT_MODE &&
                    app_key_handler_get_event() == APP_KEY_EVENT_NONE);
    app_key_handler_init();
    active[GPIO_PORT_KEY_MODE] = 1;
    poll_n(105);
    active[GPIO_PORT_KEY_MODE] = 0;
    poll_n(5);
    fail += s8_case("long_press_no_short_event", app_key_handler_get_event() == APP_KEY_EVENT_NONE);
    return fail ? 1 : 0;
}
