"""Decode historical 80-byte or V5 128-byte RAM diagnostic mailboxes."""
import argparse
import json
from pathlib import Path
import struct

FIELDS = ("magic version state error cpuid device_id rcc_cr rcc_cfgr rcc_d1cfgr "
          "scb_ccr mpu_ctrl ticks loops ram_words fault_exception cfsr hfsr mmfar bfar reserved").split()
SDRAM_FIELDS = ("sdram_state sdram_error sdram_words sdram_checks sdram_bad_address "
                "sdram_expected sdram_actual sdcr1 sdcr2 sdtr1 sdtr2 sdrtr").split()


def decode(data):
    if len(data) not in (80, 128):
        raise ValueError("Expected 80 (V1..4) or 128 (V5) bytes from 0x2400e000")
    values = dict(zip(FIELDS, struct.unpack("<20I", data[:80])))
    if values["magic"] != 0x4E445631 or values["version"] not in (1, 2, 3, 4, 5):
        raise ValueError("Unrecognized mailbox magic/version; do not treat stale RAM as execution")
    if len(data) != (128 if values['version'] == 5 else 80):
        raise ValueError('Mailbox size does not match version')
    if values['version'] == 5:
        values.update(zip(SDRAM_FIELDS, struct.unpack('<12I', data[80:])))
    if values["version"] >= 2:
        values["power_status"] = values.pop("reserved")
    return values


def is_live(current, previous):
    if previous is None:
        return False
    if current["version"] != previous["version"]:
        return False
    for report in (current, previous):
        if report["state"] != 3 or report["error"] or report["ram_words"] != 512:
            return False
        if report["version"] >= 2 and report["power_status"] & 15 != 15:
            return False
        if report["version"] == 3 and (report["rcc_cr"] & 0x30000 != 0x30000
                or report["rcc_cfgr"] & 0x3f != 0x12 or report["rcc_d1cfgr"] & 0xf0f):
            return False
        if report["version"] >= 4 and (report["rcc_cr"] & 0x3f0f001d != 0x3030005
                or report["rcc_cfgr"] & 0x3f != 0x1b or report["rcc_d1cfgr"] & 0xf7f != 0x48):
            return False
        if report['version'] == 5 and (report['sdram_state'] != 3 or report['sdram_error']
                or report['sdram_words'] != 16384 or report['sdram_checks'] != 32800):
            return False
    if any(current[key] != previous[key] for key in ("cpuid", "device_id")):
        return False
    return all(0 < ((current[key] - previous[key]) & 0xFFFFFFFF) < 0x80000000
               for key in ("ticks", "loops"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    current = decode(args.dump.read_bytes())
    previous = decode(args.previous.read_bytes()) if args.previous else None
    print(json.dumps(current, indent=2))
    if is_live(current, previous):
        print("Counters advanced between supplied snapshots; verify they came from this board/run.")
        return 0
    print("Live execution NOT established: need two valid advancing snapshots from the same run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
