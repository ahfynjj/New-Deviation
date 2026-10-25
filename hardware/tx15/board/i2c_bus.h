/* Application-owned shared I2C4 transactions; GPL-3.0-or-later. */
#ifndef TX15_I2C_BUS_H
#define TX15_I2C_BUS_H
#include <stdint.h>
enum {TX15_I2C_OK=0,TX15_I2C_IO=-1,TX15_I2C_BUSY=-2,
      TX15_I2C_INVALID=-3,TX15_I2C_UNAVAILABLE=-4};
struct tx15_i2c_report {uint32_t status,transfers,errors,max_cycles;};
extern volatile struct tx15_i2c_report tx15_i2c_report;
/* Main thread only. 1/2-byte big-endian register, 1..4 payload bytes. One
 * transaction has a shared true 1ms deadline plus a finite polling budget.
 * BUSY/UNAVAILABLE do not mutate bus/GPIO. Never initialize/reset the bus. */
int tx15_i2c_read(unsigned address,unsigned reg,unsigned reg_bytes,uint8_t *data,unsigned size);
int tx15_i2c_write(unsigned address,unsigned reg,unsigned reg_bytes,const uint8_t *data,unsigned size);
#endif
