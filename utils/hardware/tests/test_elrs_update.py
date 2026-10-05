import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'utils/hardware'))
import elrs_update,install_kit,native_update
from flash_transaction import sha
class ElrsUpdateTests(unittest.TestCase):
 def test_frozen_controls_baseline_and_reserved_settings(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'kit';elrs_update.prepare(ROOT,folder);kit=elrs_update.read(folder)
   baseline=native_update.read(ROOT/'local/tx15-hardware/install/controls-kit')
   self.assertEqual((kit.plan.original_internal,kit.plan.original_external),native_update.baseline_images(baseline))
   self.assertLessEqual(kit.plan.erase_bytes,0xf0000)
   self.assertEqual(kit.plan.original_internal,kit.plan.boot+b'\xff'*(131072-len(kit.plan.boot)))
   checklist=install_kit.checklist(kit)
   self.assertTrue(checklist['rf_enabled']);self.assertTrue(checklist['persistent_settings'])
   self.assertEqual(checklist['internal_erase_bytes'],0)
   with self.assertRaises(FileExistsError):elrs_update.prepare(ROOT,folder)
   m=json.loads((folder/'kit.json').read_text());m['settings_region']['offset']=0
   (folder/'kit.json').write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'Invalid frozen'):elrs_update.read(folder)
 def test_metadata_cannot_disguise_missing_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'kit';elrs_update.prepare(ROOT,folder)
   p=folder/'build.json';m=json.loads(p.read_text());m['persistent_settings']=False;p.write_text(json.dumps(m))
   p=folder/'kit.json';m=json.loads(p.read_text());m['files']['build.json']=sha((folder/'build.json').read_bytes());p.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'metadata'):elrs_update.read(folder)
