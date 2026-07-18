# Firmware architecture (macro view)

How the Matrix-1000 firmware is put together, at the altitude of "what runs when
and why." Details of each subsystem live in the sibling docs; this is the map
that ties them together. Everything here is derived from the **v1.11** OS ROM in
Ghidra (entry points seeded by `tools/ghidra/M1kSeed.java`, control flow read via
`tools/ghidra/M1kDecomp.java`) and cross-checked against the
[memory](../hardware/memory-map.md) / [I/O](../hardware/io-map.md) maps.

> Confidence: the boot path and the two interrupt handlers are well recovered and
> quoted by address below. The *foreground* loop is only partially resolved so
> far (it is reached through an indirect jump the decompiler can't yet follow);
> that gap is called out where it matters and is the subject of #7.

## The big idea: a dumb analog synth steered by interrupts

The analog hardware holds no state of its own — every oscillator clock, filter
cutoff, and VCA level is a voltage the CPU must continuously refresh. So the
firmware is built as a **real-time engine driven by two interrupts**, with the
foreground doing only slow housekeeping:

```
            ┌──────────────────────────────────────────────┐
   RESET ──▶│ boot/init  (vec_RESET @ $8003)                │
            │  hw init • build 6 voice blocks • load patch  │
            │  • enable interrupts • drop into foreground    │
            └───────────────┬──────────────────────────────┘
                            │ (CLI; runtime is interrupt-driven)
        ┌───────────────────┴───────────────────────────────┐
        ▼                                                     ▼
  FIRQ @ $84B4                                          IRQ  @ $85E3 ─▶ $85E7
  MIDI ACIA byte ISR                                   periodic TICK ENGINE
  • RX ring $7593–$7792                                • reload $1600 tick timer
  • TX ring $7793–$7992                                • drain MIDI RX → parser $C42B
  • re-gates ACIA TX irq                               • per-voice env/pitch update ×6
                                                       • distribute global mods (round-robin)
                                                       • scan CVs out to DAC  ($875A)
```

The "~50 Hz / 20 ms CV update" figure from the README is the cadence of this IRQ
tick engine.

## Boot / init — `vec_RESET` @ `$8003`

In order (see `docs/firmware/boot-init.md` for the full trace):

1. **Lamp/latch reset & init retry.** Drives the output latches (`$1C87`, `$1C07`,
   `$1D00`) to `0xFF`, then runs the hardware-init block inside a `while(true)`
   that repeats if a panel button is held (test/diagnostic entry, tested via
   `$1801` bits).
2. **Hardware init**, each step preceded by a progress breadcrumb written to
   `$7FFD` (a nice "where did it hang" marker):
   - `FUN_81e4` — write mid-scale (`0x8000`) to the six DAC channels
     `$1008…$1058` (DAC/voice settle).
   - `FUN_828c` — program the four **DCO timer** chips: control word `0xB6`
     (8254 mode 3, square wave) to `$0003/$0403/$0803/$0C03`, then load counts.
   - set up the `$1600` **tick timer** (`$1602=0x9C`, `$1603=0xB6`) and install
     the IRQ vector `_DAT_79f9 = $85E7`.
3. **Build six voice blocks.** A loop (counter `$7222 = 6`) constructs a
   `0x300`-byte state block per voice at `$6000 + n×$300`, pre-filling each with
   pointers to that voice's DAC/S&H channels (`$1000 + n×$10`) and work fields
   (see [voice model](#the-voice-state-model)).
4. **Clear per-voice accumulators** (`FUN_8206`) and build the voice-allocation
   table at `$7531–$7536`.
5. **Start the runtime:** on the normal path (`$7C3A == 0`) call `FUN_8505`
   (MIDI/ACIA init), `FUN_db95` (synth state / power-on patch), `FUN_d2bb`
   (patch → voice & modulation-matrix setup), enable the engine and fall into the
   foreground.

## The two interrupts

### FIRQ @ `$84B4` — MIDI byte engine

The ACIA (MC68B50 at `$1406/$1407`) raises **FIRQ** per byte. The handler is a
classic double-ring-buffer UART ISR:

- **Receive** (`status & 1` set): read `$1407`, store into the RX ring
  `$7593–$7792`, advance with wraparound.
- **Transmit** (`status & 1` clear → TDRE): pull the next byte from the TX ring
  `$7793–$7992`, write `$1407`; when the ring drains, write `0x95` to the ACIA
  control register to **turn the TX interrupt back off**.

The ISR only moves bytes; it never parses. Parsing happens in the tick engine.
(Full detail: `docs/firmware/midi-handling.md`, #10.)

### IRQ @ `$85E3 → $85E7` — the tick engine

`vec_IRQ` is a 4-byte trampoline that jumps through a RAM pointer
(`(*_DAT_79f9)()`), so the tick handler is **revectorable** — the firmware can
swap it (used by calibration/test modes). The default target `$85E7` is the
real-time engine. Each tick it:

1. **Reloads the `$1600` tick timer** (`$1603=0xB6`, `$1602=0x9C`) so the next
   interrupt fires — this is what makes it periodic.
2. **Services MIDI RX:** if the RX ring is non-empty (`$7993 != $7995`), calls
   the MIDI **parser at `$C42B`** to consume queued bytes.
3. **Per-voice update:** loops the six voice blocks (`$6000`…`$6F00`, step
   `$300`) stepping each voice's envelope/portamento/pitch state machine
   (fields `+$14…+$23`).
4. **Distributes global modulators** (LFOs / shared sources from tables at
   `$7A3B…$7AA2`) into one voice per tick, cycling through the allocation list
   via `_DAT_7228` — a round-robin that spreads slow updates across ticks.
5. **Scans CVs to hardware** via `(*0x875A)()` (DAC/mux write-out), then
   dispatches onward through `(*_DAT_753f)()`.

This single handler is the heart of the instrument: it is where modulation is
evaluated and where the analog voices actually get their voltages. Subsystems
4–5 are detailed in `voice-engine.md` (#8) and `mod-matrix.md` (#9).

### Foreground

After enabling interrupts (`ANDCC #$0E`) the boot path jumps to `$8302`, a tight
**polling dispatcher**: it spins reading six per-voice service flags
(`$2018 + n×$300`, bit 7) and, when one is raised, synthesizes a fast-IRQ stack
frame and jumps into the tick engine, which `RTI`s back to the poll. So the
foreground itself does no slow housekeeping — it exists only to raise the engine
on demand, alongside the periodic `$1600` timer IRQ. Full detail (and the three
converging paths into the engine) is in `main-loop-and-irq.md` (#7).

## The voice state model

Six **voice blocks**, `0x300` bytes each, based at `$6000 + n×$300`
(`$6000, $6300, $6600, $6900, $6C00, $6F00`). This is the firmware's core data
structure; the tick engine walks it every tick. Each block caches:

- pointers to the voice's **DAC / sample-and-hold channels** at `$1000 + n×$10`
  (pitch, pulse width, filter, VCA, etc.), so the scan-out is a few indexed
  stores;
- envelope / portamento / pitch **state machine** fields (`+$14…+$23`);
- modulation accumulators (cleared by `FUN_8206`).

Voice allocation (which physical voice plays which note, and voice-stealing) is
tracked in a small table at `$7531–$7538`. The detailed field layout is the work
of `docs/firmware/ram-map.md` (#6).

## Where to go next

| Subsystem | Entry point(s) | Doc (issue) |
|---|---|---|
| Boot / init, RAM layout | `$8003` | boot-init.md, ram-map.md (#6) |
| Foreground loop & tick timer | indirect; `$85E7` | main-loop-and-irq.md (#7) |
| Voice engine / DAC scan-out | `$85E7`, `$875A` | voice-engine.md (#8) |
| Modulation matrix | `$7A3B…` tables | mod-matrix.md (#9) |
| MIDI (ACIA, rings, parser) | `$84B4`, `$C42B` | midi-handling.md (#10) |
| Patch storage / pack-unpack | `$db95`, `$d2bb` | patch-storage.md (#11) |
| Autotune / self-test | panel-held boot branches | autotune-selftest.md (#12) |

## Open questions

- The `(*_DAT_753f)()` tick-engine continuation / mode dispatch (#12).
- Tick frequency: compute it from the `$1600` timer reload (`0x9C`) and its clock.
- The `(*0x875A)()` scan-out: confirm the full DAC/mux channel ordering (#8/#13).
