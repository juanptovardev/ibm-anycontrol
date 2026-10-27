"""Analiza una captura: cajas de palabra del bloque cabecera y marco de seleccion.

Uso: python tools/_experimentos/leer_bloque.py <ruta.png>
Solo lectura.
"""
import sys
from pathlib import Path

import pytesseract
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cp  # noqa: E402


def main(argv):
    p = Path(argv[0])
    img = Image.open(p).convert("RGB")
    print(f"imagen: {p.name} {img.size}")

    caja, alto = cp.sel_box(img)
    print(f"sel_box: caja={caja} alto={alto}")

    data = pytesseract.image_to_data(
        img, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    print("--- palabras y=95..175 ---")
    filas = {}
    for i, txt in enumerate(data["text"]):
        t = (txt or "").strip()
        if not t:
            continue
        y = data["top"][i]
        if not (95 <= y <= 175):
            continue
        filas.setdefault(y, []).append(
            (data["left"][i], data["left"][i] + data["width"][i], data["height"][i], t)
        )
    for y in sorted(filas):
        ws = sorted(filas[y])
        print(f"y={y:4d} h={ws[0][2]:2d} | " + " ".join(f"{t}[{a}-{b}]" for a, b, _, t in ws))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
