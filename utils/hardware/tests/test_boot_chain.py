import hashlib, json, shutil, struct, subprocess, sys, tempfile, unittest
from contextlib import contextmanager
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'utils/hardware'))
import boot_chain
from unittest.mock import Mock,patch
from utils.hardware.tests.build_fixtures import candidate_root

@contextmanager
def reviewed_unit_bundle():
    """Real ELF + frozen RF-off app, locally approved ONLY inside this test.

    Production pin constants stay unchanged. Current application builds must
    never become implicitly approved for an old hardware RAM experiment.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root=candidate_root(tmp,False)
        target=root/'local/tx15-hardware/boot-chain'
        target.mkdir()
        for name in ('boot-chain.elf','boot-chain.bin','build.json'):
            shutil.copy2(ROOT/'local/tx15-hardware/boot-chain'/name,target/name)
        # Loader still uses its actual reviewed pins, not a computed approval.
        assert hashlib.sha256((target/'boot-chain.elf').read_bytes()).hexdigest()==boot_chain.ELF_SHA
        assert hashlib.sha256((target/'boot-chain.bin').read_bytes()).hexdigest()==boot_chain.BIN_SHA
        backup=Path('local/backups/tx15-external-20261003-155621/external-mapped-90000000-read1.bin')
        (root/backup).parent.mkdir(parents=True)
        shutil.copy2(ROOT/backup,root/backup)
        meta=json.loads((root/'local/tx15-hardware/app-standalone/build.json').read_text())
        with patch.multiple(boot_chain,APP_SHA=meta['elf_sha256'],PAYLOAD_SHA=meta['payload_sha256']):
            yield root

class BootChainTests(unittest.TestCase):
    def test_cleanup_drains_only_systick_and_retains_active_fault_evidence(self):
        writes=[];regs=[]
        state={'active':15}
        def write(a,v):
            writes.append((a,v))
            if a==0xe000edf0 and v==0xa05f0001:state['active']=0
        read=lambda a:state['active'] if a==0xe000ed04 else 0
        boot_chain.quiesce_thread(read,write,lambda n,v:regs.append((n,v)),lambda:None,lambda _:None)
        self.assertIn((20,1),regs)
        self.assertLess(writes.index((0xe000e010,0)),writes.index((0xe000edf0,0xa05f0001)))
        writes.clear();state['active']=3
        with self.assertRaises(RuntimeError):
            boot_chain.quiesce_thread(read,write,lambda *_:None,lambda:None,lambda _:None)
        self.assertNotIn((0xe000edf0,0xa05f0001),writes)
        self.assertFalse(any(a in (0xe000ed28,0xe000ed2c) for a,_ in writes))

    def test_pinned_candidate_and_halted_upload_gate(self):
        original=boot_chain.APP_SHA
        with reviewed_unit_bundle() as root:
            binary,layout,payload,prefix=boot_chain.validate_bundle(root)
            self.assertGreater(len(binary),704)
            self.assertEqual(payload,(root/'local/tx15-hardware/app-standalone/tx15-app.nd15').read_bytes())
            self.assertEqual(len(prefix),64)
            self.assertEqual(layout['entry'],hex(struct.unpack_from('<I',binary,4)[0]))
            for name in ('boot-chain/boot-chain.elf','boot-chain/boot-chain.bin',
                         'app-standalone/tx15-app.elf','app-standalone/tx15-app.nd15'):
                p=root/'local/tx15-hardware'/name;old=p.read_bytes()
                p.write_bytes(bytes([old[0]^1])+old[1:])
                with self.assertRaisesRegex(ValueError,'Candidate differs'):
                    boot_chain.validate_bundle(root)
                p.write_bytes(old)
        self.assertEqual(boot_chain.APP_SHA,original)
        ap=Mock();dp=Mock();ap.read32.return_value=0
        with self.assertRaises(RuntimeError):boot_chain.upload(ap,dp,payload)
        dp.write_ap.assert_not_called()
        ap.read32.side_effect=[1<<17,15]
        with self.assertRaises(RuntimeError):boot_chain.upload(ap,dp,payload)
        dp.write_ap.assert_not_called()

    def test_host_write_allowlist_excludes_destinations_and_persistent_storage(self):
        import chain_ram_session as session
        with reviewed_unit_bundle() as root,patch.object(session,'REPO',root):
            image,_=session.validate_image()
        for address in (0x08000000,0x90000000,0xd0100000,0xd0200000,0x24010000,
                        0xd0080000,0x2400f000,boot_chain.CONTROL,boot_chain.CONTROL+12):
            self.assertFalse(session.allowed_ram_word(address,len(image)))
        for address in (0x24000000,0x2400e000,boot_chain.CONTROL+4,boot_chain.CONTROL+8):
            self.assertTrue(session.allowed_ram_word(address,len(image)))

    def test_upload_readback_failure_never_advances_source(self):
        ap=Mock();dp=Mock();ap.read32.side_effect=[1<<17,0]
        dp.read_ap.return_value=0x12;dp.read_ap_multiple.return_value=[0]*16
        with self.assertRaises(RuntimeError):boot_chain.upload(ap,dp,b'X'*64)
        addresses=[c.args[1] for c in dp.write_ap.call_args_list if c.args[0]==4]
        self.assertEqual(addresses,[boot_chain.SOURCE,boot_chain.SOURCE])

    def test_source_transfers_cannot_touch_app_staging_or_flash(self):
        chunks=list(boot_chain.source_chunks(bytes(529872)))
        self.assertEqual(sum(len(b) for _,b in chunks),529872)
        self.assertEqual(chunks[0][0],0xd0200000)
        for a,b in chunks:
            self.assertLessEqual(len(b),256)
            self.assertEqual(a//1024,(a+len(b)-1)//1024)
        for n in (0,63,boot_chain.MAX_BYTES+1):
            with self.assertRaises(ValueError): list(boot_chain.source_chunks(bytes(n)))

    def test_v10_live_evidence_rejects_old_mailbox_fault_and_missing_copy(self):
        v=[0x4e445631,10,3,0,0x411fc271,0x20036450,0x33030005,0x1b,0x48,0,0,100,20,31,0,0,0,0,0,15,
           2,0,0,0,0,0,0,0,0,0,0,0]
        first=boot_chain.decode(struct.pack('<32I',*v));v[11]+=100;v[12]+=20
        second=boot_chain.decode(struct.pack('<32I',*v))
        self.assertTrue(boot_chain.is_live(second,first))
        for k in ('error','fault_exception','cfsr','hfsr','mmfar','bfar','sdram_error'):
            bad=dict(second);bad[k]=1;self.assertFalse(boot_chain.is_live(bad,first))
        for k,value in [('ram_words',15),('sdram_state',3),('version',7),('loops',20),('cpuid',0)]:
            bad=dict(second);bad[k]=value;self.assertFalse(boot_chain.is_live(bad,first))
        v[1]=7
        with self.assertRaises(ValueError):boot_chain.decode(struct.pack('<32I',*v))

    def test_real_ram_build_uses_same_loader_copy_and_jump(self):
        r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-boot.py'),'--ram-chain'],cwd=ROOT,
            capture_output=True,text=True,encoding='utf8',errors='replace')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        from check_ram_elf import check
        out=ROOT/'local/tx15-hardware/boot-chain'
        self.assertEqual(check((out/'boot-chain.elf').read_bytes())['mailbox'],'0x2400e000')
        from json import loads
        meta=loads((out/'build.json').read_text())
        self.assertTrue(0x24000000 <= meta['control'] < 0x2400e000-80)
        self.assertEqual(meta['bin_sha256'],hashlib.sha256((out/'boot-chain.bin').read_bytes()).hexdigest())
        tool=ROOT.parent/'tools/arm8/bin/arm-none-eabi-objdump.exe'
        dis=subprocess.check_output([str(tool),'-d',str(out/'boot-chain.elf')],text=True)
        for name in ('tx15_boot_load','tx15_boot_jump','tx15_boot_handoff_valid','tx15_boot_image_validate'):
            self.assertIn('<'+name+'>:',dis)
        copy=dis.split('<copy>:',1)[1].split('\n\n',1)[0]
        self.assertRegex(copy,r'\bstrd\s+(?:r\d+|ip|lr),\s*(?:r\d+|ip|lr),\s*\[(?:r\d+|ip|lr)\]')

if __name__=='__main__':unittest.main()
