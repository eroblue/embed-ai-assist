#include <stdio.h>
#include <string.h>
#include "app_mode_control.h"

static int report(const char *name, int ok)
{
    printf("S8_CASE\t%s\t%s\n", name, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

int main(void)
{
    int failures = 0;
    app_mode_control_init();
    failures += report("mode_initial", app_mode_control_get_mode() == APP_MODE_AUTO &&
                       app_mode_control_is_muted() == 0 &&
                       strcmp(app_mode_control_get_display(), "AUTO") == 0);
    app_mode_control_on_key_mode();
    failures += report("mode_toggle", app_mode_control_get_mode() == APP_MODE_MANUAL &&
                       strcmp(app_mode_control_get_display(), "MANUAL") == 0);
    app_mode_control_on_key_mute();
    failures += report("mute_independent", app_mode_control_get_mode() == APP_MODE_MANUAL &&
                       app_mode_control_is_muted() == 1 &&
                       strcmp(app_mode_control_get_display(), "MUTED") == 0);
    return failures ? 1 : 0;
}
