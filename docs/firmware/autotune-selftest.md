# Autotune, calibration & self-test

The analog voices drift, so the firmware continuously tunes them and offers
panel-driven calibration and diagnostics. This doc separates the **always-on
run-time tuning** (well traced) from the **panel/boot diagnostic modes** (entry
points identified; measurement bodies partly in code the current analysis hasn't
reached — flagged honestly). From the **v1.11** ROM.

## Run-time pitch & glide (always on) — `FUN_8765`

> **Datasheet + trace note.** The CEM3396 oscillators are **clock-derived (digital
> 8253 divider, crystal-stable)**, so they need no *tuning*. But `FUN_8765` — the
> always-on routine here — is nonetheless the **pitch** primitive: it writes the
> per-note **8253 divider** (`$A652` note table → the voice's counter, LSB/MSB; see
> voice-architecture.md and timing-clocks.md). So what it "corrects" each tick is
> pitch **glide / portamento / fine-tune** toward a target divider — *not*
> oscillator drift. Genuine analog **calibration** (of the filter/VCA, which do
> drift) is the panel **CALIBRATE** routine below.

`FUN_8765` runs in the compiled voice program every tick (#8/#9). Per voice
(DP = voice page) it:

- holds a **per-voice glide/target reference** in the voice block at `+$A0/+$A2`;
- steps the current value toward it (glide) using windows/limits (`$0488`, `$05DC`,
  `$0208`) and writes the result **as a 16-bit divider to the voice's 8253 counter**
  (address cached at `+$75` from the `$8220` table);
- indexes the **`$A652` note→divider table** so the note→frequency mapping is exact
  (crystal-derived).

The per-voice **oscillator comparators** appear at `$2018 + n×$300` (bit 7),
polled by the foreground loop `$8302` (#7). These are the hardware feedback the
tuning uses to know where each oscillator actually is.

> The `$2018+` lines sit in the patch-ROM window address range; whether they are
> tuning comparators, an oscillator sync/zero-cross strobe, or both is the open
> question carried to the DAC/voice hardware doc (#13). The run-time correction
> in `FUN_8765` is firm; the precise feedback semantics are not.

## Calibration modes (panel "extended functions")

The front panel exposes an extended-function menu whose labels live in a string
table at `$DB3F`: `CALIBRATE`, `FINE TUNE`, `NUMB UNITS`, `PATCH NUM`,
`BASIC CHAN`, `DATA DUMP`, `EXT FUNCT`. **CALIBRATE** runs the full per-voice
auto-calibration (measuring each oscillator/filter against the reference and
storing the `+$A0/$A2` references the run-time path then uses); **FINE TUNE**
sets the global master tune. The measurement loop itself is reached only when the
mode is selected from the panel and is not yet traced byte-for-byte (open item).

> **From the Owner's Manual** (p.16, 22): those strings are the `Select`-key menu
> headings — `Fine Tune`, `Units`, `Data Dump`, `Ext. Funct.`, etc. **Fine Tune**
> is ±1/4-tone, displayed `+31…−31` (`0` = A-440). **Calibration routines are
> started with the `Enter` key.** So the user-facing entry points are on the panel;
> our un-traced measurement loop is what those do internally.

## Power-on diagnostic & factory reset — `FUN_DC41` (`$DC41`)

Holding a panel button at power-on sets the arm flag (`$1801 & 4` → `$7DB1 =
0xFF` at `$8181`); on the following pass `FUN_db95` calls **`FUN_DC41`**, which:

- clears the arm flag and **resets the global/master parameters to defaults** —
  basic channel (`$74A7`), mode flags (`$74xx/$75xx`), master tune, etc.;
- calls **`$B0C6`**, which loads a **built-in default patch** by copying the
  ~129-byte template at `$B11D` into the patch buffer (this incidentally
  corroborates the unpacked working-patch size of ≈129–134 bytes — see #16) and
  re-arms the engine (`$8EBD`).

So "hold a button at boot" = restore defaults + load the init patch.

## Voice self-test — `BAD OSC / BAD VCF / BAD RES / BAD WAVE`

The self-test that reports a failed voice uses the 16-char message strings at
`$B1C4` (`BAD OSC`, `BAD VCF`, `BAD RES`, `BAD WAVE`), preceded by a parameter/
limit data block (`$B11D–$B1C3`). It exercises each voice's oscillator, filter,
resonance and waveshape and names the failing stage.

> **From the Owner's Manual** (p.37): the diagnostic has a documented user entry —
> **Ext. Funct. #7, display `tst` = "Test mode."** So the self-test / `FUN_DC41`
> path we found is reached two ways: holding a panel button at power-on (the
> `$1801`/`$7DB1` arm above), *and* selecting Ext. Funct. 7 from the panel. (The
> `Ext. Funct.` menu is 0–8: 0 Unison, 1 Transpose, 2 MIDI Echo, 3 Invert Volume,
> 4 Pedal-1 CC select, 5 Unit#, 6 Memory Protect, **7 Test**, 8 Bend Range.)

The **routine body** that drives the `BAD …` strings still isn't fully
disassembled from the vector-seeded analysis, but the entry (Ext. Funct. 7 →
`FUN_DC41` region) is now known — a good seed for finishing the trace.

## Open items

- Trace the CALIBRATE measurement loop and how `+$A0/$A2` references are produced.
- Find and trace the `BAD OSC/VCF/RES/WAVE` self-test driver (panel-gated code).
- Resolve the `$2018+` comparator/strobe semantics with the schematic (#13).
