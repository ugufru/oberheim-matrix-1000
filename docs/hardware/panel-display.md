# Front panel & display

The Matrix-1000's panel is deliberately minimal — it is a preset rack, not an
editing surface. Hardware addresses below are confirmed against the **v1.11** code
([I/O map](io-map.md), #4); the firmware that scans them is the boot/UI code (#6).

## What's on the panel

A 3-digit LED display (patch number), a small set of buttons (bank/group, store,
and the panel-held boot combinations for the extended functions), and status
LEDs. There is **no alphanumeric name display** — which is why the patch ROM
stores no patch names (#17).

## Switch inputs — `$1800–$1BFF` (read)

The panel buttons are read as inputs at `$1800` and `$1801`. The boot path tests
specific bits to enter diagnostic/calibration modes (e.g. `$1801 & 4` arms the
factory-reset/self-test path, `$1800 == '$'` gates calibration — #6/#12). At run
time the foreground/UI scans these for button presses.

## Output latches — `$1C00–$1FFF` (write)

Write-only latches drive the LEDs, the display digits, and control lines. Known
from code:

| Address | Role |
|---|---|
| `$1C06/$1C07/$1C86/$1C87` | LED / display latches |
| `$1D00` | control latch (engine enable bit cleared at boot) |
| `$1D80` | **bank-select latch** (VA13–15) for patch ROM / RAM paging (#11) |
| `$1F80` | display/LED latch (`~$7A0D` shadow) |

The display and LEDs are refreshed from RAM shadow state (`$7A0D–$7A10`, #6); the
firmware writes the inverted shadow to the latch (e.g. `$1F80 = ~$7A0D`).

## Open items

- Map the exact switch bit → button assignments and the display digit/segment
  encoding (panel-gated UI code; schematic).
- Confirm which `$1C` latch carries the VA13–15 bank bits and their order (#11).
