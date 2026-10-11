"""Exercise the actual boot decision and power-button policy."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HARNESS = r'''
#include <assert.h>
#include "update_mode.h"
int main(void) {
    assert(!tx15_boot_update_mode(0,TX15_BOOT_LOAD_OK));
    assert(tx15_boot_update_mode(1,TX15_BOOT_LOAD_OK));
    assert(tx15_boot_update_mode(0,TX15_BOOT_LOAD_READ_ERROR));
    assert(tx15_boot_update_mode(0,TX15_BOOT_LOAD_BAD_IMAGE));
    assert(!tx15_boot_update_mode(1,TX15_BOOT_LOAD_COPY_ERROR));
    assert(!tx15_boot_update_mode(1,TX15_BOOT_LOAD_VERIFY_ERROR));
    assert(!tx15_boot_update_mode(1,TX15_BOOT_LOAD_BAD_ARGUMENT));
    struct tx15_update_power p={0};
    assert(!tx15_update_power_poll(&p,0,1,0));
    assert(!tx15_update_power_poll(&p,3000,1,0));
    assert(!tx15_update_power_poll(&p,3001,0,0));
    assert(!tx15_update_power_poll(&p,3020,0,0));
    assert(!tx15_update_power_poll(&p,3021,0,0));
    assert(!tx15_update_power_poll(&p,3100,1,0));
    assert(!tx15_update_power_poll(&p,5099,1,0));
    assert(tx15_update_power_poll(&p,5100,1,0));
    p=(struct tx15_update_power){0};
    tx15_update_power_poll(&p,0xfffffff0u,0,0);
    tx15_update_power_poll(&p,4,0,0);
    tx15_update_power_poll(&p,5,1,0);
    assert(!tx15_update_power_poll(&p,2005,1,1));
    assert(!tx15_update_power_poll(&p,4005,1,0)); /* busy invalidates hold */
    tx15_update_power_poll(&p,4010,0,0);
    tx15_update_power_poll(&p,4030,0,0);
    tx15_update_power_poll(&p,4040,1,0);
    assert(tx15_update_power_poll(&p,6040,1,0));
    return 0;
}
'''

class BootModeTests(unittest.TestCase):
    def test_real_policy(self):
        source=ROOT/'hardware/tx15/boot/update_mode.c'
        self.assertTrue(source.exists(),'Resident updater mode policy missing')
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);test=folder/'test.c';test.write_text(HARNESS)
            exe=folder/'test.exe'
            r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(source.parent),str(test),str(source),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
