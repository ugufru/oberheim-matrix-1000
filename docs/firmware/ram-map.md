# RAM map (work variables)

The firmware's mutable state lives in the battery-backed SRAM window at
`$6000–$7FFF` (the 43256; banked, but the working set is in this window). This
doc catalogues what is known so far, from the boot init and the two interrupt
handlers. It will keep filling in as the voice/mod/MIDI deep-dives (#8–#11)
resolve more fields.

> Status: this is a **living map**. Confirmed entries are quoted by the code that
> uses them; entries marked *(inferred)* are best-current-reading and may be
> renamed later.
>
> **DP register:** during per-voice processing the firmware sets DP to the
> current voice's page (`$60, $63, … $6F`), so `voice*$100 + offset` accesses are
> direct-page ops on that voice's block (see voice-engine.md, #8). Outside voice
> processing, treat addresses as absolute.

## Regions at a glance

| Range | Contents |
|---|---|
| `$6000–$71FF` | **Six voice blocks**, `0x300` bytes each (`$6000,$6300,$6600,$6900,$6C00,$6F00`) |
| `$7200–$74FF` | Engine scratch: iteration cursors, counters, portamento/glide flags |
| `$7531–$753F` | Voice-allocation list + tick continuation vector |
| `$7593–$7792` | **MIDI RX ring** (512 B) |
| `$7793–$7992` | **MIDI TX ring** (512 B) |
| `$7993–$79xx` | MIDI ring pointers, ACIA timers, IRQ vector, display shadow |
| `$7A00–$7Axx` | Active patch buffer pointer + global modulator output tables |
| `$7B00–$7FFF` | Mode/flags, counters, diagnostic, boot breadcrumb |

## Per-voice block (`$6000 + n×$300`)

The core data structure; the tick engine walks all six every interrupt. Offsets
are relative to the voice base. Built in `vec_RESET`, stepped in `FUN_85e7`.

| Offset | Size | Role | Source |
|---|---|---|---|
| `+$0C/+$0E/+$10` | word | modulator output slots (written each tick from the global mod tables) | `FUN_85e7` |
| `+$14` | byte | envelope/phase state (compared, `-0x0C`) *(inferred)* | `FUN_85e7` |
| `+$15` | word | pitch/target → copied to `+$1B` | `FUN_85e7` |
| `+$17` | word | source for the `+$1D/+$1F` CV pair | `FUN_85e7` |
| `+$18` | byte | voice flags / gate (bit 7 = trigger/active) | `FUN_85e7` |
| `+$1B/+$1D/+$1F` | word | computed pitch / CV outputs | `FUN_85e7` |
| `+$21/+$22/+$23` | byte | envelope sub-state | `FUN_85e7` |
| `+$30` | byte | 8253 control word for this voice's DCO counters (`$36/$76/$B6` = counter 0/1/2, mode 3), from the `$8220` table | `vec_RESET` |
| `+$31/+$32` | byte | DCO1 / DCO2 pitch-range flag (`$00`/`$FF`, threshold `$3C80`), latched to `+$77`/`+$7F` | `$8765`, `$89F6` |
| `+$35/+$37` | word | pitch-derived waveshape scale / clamped waveshape value (scratch shared by both DCOs) | `$8765`, `$8950`, `$8B67` |
| `+$39/+$3B/+$3D/+$3F` | word | per-range DCO pitch offsets (defaults `$3800`/`$4700`) | `$DD88` |
| `+$33/+$34` | byte | envelope rate / scratch | `FUN_85e7` |
| `+$71/+$73` | ptr | work pointers into this voice's RAM (`$60xx`) | `vec_RESET` |
| `+$79,+$7B,+$81,+$83,+$85,+$87,+$8D,+$8F,+$95,+$97` | ptr | **DAC channel addresses** for this voice (`$1000 + n×$10 + k`): DCO1 shape, DCO1 PW, DCO2 shape, DCO2 PW, VCF freq, VCF FM, VCA1, VCA2, DCO1 PW-off, DCO2 PW-off | `vec_RESET` |
| `+$89,+$8B` | ptr | DAC channels for **resonance** (`$106C + 2n`) and **mix** (`$1160 + 2n`), from the `$8220` table | `vec_RESET` |
| `+$75,+$91` / `+$7D,+$93` | ptr | DCO1 / DCO2 8253 counter and control-register addresses, from the `$8220` table | `vec_RESET` |
| `+$77,+$7F` | ptr | DCO1 / DCO2 range latch (`$1C00 + n` / `$1C80 + n`), from the `$8220` table | `vec_RESET` |
| `+$A4` | byte | 8253 read-back/latch command for this voice's counters (`$E2/$E4/$E8`), from the `$8220` table | `vec_RESET` |
| `+$A5` | byte | VCA2 scale factor (used by `$8D1B`) | `FUN_85e7` |
| `+$2A8` | word | per-voice resonance calibration correction (cleared `$DDAE`) | `$9866`, CALIBRATE |
| `+$2AA…+$2BA` | word×9 | per-voice VCF-frequency calibration curve (defaults `$0B19`…`$04D9`) | `$8C0A`, `$DD49`, CALIBRATE |
| `+$22D…` | word×42 | modulation accumulators (zeroed at boot) | `FUN_8206` |

The cached `$1000`-region pointers are what make CV scan-out cheap: the tick
engine stores computed values straight through these without recomputing
addresses. The channel-to-parameter derivation is in
[dac-cv-mux.md](../hardware/dac-cv-mux.md#per-voice-channel-map).

## Engine scratch (`$7200–$74FF`)

| Addr | Role |
|---|---|
| `$7200` | voice page cursor (`0x60`, `+3`/voice) |
| `$7207` | voice DAC-channel base accumulator (`$1000 + n×$10`) |
| `$7216` | voice count (`6`) |
| `$7217` | voice-select bitmask (`0x3F`) |
| `$7222` | reused loop counter |
| `$7228` | round-robin pointer into the voice-allocation list |
| `$7235` | shadow of output latch `$1D00` |
| `$7490/$7491/$74A8` | portamento / glide control flags *(inferred)* |

## Voice allocation (`$7531–$753F`)

| Addr | Role |
|---|---|
| `$7531–$7536` | voice-allocation list: which voice block (`0x60…0x6F`) plays, `0` = free |
| `$7537–$7538` | scratch copy used while re-packing the list |
| `$753F` | tick-engine continuation vector (`(*_DAT_753f)()`) |

## MIDI (`$7593–$79A2`)

| Addr | Role |
|---|---|
| `$7593–$7792` | RX ring buffer (512 B) |
| `$7793–$7992` | TX ring buffer (512 B) |
| `$7995` / `$7993` | RX ring **write** (ISR) / **read** (parser) pointers |
| `$7999` / `$7997` | TX ring **write** (app) / **read** (ISR) pointers |
| `$79A1/$79A2` | ACIA TX/RX activity timeout counters |

## System / mode (`$79C1–$7FFF`)

| Addr | Role |
|---|---|
| `$79C1…` | status/flag array (init by `FUN_d26a/FUN_d295`); `$79E1` a counter |
| `$79EB,$7A0D–$7A10` | display/LED shadow state |
| `$79F9` | **IRQ tick vector** (= `$85E7`; revectorable) |
| `$7A19` | pointer to the **active patch buffer** |
| `$7A3B,$7A4C,$7A5D,$7A6E,$7A7F,$7A91,$7AA2` | global modulator output tables (LFOs/ramps), indexed per voice |
| `$7C3A` | cold/warm-start flag (gates the normal startup path) |
| `$7C40,$7C4D` | mode / bank-latch shadow |
| `$7FFD` | boot progress breadcrumb (also general scratch) |

## Open items

- Full meaning of the `$79C1` status array and `$7A0D` display shadow (#14).
