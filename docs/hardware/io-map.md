# I/O map (memory-mapped registers)

Register-level detail for the `$0000–$1FFF` I/O region of the [memory
map](memory-map.md). Addresses with a `@$xxxx` citation are confirmed by a real
access in the v1.11 OS ROM (extracted by `tools/ghidra/M1kRefs.java`). Bit-level
meanings come from the device datasheets and the `bit-hack` schematic notes;
those not yet confirmed against code are flagged **provisional**.

## DCO clock timers — `$0000`, `$0400`, `$0800`, `$0C00`

Four 8253/8254-class programmable interval timers, one per base address, each
with four registers:

| Offset | Register | Notes |
|---|---|---|
| `+0` | Counter 0 | DCO clock |
| `+1` | Counter 1 | DCO clock |
| `+2` | Counter 2 | DCO clock |
| `+3` | Control word | mode/latch programming |

Evidence: control-word writes to each `+3` register at `@$828e` (`$0003`),
`@$8291` (`$0403`), `@$8294` (`$0803`), `@$8297` (`$0C03`), followed by counter
loads to `+0..+2` (`@$82b9…$82fb`). 4 chips × 3 counters = **12 DCO clocks**
(6 voices × 2 DCOs). **Confidence: high** (device type 8253/8254 provisional
pending the timing/clocks deep-dive, #14).

## DAC + CV sample-and-hold — `$1000–$13FF`

The single system DAC (AM6012, 12-bit per earlier research) is time-multiplexed
to every voice parameter through 4051/4053 analog muxes and per-target
sample-and-hold caps. The `bit-hack` notes describe a high/low byte pair:

- `$1000` **DAC high byte** — bits 0–6 select DAC channels 5–11; bit 7 = `FASTX`. *(provisional)*
- `$1010` **DAC low byte** — bits 2–7 control S&H enable and DAC channels 0–4. *(provisional)*

Observed in code: a burst of init writes to `$1008/$1018/$1028/$1038/$1048/$1058`
(stride `$10`, `@$81ef–$81fd`) and `$107E` (`@$9600`). The exact register decode
within this block (and how it maps to the high/low byte model above) is deferred
to the **DAC/CV-mux deep-dive (#13)**. **Confidence: medium** for the region,
**low** for individual bit assignments.

## MIDI ACIA (MC68B50) — `$1400–$15FF`

Register select is on A0; the firmware uses the mirror at `$1406/$1407`.

| Address | R/W | Register | Bits (68B50) |
|---|---|---|---|
| `$1406` | write | **Control** | firmware writes `0x95` = **8N1, ÷16**, Rx-IRQ on, Tx-IRQ off → implies a **500 kHz ACIA clock** for 31250 baud (a dedicated clock, not E/64) |
| `$1406` | read | **Status** | b0 RDRF, b1 TDRE, b2 DCD, b3 CTS, b4 FE, b5 OVRN, b6 PE, b7 IRQ |
| `$1407` | read | **Rx data** | received MIDI byte |
| `$1407` | write | **Tx data** | transmit MIDI byte |

Evidence: the **FIRQ handler** at `$84B4` polls status `$1406` (13 reads
`@$84b6`) and reads/writes data `$1407` — i.e. MIDI receive is FIRQ-driven. The
control byte is confirmed as `0x95` (8N1, ÷16) in `FUN_8505` and the FIRQ TX
drain, implying a **500 kHz ACIA clock**. **Confidence: high**. (Full parser
behaviour in [firmware/midi-handling.md](../firmware/midi-handling.md), #10.)

## System tick timer — `$1600–$17FF`

A fifth 8254-class timer (separate from the four DCO timers) that generates the
periodic **IRQ** driving the tick engine. The IRQ handler reloads it every tick
to re-arm the next interrupt: `$1603 = 0xB6` (control, mode 3) and `$1602 = 0x9C`
(count), seen at `@$85e7`; also set up at boot (`@$8054/$804f`). `$1601` is
touched read/write at `@$b306`. **Confidence: high** that this is the tick-IRQ
source; the exact tick frequency follows from the `0x9C` reload and the timer's
input clock (to compute in #7/#14).

## Front-panel switches — `$1800–$1BFF` (read)

Inputs: `$1800` (`@$818e`) and `$1801` (`@$8178`) return panel switch/encoder
state (scanned against the output latches). **Confidence: high** for "panel
input"; exact row/column mapping deferred to the panel deep-dive (#14).

> Refinement: `$1800` is also **written** — the DAC-CV output primitives
> (`$8991…$8D41`, see dac-cv-mux.md) do `STA $1800` to **select the mux / S&H
> channel** for the value being scanned out. So this address is a write-latch
> (DAC mux select) *and* a read-buffer (panel), a common overlapping decode.

## Output latches — `$1C00–$1FFF` (write)

Write-only latches driving LEDs, the display, the mux/DAC steering, and crucially
the **bank-select** lines:

| Address | Sample site | Likely role |
|---|---|---|
| `$1C06` | `@$9590` | LED/display latch |
| `$1C86` | `@$b6cc` | LED/display latch |
| `$1C07` | `@$8017` | latch |
| `$1C87` | `@$8014` | latch |
| `$1D00` | `@$801a` | latch (init) |
| `$1D80` | `@$8003`, `@$bcce` | **bank-select latch** — supplies the high address lines (VA13–15) that page the `$2000` patch-ROM and `$6000` RAM windows; toggled per byte during banked patch reads (FIRQ-masked). Confirmed in #11 |
| `$1F80` | `@$d08c` | latch |

The `bit-hack` source places three LED latches (L1–L3) at `$1C00/$1C20/$1C40`, a
6-bit **VA13–15 bank-select** latch at `$1C60`, and LED outputs at `$1C80`. Our
observed write addresses are consistent with that block but don't yet pin down
each latch's exact contents. **Confidence: medium**; exact bit assignments and
the bank-select latch are tracked in the panel/bank work (#14) and referenced by
the patch-storage banking logic (#11).

---

## Open questions (carried forward)

- Exact DAC register decode within `$1000–$13FF` and the high/low-byte + S&H/mux
  bit mapping (#13).
- Identity and purpose of the `$1600` block.
- Which `$1C` latch carries the VA13–15 bank-select bits, and their bit order
  (#11, #14).
- Confirm the four timer chips are 8253/8254 and capture their programmed modes
  (#14).
