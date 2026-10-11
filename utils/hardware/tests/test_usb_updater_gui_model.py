import importlib
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from test_usb_update_package import fixture
from usb_update.protocol import DeviceInfo,DeviceStatus,State
from usb_update.client import UpdateResult

class GuiModelTests(unittest.TestCase):
    def test_buttons_and_verified_completion(self):
        try:api=importlib.import_module('usb_update.gui_model')
        except ModuleNotFoundError:self.fail('Updater GUI state model missing')
        m=api.UpdaterModel();self.assertFalse(m.can_update)
        m.select_package(fixture());self.assertFalse(m.can_update)
        info=DeviceInfo(b'x'*12,123,1,1,0xec040,2,0xc84018,0x1000000,256,4096,0,2,0x60,1)
        m.connected(info);self.assertTrue(m.can_update)
        m.begin();self.assertFalse(m.can_update)
        ready=DeviceStatus(State.READY,0,100,100,0,0)
        m.complete(UpdateResult(True,'wrong',ready));self.assertFalse(m.success)
        done=DeviceStatus(State.DONE,0,100,100,0,1)
        m.complete(UpdateResult(True,'done',done));self.assertTrue(m.success)
        self.assertFalse(m.can_update) # requires new connection after transaction
        m.disconnected();self.assertFalse(m.can_update)
    def test_wrong_file_and_read_only_device(self):
        try:api=importlib.import_module('usb_update.gui_model')
        except ModuleNotFoundError:self.fail('Updater GUI state model missing')
        m=api.UpdaterModel()
        with self.assertRaises(ValueError):m.select_package(b'wrong')
        m.select_package(fixture())
        m.connected(DeviceInfo(b'x'*12,123,1,1,0xec040,1,0xc84018,0x1000000,256,4096,0,0,0,0))
        self.assertFalse(m.can_update)

    def test_file_io_failure_clears_previous_valid_choice(self):
        api=importlib.import_module('usb_update.gui_model')
        m=api.UpdaterModel()
        info=DeviceInfo(b'x'*12,123,1,1,0xec040,2,0xc84018,0x1000000,256,4096,0,2,0x60,1)
        m.connected(info)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'firmware.ndu';path.write_bytes(fixture())
            for method in ('oversize','stat','read'):
                m.select_package(fixture());self.assertTrue(m.can_update)
                with self.subTest(method=method):
                    if method=='oversize':
                        from types import SimpleNamespace
                        context=patch.object(Path,'stat',return_value=SimpleNamespace(st_size=0x1000000))
                    else:context=patch.object(Path,'stat' if method=='stat' else 'read_bytes',side_effect=OSError('cannot read'))
                    with context:
                        with self.assertRaises((ValueError,OSError)):m.select_file(path)
                    self.assertIsNone(m.raw);self.assertIsNone(m.package);self.assertFalse(m.can_update)
