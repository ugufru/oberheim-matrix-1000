# Disassembly workflow

How to go from the raw Matrix-1000 OS ROM to analysis we can write documentation
from, reproducibly, with standard tools. This is **working material** — the prose
docs under `docs/hardware/` and `docs/firmware/` are the actual product.

Two tools, two jobs:

| Tool | Role |
|---|---|
| **Ghidra 12.x** (+ stock 6809 language) | The analysis brain. Disassembler **and decompiler** — lifts 6809 into readable pseudocode, tracks cross-references, lets us name routines/variables. This is what we read to understand and document the firmware. |
| **asm6809** | The correctness **gate**. We keep an assembleable source of the ROM; reassembling it must produce a **byte-identical** image. This proves our understanding of code-vs-data is right and catches any disassembler misread. |

A third tool — a **6809 emulator / MAME-style trace** — is held in reserve for
dynamic analysis when a routine's control flow is hard to follow statically.

## Anchor target

Canonical ROM: **v1.11 factory**
`reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN`
(32 KB, md5 `3e0280cefb45ff1035ed378fc6ceba8e`).

Confirmed load/runtime facts (cross-checked by hand *and* by Ghidra):

| Fact | Value |
|---|---|
| ROM mapping | file `$0000–$7FFF` → CPU **`$8000–$FFFF`** |
| Ghidra language ID | **`6809:BE:16:default`** (ships in Ghidra's `MC6800` processor; no third-party module) |
| RESET vector | **`$8003`** |
| IRQ vector | **`$85E3`** |
| FIRQ vector | **`$84B4`** |
| SWI / NMI / SWI2 / SWI3 | unused (`$FFFF`) |
| Code/data extent | ≈ `$8000–$E1E6`; remainder is `$FF` padding |

## Prerequisites

- **Ghidra** (`brew install ghidra`, pulls `openjdk@21`). Launcher: `ghidraRun`;
  headless: `$(brew --prefix ghidra)/libexec/support/analyzeHeadless`.
- **asm6809** (`brew install asm6809`).
- **python3** (stock) for the baseline generator.

## Part A — Ghidra analysis (understanding)

One command imports the ROM, seeds the entry points, and runs auto-analysis:

```sh
tools/ghidra/analyze.sh                 # defaults to the v1.11 ROM
tools/ghidra/analyze.sh path/to/other.BIN
```

What it does (see the scripts in `tools/ghidra/`):

- Imports the raw image with language `6809:BE:16:default`, base address `$8000`.
- **`M1kSeed.java`** (preScript) reads the 6809 vector table, disassembles each
  in-ROM vector target, and creates a named function (`vec_RESET`, `vec_IRQ`,
  `vec_FIRQ`). Auto-analysis then follows calls/jumps from these roots.
- **`M1kStats.java`** (postScript) prints coverage (functions / instructions).

The project is written to **`build/ghidra/`** (git-ignored). Reopen it
interactively for the real work — decompiler view, renaming, comments:

```sh
ghidraRun        # File > Open Project > build/ghidra/m1k
```

First-pass coverage from the vector roots alone: ~98 functions / ~3470
instructions. Coverage grows as we mark data tables, resolve jump tables, and
follow the string-referenced UI/self-test routines.

## Part B — Round-trip gate (correctness)

Generate an assembleable baseline of the ROM and prove it reassembles exactly:

```sh
python3 tools/gen_asm_baseline.py \
    reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN \
    8000 build/v111_baseline.s
tools/roundtrip_check.sh \
    reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN \
    build/v111_baseline.s
# -> ROUND-TRIP: BYTE-IDENTICAL ✓
```

The baseline starts as pure `FCB` data (trivially byte-exact). As we identify
real code in Ghidra, we translate those regions to 6809 mnemonics in the source
and re-run the check — it must stay byte-identical. That is the standard by
which a region is considered "understood."

## Why both

Ghidra's stock 6809 spec has had rough edges historically (e.g. an immediate-
operand p-code bug, `EXG` handling). The decompiler is invaluable for *reading*
intent, but we never trust it blindly: the asm6809 round-trip is ground truth
for what the bytes actually are. Ghidra tells us *what a routine means*; asm6809
proves *we read every byte correctly*.

## Reproduce from scratch

```sh
brew install ghidra asm6809
tools/ghidra/analyze.sh                                   # Part A
python3 tools/gen_asm_baseline.py <rom> 8000 build/v111_baseline.s
tools/roundtrip_check.sh <rom> build/v111_baseline.s      # Part B
```
