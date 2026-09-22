"""Exercise the TX15 profile and its production input driver with a C harness."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "src/target/tx/radiomaster/emu_tx15"


class Tx15InputTests(unittest.TestCase):
    def test_key_events_and_raw_inputs(self):
        self.assertTrue((TARGET / "tx15_inputs.c").exists(), "TX15 input driver missing")
        self.compile_run('''#include <assert.h>
#include "common.h"
#include "target/drivers/mcu/emu/fltk.h"
#include "mixer.h"
struct Gui gui;
static void one_hot(int first, int count, int selected) {
    for (int i = 0; i < count; i++)
        assert(SWITCH_ReadRawInput(first + i) == (i == selected));
}
int main(void) {
    const int switches[] = {INP_SWA0, INP_SWB0, INP_SWC0, INP_SWD0};
    const char keys[] = "xcvz";
    assert(INP_HAS_CALIBRATION == 6);
    for (int s = 0; s < 4; s++) {
        one_hot(switches[s], 3, 0);
        for (int n = 1; n <= 3; n++) {
            assert(EMU_HandleTargetKey(keys[s], 1));
            one_hot(switches[s], 3, n % 3);
            EMU_HandleTargetKey(keys[s], 1);  /* auto-repeat must not advance */
            one_hot(switches[s], 3, n % 3);
            EMU_HandleTargetKey(keys[s], 0);
        }
    }
    EMU_HandleTargetKey('b', 1);
    EMU_HandleTargetKey('b', 1);
    one_hot(INP_SWE0, 2, 1);
    EMU_HandleTargetKey('b', 0);
    one_hot(INP_SWE0, 2, 1);
    EMU_HandleTargetKey('n', 1);
    one_hot(INP_SWF0, 2, 1);
    EMU_HandleTargetKey('n', 0);
    one_hot(INP_SWF0, 2, 0);
    EMU_HandleTargetKey('n', 1);
    EMU_ReleaseTargetKeys();
    one_hot(INP_SWF0, 2, 0);
    one_hot(INP_SWE0, 2, 1); /* focus loss preserves latching state */
    EMU_HandleTargetKey('b', 1);
    one_hot(INP_SWE0, 2, 0);
    for (int n = 0; n < 6; n++) {
        EMU_HandleTargetKey('1' + n, 1);
        one_hot(INP_SW60, 6, n);
        EMU_HandleTargetKey('1' + n, 0);
        one_hot(INP_SW60, 6, n);
    }
    assert(!EMU_HandleTargetKey('7', 1));
    assert(!EMU_HandleTargetKey('a', 1));
    gui.aux2 = 0; gui.aux3 = 10;
    assert(ADC_ReadRawInput(INP_S1) == CHAN_MIN_VALUE);
    assert(ADC_ReadRawInput(INP_S2) == CHAN_MAX_VALUE);
    gui.aux2 = 5;
    assert(ADC_NormalizeChannel(INP_S1) == 0);
    assert(ADC_ReadRawInput(INP_SWA0) == 0);
    assert(SWITCH_ReadRawInput(INP_S1) == 0);
    return 0;
}
''', [TARGET / "tx15_inputs.c"])

    def compile_run(self, code, sources=()):
        with tempfile.TemporaryDirectory(prefix="tx15-inputs-") as tmp:
            source = Path(tmp) / "check.c"
            source.write_text(code)
            exe = Path(tmp) / "check.exe"
            result = subprocess.run([os.environ.get("CC", "gcc"), "-std=c99",
                                     "-DEMULATOR=0", "-I", str(TARGET),
                                     "-I", str(ROOT / "src/target/drivers/filesystems"),
                                     "-I", str(ROOT / "src/gui/320x240x16"),
                                     "-I", str(ROOT / "src/pages/320x240x16"),
                                     "-I", str(ROOT / "src"), str(source),
                                     *map(str, sources), "-o", str(exe)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_factory_profile(self):
        self.compile_run('''#include <assert.h>
#include <string.h>
#define CHANDEF(x) #x,
static const char *names[] = {
#include "capabilities.h"
};
int main(void) {
    assert(sizeof(names) / sizeof(names[0]) == 28);
    assert(strcmp(names[4], "S1") == 0);
    assert(strcmp(names[5], "S2") == 0);
    assert(strcmp(names[6], "SWA0") == 0);
    assert(strcmp(names[21], "SWF1") == 0);
    assert(strcmp(names[27], "SW65") == 0);
    return 0;
}
''')


if __name__ == "__main__":
    unittest.main()
