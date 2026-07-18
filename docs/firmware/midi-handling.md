# MIDI handling

MIDI is handled in **two layers**: a per-byte interrupt that only moves bytes to
and from ring buffers, and a parser that runs from the tick engine and interprets
them. From the **v1.11** ROM; hardware is the MC68B50 ACIA at `$1406/$1407`
([I/O map](../hardware/io-map.md)).

## Layer 1 — the FIRQ byte ISR (`$84B4`)

The ACIA raises **FIRQ** per byte. The handler never parses; it only shuttles
bytes (full detail in [main-loop-and-irq](main-loop-and-irq.md)):

- **RX**: read `$1407` → store into the RX ring `$7593–$7792` (write pointer
  `$7995`), wrap at the end.
- **TX**: pull the next byte from the TX ring `$7793–$7992` (read pointer
  `$7997`) → write `$1407`; when the ring drains, write **`0x95`** to the ACIA
  control register to switch the **TX interrupt back off**.

### ACIA configuration

The control byte `0x95` (set in `FUN_8505` and when TX drains) decodes as
**8N1, ÷16** with RX interrupt enabled, TX interrupt disabled. At MIDI's 31250
baud the ÷16 divide implies a **500 kHz ACIA clock** (a dedicated clock, not the
CPU E-clock — this corrects the provisional ÷64 note in #4). To send, the
firmware rewrites the control byte with the TX interrupt enabled; the drain path
restores `0x95`.

## Layer 2 — the parser (`$C42B`, run from the tick engine)

Each tick, if the RX ring is non-empty (`$7993 != $7995`), the tick engine calls
the parser. It consumes queued bytes until the ring empties.

### The coroutine byte-fetcher (`$C457`)

The parser is written as straight-line code that "asks for the next byte" via
`$C457`, even though bytes arrive asynchronously. It pulls this off with a
**private stack**:

```
c42b  STS $7C2E      ; save caller's stack
      LDS $7C2C      ; switch to the parser's own stack
      ...
c457  LDX $7993 ; CMPX $7995 ; BEQ empty   ; RX ring empty?
      LDA ,X+    ; (wrap $7792 -> $7593)    ; else take a byte
empty: STS $7C2C ; LDS $7C2E ; RTS          ; yield back to caller
```

When the ring runs dry, `$C457` swaps the stacks back and returns to the *tick
engine* — i.e. the parser **suspends mid-message** and resumes exactly where it
left off on the next tick. This is how a non-blocking parser is written as
blocking-style code, and it makes running status across ticks trivial.

### Byte classification (in `$C457`)

- **data byte** (`< $80`): returned to the caller.
- **system realtime** (`≥ $F8`, e.g. clock/active-sensing): handled inline
  (`JSR $C836`) and *not* returned — never breaks a running-status message.
- **status byte** (`$80–$F7`): starts/!resets a message (`$C494`).

### Status dispatch

On a status byte the parser saves it (`$7592`), extracts the **channel** into
`$7B19` (`ANDB #$0F`) and the **message-type** index (`ANDA #$70`, `>>3`), then
jumps through an 8-entry table at **`$C4AC`**:

| Type | Status | Handler | Notes |
|---|---|---|---|
| 0 | `$80` note-off | `$C4BC` | fetch note, velocity → `$7C32/$7C33` |
| 1 | `$90` note-on | `$C4DD` | vel 0 ⇒ treated as note-off (`$C502`); else note-on (`JSR $D3F6`) |
| 2 | `$A0` poly aftertouch | `$C860` | not ignored: feeds pressure into the mod-update path (`$8561/$857E/$85C3`) under a mode flag. Likely applied as the mono "Pressure" mod source rather than true per-note response — to confirm |
| 3 | `$B0` control change | `$C506` | CC / NRPN parameter edit path |
| 4 | `$C0` program change | (table) | patch select |
| 5 | `$D0` channel aftertouch | (table) | |
| 6 | `$E0` pitch bend | (table) | |
| 7 | `$F0` system / SysEx | (table) | patch dump/load, parameter edit |

Note handling routes through `$D3F6` (note on/off → voice allocation, see #8) and
`$D683` (key/velocity processing). **Running status** is supported: after a
message the parser loops back and a following data byte reuses the saved status.

### Channel filtering

The received channel (`$7B19`) is checked against the **basic channel**
(`$74A7`) before a message is acted on (the `ADDA $74A7` / `BMI` guards in the
handlers), implementing omni/!single-channel behaviour.

## SysEx, NRPN & CC parameter edit

- **CC / NRPN** (`$B0`, `$C506`) is the real-time parameter-edit path — writing a
  parameter triggers the modulation-matrix recompile (#9), which is the source of
  the original firmware's edit lag.
- **SysEx** (`$F0`) carries single/bulk **patch dump & load** and parameter edit;
  the patch transfer format (nibble encoding, the 80↔134-byte pack/unpack) is
  documented with patch storage (#11) and the patch parameter map (#16).

These two paths are characterised here but not yet traced byte-for-byte — that
detail is carried in #11/#16.

## From the Owner's Manual — the user-facing MIDI behaviour

Context for the internals above (manual p.19, 21, 26, 34–37):

- **Controllers the patches respond to:** Pitch Bend, Pressure (after-touch),
  Mod Wheel (**CC#1**), Breath (**CC#2**), Pedal 1 (**CC#4** by default, remappable
  to any CC 0–121 via Ext. Funct. #4), Sustain (**CC#64**), Volume (**CC#7**,
  optionally *inverted* via Ext. Funct. #3 for whammy-bar/cross-fade), and a
  settable **Bend Range** (Ext. Funct. #8). These are the real sources behind the
  matrix "Lever/Pedal/Pressure" inputs (#9).
- **Program/Bank change:** patch changes are received on the Basic Channel in *all*
  panel modes; a bank is selected by pushing **CC#1 (vibrato/mod) past half**, or
  by **CC#31** (the DPX-1 convention) — which is exactly the two-stage bank logic in
  the program-change handler (`$C6F2`, #11).
- **MIDI Echo** (Ext. Funct. #2) turns MIDI-OUT into a soft THRU (echoes everything
  received *except* Active Sensing, including SysEx).
- **The "SEND ALL" drop** (manual p.35): a Matrix-6/6R on v2.13 or earlier
  *transmits patches faster than the Matrix-1000 can receive them* during a bulk
  dump, so some are lost — use SEND ONE. This is the same **receive-buffer
  saturation** our two-layer design (rings + tick-drained parser) is built around,
  and the exact bottleneck the Nordcore/GliGli CFWs later attacked.

## Open items

- Trace the CC/NRPN handler (`$C506`) and the SysEx handler (`$F0` entry) in full.
- Confirm the TX-enable control byte and the realtime handler (`$C836`) coverage.
- Enumerate the remaining jump-table handlers (`$C0/$D0/$E0`).
