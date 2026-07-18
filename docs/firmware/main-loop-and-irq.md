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
8302  LDA $2018 ; BMI $8322     ; voice 0 service flag (bit 7)?
8307  LDA $2318 ; BMI $8322     ; voice 1   ($2018 + n*$300)
830c  LDA $2618 ; BMI $8322     ; voice 2
8311  LDA $2918 ; BMI $8322     ; voice 3
8316  LDA $2C18 ; BMI $8322     ; voice 4
831b  LDA $2F18 ; BMI $8322     ; voice 5
8320  BRA $8302                 ; otherwise spin
```

The foreground is a **polling dispatcher**: it spins reading six per-voice status
bytes and, the moment any voice raises bit 7, services it via the engine. There
is no other foreground work in this loop — all heavy lifting is in the engine and
the MIDI ISR.

### How it calls the engine — a synthesized IRQ frame

```
8322  LDD  #$8302     ; return address
8325  PSHS B,A        ;   pushed as PC  -> $8302
8327  TFR  CC,A
8329  ANDA #$0E       ; CC with E=0 (a "fast"/non-entire frame)
832b  PSHS A          ;   pushed as CC
832d  JMP  $85E3      ; = the IRQ handler entry
```

Rather than busy-call a subroutine, the loop **fakes a fast (non-`E`) IRQ stack
frame** — return PC `$8302` plus a CC with the `E` bit clear — and jumps to the
IRQ vector target `$85E3`. The engine runs and ends in `RTI`, which (because
`E=0`) pulls just CC + PC and lands back at `$8302`. The poll resumes. Net
effect: the foreground "raises" the tick engine on demand, reusing the exact same
handler the hardware timer uses.

> Open question: the polled bytes `$2018 + n×$300` sit inside the nominal patch-
> ROM window (`$2000–$3FFF`). They are clearly **per-voice status inputs** here,
> not ROM — so either a finer address decode or a bank state exposes voice
> service/timing lines in this region. Resolving this belongs to the DAC/voice
> hardware deep-dive (#13); flagged, not guessed.

## The three paths into the engine

```
   FIRQ ($84B4) ──▶ MIDI ACIA byte ISR         (highest priority, per byte)
   IRQ  ($85E3) ──▶ JMP [$79F9] ──▶ $85E7       (hardware $1600 tick timer)
   foreground   ──▶ fake frame ──▶ JMP $85E3 ──▶ $85E7   (on voice request)
```

- **FIRQ** is independent and fastest: it only shuttles MIDI bytes in/out of the
  ring buffers (see midi-handling.md, #10). It can interrupt the IRQ engine.
- **IRQ** and the **foreground** both converge on `$85E7`, the tick engine. The
  `$1600` timer provides a periodic floor; the poll loop adds on-demand servicing
  between timer ticks.

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

The periodic IRQ is paced by the `$1600` timer, reloaded each tick (`$1602=0x9C`,
control `$1603=0xB6`, 8254 mode 3). The **exact frequency** depends on that
timer's input clock, which isn't yet confirmed from the schematic — so rather
than state a number we trust the external "~50 Hz / 20 ms CV update" figure for
now and leave the precise calculation to the timing/clocks hardware doc (#14).
Note that on-demand foreground servicing means the effective CV-refresh rate is
not the timer rate alone.

## Open items

- Identity of the `$2018+n×$300` voice service lines vs the patch-ROM window (#13).
- Confirm whether the `$1600` timer IRQ is the sole periodic source or works
  together with the poll loop; measure the real tick rate (#14).
- Enumerate the `$753F` continuation targets (the mode dispatch) (#12).
