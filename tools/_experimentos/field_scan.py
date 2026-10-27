"""Scan a native 1:1 capture for the form's underline rows.

5250 input fields render as long underscore lines. For each image row in the
given y-range, count bright pixels in the x-range; rows above a threshold
are (parts of) an underline. Groups consecutive rows and prints the band
centres, so clicks can aim at the middle of the field row.

Usage: python tools/field_scan.py <png> [y0 y1 x0 x1]
"""
import sys

from PIL import Image

path = sys.argv[1]
y0, y1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (90, 250)
x0, x1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (380, 800)
thr = int(sys.argv[6]) if len(sys.argv) > 6 else 200
bright = int(sys.argv[7]) if len(sys.argv) > 7 else 200

im = Image.open(path).convert("RGB")
W, H = im.size
px = im.load()
hits = []
for y in range(y0, min(y1, H)):
    c = 0
    for x in range(x0, min(x1, W)):
        r, g, b = px[x, y]
        if r + g + b > bright:
            c += 1
    if c > thr:
        hits.append(y)

bands = []
for y in hits:
    if bands and y - bands[-1][-1] <= 2:
        bands[-1].append(y)
    else:
        bands.append([y])
print("size", W, H)
for b in bands:
    print("band", b[0], "-", b[-1], "centre", (b[0] + b[-1]) // 2)
