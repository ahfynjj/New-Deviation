"""TX15 internal bootloader replacement; external Flash has no write path.

Uses the reviewed reset/RAM initializer, internal writer and durable journal.
Always leaves the CPU halted. --recover restores only the saved internal bank.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from flash_journal import Journal
from flash_transaction import sha, _internal

ROOT = Path(__file__).resolve().parents[2]
UID = '1c0039000e51333234363236'
CANDIDATE_SHA = 'bc4e7c93d36da80e5adcc06b27d0ba88cee523c88f6724d06bb51b76b08d9221'
OLD_PADDED_SHA = '737940be15412eca5b494cd190e01ea545d4929f6ee031d8db3945fb533c1de3'


@dataclass(frozen=True)
class Plan:
    boot: bytes
    original_internal: bytes
    original_external: bytes
    uid: str = UID
    payload: bytes = b''
    erase_bytes: int = 0

    def __post_init__(self):
        if (any(type(v) is not bytes for v in (self.boot, self.original_internal, self.original_external))
                or not 0 < len(self.boot) <= 131072 or len(self.boot) % 32
                or len(self.original_internal) != 131072 or len(self.original_external) != 1048576
                or self.uid != UID or self.payload != b'' or self.erase_bytes != 0):
            raise ValueError('Invalid internal-only plan')

    def manifest(self):
        return dict(schema=1, operation='internal-boot-only', device_uid=self.uid,
                    internal_address='0x08000000', internal_erase_bytes=131072,
                    internal_program_bytes=len(self.boot), boot_sha256=sha(self.boot),
                    original_internal_sha256=sha(self.original_internal),
                    original_external_sha256=sha(self.original_external),
                    external_erase_bytes=0, external_program_bytes=0)

    @property
    def seal(self):
        return sha(json.dumps(self.manifest(), sort_keys=True).encode())

    @property
    def recovery_seal(self): return sha(('recover:'+self.seal).encode())


class BootJournal(Journal):
    @classmethod
    def create(cls, path, plan, action, authorization):
        journal = super().create(path, plan, action, authorization)
        # Recovery is internal-only too; never mark an external write intent.
        record = dict(journal.record, external_dirty=False)
        journal._save(record)
        return journal

    def before(self, operation, address, value):
        if operation not in ('internal-erase', 'internal-program'):
            raise ValueError('External Flash mutation is forbidden in boot-only update')
        super().before(operation, address, value)

    def preserved_external(self):
        if self.record['state'] != 'prepared': raise ValueError('Preflight must precede all writes')
        self._save(dict(self.record, state='checkpoint', checkpoints=['external'],
                        external_verified_read_only=True))


def execute(plan, factory, action, authorization, path):
    journal = BootJournal.create(path, plan, action, authorization)
    try:
        backend = factory(journal)
        backend.check_device()
        if backend.read_external(0, 1048576) != plan.original_external:
            raise ValueError('External snapshot differs; no erase')
        if action == 'install' and backend.read_internal(0x08000000, 131072) != plan.original_internal:
            raise ValueError('Internal snapshot differs; no erase')
        journal.preserved_external()
        target = plan.boot if action == 'install' else plan.original_internal
        print('INTERNAL ONLY: erase/program/full-bank readback', flush=True)
        _internal(backend, target)
        if backend.read_external(0, 1048576) != plan.original_external:
            raise RuntimeError('Preserved external application/settings readback differs')
        journal.checkpoint('internal')
        result = (['external-verified', 'internal-verified'] if action == 'install'
                  else ['original-external-verified', 'original-internal-verified'])
        journal.finish(result)
        return journal.record
    except BaseException as error:
        try: journal.failed(str(error))
        except Exception as log_error: error.add_note('Journal save failed: '+str(log_error))
        raise


def save_bytes(path, data):
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    if path.read_bytes() != data: raise RuntimeError('Backup disk readback differs')


def main():
    import flash_install, install_entry, flash_info_bundle, usb_boot_update
    from check_ram_elf import check
    from recovery_context import RecoveryContext
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', action='store_true')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--install', action='store_true')
    modes.add_argument('--recover', type=Path, help='Previous boot-only session folder')
    parser.add_argument('--candidate', type=Path, default=ROOT/'local/tx15-hardware/boot-progress-20261021')
    args = parser.parse_args()
    if not args.arm or not sys.stdin.isatty(): parser.error('Requires --arm and interactive power-held gate')
    elf = (args.candidate/'tx15-boot-usb.elf').read_bytes()
    raw = (args.candidate/'tx15-boot-usb.bin').read_bytes()
    metadata = json.loads((args.candidate/'build.json').read_text(encoding='utf8'))
    usb_boot_update.validate_boot(elf, raw, metadata)
    if sha(raw) != CANDIDATE_SHA: raise ValueError('Unreviewed progress boot image')
    kit_folder = ROOT/'local/tx15-hardware/install/usb-boot-kit'
    reader = (kit_folder/'reader.bin').read_bytes()
    reader_elf = (kit_folder/'reader.elf').read_bytes()
    if sha(reader) != flash_info_bundle.BIN_SHA or sha(reader_elf) != flash_info_bundle.ELF_SHA:
        raise ValueError('RAM initializer digest mismatch')
    kit = SimpleNamespace(reader=reader, entry=int(check(reader_elf)['entry'],16), uid=UID)
    old = (kit_folder/'boot.bin').read_bytes()
    if sha(old) != OLD_PADDED_SHA: raise ValueError('Historical BL reference mismatch')
    boot = raw+b'\xff'*((-len(raw))%32)
    folder = ROOT/'local/hardware-session'/('boot-only-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True)
    context = None
    report = dict(utc=datetime.now(timezone.utc).isoformat(), operation='boot-only', external_write_commands=0)
    try:
        with install_entry.lease(Path(tempfile.gettempdir()), 'new-deviation-tx15-pwlink2.lock'):
            context = RecoveryContext(flash_install.open_probe(500000), wait=600,
                                      ready_gate=lambda: flash_install.power_held_gate(600))
            try:
                observed = context.enter(kit)
                backend = context.backend(read_only=True)
                if backend.check_device() != observed: raise ValueError('RAM/SWD identity observations differ')
                if args.recover:
                    source = args.recover
                    plan = Plan((source/'boot.bin').read_bytes(), (source/'original-internal.bin').read_bytes(),
                                (source/'original-external.bin').read_bytes())
                    manifest = json.loads((source/'plan.json').read_text(encoding='utf8'))
                    if plan.manifest() != manifest or plan.boot != boot: raise ValueError('Recovery snapshot differs')
                    action = 'recover'
                else:
                    internal = backend.read_internal(0x08000000, 131072)
                    if internal != old+b'\xff'*(131072-len(old)):
                        raise ValueError('Live internal BL differs from reviewed installed BL; no erase')
                    external = backend.read_external(0, 1048576)
                    plan = Plan(boot, internal, external)
                    action = 'install'
                for name, data in [('boot.bin', plan.boot), ('original-internal.bin', plan.original_internal),
                                   ('original-external.bin', plan.original_external), ('reader.bin', reader),
                                   ('reader.elf', reader_elf)]: save_bytes(folder/name, data)
                save_bytes(folder/'plan.json', (json.dumps(plan.manifest(), indent=2)+'\n').encode())
                print('BACKUPS SAVED AND DISK READBACK VERIFIED:', folder, flush=True)
                report['transaction'] = execute(plan, lambda j: context.backend(j, read_only=False), action,
                    plan.seal if action == 'install' else plan.recovery_seal, folder/'journal.json')
                report.update(status='verified-halted', plan=plan.manifest())
                print('VERIFIED INTERNAL BL; EXTERNAL 1MiB UNCHANGED; CPU HALTED.', flush=True)
            finally: install_entry.finish_context(context)
    except BaseException as error:
        report.update(status='failed-no-resume', error=type(error).__name__+': '+str(error))
        print(report['error'], flush=True)
        raise
    finally:
        if context: report['context'] = context.report
        (folder/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
        print('Saved', folder/'result.json', flush=True)
    return 0

if __name__ == '__main__': raise SystemExit(main())
