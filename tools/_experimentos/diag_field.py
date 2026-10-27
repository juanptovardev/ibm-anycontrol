"""Diagnostico de un campo 5250: recorta, amplia y mide si hay texto.

Uso: python diag_field.py <png> <y0> <y1> <x0> <x1> [out.png]

Sirve para saber si un campo "vacio" en pantalla tiene texto invisible bajo la
barra de seleccion (cyan solido) y para revisarlo a ojo con el recorte x3.
"""
import sys
from collections import Counter

from PIL import Image


def main(argv):
    if len(argv) < 6:
        print("usage: diag_field.py <png> <y0> <y1> <x0> <x1> [out.png]", file=sys.stderr)
        return 2
    img = Image.open(argv[1]).convert("RGB")
    y0, y1, x0, x1 = (int(v) for v in argv[2:6])
    crop = img.crop((x0, y0, x1, y1))
    colores = Counter(crop.getdata())
    total = crop.width * crop.height
    print(f"crop={crop.width}x{crop.height} colores={len(colores)}")
    for c, n in colores.most_common(5):
        print(f"  {c} x{n} ({100.0 * n / total:.1f}%)")
    fondo = colores.most_common(1)[0][0]
    otros = total - colores.most_common(1)[0][1]
    print(f"pixeles no-fondo={otros} ({100.0 * otros / total:.1f}%)")
    salida = argv[6] if len(argv) > 6 else "diag.png"
    crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS).save(salida)
    print(f"guardado -> {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
