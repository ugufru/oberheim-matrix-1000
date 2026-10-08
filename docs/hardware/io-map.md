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

The single system DAC (AM6012, 12-bit) is time-multiplexed to every voice
parameter through CD4051 muxes and per-target hold capacitors. The address of a
write is itself the route (schematic page 4, confirmed against the code):

- **Even address** (high byte): data bits 6–0 → DAC D1–D7, bit 7 → `FASTb`
  (active low). The same write latches A1–A3 (mux channel), A4–A6 (which mux:
  voices 1–6, then the shared resonance/mix muxes) and A7/A8 (`RANGE1`/`RANGE2`,
  the output range).
- **Odd address** (low byte): bits 7–3 → DAC D8–D12, bit 2 → `ENS&Hb` (0 = mux
  connected).

This replaces the `bit-hack` model ("`$1000` high byte: bits 0–6 select DAC
channels 5–11, bit 7 = FASTX; `$1010` low byte: S&H enable + channels 0–4"),
which had the FAST bit and S&H enable but not the address-as-route decode.
Full detail, the per-channel map and the init write (`$1008 + n×$10` = VCA2 = 0,
`@$81ef–$81fd`) are in [dac-cv-mux.md](dac-cv-mux.md). `$107E` (`@$9600`)
decodes to an unconnected mux channel; its purpose is unknown. **Confidence:
high.**

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

> `$1800` is written once, at `$8995` inside the DCO1 waveshape primitive.
> An earlier revision read that as a DAC mux-select strobe. The schematic shows
> `$1800` decodes only to `SWb`, the enable of the panel switch read buffers
> (74HC240s), and the DAC route is latched from the DAC write address. So that
> store has no documented effect; its purpose is unexplained.

## Output latches — `$1C00–$1FFF` (write)

Write-only latches driving LEDs, the display, the mux/DAC steering, and crucially
the **bank-select** lines:

| Address | Sample site | Likely role |
|---|---|---|
| `$1C00–$1C05` | `@$899C` (via voice `+$77`) | **DCO1 range switch** `RA1–RA6`, one per voice. `$1C00` is a 74HC259 addressable latch (U703): A0–A2 pick the bit, BD0 is the data. Schematic-confirmed; see dac-cv-mux.md |
| `$1C80–$1C85` | `@$8BB0` (via voice `+$7F`) | **DCO2 range switch** `RB1–RB6` (U704, 74HC259), as above |
| `$1C06` | `@$9590` | **Noise enable** `NOI` (U703 Q6), global to all voices |
| `$1C86` | `@$b6cc` | LED/display latch |
| `$1C07` | `@$8017` | latch |
| `$1C87` | `@$8014` | latch |
| `$1D00` | `@$801a`, `@$9587` | **Global voice control** (U705, 74HC174): bit 1 `MUTE`, bit 2 `SYNC2`, bit 3 `SYNC1`, bits 4–5 **wave select** (one line to every voice's CEM3396 pin 6). Shadow `$7235`. See dac-cv-mux.md |
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
