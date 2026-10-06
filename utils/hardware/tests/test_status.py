import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class StatusTests(unittest.TestCase):
 def test_voltage_and_link_validity(self):
  gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
  env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ['PATH'])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(r"""
#include <assert.h>
#include "status.h"
int main(void) {
 assert(tx15_battery_scale(0)==0);
 assert(tx15_battery_scale(2048)>=6800 && tx15_battery_scale(2048)<=6810);
 struct tx15_link_status s={0};struct crsf_frame f;
 unsigned char data[10]={75,80,99,0,0,0,0,90,100,0};
 assert(crsf_frame_build(&f,0xea,0x14,data,10));
 assert(tx15_status_frame(&s,&f,10));assert(tx15_status_connected(&s,10));
 assert(s.rssi_dbm==-75 && s.lq==99);assert(!tx15_status_connected(&s,3011));
 data[2]=0;assert(crsf_frame_build(&f,0xea,0x14,data,10));
 assert(tx15_status_frame(&s,&f,20));assert(!tx15_status_connected(&s,20));
 data[2]=101;assert(crsf_frame_build(&f,0xea,0x14,data,10));assert(!tx15_status_frame(&s,&f,21));
 assert(crsf_frame_build(&f,0xea,0x14,data,9));assert(!tx15_status_frame(&s,&f,22));
 f.bytes[3]^=1;assert(!tx15_status_frame(&s,&f,23));
}
""")
   r=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT/'src'),'-I',str(ROOT/'hardware/tx15/board'),str(p/'test.c'),str(ROOT/'src/protocol/transport/crsf_link.c'),'-o',str(p/'test.exe')],env=env,capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);subprocess.run([str(p/'test.exe')],env=env,check=True)
