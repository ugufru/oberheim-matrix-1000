# Boot / initialisation (`vec_RESET` @ `$8003`)

A step-by-step trace of what the firmware does from power-on until the runtime is
live. This expands section "Boot / init" of the [overview](overview.md).
Addresses are from the **v1.11** ROM. Inferred roles are flagged; confirmed
behaviour is quoted by address.

## Progress breadcrumb

Throughout init the code writes the address of the *next* step to a fixed RAM
word, `$7FFD` (seen in the decompiler as `_DAT_7ffd = 0x8023`, `= 0x8026`, …).
It is a "where did I hang" marker: if the boot wedges, `$7FFD` tells you which
init call it died in. Harmless to runtime; handy for diagnosis.

## Init-retry / diagnostic outer loop

The hardware-init block runs inside a `while (true)`. Normally it executes once
and breaks; if a panel button is held it loops or branches into diagnostic
paths:

- `$1801 & 4` — if set, set `$7DB1 = $7B12 = 0xFF` and repeat the init block
  (test-mode arming).
- after the loop, `$1801 & 2` with `$1800 == '$'` (`0x24`) gates a calibration
  wait loop.

These are the entry hooks for the self-test / calibration covered in #12.

## Ordered init steps

| # | Code | What it does |
|---|---|---|
| 1 | `$1C87/$1C07/$1D00 ← 0xFF` | drive output latches (LED/lamp reset) |
| 2 | `FUN_81e4` | write mid-scale `0x8000` to the six DAC channels `$1008…$1058`, 50× (DAC/voice settle) |
| 3 | `FUN_d06e` | clear display/LED shadow state (`$7A0D–$7A10`, `$79EB`) |
| 4 | `FUN_d26a` / `FUN_d295` | initialise the `$79C1` status/flag array (copy with bit6 masked / set bit6) |
| 5 | `FUN_d088` | drive the `$1F80` latch (`~$7A0D`) and refresh display state |
| 6 | delay `15000` | settle delay |
| 7 | `FUN_828c` | program the four **DCO timers**: control `0xB6` (8254 mode 3, square wave) to `$0003/$0403/$0803/$0C03`, then load counts (`0x11`) into all twelve counters |
| 8 | inline | set up the **tick timer** (`$1602=0x9C`, `$1603=0xB6`) and install the IRQ vector `$79F9 = $85E7` |
| 9 | voice-build loop | construct six `0x300`-byte **voice blocks** at `$6000 + n×$300` (see [ram-map](ram-map.md)); pre-fill DAC/S&H channel pointers and work fields |
| 10 | `FUN_8206` | zero the per-voice modulation accumulators (`$622D + n×$300`, 42 words each) |
| 11 | inline | build the **voice-allocation table** `$7531–$7536` with the voice page numbers `0x60,0x63,…,0x6F` |

## Starting the runtime (normal path, `$7C3A == 0`)

| Code | Role |
|---|---|
| `FUN_8505` | **MIDI/ACIA init** — control reg `$1406 ← 0x95`, reset RX/TX ring pointers (`$7993=$7995=$7593`, `$7997=$7999=$7793`) |
| `FUN_db95` | **synth state / power-on patch** — clear edit flags and defaults, then `FUN_bb00` etc. |
| `FUN_d2b5`, `FUN_d2bb` | **patch → voice & modulation-matrix setup** (reads the active patch buffer `$7A19`, builds per-voice routing) |
| `FUN_8eba` | a per-voice processing pass over the six blocks (`$6000` step `$300`, selected by mask `$7217`) |
| `FUN_8ebd(3)` | engine enable |
| `$1D00 ← $7235 & 0xFD` | clear a bit in the output latch (enable) |
| `FUN_8302` | drop into the runtime |

From here the instrument is interrupt-driven (FIRQ MIDI, IRQ tick engine); see
the [overview](overview.md) and #7.

## Cross-checks / open items

- The four-timer control word `0xB6` (mode 3, square wave) corroborates the
  "DCO clock generator" role assigned in the [I/O map](../hardware/io-map.md).
- `FUN_81e4`'s mid-scale DAC writes confirm six DAC channels at `$1008 + n×$10`.
- Exact contents of the `$79C1` status array and the `$7A0D` display shadow are
  not yet fully mapped (touched again by the panel/display work, #14).
