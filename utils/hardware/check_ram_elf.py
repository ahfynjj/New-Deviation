"""Check the actual ARM ELF load map before a TX15 RAM-only bench session."""
import argparse
from pathlib import Path
import struct


def check(data):
    if len(data) < 52 or data[:7] != b"\x7fELF\x01\x01\x01":
        raise ValueError("Expected ELF32 little-endian")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    _, kind, machine, version, entry, phoff, _, _, _, phsize, phnum, _, _, _ = header
    if (kind, machine, version, phsize) != (2, 40, 1, 32) or phnum == 0:
        raise ValueError("Expected executable ARM ELF with program headers")
    if not (entry & 1):
        raise ValueError("Entry must be Thumb code")
    segments = []
    for i in range(phnum):
        if phoff + (i + 1) * phsize > len(data):
            raise ValueError("Truncated program headers")
        segment = struct.unpack_from("<8I", data, phoff + i * phsize)
        ptype, offset, vaddr, paddr, filesz, memsz, flags, _ = segment
        if ptype != 1:
            continue
        if (vaddr != paddr or not 0x24000000 <= vaddr < 0x24010000
                or vaddr + memsz > 0x24010000 or filesz > memsz
                or (filesz and offset + filesz > len(data))):
            raise ValueError("Invalid/non-RAM load segment")
        if filesz and vaddr + filesz > 0x2400E000:
            raise ValueError("Image bytes overlap mailbox/stack")
        segments.append(segment)
    if not segments:
        raise ValueError("No loadable RAM segments")
    # Check the linked reservations, rather than reporting assumed addresses.
    for address, size in ((0x2400E000, 128), (0x2400F000, 4096)):
        if not any(s[2] == address and s[4] == 0 and s[5] == size
                   and s[6] == 6 for s in segments):
            raise ValueError("Missing/moved mailbox or stack reservation")
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            if max(a[2], b[2]) < min(a[2] + a[5], b[2] + b[5]):
                raise ValueError("Overlapping load segments")

    def code_address(address):
        return any(s[6] & 1 and s[2] <= (address & ~1) < s[2] + s[4] for s in segments)

    vector = next((s for s in segments if s[2] == 0x24000000 and s[4] >= 704), None)
    if vector is None or not code_address(entry):
        raise ValueError("Missing vector/code image")
    vectors = struct.unpack_from("<176I", data, vector[1])
    if vectors[0] != 0x24010000 or vectors[1] != entry:
        raise ValueError("Wrong initial SP/reset vector")
    if any(not (address & 1) or not code_address(address) for address in vectors[1:]):
        raise ValueError("Invalid exception vector")
    return {"entry": hex(entry), "stack_top": hex(vectors[0]), "mailbox": "0x2400e000",
            "load_segments": len(segments)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    args = parser.parse_args()
    print("PASS RAM ELF layout:", check(args.elf.read_bytes()))


if __name__ == "__main__":
    main()
