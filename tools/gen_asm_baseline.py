#!/usr/bin/env python3
"""Generate an asm6809 source that reproduces a raw ROM image byte-for-byte.

Every byte is emitted as an FCB at a fixed ORG. This is the *baseline* for the
round-trip validation gate: as the disassembly progresses, runs of FCB data are
replaced by real 6809 instructions, and the reassembled output must remain
byte-identical to the original ROM (verified by tools/roundtrip_check.sh).

Usage:
    gen_asm_baseline.py <rom-file> <base-hex> <out.s>
Example (Matrix-1000 v1.11 OS ROM maps to $8000-$FFFF):
    gen_asm_baseline.py .../M1000-CAT27256P-17_v111.BIN 8000 build/v111_baseline.s
"""
import sys


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    rom_path, base_hex, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    base = int(base_hex, 16)
    rom = open(rom_path, "rb").read()

    out = [
        f"; Round-trip baseline for {rom_path.split('/')[-1]}",
        "; Pure-data (FCB) image. Reassemble with asm6809 and confirm the output",
        "; is byte-identical to the original ROM (tools/roundtrip_check.sh).",
        f"        org   ${base:04X}",
    ]
    for off in range(0, len(rom), 8):
        chunk = rom[off:off + 8]
        out.append("        fcb   " + ",".join(f"${b:02X}" for b in chunk))
    out.append("        end")
    open(out_path, "w").write("\n".join(out) + "\n")
    print(f"wrote {out_path}: {len(rom)} bytes at ${base:04X}")


if __name__ == "__main__":
    main()
