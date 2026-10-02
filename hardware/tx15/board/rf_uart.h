/* Internal-module USART6, discovery bench only. GPL-3.0-or-later. */
#ifndef TX15_RF_UART_H
#define TX15_RF_UART_H
#include <stdint.h>
struct tx15_rf_uart_stats { uint32_t rx_bytes, tx_bytes, rx_dropped, errors; };
extern volatile struct tx15_rf_uart_stats tx15_rf_uart_stats;
int tx15_rf_uart_init(void);
void tx15_rf_uart_stop(void);
int tx15_rf_uart_send(const uint8_t *data, unsigned size);
int tx15_rf_uart_read(uint8_t *value);
void USART6_IRQHandler(void);
#endif
