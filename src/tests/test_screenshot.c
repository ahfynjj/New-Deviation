#include "CuTest.h"

static char missing_name[64];

static void check_missing_screenshot(CuTest *t)
{
    AssertScreenshot(t, missing_name);
}

void TestMissingScreenshotFailsWithoutCreatingBaseline(CuTest *t)
{
    char reference[128];
    char actual[80];
    snprintf(missing_name, sizeof(missing_name), "missing_baseline_%d", (int)getpid());
    snprintf(reference, sizeof(reference), "../../tests/320x240x16/%s.png", missing_name);
    snprintf(actual, sizeof(actual), "%s.png", missing_name);
    CuAssertTrue(t, access(reference, F_OK) != 0);

    CuTest *probe = CuTestNew("missing screenshot probe", check_missing_screenshot);
    CuTestRun(probe);
    int failed = probe->failed;
    int wrote_reference = access(reference, F_OK) == 0;
    int wrote_actual = access(actual, F_OK) == 0;
    CuTestDelete(probe);
    /* Remove only files with this test's process-specific fixture name. */
    if (wrote_reference) remove(reference);
    if (wrote_actual) remove(actual);

    CuAssertIntEquals(t, 1, failed);
    CuAssertIntEquals(t, 0, wrote_reference);
    CuAssertIntEquals(t, 1, wrote_actual);
}
