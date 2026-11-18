#include <string.h>
#include "hal_init.h"
#include "s8_case.h"

static char calls[9];
static unsigned count;
void clock_init(void) { calls[count++] = 'C'; }
void nvic_init(void) { calls[count++] = 'N'; }
void gpio_init(void) { calls[count++] = 'G'; }
void tim4_init(void) { calls[count++] = 'T'; }
void adc3_init(void) { calls[count++] = 'A'; }
void fsmc_lcd_init(void) { calls[count++] = 'F'; }
void usart1_init(void) { calls[count++] = 'U'; }
void dht11_init(void) { calls[count++] = 'D'; }

int main(void)
{
    hal_init();
    calls[count] = '\0';
    return s8_case("init_order", count == 8 && strcmp(calls, "CNGTAFUD") == 0);
}
