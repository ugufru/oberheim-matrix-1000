# MIDI interface (MC68B50 ACIA)

The hardware side of MIDI; the firmware protocol is in
[firmware/midi-handling.md](../firmware/midi-handling.md) (#10).

## Chip & mapping

A Motorola **MC68B50 ACIA** in the `$1400–$15FF` I/O block provides the serial
UART for **MIDI In / Out / Thru**. The firmware accesses two registers (register
select on A0), using the mirror at:

| Address | Read | Write |
|---|---|---|
| `$1406` | status | control |
| `$1407` | Rx data | Tx data |

## Configuration

The firmware writes control byte **`0x95`** (`FUN_8505`, and on TX-queue drain):

- **8N1** word format (8 data, no parity, 1 stop),
- **÷16** clock divide,
- **Rx interrupt enabled, Tx interrupt disabled**.

At MIDI's 31250 baud, ÷16 implies a **500 kHz** clock at the ACIA — a dedicated
rate, not the 2 MHz CPU E-clock (see [timing-clocks.md](timing-clocks.md)). To
transmit, the firmware rewrites the control byte with the Tx interrupt enabled;
the FIRQ TX-drain path restores `0x95`.

## Interrupt wiring

The ACIA drives **FIRQ** (the 6809 fast interrupt), one interrupt per byte, which
is why the byte-level ISR is short and high-priority (it can preempt the IRQ tick
engine). Receive is interrupt-driven into a ring buffer; transmit is interrupt-
driven from a ring buffer with the Tx interrupt gated on/off as the queue fills
and drains (#10).

## Open items

- Confirm the 500 kHz ACIA clock source on the schematic.
- Confirm In/Out/Thru opto/buffer wiring (schematic).
