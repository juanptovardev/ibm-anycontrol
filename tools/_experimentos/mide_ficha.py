"""Busca una captura de la FICHA DEL EDIFICIO y devuelve las cajas de texto.

Uso:
    python tools/_experimentos/mide_ficha.py            # escanea y reporta la primera ficha
    python tools/_experimentos/mide_ficha.py --img ruta.png

Solo lectura: no envia input ni conecta al MCP.
"""
import re
import sys
from pathlib import Path

import pytesseract
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
EVID = REPO / "evidencia"

MARCA_FICHA = re.compile(r"OTRAS\s+DIRECCIONES|TOTAL\s+UNIDADES|MULTI-?EDIFICIO", re.I)


def lineas(img):
    data = pytesseract.image_to_data(
        img, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    out = []
    for i, txt in enumerate(data["text"]):
        t = (txt or "").strip()
        if not t:
            continue
        out.append(
            {
                "t": t,
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i],
            }
        )
    return out


def agrupa(words, tol=6):
    """Agrupa palabras en lineas por su top."""
    renglones = {}
    for w in words:
        clave = min(renglones, key=lambda k: abs(k - w["y"]), default=None)
        if clave is not None and abs(clave - w["y"]) <= tol:
            renglones[clave].append(w)
        else:
            renglones[w["y"]] = [w]
    out = []
    for y in sorted(renglones):
        ws = sorted(renglones[y], key=lambda w: w["x"])
        out.append(
            {
                "y": y,
                "texto": " ".join(w["t"] for w in ws),
                "x0": ws[0]["x"],
                "x1": ws[-1]["x"] + ws[-1]["w"],
                "h": max(w["h"] for w in ws),
            }
        )
    return out


def escanea(limite=60):
    imgs = sorted(EVID.glob("native-*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in imgs[:limite]:
        try:
            img = Image.open(p)
        except OSError:
            continue
        txt = " ".join(w["t"] for w in lineas(img))
        if MARCA_FICHA.search(txt):
            return p, img
    return None, None


def main(argv):
    if "--img" in argv:
        p = Path(argv[argv.index("--img") + 1])
        img = Image.open(p)
    else:
        p, img = escanea()
        if p is None:
            print("no se encontro ninguna captura con marcas de ficha")
            return 1
    print(f"imagen: {p.name}  {img.size[0]}x{img.size[1]}")
    print("--- renglones (y | x0..x1 | texto) ---")
    for r in agrupa(lineas(img)):
        if r["y"] > 380:
            continue
        print(f"{r['y']:4d} | {r['x0']:4d}..{r['x1']:4d} | {r['texto'][:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
