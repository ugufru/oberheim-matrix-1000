# Memory map (6809 address space)

The Matrix-1000 CPU is a Motorola 6809 with a full 64 KB address space. This map
is **derived two ways and reconciled**: (a) the published address-decode map in
`bit-hack/OberheimMatrix1000` (gleaned from the schematics), and (b) the
addresses the v1.11 firmware *actually* reads/writes, extracted from the Ghidra
analysis by `tools/ghidra/M1kRefs.java`. Where a row cites a `@$xxxx` sample
site, that is a real instruction in the OS ROM that touches the address —
i.e. the entry is **verified against code**, not just the schematic.

> Coverage caveat: the reference extraction reflects the code analyzed so far
> (~100 functions seeded from the vectors). Regions are all represented, but
> individual addresses will keep accruing evidence as later issues deepen the
> disassembly. Confidence is flagged per row.

## Top-level map

| CPU range | Size | Contents | Device | Evidence / confidence |
|---|---|---|---|---|
| `$0000–$0FFF` | 4 KB | **DCO clock timers** — four interval-timer chips at `$0000/$0400/$0800/$0C00`, registers `+0..+3` | 4 × 8253/8254-class | **code** — init writes `@$828e–$82fb`; **high** |
| `$1000–$13FF` | 1 KB | **DAC + CV sample-and-hold / mux control** | AM6012 DAC + 4051/4053 + S&H | **code** — writes `@$81ef–$81fd`, `@$9600`; **med** (bit meanings via schematic) |
| `$1400–$15FF` | 512 B | **MIDI ACIA** (control/status `$1406`, data `$1407`) | MC68B50 | **code** — FIRQ serial RX reads `$1406` ×13 `@$84b6`; **high** |
| `$1600–$17FF` | 512 B | **System tick timer** (generates the periodic IRQ) | 8254-class | **code** — reloaded every tick by the IRQ engine (`$1602=0x9C`, `$1603=0xB6`) `@$85e7`; **high** |
| `$1800–$1BFF` | 1 KB | **Front-panel switch inputs** (read-only) | switch matrix | **code** — reads `$1800/$1801` `@$8178/$818e`; **high** |
| `$1C00–$1FFF` | 1 KB | **Output latches** — LEDs, display, and the **VA13–15 bank-select** latch | latches | **code** — write-only `$1C06/$1C86/$1D00/$1D80/$1F80`; `$1D80` written at reset `@$8003`; **med** |
| `$2000–$3FFF` | 8 KB | **Patch ROM window** (banked; see below) | 27512 | **code** — reads `$2018…$2F18` `@$8302–$831b`; **high** |
| `$4000–$5FFF` | 8 KB | **Expansion ROM** socket (optional, often empty) | 27512 (U802) | schematic only — no code refs observed; **low** |
| `$6000–$7FFF` | 8 KB | **Battery-backed RAM window** (banked; patch edit buffer + work RAM) | 43256 SRAM | **code** — heavy R/W across `$60xx–$7Fxx`; **high** |
| `$8000–$FFFF` | 32 KB | **OS / code ROM** (the firmware) | 27256 | execution; vectors at `$FFF0–$FFFF`; **high** |

(Device U-numbers above are from the bit-hack/schematic source and not yet
independently confirmed; treat them as provisional.)

## DCO clock timers (`$0000–$0FFF`)

Four interval-timer chips, decoded at `$0000`, `$0400`, `$0800`, `$0C00`, each
exposing four registers at offsets `+0/+1/+2/+3` (three counters + a control
word — the classic 8253/8254 layout). The firmware programs all four during
init (control-word writes to the `+3` register at `@$828e/$8291/$8294/$8297`,
then counter loads). Four chips × three counters = **twelve oscillator clocks**,
one per DCO across the six voices (2 DCOs each). This is the hardware behind the
README's "four DCO clock-divider counters" note.

## I/O block (`$1000–$1FFF`)

A 4 KB region sub-decoded (roughly by address bits A10/A11, then finer) into the
DAC, ACIA, panel inputs, and output latches — detailed register-by-register in
[`io-map.md`](io-map.md).

## Banking (`$2000–$7FFF` windows)

The patch ROM (27512 = **64 KB**) and the work/patch RAM (43256 = **32 KB**) are
each larger than their 8 KB CPU windows. A latch in the `$1C00` block supplies
the upper address lines **VA13–VA15** (the bit-hack source calls it the "6-bit
latch with VA13–VA15 bank select"):

- Patch ROM: 8 KB window `$2000–$3FFF` × **8 banks** (VA13–15) = 64 KB → all 800
  factory patches reachable.
- RAM: 8 KB window `$6000–$7FFF` × **4 banks** (VA13–14) = 32 KB.

So reading a patch = set the bank latch, then read through `$2000–$3FFF`. This
is the mechanism the patch-storage firmware (#11) and the patch-ROM decode track
(#15) build on. *Exact latch bit assignments to be confirmed against the
schematic and the bank-select code.*

## Vector table (`$FFF0–$FFFF`)

Eight big-endian 16-bit vectors. On v1.11 (see `tools/ghidra/M1kSeed.java`,
confirmed by hand and by Ghidra):

| Vector | Address | Target |
|---|---|---|
| FIRQ | `$FFF6` | `$84B4` (serial / MIDI) |
| IRQ | `$FFF8` | `$85E3` |
| RESET | `$FFFE` | `$8003` |
| SWI / NMI / SWI2 / SWI3 | — | unused (`$FFFF`) |

## How to reproduce the evidence

```sh
tools/ghidra/analyze.sh                      # import + analyze v1.11
# then, against the analyzed project:
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless" build/ghidra m1k \
    -process -noanalysis -scriptPath tools/ghidra -postScript M1kRefs.java
```
