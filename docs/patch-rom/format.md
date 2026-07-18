# Packed patch format (the 80-byte stored record)

Each stored Matrix-1000 patch is **80 bytes**, bit-packed. The firmware expands it
into a ~126–134-byte working buffer at load time (#11). This doc documents the
packed record and the unpack, validated by a faithful reimplementation of the
firmware's own unpack code. From the **v1.11** OS ROM + the factory patch ROM.

## Where the records are

- 80 bytes per patch (`$BD39`: `×$50`); 100 patches per 8 KB bank.
- **Factory**: banks 2–9 → the 64 KB patch ROM
  (`reference/extracted/matrix-1000/patch-rom/…`), 800 patches, file offset
  `(patch# − 200) × 80`.
- **User**: banks 0–1 → battery RAM, 200 patches.

## The unpack is two-pass threaded code (`$E12D`)

```
e12d  LDU #$DF85 ; JSR $E19F     ; pass 1: bit-stream -> parameter bytes
e137  LDU #$E08B ; JSR $E1A5     ; pass 2: post-process / bit distribution
e13f  LEAX $60,X ; ...           ; name fixup at output offset +$60
```

### Pass 1 — bit-stream extractor (`$DF85` / `$E19F`)

The descriptor at `$DF85` is a list of **extractor-routine addresses** (threaded
code). They share one `LSRA`/`ROLB` shift chain at `$E16A–$E1A4`; the **entry
offset selects the field width** (each `LSRA/ROLB` pair = one bit), and there are
three store modes:

| Store mode | Block | Output |
|---|---|---|
| store A (`STA ,X+`, refill A from `,Y+`) | `$E16A…` | 1 byte |
| store B (`STB ,X+`, `CLRB`) | `$E17E…` | 1 byte |
| store D (`STD ,X++`, refill A) | `$E18F…` | 2 bytes |

`$E19F` (`CLRB; LDA ,Y+; PULU PC`) fetches the next packed byte and threads to the
next descriptor entry; `$E1A4` (`RTS`) terminates. So pass 1 walks the descriptor,
pulling fields of varying bit-width out of the 80-byte stream into successive
output bytes.

### Pass 2 — bit distribution (`$E08B` / `$E1A5`)

`$E1A5` reads `(count, index)` pairs from the `$E08B` descriptor and spreads bits
into specific output offsets (the descriptor bytes are literally
`02 0B  01 4E 01 4F 01 50 …` — counts and target indices `$4E,$4F,$50…`). This
fills in the fields pass 1 doesn't, e.g. the modulation-matrix routing bytes.

### Name — not stored on the Matrix-1000

The 80-byte record is **parameters only** (the canonical params 8–133). The
Matrix-1000 is a number-addressed rack with no name display, so the 8-character
name (params 0–7) is not stored. Semi-ASCII bytes visible in the raw record
(`$zSex`, `pK7P`) are parameter data that happens to land in the ASCII range, not
names. (The `+$60` fixup in `$E12D` is the 10×3-byte mod-matrix sanity pass, not a
name field.) See #17.

## Validation: a faithful reimplementation

`tools/unpack_patch.py` emulates the exact extractor opcodes (`LSRA/ROLB/CLRB/
STA/STB/STD/LDA,Y+/PULU PC`) driven by the `$DF85` descriptor — so it reproduces
the firmware's **pass 1** by construction. Run on factory patches it consumes the
80 packed bytes and emits **126 bytes of sane parameter values** (almost all in
`0–$3F`, the Matrix's 6-bit parameter range), e.g.:

```
$ tools/unpack_patch.py <os-rom> <patch-rom> 0
patch index 0  packed=80 consumed=81 unpacked=126
unpacked: 01 00 00 00 03 02 0C 1E 20 03 03 32 1F 00 …
```

The ~126-byte result also matches the ~129-byte default-patch template seen in the
factory-reset path (#12). This confirms the record size, the unpack mechanism, and
the field-width/store-mode model.

## What's confirmed vs. open

**Confirmed**: 80-byte packed record; two-pass threaded-code unpack; the extractor
width/store-mode scheme; pass-1 output is faithfully reproduced and yields valid
parameter values; the name is 6-bit-packed near offset `$24`.

**Resolved in #17**:
- the output-offset → parameter mapping is simply `internal[i] = parameter i+8`;
- names are not stored on the M1000;
- all 819 factory records decode to labelled parameters, validated by bitfield
  ranges.
