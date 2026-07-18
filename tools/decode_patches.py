#!/usr/bin/env python3
"""Decode every factory patch from the patch ROM into named, labelled parameters.

Faithful pass-1 unpack (unpack_patch) + the +8 parameter mapping (patch_params) +
the patch names by number (patch_names). The Matrix-1000 stores no names itself;
they come from the patchbook and pair with the decode by number:

    patch-ROM record r  ==  patch #(r + 200)  ==  patchbook entry (r + 200)

Writes a named CSV to build/ and prints validation + named samples.

Usage:
    decode_patches.py <os-rom> <patch-rom> [out.csv]
"""
import sys
from unpack_patch import unpack
from patch_params import labelled, PARAMS
from patch_names import NAMES

ROM_FIRST_PATCH = 200  # record 0 = patch #200 (banks 2-9 are the patch ROM)


def main():
    os_rom = open(sys.argv[1], "rb").read()
    patch_rom = open(sys.argv[2], "rb").read()
    out_csv = sys.argv[3] if len(sys.argv) > 3 else "build/patches.csv"

    n = len(patch_rom) // 80
    cols = [PARAMS[p][0] for p in sorted(PARAMS)]
    in_range = total = 0
    rows = []
    for i in range(n):
        out, _ = unpack(os_rom, patch_rom[i * 80:i * 80 + 80])
        for v in out:
            total += 1
            in_range += (v <= 0x3F)
        rows.append((i, ROM_FIRST_PATCH + i, NAMES.get(ROM_FIRST_PATCH + i, ""), labelled(out)))

    import os
    os.makedirs("build", exist_ok=True)
    with open(out_csv, "w") as f:
        f.write("record,patch_number,name," + ",".join(cols) + "\n")
        for rec, num, name, d in rows:
            f.write("%d,%d,%s," % (rec, num, name))
            f.write(",".join(str(d[c]) for c in cols) + "\n")

    print("patches decoded : %d" % n)
    print("values <= 0x3F  : %d / %d (%.1f%%)  [rest are signed mod amounts]"
          % (in_range, total, 100.0 * in_range / total))
    print("wrote %s (named, labelled)" % out_csv)
    print("\nnamed samples:")
    for rec in (0, 1, 50, 400):
        num, name, d = rows[rec][1], rows[rec][2], rows[rec][3]
        print("  #%d %-9s  VCF f/reso=%d/%d  VCA1=%d  ENV1 A/D/S/R=%d/%d/%d/%d"
              % (num, name, d["vcf_freq"], d["vcf_reso"], d["vca1_level"],
                 d["env1_attack"], d["env1_decay"], d["env1_sustain"], d["env1_release"]))


if __name__ == "__main__":
    main()
