#ifndef TX15_RF_EXTERNAL_H
#define TX15_RF_EXTERNAL_H
#include "rf_uart.h"
extern volatile struct tx15_rf_uart_stats tx15_rf_external_stats;
int tx15_rf_external_init(void);
void tx15_rf_external_stop(void);
int tx15_rf_external_send(const uint8_t *,unsigned);
int tx15_rf_external_read(uint8_t *);
void USART1_IRQHandler(void);
#endif
