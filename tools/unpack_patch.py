#!/usr/bin/env python3
"""Faithfully reproduce the Matrix-1000 patch unpack, PASS 1 ($DF85 / $E19F).

The OS ROM unpacks an 80-byte stored patch in two passes ($E12D): pass 1 ($DF85)
pulls bit-fields into parameter bytes; pass 2 ($E08B) post-distributes bits; a
name fixup follows. This tool simulates the exact 6809 opcodes of the pass-1
extractor block ($E16A-$E1A4), driven by the descriptor at $DF85, so its output
is the firmware's pass-1 behaviour by construction. Pass 2 + name decode are TODO
(see docs/patch-rom/format.md and #17).

Usage:
    unpack_patch.py <os-rom> <patch-rom> [patch-index]
"""
import sys

OS_BASE = 0x8000
DESC = 0xDF85          # primary unpack descriptor (from $E12D: LDU #$DF85)
START = 0xE19F         # $E12D enters the threaded code via JSR $E19F
STORE_END = 0xE1A4     # RTS terminator


def unpack(os_rom, src):
    """Run the threaded unpacker over 80 packed bytes -> list of output bytes."""
    def rd(addr):
        return os_rom[addr - OS_BASE]

    A = 0
    B = 0
    C = 0
    out = []
    yptr = 0           # index into src (the ,Y+ stream)
    uptr = DESC        # descriptor pointer (the ,U threaded stream)
    pc = START
    steps = 0
    while True:
        steps += 1
        if steps > 100000:
            raise RuntimeError("runaway unpack")
        if pc == STORE_END:        # 0x39 RTS -> done
            break
        op = rd(pc)
        if op == 0x44:             # LSRA
            C = A & 1
            A >>= 1
            pc += 1
        elif op == 0x59:           # ROLB
            B = ((B << 1) | C) & 0xFF
            C = (B >> 8) & 1       # (B already masked; carry handled below)
            C = 0 if (B & 0x100) == 0 else 1
            B &= 0xFF
            pc += 1
        elif op == 0x5F:           # CLRB
            B = 0
            pc += 1
        elif op == 0xA7:           # STA ,X+   (A7 80)
            out.append(A)
            pc += 2
        elif op == 0xA6:           # LDA ,Y+   (A6 A0)
            A = src[yptr] if yptr < len(src) else 0
            yptr += 1
            pc += 2
        elif op == 0xE7:           # STB ,X+   (E7 80)
            out.append(B)
            pc += 2
        elif op == 0xED:           # STD ,X++  (ED 81)
            out.append(A)
            out.append(B)
            pc += 2
        elif op == 0x37:           # PULU PC   (37 80) -> pull next descriptor entry
            hi = os_rom[uptr - OS_BASE]
            lo = os_rom[uptr - OS_BASE + 1]
            uptr += 2
            pc = (hi << 8) | lo
        else:
            raise RuntimeError("unexpected opcode %02X at %04X" % (op, pc))
    return out, yptr


def main():
    os_rom = open(sys.argv[1], "rb").read()
    patch_rom = open(sys.argv[2], "rb").read()
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    packed = patch_rom[idx * 80:idx * 80 + 80]
    out, consumed = unpack(os_rom, packed)
    print("patch index %d  packed=%d bytes consumed=%d  unpacked=%d bytes"
          % (idx, len(packed), consumed, len(out)))
    name = "".join(chr(b) if 32 <= b < 127 else "." for b in out[:8])
    print("first 8 unpacked bytes as ASCII: %r" % name)
    print("unpacked:", " ".join("%02X" % b for b in out))


if __name__ == "__main__":
    main()
