"""Detecta las filas del formulario 5250 por pixeles (sin coords cacheadas).

El usuario redimensiona/maximiza AnyDesk y todas las coordenadas viejas
mueren. Esto mide sobre la captura actual:

  1. bandas de texto VERDE (etiquetas de la columna izquierda).
  2. se descarta lo que este por encima del mayor hueco vertical (cabecera)
     y queda el bloque de campos.
  3. inicio de campo = primera corrida larga de pixeles no-negros despues
     del final de la etiqueta (el subrayado del input).

Uso: python tools/rows.py <hwnd> [--draw]
"""
import sys

from PIL import ImageDraw

import native_shot
from _mcp import REPO, need_hwnd

sys.path.insert(0, REPO)
from mcp_anydesk_server import window_manager as W  # noqa: E402

LABEL_X = (150, 500)
FIELD_MIN_X = 400


def _green(p):
    r, g, b = p[:3]
    return g > 140 and r < 130 and b < 130


def green_rows(img):
    px = img.load()
    x0, x1 = LABEL_X
    x1 = min(x1, img.width)
    rows, ends = [], []
    for y in range(img.height):
        last = -1
        for x in range(x0, x1):
            if _green(px[x, y]):
                last = x
        rows.append(last >= 0)
        ends.append(last)
    return rows, ends


def bands(rows, min_h=5, max_h=26):
    out, start = [], None
    for y, on in enumerate(rows):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if min_h <= y - start <= max_h:
                out.append((start, y - 1))
            start = None
    if start is not None and min_h <= len(rows) - start <= max_h:
        out.append((start, len(rows) - 1))
    return out


def field_block(bs):
    """Bloque de campos: todo lo que queda bajo el mayor hueco vertical."""
    if len(bs) < 2:
        return bs
    gaps = [(bs[i + 1][0] - bs[i][1], i) for i in range(len(bs) - 1)]
    _, idx = max(gaps)
    return bs[idx + 1:]


def field_start(img, y0, y1, label_end, gap=10, min_len=20):
    px = img.load()
    ys = range(max(0, y0 - 3), min(img.height, y1 + 5))
    start_x = max(FIELD_MIN_X, label_end + 25)
    runs, cur = [], None
    for x in range(start_x, img.width):
        on = any(sum(px[x, y][:3]) > 90 for y in ys)
        if on and cur is None:
            cur = x
        elif not on and cur is not None:
            runs.append([cur, x - 1])
            cur = None
    if cur is not None:
        runs.append([cur, img.width - 1])

    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    merged = [r for r in merged if r[1] - r[0] >= min_len]
    return merged[0][0] if merged else None


def detect(hwnd):
    """Devuelve (img, filas) con filas = [{y0,y1,cy,label_end,field_x}]."""
    vp = W.find_viewport(hwnd)
    img = native_shot.grab(vp["hwnd"])
    rows, ends = green_rows(img)
    bs = field_block(bands(rows))
    out = []
    for y0, y1 in bs:
        label_end = max(ends[y0:y1 + 1])
        out.append({
            "y0": y0,
            "y1": y1,
            "cy": (y0 + y1) // 2,
            "label_end": label_end,
            "field_x": field_start(img, y0, y1, label_end),
        })
    return img, vp, out


def main():
    hwnd = need_hwnd(sys.argv)
    img, vp, rows = detect(hwnd)
    print(f"viewport hwnd={vp['hwnd']} img={img.size} filas={len(rows)}")
    for i, r in enumerate(rows):
        print(f"  [{i}] y={r['y0']}..{r['y1']} cy={r['cy']} "
              f"label_end={r['label_end']} field_x={r['field_x']}")
    if "--draw" in sys.argv:
        d = ImageDraw.Draw(img)
        for i, r in enumerate(rows):
            d.line([(0, r["cy"]), (img.width, r["cy"])], fill=(255, 0, 0))
            d.text((5, r["y0"]), str(i), fill=(255, 0, 0))
            if r["field_x"]:
                d.line([(r["field_x"], r["cy"] - 6), (r["field_x"], r["cy"] + 6)],
                       fill=(255, 255, 0))
        print(f"draw -> {native_shot.save(img, 'rows-detect')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
