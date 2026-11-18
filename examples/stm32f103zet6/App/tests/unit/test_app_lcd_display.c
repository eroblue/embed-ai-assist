#include <string.h>
#include "app_lcd_display.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "app_alarm_control.h"
#include "driver_lcd.h"
#include "par_port.h"
#include "s8_case.h"

static env_data_t env = {25, 60, 75};
static app_alarm_t alarm = APP_ALARM_NORMAL;
static char lines[4][DRIVER_LCD_LINE_CHARS + 1];
static int writes;
const env_data_t *app_env_sensor_get_data(void) { return &env; }
const char *app_mode_control_get_display(void) { return "AUTO"; }
app_alarm_t app_alarm_control_get_alarm(void) { return alarm; }
const char *app_alarm_control_get_display(void) { return alarm == APP_ALARM_NORMAL ? "NORMAL" : "HIGH_T"; }
int32_t driver_lcd_init(void) { return PORT_OK; }
int32_t driver_lcd_show_line(uint8_t line, const char *text)
{
    if (line > 3) return PORT_ERR_PARAM;
    strncpy(lines[line], text, DRIVER_LCD_LINE_CHARS);
    lines[line][DRIVER_LCD_LINE_CHARS] = '\0';
    writes++;
    return PORT_OK;
}
void driver_lcd_diag_dump(void) { }
uint8_t driver_lcd_get_diag_code(void) { return 0; }
static void poll_n(int n) { while (n-- > 0) app_lcd_display_poll(); }

int main(void)
{
    int fail = 0;
    fail += s8_case("display_init", app_lcd_display_init() == PORT_OK && app_lcd_display_is_ready());
    poll_n(19);
    fail += s8_case("before_refresh", writes == 0);
    poll_n(1);
    fail += s8_case("normal_render", writes == 4 && strcmp(lines[0], "ENV MONITOR") == 0 &&
                    strcmp(lines[1], "T:25C H:60%") == 0 && strcmp(lines[2], "L:75%") == 0 &&
                    strcmp(lines[3], "M:AUTO A:NORMAL") == 0);
    alarm = APP_ALARM_HIGH_TEMP;
    poll_n(20);
    fail += s8_case("alarm_dark_phase", writes == 8 && lines[3][0] == '\0');
    poll_n(20);
    fail += s8_case("alarm_light_phase", writes == 12 && strcmp(lines[3], "M:AUTO A:HIGH_T") == 0);
    return fail ? 1 : 0;
}
