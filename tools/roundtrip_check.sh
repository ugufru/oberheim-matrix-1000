#!/usr/bin/env bash
# Round-trip validation gate for the Matrix-1000 disassembly.
#
# Assembles a 6809 source with asm6809 and checks the result is byte-identical
# to the reference ROM. This must pass at every step: the disassembly is only
# trustworthy if it reassembles to exactly the original bytes.
#
# Usage:  tools/roundtrip_check.sh <reference-rom> <source.s>
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <reference-rom> <source.s>" >&2
    exit 2
fi
rom="$1"
src="$2"
out="$(mktemp -t roundtrip).bin"
trap 'rm -f "$out"' EXIT

asm6809 -B -o "$out" "$src"

rom_md5=$(md5 -q "$rom")
out_md5=$(md5 -q "$out")
echo "reference : $rom_md5  ($rom)"
echo "reassembled: $out_md5  ($src)"
if [ "$rom_md5" = "$out_md5" ]; then
    echo "ROUND-TRIP: BYTE-IDENTICAL ✓"
else
    echo "ROUND-TRIP: MISMATCH ✗" >&2
    exit 1
fi
