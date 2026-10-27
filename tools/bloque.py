"""Copia el bloque cabecera del listado: Cuenta / Edificio / Direccion.

Mide la cabecera por OCR sobre una captura 1:1 fresca (nada de coordenadas
cacheadas), ancla el cursor en la primera linea, extiende la seleccion con
Shift+clic al final de la tercera y copia con Ctrl+C.

Uso:
    python tools/bloque.py <hwnd>            # mide + selecciona + copia
    python tools/bloque.py <hwnd> --dry      # mide + selecciona, sin copiar
    python tools/bloque.py <hwnd> --downs 2  # ancla con N bajadas (receta manual)

El texto copiado queda en el portapapeles REMOTO. Si AnyDesk sincroniza
portapapeles, tambien aparece en el local (Get-Clipboard).
"""
import asyncio
import sys
from pathlib import Path

import pytesseract
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cp  # noqa: E402
import preflight_auto as pf  # noqa: E402
from _mcp import connect, need_hwnd  # noqa: E402

MARGEN_X = 10  # px a la derecha del ultimo glifo util
MARGEN_ANCLA = 4  # px desde el borde izquierdo del texto


def _palabras(img):
    data = pytesseract.image_to_data(
        img, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    out = []
    for i, txt in enumerate(data["text"]):
        t = (txt or "").strip()
        if not t:
            continue
        out.append(
            {"t": t, "x": data["left"][i], "y": data["top"][i],
             "w": data["width"][i], "h": data["height"][i]}
        )
    return out


def renglones(palabras, tol=6):
    filas = {}
    for p in palabras:
        clave = None
        for k in filas:
            if abs(k - p["y"]) <= tol:
                clave = k
                break
        if clave is None:
            filas[p["y"]] = [p]
        else:
            filas[clave].append(p)
    out = []
    for y in sorted(filas):
        ws = sorted(filas[y], key=lambda p: p["x"])
        out.append(
            {"y": y, "h": max(p["h"] for p in ws),
             "texto": " ".join(p["t"] for p in ws),
             "x0": ws[0]["x"], "x1": ws[-1]["x"] + ws[-1]["w"]}
        )
    return out


def _util(r):
    """Renglon con texto real (descarta basura de 1-2 caracteres)."""
    return len(r["texto"]) >= 6 and r["x1"] - r["x0"] > 40


def bloque_cabecera(img):
    """Devuelve las 3 lineas de la cabecera y las coordenadas de seleccion.

    La primera linea suele traer ademas "Com: X Div: Y"; si aparece, el corte
    horizontal se calcula con las otras dos para no arrastrar ese sobrante.
    """
    rs = [r for r in renglones(_palabras(img)) if _util(r)]
    idx = None
    for i, r in enumerate(rs):
        if r["texto"].upper().startswith("CUENTA"):
            idx = i
            break
    if idx is None:
        return None
    if idx + 2 >= len(rs):
        return None
    tres = rs[idx: idx + 3]
    sobrante = any(t.upper().startswith(("COM:", "DIV:")) for t in tres[0]["texto"].split())
    base = tres[1:] if sobrante else tres
    return {
        "lineas": [r["texto"] for r in tres],
        "x_ancla": tres[0]["x0"] + MARGEN_ANCLA,
        "y_ancla": tres[0]["y"] + tres[0]["h"] // 2,
        "x_fin": max(r["x1"] for r in base) + MARGEN_X,
        "y_fin": tres[2]["y"] + tres[2]["h"] // 2 + 2,
        "y0": tres[0]["y"],
        "y1": tres[2]["y"] + tres[2]["h"],
    }


async def _run(hwnd, dry, downs):
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        img = pf.shot(hwnd, "bloque-antes")
        b = bloque_cabecera(img)
        if not b:
            print("no se encontro la cabecera (Cuenta/Edificio/Direccion)")
            return 1
        for i, t in enumerate(b["lineas"]):
            print(f"linea {i + 1}: {t}")
        print(f"ancla=({b['x_ancla']},{b['y_ancla']}) fin=({b['x_fin']},{b['y_fin']})")

        if downs:
            await pf.step(s, "bajar", "press_keys", {"keys": ["down"] * downs})
        else:
            await pf.step(s, "ancla", "click_point",
                          {"x": b["x_ancla"], "y": b["y_ancla"]})
        await pf.step(s, "seleccion", "click_point",
                      {"x": b["x_fin"], "y": b["y_fin"], "shift": True})
        img2 = pf.shot(hwnd, "bloque-sel")
        caja, alto = cp.sel_box(img2)
        print(f"sel caja={caja} alto={alto}")
        if not caja:
            print("AVISO: no se detecto marco de seleccion (informativo)")
        if dry:
            await pf.step(s, "escape", "press_keys", {"keys": ["escape"]})
            print("DRY: sin copiar")
            return 0
        await pf.step(s, "ctrl_c", "copy_clipboard", {})
        print("ctrl_c enviado")
    return 0


def main(argv):
    hwnd = need_hwnd(argv, pos=1)
    args = argv[2:]
    dry = "--dry" in args
    downs = 0
    if "--downs" in args:
        downs = int(args[args.index("--downs") + 1])
    return asyncio.run(_run(hwnd, dry, downs))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
