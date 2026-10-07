import json,tempfile,unittest
from pathlib import Path
import status_update as u,elrs_update,native_update
from flash_transaction import sha
ROOT=Path(__file__).resolve().parents[3]
class UpdateTests(unittest.TestCase):
 def test_preserves_live_models_and_freezes_recovery(self):
  base=elrs_update.read(ROOT/'local/tx15-hardware/install/elrs-kit')
  internal,external=native_update.baseline_images(base)
  external=external[:0xf0000]+bytes(range(256))*256
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'kit';u.prepare(ROOT,folder,internal,external)
   kit=u.read(folder);self.assertEqual(kit.plan.original_external,external)
   self.assertLessEqual(kit.plan.erase_bytes,0xf0000)
   self.assertEqual(kit.plan.original_internal,internal)
   with self.assertRaises(FileExistsError):u.prepare(ROOT,folder,internal,external)
   p=folder/'original-external.bin';bad=b'!'+external[1:];p.write_bytes(bad)
   m=kit.manifest;m['files'][p.name]=sha(bad)
   (folder/'kit.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):u.read(folder)
 def test_unknown_app_or_loader_cannot_prepare(self):
  base=elrs_update.read(ROOT/'local/tx15-hardware/install/elrs-kit')
  internal,external=native_update.baseline_images(base)
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'kit'
   with self.assertRaises(ValueError):u.prepare(ROOT,folder,b'!'+internal[1:],external)
   with self.assertRaises(ValueError):u.prepare(ROOT,folder,internal,b'!'+external[1:])
   self.assertFalse(folder.exists())

 def test_invalid_active_pointer_is_rejected(self):
  from dataclasses import replace
  from unittest.mock import patch
  b,j=u.baseline(ROOT)
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);(folder/j.name).write_bytes(j.read_bytes());fake=replace(b,folder=folder)
   for pointer in ({'schema':9,'journal':j.name},{'schema':1,'journal':'../'+j.name}):
    (folder/'active.json').write_text(json.dumps(pointer))
    with patch.object(u,'read_native',return_value=fake):
     with self.assertRaises(ValueError):u.baseline(ROOT)

 def test_next_update_accepts_installed_status_and_preserves_models(self):
  folder0=ROOT/'local/tx15-hardware/install/status-kit'
  base=u.read(folder0);internal,external=native_update.baseline_images(base)
  external=external[:0xf0000]+bytes(range(256))*256
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'next';kit=u.prepare(ROOT,folder,internal,external,folder0)
   self.assertEqual(kit.plan.original_external,external)
   self.assertEqual(u.read(folder).approval('recover'),kit.approval('recover'))
