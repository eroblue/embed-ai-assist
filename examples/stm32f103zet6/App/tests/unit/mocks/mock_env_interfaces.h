#ifndef MOCK_ENV_INTERFACES_H
#define MOCK_ENV_INTERFACES_H

#include <stdint.h>

extern int mock_dht_read_result;
extern int16_t mock_temp;
extern uint8_t mock_humi;
extern uint16_t mock_light_mv;
extern int mock_dht_read_count;
extern int mock_fault_events;
extern int mock_recovery_events;
void mock_env_reset(void);

#endif
