# Clocks & timing

Every clock in the machine and what it drives. CPU/crystal figures are from the
hardware sources (untergeek/Bob Grieb, `bit-hack`); the timer programming is from
the **v1.11** ROM.

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
because these per-note writes go through that cached pointer. (This corrects an
earlier note that called these "fixed clocks" and put pitch on a DAC CV — the
CEM3396 has no pitch CV; pitch is this timer divider. See voice-architecture.md.)

### The system tick timer — `$1600`

A separate 8254-class timer that generates the periodic **IRQ** driving the tick
engine. Unlike the DCO timers it is **reloaded every tick** by the IRQ handler
(`$1603 = 0xB6`, `$1602 = 0x9C`, at `$85E7`) to re-arm the next interrupt. This is
the firmware's real-time heartbeat (#7); the README/community "~50 Hz / 20 ms CV
update" is its cadence.

> The exact tick frequency follows from the `0x9C` reload and the timer's input
> clock, which isn't confirmed from code alone — left for schematic confirmation.

## ACIA clock

The MC68B50 runs from a **500 kHz** clock (÷16 → 31250 baud), separate from E.
See [midi-acia.md](midi-acia.md).

## Summary

| Clock | Frequency | Drives |
|---|---|---|
| Crystal | 8 MHz | CPU clock chain |
| 6809 E | 2 MHz | CPU bus timing |
| 4× 8253/8254 DCO timers | 12 per-note dividers | **oscillator pitch** (one per DCO) |
| `$1600` tick timer | ~tick rate (reloaded each IRQ) | the IRQ tick engine |
| ACIA clock | 500 kHz | MIDI 31250 baud |
