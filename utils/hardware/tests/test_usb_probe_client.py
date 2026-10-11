"""The RAM checker must never transfer to a writable or mismatched radio."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from test_usb_update_package import fixture,ROOT
from usb_update.protocol import Frame,FrameCodec,encode

class ReplyPort:
    def __init__(self,hello):self.hello=encode(hello);self.requests=[];self.codec=FrameCodec()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def write(self,data):
        self.requests.extend(self.codec.feed(data))
        if any(f.kind!=1 for f in self.requests):raise AssertionError('Unexpected transfer beyond HELLO')
        return len(data)
    def read(self,n):
        part=self.hello[:7];self.hello=self.hello[7:];return part

class USBProbeClientTests(unittest.TestCase):
    def test_windows_port_not_ready_retry_before_any_protocol(self):
        spec=importlib.util.spec_from_file_location('readonly_checker',ROOT/'utils/test-tx15-usb-probe.py')
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        self.assertTrue(hasattr(api,'open_cdc_port'),'Windows enumeration needs a bounded port-open retry')
        serial=SimpleNamespace(SerialException=OSError,
            Serial=Mock(side_effect=[OSError('COM path not ready'),OSError('COM path not ready'),'OPEN']))
        with patch.object(api.time,'sleep'):
            self.assertEqual(api.open_cdc_port(serial,'TEST'),'OPEN')
        self.assertEqual(serial.Serial.call_count,3)
        serial.Serial=Mock(side_effect=OSError('not ready'))
        with patch.object(api.time,'monotonic',side_effect=[0,1,4]),patch.object(api.time,'sleep'):
            with self.assertRaises(OSError):api.open_cdc_port(serial,'TEST',timeout=3)
        self.assertEqual(serial.Serial.call_count,2)

    def test_writable_unknown_flags_and_wrong_uid_stop_before_begin(self):
        spec=importlib.util.spec_from_file_location('readonly_checker',ROOT/'utils/test-tx15-usb-probe.py')
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        uid=bytes.fromhex('1c0039000e51333234363236')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);package=tmp/'candidate.ndu';package.write_bytes(fixture())
            report=tmp/'report.json'
            for flags,response_uid in [(0,uid),(2,uid),(3,uid),(1,bytes(12))]:
                with self.subTest(flags=flags,uid=response_uid.hex()):
                    payload=response_uid+struct.pack('<8I4B',1,1,0xec040,flags,0xc84018,0x1000000,256,4096,0,0,0,0)
                    port=ReplyPort(Frame(0x81,123,0,0,payload))
                    serial=ModuleType('serial');serial.Serial=Mock(return_value=port)
                    serial_tools=ModuleType('serial.tools');ports=ModuleType('serial.tools.list_ports')
                    ports.comports=lambda:[SimpleNamespace(vid=0xcafe,pid=0x4015,serial_number=uid.hex(),device='TEST')]
                    argv=['checker','--uid',uid.hex(),'--package',str(package),'--report',str(report)]
                    with patch.dict(sys.modules,{'serial':serial,'serial.tools':serial_tools,'serial.tools.list_ports':ports}),patch.object(sys,'argv',argv):
                        with self.assertRaisesRegex(RuntimeError,'exact read-only RAM probe'):api.main()
                    self.assertEqual([f.kind for f in port.requests],[1])
                    self.assertFalse(report.exists())
