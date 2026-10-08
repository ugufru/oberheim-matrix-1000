# Clocks & timing

Every clock in the machine and what it drives. Clock sources are from the
schematic (Bob Grieb's redraw, pages 1 and 3; Oberheim sheet 4 "Timer"); the timer
programming is from the **v1.11** ROM.

## CPU clock

- **8 MHz crystal** → Motorola 6809 **E-clock = 2 MHz**. All CPU-side timing is
  derived from E.
- Upgrade note: a 6309 drop-in can be overclocked toward ~4 MHz (#hardware notes
  in the README).

## Programmable interval timers (8254-class)

There are **five** 8254-class timer counters' worth of programmable timing,
in two roles:

### Four DCO timer chips — `$0000/$0400/$0800/$0C00` — **these set pitch**

Four **8253/8254** chips, three counters each = **12 counters, one per DCO** across
the six voices. Each counter is a **programmable frequency divider** whose output
clocks a CEM3396 waveform converter — and per the datasheet *"the frequency of
these waveforms is equal to the input digital timing signal,"* with the chip's
timing input annotated **"FROM µP TIMER (e.g. 8253) DETERMINES FREQUENCY."** So
**these timers are the pitch source**: to play a note the firmware loads the
divider for that voice's counter. Oscillators are therefore crystal-stable (no
analog tuning).

`FUN_828c` (mode 3, square-wave, initial counts) is the **boot init**. The
**per-note divider updates** are written at runtime by the pitch primitive
**`FUN_8765`**: it looks a 16-bit count out of the **`$A652`** note→divider table
and loads it **LSB-then-MSB** into the voice's counter, whose address is cached in
the voice block (`+$75`, from the **`$8220`** table = the `$0000`-region counter
addresses). A direct-address xref of `$0000…` shows only the boot writes precisely
because these per-note writes go through that cached pointer.

**Every DCO counter is clocked by E (2 MHz)** (page 3), so pitch is
**f = 2,000,000 / count**. The `$A652` table bears this out: entry 57 is `$11C1` =
4545, which gives **440.04 Hz**, and adjacent entries step by exactly 2^(1/12).
The chips map onto the voices as the `$8220` table says: `$0000` (U813) and
`$0400` (U812) drive the A converters `CLKA1–3` and `CLKA4–6` (DCO1); `$0800`
(U811) and `$0C00` (U810) drive `CLKB1–3` and `CLKB4–6` (DCO2). Only the A
counters have their `GATE` inputs wired (`GATEA1–6`, from each voice's sync
logic, page 5); the B counters' gates are tied high. That is how hard sync makes
DCO1 follow DCO2. (This corrects an
earlier note that called these "fixed clocks" and put pitch on a DAC CV — the
CEM3396 has no pitch CV; pitch is this timer divider. See voice-architecture.md.)

### The system timer: `$1600` (U808)

A fifth 82C54 with three counters (page 3):

| Counter | Clock | Use |
|---|---|---|
| 2 | E (2 MHz) | **the tick**: OUT2 drives `IRQ` |
| 1 | E (2 MHz) | timebase for CALIBRATE's period measurement |
| 0 | `PULSE` | the voice-output comparator (see voice-architecture.md); set up at boot (`$805E`) |

The tick count is `$9C40` = 40,000 (`$8052–$8059`, LSB `$40` then MSB `$9C`), in
mode 3: **2 MHz / 40,000 = exactly 50 Hz, a 20 ms period.** That confirms the
community "~50 Hz / 20 ms" figure from the hardware.

The IRQ entry (`$85E7`) reprograms counter 2 every time the engine runs: first
mode 1 with a count of 1, then mode 3 with `$9C40` again. Writing the control
word restarts the counter, so the next tick comes **20 ms after the last engine
run**, not on a fixed grid. That matters for the foreground's on-demand
dispatch (main-loop-and-irq.md), which runs the engine through the same entry
and so also restarts the 20 ms clock.

## ACIA clock

The MC68B50 runs from a **500 kHz** clock (÷16 → 31250 baud). It is derived from
E: two 74LS74 flip-flops (U807, page 1) divide 2 MHz by 4. See
[midi-acia.md](midi-acia.md).

## Summary

| Clock | Frequency | Drives |
|---|---|---|
| Crystal | 8 MHz | CPU clock chain |
| 6809 E | 2 MHz | CPU bus timing |
| 4× 8253/8254 DCO timers | 12 per-note dividers | **oscillator pitch** (one per DCO) |
| 4× DCO timer input | 2 MHz (E) | pitch = 2 MHz / count |
| `$1600` counter 2 | 50 Hz (2 MHz / 40,000) | the IRQ tick engine, restarted on every engine run |
| `$1600` counter 1 | 2 MHz (E) | CALIBRATE period timebase |
| ACIA clock | 500 kHz (E / 4) | MIDI 31250 baud |
