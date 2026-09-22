#include "CuTest.h"

static unsigned run_once_calls;

static void count_run_once_callback(void)
{
    ++run_once_calls;
}

void TestClockRunOnceInvokesCallback(CuTest *t)
{
    run_once_calls = 0;
    CLOCK_RunOnce(count_run_once_callback);
    CuAssertIntEquals(t, 1, run_once_calls);
    CLOCK_RunOnce(count_run_once_callback);
    CuAssertIntEquals(t, 2, run_once_calls);
}

void TestHostSleepReturns(CuTest *t)
{
    (void)t;
    _usleep(1);
}
