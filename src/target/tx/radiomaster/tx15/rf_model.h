#ifndef TX15_RF_MODEL_H
#define TX15_RF_MODEL_H
#include <stdint.h>
void tx15_rf_model_start(uint32_t now);
void tx15_rf_model_reset(void);
void tx15_rf_model_service(uint32_t now);
#endif
