#!/usr/bin/env python3
"""Aggregate sound-design statistics across the factory patch ROM.

Decodes every record (faithful pass-1 unpack + the +8 parameter mapping) and
prints distributions used for docs/patch-rom/sound-design-notes.md.

Note: core synthesis parameters (DCO/VCF/VCA/envelopes/LFOs) are byte-exact from
pass 1. The matrix-routing bytes (params 104-133) are refined by the firmware's
pass-2 ($E08B), which is not emulated here, so matrix-routing tallies are
INDICATIVE (invalid source codes 21-31 may appear as artifacts).

Usage:
    analyze_patches.py <os-rom> <patch-rom>
"""
import sys
import collections
from unpack_patch import unpack
from patch_params import labelled, SOURCES, DESTS
from patch_names import NAMES

KB = {0: "Reassign", 1: "Rotate", 2: "Unison", 3: "Reassign-Rob"}


def main():
    os_rom = open(sys.argv[1], "rb").read()
    pr = open(sys.argv[2], "rb").read()
    n = len(pr) // 80
    P = []
    for i in range(n):
        d = labelled(unpack(os_rom, pr[i * 80:i * 80 + 80])[0])
        d["_num"] = 200 + i
        d["_name"] = NAMES.get(200 + i, "")
        P.append(d)
    real = [d for d in P if (d["vcf_freq"] or d["dco1_freq"] or d["env1_attack"]
                             or any(d["mod%d_source" % k] for k in range(10)))]
    m = len(real)
    print("records=%d  non-empty=%d" % (n, m))

    print("\n[voice] keyboard mode:",
          dict(collections.Counter(KB.get(d["keyboard_mode"], d["keyboard_mode"]) for d in real)))
    print("[osc] DCO2 sync on:", sum(1 for d in real if d["dco_sync"]), "/", m)

    def bucket(key, edges):
        c = collections.Counter()
        for d in real:
            v = d[key]
            for lo, hi, lab in edges:
                if lo <= v <= hi:
                    c[lab] += 1
                    break
        return dict(c)

    print("[filter] VCF cutoff (0-127):",
          bucket("vcf_freq", [(0, 15, "0-15"), (16, 47, "16-47"), (48, 79, "48-79"), (80, 127, "80-127")]))
    print("[filter] VCF resonance (0-63):",
          bucket("vcf_reso", [(0, 5, "0-5"), (6, 31, "6-31"), (32, 63, "32-63")]))
    print("[filter] mean cutoff=%.1f reso=%.1f" %
          (sum(d["vcf_freq"] for d in real) / m, sum(d["vcf_reso"] for d in real) / m))

    fast = sum(1 for d in real if d["env1_attack"] <= 2)
    print("[env] ENV1 attack<=2 (percussive): %d (%.0f%%)" % (fast, 100 * fast / m))
    print("[env] ENV1 mean A/D/S/R=%.1f/%.1f/%.1f/%.1f" % (
        sum(d["env1_attack"] for d in real) / m, sum(d["env1_decay"] for d in real) / m,
        sum(d["env1_sustain"] for d in real) / m, sum(d["env1_release"] for d in real) / m))

    # matrix (indicative)
    pairs, srcs, dsts, nb = collections.Counter(), collections.Counter(), collections.Counter(), []
    for d in real:
        a = 0
        for k in range(10):
            s, ds, amt = d["mod%d_source" % k], d["mod%d_dest" % k], d["mod%d_amount" % k]
            if s and ds and amt:
                a += 1
                pairs[(SOURCES.get(s, "?%d" % s), DESTS.get(ds, "?%d" % ds))] += 1
                srcs[SOURCES.get(s, "?%d" % s)] += 1
                dsts[DESTS.get(ds, "?%d" % ds)] += 1
        nb.append(a)
    print("\n[matrix, indicative] avg active buses/patch=%.2f  zero-bus patches=%d"
          % (sum(nb) / m, sum(1 for x in nb if x == 0)))
    print("[matrix] top routings:")
    for k, v in pairs.most_common(12):
        print("   %-26s %d" % ("%s -> %s" % k, v))
    print("[matrix] top sources:", dict(srcs.most_common(8)))
    print("[matrix] top destinations:", dict(dsts.most_common(8)))

    def tag(d):
        return "#%d %s" % (d["_num"], d["_name"])

    def buses(d):
        return sum(1 for k in range(10)
                   if d["mod%d_source" % k] and d["mod%d_dest" % k] and d["mod%d_amount" % k])

    print("\n[named examples]")
    hr = max(real, key=lambda d: d["vcf_reso"])
    print("  highest resonance : %-14s reso=%d" % (tag(hr), hr["vcf_reso"]))
    mb = max(real, key=buses)
    print("  most matrix buses : %-14s buses=%d" % (tag(mb), buses(mb)))
    perc = [d for d in real if d["env1_attack"] <= 1 and d["env1_decay"] >= 30]
    if perc:
        print("  percussive (fast atk, long decay): " + ", ".join(tag(d) for d in perc[:5]))


if __name__ == "__main__":
    main()
