"""Pack a verified standalone product build for the native USB updater."""
import argparse
import hashlib
import json
from pathlib import Path
from hardware import app_image, boot_image
from usb_update.package import pack, unpack


def product_package(folder: Path) -> bytes:
    elf = (folder/'tx15-app.elf').read_bytes()
    image = (folder/'tx15-app.nd15').read_bytes()
    meta = json.loads((folder/'build.json').read_text(encoding='utf8'))
    if (meta.get('schema') != 1 or meta.get('mode') != 'standalone-elrs-candidate'
        or meta.get('rf_enabled') is not True or meta.get('persistent_settings') is not True
        or meta.get('elf_sha256') != hashlib.sha256(elf).hexdigest()
        or meta.get('payload_sha256') != hashlib.sha256(image).hexdigest()):
        raise ValueError('Require matching standalone RF/persistence product metadata')
    if boot_image.unpack(image) != app_image.parse(elf):
        raise ValueError('ND15 does not match the product ELF')
    # ABI1 is a source-level storage contract, not an arbitrary CLI option.
    return pack(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = product_package(args.build)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'Cannot package update: {exc}\n')
    print(json.dumps(dict(format='ND15UPD1', bytes=len(raw), image_bytes=len(unpack(raw).image),
                          sha256=hashlib.sha256(raw).hexdigest(), flash_written=False)))


if __name__ == '__main__': main()
