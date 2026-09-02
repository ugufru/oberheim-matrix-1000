# Note: One ROM as the firmware dev rig

*2026-08-31 — working note, not derived from the ROM. Nothing here is verified against
hardware yet; treat every number as "claimed by the vendor" until measured.*

## What prompted this

Considering buying a [One ROM](https://www.retrohackshack.com/product/one-rom/)
(Retro Hack Shack / Piers Finlayson) to replace the socketed EPROMs in the M-1000, so
firmware can be iterated without a burn/erase cycle.

This targets README §6's last bullet directly:

> **No in-field update path:** firmware changes require physically reprogramming the 27C256.

## Why it fits this machine

- One ROM is an RP2350-based drop-in replacement for "the 24, 28, 32 and 40 pin EPROMs and
  mask programmed ROMs used in nearly every computer-based system from the late 1970s through
  to the early 1990s." The 28-pin list explicitly includes **27×256** and **27×512**.
- Our two ROMs are both 28-pin and both covered:
  - **OS ROM** — 32 KB 27C256 @ `$8000` (the firmware; see `docs/hardware/memory-map.md`)
  - **Patch ROM** — 64 KB 27C512, 8 KB window × 8 banks (the factory patch set)
- 28-pin "Fire" variant is in stock. Price range across all variants: **$10.00–$32.00**.

## The two features that actually matter

1. **In-circuit reflash.** onerom.org: "One ROM can be reflashed in-circuit without removal
   from the host system," and browser-based flashing "in 10 seconds with no separate
   programmer required" (also a CLI and a GUI studio app). This collapses the edit→test loop
   from *pull chip → UV erase → burn → reseat* to seconds. That's the difference between a
   firmware project happening and not happening.
2. **Multiple images + bank switching.** onerom.org: "A single One ROM can store multiple
   different ROM images, selectable via jumpers, and supports dynamic bank switching to change
   ROM images on the fly, while the host system is running."
   → **A/B rig**: stock v1.11 in one slot, our build in another, switch and compare the same
   patch through the same analog voices. For a synth where "correct" is partly a listening
   judgement, this is the single most valuable property of the board.

## Open questions / things to check before ordering

1. **Access time is unpublished.** Not stated on the product page, the GitHub README, or
   onerom.org. Our budget:
   - 6809 @ **2 MHz** E-clock → comfortable address-valid→data-valid window; the RP2350 PIO
     path should clear it easily. *This is an expectation, not a measured or published spec.*
   - If the **6309 @ ~4 MHz** upgrade (README §1) is ever fitted, the margin roughly halves.
   - **Action:** ask Piers directly for a number in ns.
2. **Mechanical clearance.** The M-1000 is 1U. A daughterboard stands taller than a DIP —
   check clearance to the lid and any overhanging parts near the ROM sockets before planning
   to leave it permanently installed.
3. **Buy two.** One for the OS ROM, one for the patch ROM. Fast patch-set swapping lets the
   `tools/` patch decode work (`decode_patches.py`, `unpack_patch.py`, `patches.csv`) be
   round-tripped against *hardware* instead of only against CSV.
4. Current draw off the 5V rail vs. a plain EPROM — expected fine, unconfirmed.

## What it does NOT solve

A ROM emulator fixes the **burn** loop, not the **debug** loop. On this machine we are
otherwise blind: no serial console, a two-digit LED panel, and the MC68B50 ACIA as the only
real-time channel. Pair the board with:

- **A software 6809 harness**, so most iterations never touch hardware. We already have the
  disassembly baseline (`build/v111_baseline.s`, `build/v111_full.asm`), the byte-identical
  asm6809 round-trip gate (`tools/roundtrip_check.sh`), and the Ghidra pipeline
  (`docs/disassembly/workflow.md`).
- **SysEx-over-MIDI as `printf`.** The ACIA at `$1400–$15FF` is the only way to get bytes out
  in real time; see `docs/hardware/midi-acia.md` and `docs/firmware/midi-handling.md`.

Hardware then becomes where we *confirm*, not where we *discover*.

## Recommendation

Order the **28-pin USB "Fire", ×2**, and ask about access time in the same message. Cost is
trivial against the workflow unlock; the only genuine risk is bus timing, and that is one
email away from being settled.

## Sources

- <https://www.retrohackshack.com/product/one-rom/>
- <https://onerom.org/>
- <https://github.com/piersfinlayson/one-rom>
- <https://hackaday.com/2025/09/03/one-rom-the-latest-incarnation-of-the-software-defined-rom/>
