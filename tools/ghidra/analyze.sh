#!/usr/bin/env bash
# Reproducible Ghidra headless import + auto-analysis of a Matrix-1000 OS ROM.
#
# Imports the raw 6809 image at base $8000, seeds the hardware-vector entry
# points (M1kSeed), runs auto-analysis, and prints coverage stats (M1kStats).
# The Ghidra project is written under build/ghidra/ (git-ignored); reopen it
# interactively with `ghidraRun` for decompiler-driven analysis.
#
# Usage:
#   tools/ghidra/analyze.sh [rom-file]
# Defaults to the v1.11 factory OS ROM. Override Ghidra location with GHIDRA_HOME.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
GHIDRA_HOME="${GHIDRA_HOME:-$(brew --prefix ghidra 2>/dev/null)/libexec}"
HEADLESS="$GHIDRA_HOME/support/analyzeHeadless"
ROM="${1:-$REPO/reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN}"
PROJ="$REPO/build/ghidra"
NAME="m1k"

if [ ! -x "$HEADLESS" ]; then
    echo "analyzeHeadless not found at $HEADLESS (set GHIDRA_HOME)" >&2
    exit 1
fi
mkdir -p "$PROJ"

"$HEADLESS" "$PROJ" "$NAME" \
    -import "$ROM" -overwrite \
    -processor "6809:BE:16:default" \
    -loader BinaryLoader -loader-baseAddr 0x8000 \
    -scriptPath "$REPO/tools/ghidra" \
    -preScript M1kSeed.java \
    -postScript M1kStats.java
