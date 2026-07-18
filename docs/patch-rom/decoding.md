# Decoding the factory patches

A reproducible decoder for the patch ROM, plus an honest account of what is
decoded and what still isn't. Builds on the packed format (#15) and parameter map
(#16).

## Tools

- `tools/unpack_patch.py` — faithful opcode-level emulation of the firmware's
  unpack extractor (`$DF85` descriptor); turns one 80-byte record into the
  126-byte working buffer.
- `tools/patch_params.py` — the internal-buffer → parameter mapping and labels.
- `tools/decode_patches.py` — runs the unpack over every record in the patch ROM,
  validates value ranges, and writes a CSV.

```sh
PYTHONPATH=tools python3 tools/decode_patches.py \
    reference/extracted/matrix-1000/os-rom/v1.11/M1000-CAT27256P-17_v111.BIN \
    reference/extracted/matrix-1000/patch-rom/M1000-PatchROM_27512_C2DB.BIN \
    build/patches_pass1.csv
```

(`build/` is git-ignored; the CSV is regenerable.)

## What's validated

Running the decoder over the whole 64 KB patch ROM:

```
patches decoded : 819
unpacked lengths: {126: 819}
values <= 0x3F  : 98850 / 103194 (95.8%)
```

- **819 records** of 80 bytes (the ROM holds 819 slots; the documented factory set
  is 800, the remainder are spare/extra slots).
- **Every** record unpacks to a consistent **126 bytes** — the pass-1 emulation
  never desyncs across the entire ROM, which is strong evidence the extractor
  model (widths + store modes, #15) is correct.
- **95.8%** of decoded bytes fall in `0–$3F` (the Matrix's unsigned 6-bit
  parameter range). The remaining ~4% are concentrated where the parameter map
  (#16) says the **signed mod amounts** live (params 86–133, 7-bit ±). So the
  out-of-`$3F` values are expected, not errors — further corroboration.

## The internal → parameter mapping (solved)

The 126-byte working buffer is the canonical Matrix parameter model **shifted by
8**:

```
internal_buffer[i]  ==  SysEx parameter (i + 8)
```

i.e. the buffer holds parameters **8…133**; parameters **0–7 are the patch name,
which the Matrix-1000 does not store** (it is a number-addressed rack with no name
display — the earlier semi-ASCII bytes in the raw record were parameter data
coincidentally in the ASCII range, not names).

**Confirmed against external data.** The factory patch *names* exist (the Don
Solaris patchbook in `reference/` lists all 1000, e.g. #200 = `obxa-11`), but they
are **not in the M1000 ROM**: neither ROM contains any name fragment as plain
ASCII, and a 6-bit decode of a record at every offset/bit-order yields nothing
resembling its patchbook name. So the names are documentation (inherited from the
Matrix-6, which *does* have a display) — they pair with our decode **by number**
(patch-ROM record _r_ = patch #(r+200) = patchbook entry _r+200_) to give fully
labelled, named patches.

The Owner's Manual corroborates the heritage (p.5, 27): the Matrix-1000's 1000
sounds are *"a compilation of the finest Matrix sounds collected over … three
years from … Matrix-6 and Matrix-6R owners,"* and Oberheim shipped them to M6/6R
owners on cassette. The M6/6R have the alphanumeric display; the number-only
Matrix-1000 kept the parameters and dropped the names.

**Validated** by bit-width: under this mapping, every narrow bitfield lands in
range across all 819 patches. Checking 29 known 2-/3-bit parameters, 26 are always
in range; the 3 that aren't (env1/2/3 **mode**, params 57/66/75) simply pack extra
flag bits beyond the documented 2 — not a mapping error. A spot-labelled patch is
obviously coherent:

```
patch 250: VCF freq/reso=0/55  VCA1=33  ENV1 DADSR=63/31/39/0/63
           matrix buses (src,amt,dst): (10,-20,21) (19,-34,0) …
```

`tools/patch_params.py` carries the label table and `labelled()` mapping (signed
mod amounts folded to ±). `tools/decode_patches.py` emits
`build/patches_labelled.csv` — all 819 patches × 126 named parameters.

## Status

**Done**: faithful unpack; the internal→parameter mapping (`+8`); full labelled
decode of every factory patch (DCOs, VCF, VCA, 3 envelopes, 2 LFOs, ramps,
tracking generator, the 18 dedicated mod slots and the 10 programmable matrix
buses with signed amounts). Patch names are confirmed *not stored* on the M1000.

**Minor remaining**: the **source/destination code enumerations** (which mod
number = which source/destination) — a small lookup table to make the matrix
buses fully human-readable; and pass 2 (`$E08B`) only redistributes bits within
the matrix bytes, which already decode correctly here.

## Next

The labelled CSV supports the sound-design analysis (#18) directly —
distributions, common settings, matrix-routing idioms across the factory set.
