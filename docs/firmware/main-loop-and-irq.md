# Main loop, interrupts & scheduling

This closes the gap the [overview](overview.md) left open: what the foreground
actually does, and how it relates to the two interrupts. Read after the
overview. From the **v1.11** ROM; key instructions quoted by address.

## Entering the runtime

The last thing boot does (`vec_RESET` tail) is:

```
81df  ANDCC #$0E      ; clear E,F,H,I,C — i.e. UNMASK IRQ and FIRQ
81e1  JMP  $8302      ; enter the foreground loop (never returns)
```

So interrupts are switched on and the CPU drops into the `$8302` loop and never
comes back. Everything from here is one of three paths into the engine.

## The foreground loop — `$8302`

```
8302  LDA $2018 ; BMI $8322     ; meant: voice 0 "service now" flag (bit 7)
8307  LDA $2318 ; BMI $8322     ; voice 1   ($2018 + n*$300)
830c  LDA $2618 ; BMI $8322     ; voice 2
8311  LDA $2918 ; BMI $8322     ; voice 3
8316  LDA $2C18 ; BMI $8322     ; voice 4
831b  LDA $2F18 ; BMI $8322     ; voice 5
8320  BRA $8302                 ; otherwise spin
```

The foreground is a **polling dispatcher** inherited from the Matrix-6, and in
the M1000 it is **broken**: it never dispatches.

The six addresses are each voice block's `+$18` flag byte, **as laid out in the
Matrix-6**, whose voice blocks start at `$2000` (its code sets DP to `$20`–`$2F`;
the M1000's uses `$60`–`$6F`). In both machines bit 7 of `+$18` means "service
this voice now": the voice-assignment code sets it to `$80` when a note is
assigned (`$D570`, `$D5F6`), the engine sets it when an envelope stage changes
(`$864C`), and the engine clears it after running the voice's program (`$8734`).
So in the Matrix-6 this loop runs the engine **as soon as a note arrives**,
instead of waiting for the next timer tick.

When the code moved to the M1000, the voice blocks moved to `$6000 + n×$300`
because `$2000–$3FFF` became the patch-ROM window (schematic page 1: U815 decodes
that range only to the patch ROM). The DP setups were updated; these six absolute
addresses were not. So the loop reads **patch-ROM bytes** in whatever bank `$1D80`
selects. Boot sets bank 0 (`$8047`) and the banked patch reads restore it
(`$BCD3`, `$BD15`), and in bank 0 the six bytes are `4C 42 44 1A 7E 3F`, none
with bit 7 set. The loop spins forever, and every voice update waits for the
50 Hz timer tick (up to 20 ms after a note-on).

| Version | Loop reads | Dispatches? |
|---|---|---|
| Matrix-6 v2.13, Matrix-6R v2.11 | `$2018…` (its voice RAM) | yes |
| M1000 v1.03, v1.11 (Oberheim) | `$2018…` (patch ROM) | **no** |
| v1.13, v1.14 (Nordcore), v1.16 (GliGli) | `$2018…` | **no** |
| v1.20 (Tauntek) | `$6018…` | yes: fixed |

Bob Grieb's v1.20 changes exactly these six operands, which independently
confirms the diagnosis. For a firmware rewrite or a patch to v1.11, it is a
six-byte fix (`$8303`, `$8308`, `$830D`, `$8312`, `$8317`, `$831C`: high byte
`$2x` → `$6x`).

### How it calls the engine — a synthesized IRQ frame

```
8322  LDD  #$8302     ; return address
8325  PSHS B,A        ;   pushed as PC  -> $8302
8327  TFR  CC,A
8329  ANDA #$0E       ; CC with E=0 (a "fast"/non-entire frame)
832b  PSHS A          ;   pushed as CC
832d  JMP  $85E3      ; = the IRQ handler entry
```

When it does fire (Matrix-6, v1.20), rather than busy-call a subroutine the loop
**fakes a fast (non-`E`) IRQ stack frame**: return PC `$8302` plus a CC with
the `E` bit clear. It jumps to the IRQ vector target `$85E3`; the engine runs and
ends in `RTI`, which (because `E=0`) pulls just CC + PC and lands back at
`$8302`, and the poll resumes. So the foreground raises the tick engine on demand,
reusing the exact handler the hardware timer uses.


## The three paths into the engine

```
   FIRQ ($84B4) ──▶ MIDI ACIA byte ISR         (highest priority, per byte)
   IRQ  ($85E3) ──▶ JMP [$79F9] ──▶ $85E7       (hardware $1600 tick timer)
   foreground   ──▶ fake frame ──▶ JMP $85E3 ──▶ $85E7   (on voice request; dead in v1.11)
```

- **FIRQ** is independent and fastest: it only shuttles MIDI bytes in/out of the
  ring buffers (see midi-handling.md, #10). It can interrupt the IRQ engine.
- **IRQ** and the **foreground** both converge on `$85E7`, the tick engine. The
  `$1600` timer provides a periodic floor; the poll loop was meant to add
  on-demand servicing between ticks, but in v1.11 it never fires (above), so the
  timer is the only path.

## The tick engine `$85E7` (recap) and its dispatch

Per invocation it reloads the `$1600` tick timer, drains the MIDI RX ring into
the parser (`$C42B`), steps all six voices' envelope/pitch state, distributes one
voice's slow modulators (round-robin via `$7228`), scans CVs to the DAC
(`$875A`), and finally jumps through a continuation pointer `(*_DAT_753f)()`.
Full detail is in voice-engine.md (#8).

## Scheduling by revectorable pointers

The firmware "schedules" different behaviour (normal play vs calibration/test)
by swapping a handful of **RAM function pointers** rather than with a state
machine in one place:

| Pointer | Default | Role |
|---|---|---|
| `$79F9` | `$85E7` | IRQ handler (the tick engine); swapped by diagnostic modes |
| `$753F` | (set by engine) | tick-engine continuation / mode dispatch (jumptable at `$873F`) |
| `$720F` | `DAT_8E4F` | per-voice processing routine, invoked for each selected voice in `FUN_8EBA` (mask `$7217`) |

Because the IRQ vector itself is indirected through `$79F9`, calibration and
self-test can substitute their own tick behaviour without touching the hardware
vector table (#12).

## Tick cadence

The periodic IRQ is `$1600` counter 2, clocked by E (2 MHz, schematic page 3)
with a count of `$9C40` = 40,000 in mode 3: **exactly 50 Hz, 20 ms**. The IRQ
entry reprograms the counter on every engine run, so the period restarts from
each run (timing-clocks.md). With the foreground dispatch dead, v1.11 refreshes
CVs at exactly that rate; in the Matrix-6 and v1.20, a note-on runs the engine
early and restarts the 20 ms clock.

## Open items

- Enumerate the `$753F` continuation targets (the mode dispatch) (#12).
