#!/usr/bin/env python3
"""Render all factory patches as a force-directed map: brightness x register.

Each patch is positioned from its DECODED parameters:
  x (mellow -> bright) = static cutoff + envelope filter-opening + resonance ring
  y (low -> high)      = oscillator register (DCO frequency)
Values are rank-normalised (so the cloud fills the canvas; order is preserved),
used as anchors, then a light force relaxation separates overlapping points.
Colour = heuristic genre from the patch name (tools/patch_genre.py).

Usage:
    patch_map_svg.py <os-rom> <patch-rom> <out.svg>
"""
import sys
import random
from unpack_patch import unpack
from patch_params import labelled
from patch_names import NAMES
from patch_genre import genre, COLORS

X0, Y0, W, H = 70, 80, 1000, 700      # plot area
R = 15.0                               # desired min separation
ITERS = 150
SPRING = 0.035                         # weak anchor pull -> repulsion de-stripes


def brightness(d):
    return d["vcf_freq"] + 0.7 * max(0, d["m_vcff_by_env1"]) + 0.4 * d["vcf_reso"]


def register(d):
    return (d["dco1_freq"] + d["dco2_freq"]) / 2.0


def rank_norm(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    for rank, i in enumerate(order):
        out[i] = rank / (len(vals) - 1)
    return out


def main():
    os_rom = open(sys.argv[1], "rb").read()
    pr = open(sys.argv[2], "rb").read()
    out_svg = sys.argv[3]
    n = len(pr) // 80

    pts = []
    for i in range(n):
        d = labelled(unpack(os_rom, pr[i * 80:i * 80 + 80])[0])
        nm = NAMES.get(200 + i, "")
        if not (d["vcf_freq"] or d["dco1_freq"] or any(d["mod%d_source" % k] for k in range(10))):
            continue  # skip empty slots
        pts.append({"num": 200 + i, "name": nm, "g": genre(nm),
                    "b": brightness(d), "r": register(d)})

    # jitter before ranking so the many tied values (e.g. cutoff=0) don't rank
    # into straight lines; ordering is otherwise preserved.
    jr = random.Random(7)
    bx = rank_norm([p["b"] + jr.uniform(-0.5, 0.5) for p in pts])
    ry = rank_norm([p["r"] + jr.uniform(-0.5, 0.5) for p in pts])
    rng = random.Random(12345)
    for i, p in enumerate(pts):
        p["tx"] = X0 + bx[i] * W
        p["ty"] = Y0 + (1 - ry[i]) * H        # +y up = higher register
        p["x"] = p["tx"] + rng.uniform(-8, 8)
        p["y"] = p["ty"] + rng.uniform(-8, 8)

    # force relaxation: spring to anchor + local repulsion (spatial grid)
    cell = R
    for _ in range(ITERS):
        grid = {}
        for idx, p in enumerate(pts):
            grid.setdefault((int(p["x"] // cell), int(p["y"] // cell)), []).append(idx)
        for idx, p in enumerate(pts):
            fx = fy = 0.0
            cx, cy = int(p["x"] // cell), int(p["y"] // cell)
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for j in grid.get((gx, gy), ()):
                        if j == idx:
                            continue
                        q = pts[j]
                        dx, dy = p["x"] - q["x"], p["y"] - q["y"]
                        d2 = dx * dx + dy * dy
                        if 0 < d2 < R * R:
                            d = d2 ** 0.5
                            f = (R - d) / d * 0.5
                            fx += dx * f
                            fy += dy * f
            # spring to anchor + tiny jitter to break grid symmetry
            fx += (p["tx"] - p["x"]) * SPRING + rng.uniform(-0.4, 0.4)
            fy += (p["ty"] - p["y"]) * SPRING + rng.uniform(-0.4, 0.4)
            p["x"] = min(X0 + W, max(X0, p["x"] + fx))
            p["y"] = min(Y0 + H, max(Y0, p["y"] + fy))

    # ---- emit SVG ----
    genres = [g for g in COLORS if any(p["g"] == g for p in pts)]
    out = []
    out.append('<svg xmlns="http://www.w3.org/2000/svg" width="1380" height="860" '
               'viewBox="0 0 1380 860" font-family="Helvetica, Arial, sans-serif">')
    out.append('<rect x="0" y="0" width="1380" height="860" fill="#fcfcfb"/>')
    out.append('<text x="40" y="40" font-size="22" font-weight="bold" fill="#222">'
               'Oberheim Matrix-1000 — factory patch map (%d patches)</text>' % len(pts))
    out.append('<text x="40" y="62" font-size="13" fill="#666">Position from decoded '
               'parameters: x = mellow → bright, y = low → high register (rank-scaled). '
               'Colour = genre from the patch name.</text>')
    # quadrant guides + axis labels
    out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#ddd"/>' % (X0, Y0, W, H))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#eee"/>' % (X0 + W // 2, Y0, X0 + W // 2, Y0 + H))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#eee"/>' % (X0, Y0 + H // 2, X0 + W, Y0 + H // 2))
    out.append('<text x="%d" y="%d" font-size="13" fill="#999" text-anchor="middle">← mellow</text>' % (X0 + 90, Y0 + H + 24))
    out.append('<text x="%d" y="%d" font-size="13" fill="#999" text-anchor="middle">bright →</text>' % (X0 + W - 90, Y0 + H + 24))
    out.append('<text x="%d" y="%d" font-size="13" fill="#999" transform="rotate(-90 %d %d)" text-anchor="middle">low → high register</text>' % (X0 - 28, Y0 + H // 2, X0 - 28, Y0 + H // 2))

    for p in pts:
        out.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s" fill-opacity="0.82" stroke="#fff" stroke-width="0.4"><title>#%d %s (%s)</title></circle>'
                   % (p["x"], p["y"], COLORS[p["g"]], p["num"], p["name"], p["g"]))

    # legend
    lx, ly = X0 + W + 40, Y0 + 6
    out.append('<text x="%d" y="%d" font-size="14" font-weight="bold" fill="#333">Genre</text>' % (lx, ly))
    for k, g in enumerate(genres):
        yy = ly + 22 + k * 22
        out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (lx + 6, yy - 4, COLORS[g]))
        out.append('<text x="%d" y="%d" font-size="12" fill="#333">%s</text>' % (lx + 18, yy, g))

    out.append('</svg>')
    open(out_svg, "w").write("\n".join(out) + "\n")
    print("wrote %s : %d patches, %d genres" % (out_svg, len(pts), len(genres)))


if __name__ == "__main__":
    main()
