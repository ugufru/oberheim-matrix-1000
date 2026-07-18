# Patch storage (load, banking & unpack)

How a patch goes from storage to the sounding edit buffer, and the packed
on-storage format. This is the bridge to the patch-ROM decode track (#15–#18):
the **unpack routine here is the authoritative key** to the stored byte layout.
From the **v1.11** ROM.

## Where patches live

1000 patches, numbered 0–999 (`$7AD7` holds the current number), split into ten
banks of 100. Each stored patch is **80 bytes** (`$BD39`: `LDA #$50 / MUL`,
`LDY #$50`). Addressing, from `$BD39`:

```
patch-in-bank = patch# mod 100      ; 0..99
bank          = patch# div 100      ; 0..9
offset        = patch-in-bank * $50 ; *80 within the bank's 8 KB window
```

The bank then routes to one of two devices (the `SUBA #2 / BGE` test):

| Banks | Patches | Device | Window |
|---|---|---|---|
| 0–1 | 0–199 | **user RAM** (battery-backed 43256) | `$6000` |
| 2–9 | 200–999 | **factory patch ROM** (27512) | `$2000` |

So **200 user + 800 factory = 1000** — confirming the split in the top-level
README, now from code. 100 patches × 80 B = 8000 B, fitting one 8 KB bank.

> **From the Owner's Manual** (p.33), verbatim confirmation: *"the first 200 sounds
> (000–199) [are] stored in RAM … you can edit, change, overwrite … The remaining
> 800 sounds (200–999) are in permanent ROM and cannot be changed."* User-facing
> ways to write the RAM 000–199: **Patch Copy** (copy FROM any 000–999 TO 000–199;
> 200–999 are permanent — p.27), and **Data Dump** SysEx (p.33–35): `Dump one` /
> `Dump bank` / `Dump all` (all-RAM 000–199). Writes are gated by **Memory Protect**
> (Ext. Funct. #6) — a dump is ignored if it's on. This is exactly the RAM-bank
> write side of the banking mechanism above.

## Bank-switched read — `$BCAF`

Both windows are paged by the **`$1D80` bank-select latch**. The read loop:

```
bcce  STA $1D80      ; select bank (high address lines)
bcd1  LDB ,U+        ; read a byte from the $2000/$6000 window
bcd3  CLR $1D80      ; deselect
bcd6  STB ,X+        ; store into the staging buffer
...   (ORCC #$40 around the loop: FIRQ masked during banked access)
```

The bank latch is toggled per byte, and **FIRQ is masked** (`ORCC #$40` … `ANDCC
#$BF`) across the access so a MIDI interrupt can't change the bank mid-read. The
80 bytes are copied to a staging buffer at `$73BB`.

## Unpack — `$E12D` (the format key)

The 80-byte packed record is expanded into the working parameter buffer at
`$723F` (edit buffer base `$7237`, pointer `$7A19`). The unpack is **table-driven
threaded code**:

- descriptor streams at **`$DF85`, `$E05D`, `$E08B`, `$E0C6`** drive interpreters
  `$E19F` / `$E1A5`;
- each descriptor entry names a bit-field extractor; the extractors (`$E16A`,
  `$E17E`, `$E18F`… — runs of `LSRA/ROLB`) pull fields of various bit widths out
  of the packed stream and store them, byte-aligned, into the working buffer;
- a post-pass fixes up the name field (10 entries; substitutes a space `$20`
  where appropriate).

In other words the stored format is **bit-packed**, and the descriptor tables are
the exact field map. **Decoding `$DF85/$E05D/$E08B/$E0C6` yields the 80-byte
record layout** — that is the task handed to the patch-ROM format work (#15), and
the unpacked working layout is the patch parameter map (#16).

## Load sequence — `$BC2D` (called by program change `$C6F2`)

1. point the edit buffer (`$7A19 = $7C41 = $7237`);
2. `$BD39` → resolve bank + address + size (80); `$BCAF` → banked read to `$73BB`;
3. `$E12D` → unpack `$73BB → $723F`;
4. patch some header bytes; read the keyboard-mode byte (`+8`) to set unison
   (`$752E`);
5. `$8EBD` + **`$D2BB`** → rebuild voice allocation and **recompile the
   modulation matrix** (#9) — this is why patch changes (and edits) cost a
   recompile.

Program selection itself (`$C6F2`) implements the Matrix's **two-message bank
scheme**: a program value ≤9 selects a bank (`×100`), a following value 0–99
selects the patch within it, combined into `$7AD7`.

## Save / pack and SysEx

- **Save to user RAM** is the reverse: pack the working buffer back to 80 bytes
  (the descriptor tables are bijective) and bank-write into banks 0–1. The pack
  routine and write path are not yet traced byte-for-byte — open item.
- **SysEx** single/bulk dump & load transfer patches over MIDI with the
  nibble-encoding scheme; that wire format is documented with the patch
  parameter map (#16), and the SysEx handler is `$C82B` (#10 open item).

## Open items

- Decode the unpack descriptor tables (`$DF85` etc.) into the explicit 80-byte
  packed field map (#15).
- Trace the pack (save) path and confirm it is the inverse.
- Trace the SysEx handler `$C82B` and the nibble wire format (#16).
