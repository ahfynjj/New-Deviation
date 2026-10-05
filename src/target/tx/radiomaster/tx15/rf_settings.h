/* Per-model module configuration; zero initialized means RF off. */
#ifndef TX15_RF_SETTINGS_H
#define TX15_RF_SETTINGS_H
#include <stdint.h>
#include <string.h>
struct tx15_module_setting { uint8_t enabled, protocol; };
static inline int tx15_module_enabled(const struct tx15_module_setting *m)
{ return m->enabled==1 && m->protocol==1; }
static inline int tx15_module_parse(struct tx15_module_setting *m,const char *key,const char *value)
{
 if(!strcmp(key,"enabled")) {
  m->enabled=!strcmp(value,"1");
  return !strcmp(value,"0") || !strcmp(value,"1");
 }
 if(!strcmp(key,"protocol")) {
  m->protocol=!strcmp(value,"CRSF");
  return !strcmp(value,"None") || !strcmp(value,"CRSF");
 }
 return 0;
}
#endif
