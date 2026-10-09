"""Immutable installed images for offline kit tests; never a hardware approval.

Use a private root so RF-off / ELRS tests cannot depend on the last build mode.
Real ELF, payload, baseline journals and production validators stay in use.
"""
import hashlib
import json
from pathlib import Path
import shutil
from boot_image import pack

ROOT=Path(__file__).resolve().parents[3]

def candidate_root(folder,product):
    root=Path(folder)/'fixture-root'
    install=root/'local/tx15-hardware/install'
    source=ROOT/'local/tx15-hardware/install'/('elrs-kit' if product else 'controls-kit')
    for name in ('kit','controls-kit','elrs-kit'):
        shutil.copytree(ROOT/'local/tx15-hardware/install'/name,install/name)
    out=root/'local/tx15-hardware/app-standalone';out.mkdir(parents=True)
    app=(source/'app.elf').read_bytes();payload=pack(app)
    meta=(source/'build.json').read_bytes();info=json.loads(meta)
    assert info['rf_enabled']==product
    assert info['elf_sha256']==hashlib.sha256(app).hexdigest()
    assert info['payload_sha256']==hashlib.sha256(payload).hexdigest()
    (out/'tx15-app.elf').write_bytes(app);(out/'tx15-app.nd15').write_bytes(payload)
    (out/'build.json').write_bytes(meta)
    boot=root/'local/tx15-hardware/boot';boot.mkdir()
    shutil.copy2(source/'boot.elf',boot/'tx15-boot.elf')
    return root
