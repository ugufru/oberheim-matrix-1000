# Sources & references

This project derives its conclusions **from the ROMs themselves** (see
`disassembly/workflow.md`), and cross-checks them against prior community work.
Our prose is original; the sources below were used for corroboration, hardware
detail we can't see in code, and the patch parameter model. Where a source's
licence is restrictive, we cite facts and do not copy text.

## Primary artefacts (in this repo)

- **v1.11 OS ROM** and the **factory patch ROM**, plus other firmware versions —
  `../reference/extracted/` (see `../reference/extracted/MANIFEST.md`). These are
  third-party firmware images included for study; they are **not** covered by this
  project's licence and remain the property of their respective owners.

## Hardware

- **Bob Grieb (Tauntek) redrawn Matrix-1000 schematics**, hosted on untergeek.de
  — the cleanest schematic set (CPU/memory/decode, MIDI, timers, DAC/CV-mux,
  voice, LEDs/switches). Authority for the analog signal path.
  <https://www.untergeek.de/howto/oberheim-matrix-1000/>
- **`bit-hack/OberheimMatrix1000`** (GitHub) — a memory map gleaned from the
  schematics and a DASMx listing; used to corroborate our code-derived map.
  <https://github.com/bit-hack/OberheimMatrix1000>
- **untergeek "Geek's Guide" / "Brain Surgery"** — practical hardware, failure
  modes, the 6809/6309 detail. <https://www.untergeek.de/2014/09/matrix-1000-brain-surgery/>
- Component datasheets: **MC6809E**, **MC68B50** (ACIA), **AM6012** (DAC),
  **82C54** (timers), and the **CEM3396** voice chip —
  `reference/CEM3396-datasheet.pdf` (Curtis, June 1984). The datasheet is the
  authority for the analog voice and corrected several firmware-side inferences
  (pitch is a digital timer/divider not a CV; ~5 VCAs; high-Z inputs eliminate
  dedicated sample-and-hold buffers). Source: <https://www.deepsonic.ch/deep/docs_manuals/cem_3396_manual.pdf>

## Manuals & patch references (in `reference/`)

- **Oberheim Matrix-1000 Owner's Manual** (2nd ed., July 1988, P/N 950071) —
  `reference/OberheimMatrix1000.pdf`. The official parameter / MIDI / SysEx tables.
- **Don Solaris — Matrix-1000 patchbook** — `reference/donsolaris-matrix1000.pdf`.
  Human names for all 1000 factory patches by number (the names the M1000 itself
  does not store; see patch-rom/decoding.md). Source: <https://donsolaris.com/m1000/>

## Patch format

- **CMU — Matrix-6 patch & SysEx format** (Eli Brandt):
  <https://www.cs.cmu.edu/~eli/music/m6-patch.html> ·
  <https://www.cs.cmu.edu/~eli/music/m6-sysex.html>
- **youngmonkey — Matrix-1000 SysEx reference** (parameter / source / destination
  code tables): <http://www.youngmonkey.ca/nose/audio_tech/synth/Oberheim-Matrix1000.html>

## Firmware lineage / prior art

- **Tauntek (Bob Grieb)** custom firmware: <https://www.tauntek.com/Matrix1000Firmware.htm>
- **GliGli** v1.16 ROM-only upgrade (blog) and **Nordcore** v1.13/1.14 bug-fix
  builds — documented in the `../reference/extracted/` changelogs and community
  threads (Gearspace / Mod Wiggler "Matrix 1000 firmware hacks").
- **Vintage Synth Explorer** — Matrix-1000 overview:
  <https://www.vintagesynth.com/oberheim/matrix-1000>

## Tools used

- **Ghidra** 12.x (stock 6809 language) — primary analysis.
- **asm6809** — the byte-identical round-trip correctness gate.
- **Python 3** — the patch decoders/analysis.

## A note on accuracy

Anything stated as fact is backed by a ROM address or a cited source; inferences
are marked as such, and open questions are flagged in-place. Where our
code-derived findings differ from a source, we say so rather than defer (e.g. the
ACIA divide, the `$1600` tick timer, the 200/800 patch split — all confirmed from
code).
