# Oberheim Matrix-1000

A reference for the **hardware and electronics of the Oberheim Matrix-1000**, written as the
shared baseline for discussing its **firmware** — how the firmware works, and how it might be
changed or rewritten.

> 📖 **Full technical documentation is in [`docs/`](docs/README.md)** — hardware, a complete
> firmware analysis (derived from the v1.11 ROM), and a decode of the factory patch ROM.
> Licensed [CC BY 4.0](LICENSE).

The Matrix-1000 (1987) is a 6-voice **digitally-controlled analog** rack synthesizer. Its sound
engine is inherited from the Oberheim Matrix-6; the Matrix-1000 removes almost all front-panel
editing, reducing the panel to bank/program selection, and ships with 1000 onboard patches.

The reason this synth is interesting from a firmware standpoint is that **almost all of its
behavior lives in firmware**: patch storage and recall, evaluation of the modulation matrix,
generation of every control voltage that drives the analog voices, MIDI handling, and the
auto-tune calibration routine. The analog hardware is "dumb" — the firmware is the instrument.

> **Accuracy note.** A widely-repeated claim is that the Matrix-1000 uses an Intel 8031. It does
> **not** — the CPU is a Motorola 6809. Items still to be independently confirmed are flagged
> **(to confirm)** below; they don't change the overall picture but we'll nail them down as we
> dig into the actual code.

---

## 1. Digital / control system — the firmware's world

| Item | Spec | Why it matters for firmware |
|---|---|---|
| **CPU** | Motorola **6809** (8-bit), **2 MHz** E-clock, derived from an **8 MHz** crystal | The processor that runs everything. Target ISA for any rewrite. |
| **CPU mod** | Drop-in **Hitachi 6309** (binary-compatible, overclockable to ~4 MHz) | Popular headroom upgrade; the 6309 also has extra registers/native mode a rewrite could exploit. |
| **OS / program ROM** | **32 KB** firmware in a socketed **27C256** EPROM | This *is* the firmware. Update = reburn/swap the chip — there is **no MIDI firmware upload**. |
| **Patch ROM** | A **separate 64 KB** EPROM (**27C512**) holding the factory patch set | A second physical chip — distinct from the OS ROM. The firmware reads patch data from here (see §4). |
| **RAM / battery** | User patch RAM kept alive by a soldered **CR2032** | Dead battery ⇒ lost user patches. Firmware owns the RAM patch format. |
| **DCO clock generation** | **Four** socketed DCO clock-divider counters; voice pitch references derived from the CPU clock chain | Oscillator pitch is generated digitally and steered by firmware. |
| **MIDI** | Serial **UART/ACIA** (likely a 6850-class ACIA — **to confirm**), MIDI **In / Out / Thru** | The firmware's only real-time I/O. MIDI throughput is a known bottleneck (see §6). |
| **CV update rate** | Original firmware refreshes voice CVs at **~50 Hz (20 ms)** | Sets the **~20 ms minimum attack** and overall responsiveness — a key limit later firmware pushes on. |

---

## 2. Voice architecture — what the firmware steers

- **6 voices**, each a single **Curtis CEM3396** (24-pin DIP). One chip = a complete voice:
  **2 DCOs + waveshaper + multimode filter (VCF) + 2 VCAs**.
- **CV delivery is multiplexed.** A single **DAC** is time-shared: the firmware writes a value,
  then routes it through **CD4051 / CD4053** analog multiplexers into a **sample-and-hold**
  capacitor for one specific parameter of one specific voice. The firmware continuously scans
  through all parameters × voices to keep the S&H caps refreshed.
  - Practical note: the DAC, **4053** (next to the DAC) and the pair of **4051s** behind each
    voice are the classic failure points — and they're exactly the path the firmware drives.
- **Auto-tune.** A firmware routine calibrates oscillator and filter CVs against the pitch
  reference so the analog voices stay in tune.

---

## 3. Synthesis / modulation model — the math the firmware runs

This is the per-cycle computation the firmware performs **for all 6 voices**:

- **Matrix Modulation:** **20 user-definable routings**, ~20 modulation **sources** → ~32
  **destinations**, in addition to a set of fixed/hardwired routings.
- **Per voice modulators:**
  - **3 × DADSR** envelopes
  - **2 × LFOs**
  - **2 × ramp / portamento** generators
  - tracking generator, plus FM / cross-modulation between the DCOs.
- **Patch format:** the internal patch byte layout and the single-patch MIDI SysEx format will
  be documented separately once we get into the firmware itself.

---

## 4. Memory & patches

- **Two ROMs, not one.** The synth has a **32 KB OS ROM** (27C256, the firmware) *and* a
  **64 KB patch ROM** (27C512, the factory sounds). They are separate physical chips. Confirmed
  by the dumps in `reference/extracted/` — the patch ROM image is 64 KB and self-identifies as
  *"Original Patch ROM image"* (same image for black- and white-faced units).
- **1000 patches** total — approximately **200 user-writable** (battery-backed RAM) plus
  **~800 factory** (patch ROM). *(Exact user/factory bank split: **to confirm**.)*
- Patch transfer over MIDI **SysEx** (single-patch and bulk dump/load); standard **bank/program
  change** for selection.

---

## 5. Firmware (OS ROM) versions

There are **two independent custom-firmware lineages**. Don't conflate them.

**Lineage A — Nordcore / GliGli bug-fix builds** (these are the OS images in
`reference/extracted/matrix-1000/os-rom/`):

| Version | Source | Notes |
|---|---|---|
| **v1.03 / v1.11** | Oberheim factory | Original shipping firmware (v1.11 is the last stock OS). |
| **v1.13** | **Nordcore** (CFW) | 3 bug fixes over stock. |
| **v1.14** | **Nordcore** (CFW) | 4 bug fixes incl. NRPN. Ships with an exact **byte-patch map** (`os-rom/v1.14/M1000-firmware_fixes.txt`) — offset, orig→fixed value, and description for each fix. A ready-made set of landmarks into the binary. |
| **v1.16** | **GliGli** (CFW) | NRPN fix, faster mod-matrix rebuild, and **unison detune** via MIDI CC#94. |

**Lineage B — Tauntek rewrite** (*not* present in our archive):

| Version | Source | Notes |
|---|---|---|
| **v1.20 / v1.21** | **Bob Grieb (Tauntek)** | Larger partial **reverse-engineered rewrite**: faster real-time MIDI CC handling **without dropping input**, added display feedback, sped-up critical control paths. The most relevant prior art for a substantial rewrite. |

---

## 6. Known firmware-relevant limitations

- **MIDI under load:** the factory firmware can drop incoming MIDI CC data; modulation/parameter
  response is sluggish. Both the GliGli (v1.16) and Tauntek (v1.20+) work target this.
- **Coarse CV timing:** the ~50 Hz / 20 ms update loop caps attack speed and modulation
  smoothness.
- **No in-field update path:** firmware changes require physically reprogramming the 27C256.

---

## Roadmap

The goal of this project is **the best openly-usable technical documentation of the
Matrix-1000** — its hardware and how the **existing firmware operates at a macro level** —
derived by disassembling the OS ROM (anchored on **v1.11 factory**) with standard 6809 tools.
The disassembly is working material; the **prose docs are the product**. A secondary track mines
the 64 KB **patch ROM** for sound-design data and documents the patch format.

Planned documentation tree (built incrementally):

```
docs/
  hardware/     memory map, I/O map, DAC/CV-mux, voice (CEM3396), MIDI/ACIA, clocks, panel
  firmware/     macro overview, boot/init, main-loop & IRQ scheduler, voice engine,
                mod-matrix, MIDI handling, patch storage, autotune/self-test, RAM map
  patch-rom/    packed record format, 134-byte parameter map, decoder, sound-design notes
  disassembly/  reproducible standard-tools workflow + entry points (derivation material)
```

Work is tracked as a prioritized backlog in [`issues.jsonl`](issues.jsonl). The order:

1. **Foundation** — reproducible 6809 disassembly pipeline with `asm6809` round-trip
   validation (re-assembled output must be byte-identical to the ROM), then a memory/IO map
   verified against actual code accesses.
2. **Firmware (macro)** — a flagship architecture overview, then subsystem deep-dives.
3. **Patch-ROM track** *(parallel side project)* — the firmware's pack/unpack routine is the key
   that unlocks decoding all 800 factory patches and the sound-design analysis.

Everything will be cross-checked against existing prior art (Bob Grieb's redrawn schematics,
the `bit-hack/OberheimMatrix1000` memory map, the CMU Matrix-6 patch tables) — cited, not copied
— and published under an open license so anyone can reuse it.

---

## Local reference material

Firmware/patch dumps and schematics live in `reference/` (original zips) and are unzipped,
deduplicated, and organized under `reference/extracted/` — see
`reference/extracted/MANIFEST.md` for the full inventory, md5s, and provenance. Highlights:
OS ROM images v1.03–v1.16, the 64 KB patch ROM, Matrix-6/6R firmware, and XK schematics.

## References

- untergeek — "Geek's Guide to the Matrix-1000" / "Matrix-1000 Brain Surgery":
  <https://www.untergeek.de/2014/09/matrix-1000-brain-surgery/>
- Matrix-1000 hardware notes (wolzow / mindworks): `http://wolzow.mindworks.ee/analog/m1k-hardware.htm`
- Tauntek — Matrix-1000 firmware (Bob Grieb): <https://www.tauntek.com/Matrix1000Firmware.htm>
- Vintage Synth Explorer — Oberheim Matrix-1000: <https://www.vintagesynth.com/oberheim/matrix-1000>

*Items marked **(to confirm)** are our open questions to verify against the firmware/schematics
as the discussion proceeds.*
