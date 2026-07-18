# What the Matrix-1000 actually is

A one-page mental model of the whole machine, before you dive into the subsystem
docs. The two diagrams below are the holistic view; everything else in `docs/`
fills in a corner of them.

- **System architecture & data flow:** [diagrams/architecture.svg](diagrams/architecture.svg)
- **Memory map:** [diagrams/memory-map.svg](diagrams/memory-map.svg)

## In one paragraph

The Matrix-1000 is a **six-voice analog synthesizer whose voices have no memory of
their own** — every oscillator clock, filter cutoff and amplifier level is a
control voltage the CPU must refresh continuously. So at heart it is a small
**hard-real-time 6809 computer** wrapped around a **multiplexed DAC** and six
**CEM3396** analog voice chips. There is no keyboard, no screen, no general
computing — just a 2 MHz 6809, 32 KB of firmware, a bank-switched patch store,
a MIDI port, and the analog voice array. Almost everything that makes it a
*synthesizer* happens in firmware.

## The four layers

1. **Digital core.** A Motorola 6809 at 2 MHz, 32 KB of OS ROM at `$8000`, and a
   bank-switched RAM/patch-ROM store. The single `$1D80` latch pages the 64 KB
   patch ROM and 32 KB RAM through small windows — the machine's only "MMU."

2. **I/O and interrupts.** Two interrupt sources drive the whole instrument: an
   **MC68B50 ACIA** raises **FIRQ** for every MIDI byte, and an **8254 timer**
   raises a periodic **IRQ** (~50 Hz). Four more 8254s emit twelve fixed
   oscillator clocks. The front panel is just switch inputs and LED/display
   latches — it's a preset rack, not an editing surface (which is why patches
   have no stored names).

3. **The voice path.** One **AM6012 DAC** is time-multiplexed through **4051/4053**
   muxes and a **sample-and-hold** array to ~15 control voltages per voice, into
   six **CEM3396** chips (2 DCO + waveshaper + 4-pole VCF + 2 VCA each), summed to
   the audio output. The CPU is *constantly* topping up these S&H voltages.

4. **The software model.** Three execution contexts converge on one engine:
   - **FIRQ** shuttles MIDI bytes to/from ring buffers (never parses);
   - the **IRQ tick engine** (`$85E7`) is the heartbeat — it parses MIDI, steps
     all six voices' envelopes, runs each voice's *compiled* modulation program,
     and scans the CVs out to the DAC;
   - the **foreground** (`$8302`) does nothing but poll voice-service flags and
     "raise" the tick engine on demand by synthesizing a fast-IRQ frame.

   The defining trick: **the modulation matrix is compiled to threaded code** per
   voice when a patch loads, then executed cheaply every tick. That is how a
   2 MHz 8-bit CPU sustains a 20-routing matrix across six voices in real time.

## How complex is it, really?

It is a *specialised* machine, not a broad one. Compared with a general-purpose
6809 computer of the era (e.g. the TRS-80 Color Computer — same CPU): the CoCo
has more *breadth* (video via SAM+VDG, two PIAs, cassette, cartridge port, a big
BASIC ROM), while the Matrix-1000 has more *real-time depth* (the multiplexed CV
scan-out, per-byte FIRQ MIDI, and the threaded-code synthesis engine). Different
axes of complexity; comparable overall.

## On rewriting the firmware (and Forth)

A from-scratch or partial rewrite is very feasible, and unusually **Forth-friendly**:

- **Same ISA.** It's a 6809, so a 6809 Forth kernel, its assembler, and any
  6809 code-generation tooling transfer directly — no porting of the core.
- **The architecture already thinks in threaded code.** The existing modulation
  engine *is* a threaded-code interpreter (a per-voice list of primitive
  addresses executed via `PULU PC`). A Forth — itself threaded code — is working
  *with* the grain here, not against it.
- **What the real work is:** (1) a hardware-driver layer for *this* machine
  (DAC/mux/S&H, the four DCO timers, the `$1600` tick timer, the 68B50 ACIA, the
  bank latch, the panel) — the equivalent of a CoCo Forth's screen/keyboard layer,
  rewritten for synth I/O; (2) the **hard-real-time inner loops** — the FIRQ MIDI
  ISR (a byte every ~320 µs at 31250 baud) and the per-tick voice scan-out — want
  to be hand-tuned `CODE` words (assembly), with the patch/UI/matrix-compile logic
  in high-level Forth; (3) **fit in 32 KB** ROM (the stock synth code uses ~25 KB,
  so there's room, but a Forth kernel + dictionary competes for it).
- **A cross-compiled / metacompiled Forth is the right model** — the device is
  headless (no console), so you want a turnkey ROM image, not an interactive
  Forth-on-target. A CoCo Forth aimed at interactive use would need re-targeting
  to produce a standalone ROM, but a Forth *cross-development* toolchain already
  does exactly that.

Bottom line: of all the ways to rewrite this firmware, **Forth is a natural fit** —
the ISA matches, the synthesis engine is already threaded code, and the only
genuinely hard part (the real-time CV/MIDI loops) is small enough to drop into
assembly `CODE` words while keeping the bulk of the synth in readable Forth.

## "6 mono voices, one sound each" — the stock **guitar mode** already does most of it

Just six independent monophonic voices, each with its own sound, one per MIDI
channel. It turns out the stock firmware gets you almost all the way there.

**Guitar mode is real and factory** (Owner's Manual p.20–21). In **CHANNEL** mode,
selecting **G1–G9** puts the Matrix-1000 in **MONO mode (MIDI mode 4)** — "the *G*
stands for guitar, since MONO mode is usually used with guitar controllers to
allow independent pitch bend on each string." With basic channel *B*:

- **voice 1 → channel B, voice 2 → B+1, … voice 6 → B+5** (a fixed channel→voice map);
- each voice responds to **pitch bend, volume pedal and pressure/after-touch
  *independently* on its own channel**;
- vibrato (mod wheel) and sustain stay **global** (lowest channel, all voices);
- G1–G9 only (needs six consecutive channels; not 10–16). The mode is stored and
  settable from the panel or by MIDI mode messages.

So the two things I'd earlier (wrongly) called "residual work" are **already
built**: channel→voice binding *and* per-channel controller routing (bend/pressure/
volume) both ship in guitar mode. Combined with **per-voice LFOs** (confirmed, see
voice-engine.md) and the **per-voice compiled programs**, that leaves exactly one
missing piece:

> **Per-voice patch binding.** All six voices still compile from the single global
> patch (`_DAT_7218`). Feed the rebuild loop (`FUN_8EBA`) a **per-voice** patch
> pointer instead, keep N resident patches (RAM is not the limit), and each voice
> sounds different — with independent LFOs and independent per-channel expression
> already handled by guitar mode. Small change on a structure already shaped for it.

The ceiling is still CPU (six channels of MIDI + six live LFOs on a 2 MHz 6809; a
6309/overclock is the relief). But the instinct was exactly right: it's a
sound-generation change, and guitar mode already supplies the tracking *and* the
per-channel expression.

**Related: Group Mode.** Oberheim's own answer to "more" was orthogonal — the
**Units / Group Mode** feature (manual p.29–32) chains up to **six Matrix-1000s**
into one 36-voice instrument (notes "alternating-rotate" across units, patch/bank
changes propagated master→slaves; each patch can opt in/out of group mode, stored
even for ROM patches). Notably, **MIDI MONO / guitar mode is incompatible with
group mode** — so the factory offered *either* per-channel voices on one unit
*or* pooled polyphony across units, never both. The per-voice-patch idea above is
a third path they didn't ship.
