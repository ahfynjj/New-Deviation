/* Native Deviation menu entry; Lua runs outside page creation callbacks. */
#ifdef TX15_ELRS_RC
#include "common.h"
#include "pages.h"
void tx15_request_lua(void);
void PAGE_ElrsLuaInit(int page)
{
    (void)page;
    /* Return to the existing menu before the blocking tool takes input. */
    PAGE_Pop();
    tx15_request_lua();
}
#endif
