# Oberheim Matrix-1000 — technical documentation

Reverse-engineered, evidence-grounded documentation of the Matrix-1000's hardware
and firmware, plus a full decode of its factory patch ROM. Everything here is
derived from the **v1.11** OS ROM and the factory patch ROM (in `../reference/`),
analysed with the reproducible pipeline in
[disassembly/workflow.md](disassembly/workflow.md). Claims are cited by ROM
address; genuinely open questions are flagged rather than guessed.

Licensed **CC BY 4.0** (see [../LICENSE](../LICENSE)); sources and their terms in
[sources.md](sources.md).

## Reading order

**Start here for the whole-machine view:** [architecture.md](architecture.md) —
a one-page mental model with two diagrams ([system](diagrams/architecture.svg),
[memory map](diagrams/memory-map.svg)). Then the firmware
**[overview](firmware/overview.md)** for the software big picture, then drill in.

### Hardware
- [memory-map.md](hardware/memory-map.md) — the 6809 64K map (start here)
- [io-map.md](hardware/io-map.md) — every I/O register, verified against code
- [voice-architecture.md](hardware/voice-architecture.md) — the CEM3396 voice
- [dac-cv-mux.md](hardware/dac-cv-mux.md) — DAC + mux + S&H CV delivery
- [midi-acia.md](hardware/midi-acia.md) — the 68B50 MIDI interface
- [timing-clocks.md](hardware/timing-clocks.md) — crystal, E-clock, the timers
- [panel-display.md](hardware/panel-display.md) — switches, LEDs, bank latch

### Firmware
- [overview.md](firmware/overview.md) — **the flagship**: the two-interrupt architecture
- [boot-init.md](firmware/boot-init.md) — the reset path
- [ram-map.md](firmware/ram-map.md) — work-RAM layout + the voice-block fields
- [main-loop-and-irq.md](firmware/main-loop-and-irq.md) — foreground, IRQ tick, scheduling
- [voice-engine.md](firmware/voice-engine.md) — per-voice CV compute + scan-out
- [mod-matrix.md](firmware/mod-matrix.md) — the matrix compiled to threaded code
- [midi-handling.md](firmware/midi-handling.md) — the coroutine MIDI parser
- [patch-storage.md](firmware/patch-storage.md) — load, banking, pack/unpack
- [autotune-selftest.md](firmware/autotune-selftest.md) — tuning, calibrate, self-test

### Patch ROM (sound-design track)
- [diagrams/patch-map.svg](diagrams/patch-map.svg) — all 813 patches mapped by brightness × register, coloured by genre
- [format.md](patch-rom/format.md) — the packed 80-byte record
- [parameter-map.md](patch-rom/parameter-map.md) — the 134-parameter model
- [decoding.md](patch-rom/decoding.md) — the decoder + the +8 mapping
- [sound-design-notes.md](patch-rom/sound-design-notes.md) — what the factory did

### Method
- [disassembly/workflow.md](disassembly/workflow.md) — reproduce all of it

## Tools (`../tools/`)

| Tool | Purpose |
|---|---|
| `ghidra/analyze.sh` + `M1kSeed/Stats.java` | import + auto-analyse the ROM in Ghidra |
| `ghidra/M1kDecomp/M1kAsm/M1kRefs/M1kXrefTo.java` | decompile / disassemble / xref helpers |
| `gen_asm_baseline.py` + `roundtrip_check.sh` | the asm6809 byte-identical correctness gate |
| `unpack_patch.py` / `patch_params.py` | faithful patch unpack + parameter labels |
| `decode_patches.py` / `analyze_patches.py` | bulk decode + sound-design statistics |

## Status & open threads

The documented subsystems are complete and cross-checked. A few items are
deliberately left open (and noted in-place) rather than asserted without evidence:

- the exact `$2018+` voice-status/comparator semantics (needs the schematic);
- the precise role of the 12 fixed DCO timer clocks vs the DAC pitch CV;
- pass-2 (`$E08B`) emulation for byte-exact matrix-routing decode (core synth
  parameters are exact);
- the panel-gated `BAD OSC/VCF/RES/WAVE` self-test body;
- the mod source/destination code enumerations are tabulated; per-channel
  DAC→parameter mapping is partial.
