"""Compile and exercise the same coordinate helper used by FLTK events."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class EmulatorTouchTests(unittest.TestCase):
    def test_canvas_hit_testing_and_scaling(self):
        with tempfile.TemporaryDirectory(prefix="deviation-touch-") as tmp:
            source = Path(tmp) / "touch.c"
            source.write_text('''#include <assert.h>
#include "target/drivers/mcu/emu/touch.h"
int main(void) {
    unsigned x = 999, y = 999;
    assert(EMU_MapTouch(0, 30, 30, 480, 320, 480, 320, &x, &y));
    assert(x == 0 && y == 0);
    assert(EMU_MapTouch(479, 349, 30, 480, 320, 480, 320, &x, &y));
    assert(x == 479 && y == 319);
    assert(!EMU_MapTouch(-1, 30, 30, 480, 320, 480, 320, &x, &y));
    assert(!EMU_MapTouch(480, 30, 30, 480, 320, 480, 320, &x, &y));
    assert(!EMU_MapTouch(1, 29, 30, 480, 320, 480, 320, &x, &y));
    assert(!EMU_MapTouch(1, 350, 30, 480, 320, 480, 320, &x, &y));
    assert(EMU_MapTouch(639, 489, 10, 640, 480, 320, 240, &x, &y));
    assert(x == 319 && y == 239);
    assert(!EMU_MapTouch(0, 0, 0, 0, 320, 480, 320, &x, &y));
    return 0;
}
''')
            exe = Path(tmp) / "touch.exe"
            result = subprocess.run([os.environ.get("CC", "gcc"), "-std=c99",
                                     "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "src"),
                                     str(source), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
