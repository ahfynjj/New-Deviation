import hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import install_plan,boot_elf,test_app_image,test_boot_firmware
from boot_image import pack

class InstallPlanTests(unittest.TestCase):
    def inputs(self):
        elf=test_app_image.AppImageTests().image();payload=pack(elf)
        boot=test_boot_firmware.fixture();binary=boot_elf.binary(boot)
        meta={'schema':1,'mode':'standalone-first-boot-rf-off','rf_enabled':False,'persistent_settings':False,
              'elf_sha256':hashlib.sha256(elf).hexdigest(),'payload_sha256':hashlib.sha256(payload).hexdigest()}
        return boot,binary,elf,payload,meta

    def test_plan_binds_both_images_and_limits_erase_program_ranges(self):
        manifest,internal,external=install_plan.build_plan(*self.inputs())
        self.assertFalse(manifest['flash_write_authorized'])
        self.assertEqual(manifest['operation'],'plan-only-no-device-access')
        first,second=manifest['writes']
        self.assertEqual(first['address'],'0x08000000');self.assertEqual(first['erase_bytes'],131072)
        self.assertEqual(second['address'],'0x90000000');self.assertLessEqual(second['erase_bytes'],1048576)
        self.assertEqual(len(internal)%32,0);self.assertEqual(len(external)%256,0)
        self.assertEqual(first['sha256'],hashlib.sha256(internal).hexdigest())
        self.assertTrue(manifest['pending_verification'])

    def test_wrong_mode_hash_binary_and_payload_elf_pair_are_rejected(self):
        for key,value in [('mode','ram-bench'),('rf_enabled',True),('elf_sha256','0'*64),('persistent_settings',True)]:
            args=list(self.inputs());args[4]=args[4]|{key:value}
            with self.assertRaises(ValueError):install_plan.build_plan(*args)
        args=list(self.inputs());args[1]=b'x'+args[1][1:]
        with self.assertRaises(ValueError):install_plan.build_plan(*args)
        args=list(self.inputs());args[3]=args[3][:-1]+b'X'
        args[4]=args[4]|{'payload_sha256':hashlib.sha256(args[3]).hexdigest()}
        with self.assertRaises(ValueError):install_plan.build_plan(*args)

    def test_backup_pair_requires_distinct_files_correct_size_and_recorded_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'one.bin',Path(tmp)/'two.bin';a.write_bytes(b'abcd');b.write_bytes(b'abcd')
            digest=hashlib.sha256(b'abcd').hexdigest()
            self.assertEqual(install_plan.backup_pair(a,b,4,digest),b'abcd')
            for inputs in [(a,a,4,digest),(a,b,5,digest),(a,b,4,'0'*64)]:
                with self.assertRaises(ValueError):install_plan.backup_pair(*inputs)
            b.write_bytes(b'abce')
            with self.assertRaises(ValueError):install_plan.backup_pair(a,b,4,digest)

if __name__=='__main__':unittest.main()
