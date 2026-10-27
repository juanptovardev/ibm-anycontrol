"""Captura la pantalla remota AHORA y mide las lineas de la ficha.

Busca la raiz de AnyDesk por clase ad_win, resuelve el viewport hijo,
captura 1:1 y hace OCR para devolver las lineas con sus cajas.

Uso: python tools/_experimentos/ficha_ahora.py [etiqueta]
Solo lectura: no envia input.
"""
import ctypes
import re
import sys
from pathlib import Path

import pytesseract
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_shot  # noqa: E402

user32 = ctypes.windll.user32
REPO_MCP = Path(r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk")
sys.path.insert(0, str(REPO_MCP))

MARCA_FICHA = re.compile(r"OTRAS\s+DIRECCIONES|TOTAL\s+UNIDADES|MULTI-?EDIFICIO", re.I)


def raiz_anydesk():
    """Devuelve (hwnd, titulo) de la ventana raiz de AnyDesk."""
    hallados = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value.startswith("ad_win"):
            t = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, t, 256)
            hallados.append((hwnd, t.value))
        return True

    user32.EnumWindows(cb, 0)
    return hallados


def lineas(img):
    data = pytesseract.image_to_data(
        img, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    out = []
    for i, txt in enumerate(data["text"]):
        t = (txt or "").strip()
        if not t:
            continue
        out.append({"t": t, "x": data["left"][i], "y": data["top"][i],
                    "w": data["width"][i], "h": data["height"][i]})
    return out


def agrupa(words, tol=6):
    renglones = {}
    for w in words:
        clave = None
        for k in renglones:
            if abs(k - w["y"]) <= tol:
                clave = k
                break
        if clave is None:
            renglones[w["y"]] = [w]
        else:
            renglones[clave].append(w)
    out = []
    for y in sorted(renglones):
        ws = sorted(renglones[y], key=lambda w: w["x"])
        out.append({"y": y, "texto": " ".join(w["t"] for w in ws),
                    "x0": ws[0]["x"], "x1": ws[-1]["x"] + ws[-1]["w"],
                    "h": max(w["h"] for w in ws)})
    return out


def main(argv):
    etiqueta = argv[0] if argv else "ficha-medir"
    raices = raiz_anydesk()
    if not raices:
        print("no hay ventana AnyDesk abierta")
        return 1
    print("raices AnyDesk:", [(h, t) for h, t in raices])
    root = raices[0][0]

    from mcp_anydesk_server import window_manager as wm  # noqa: E402

    vp = wm.find_viewport(root)
    print("viewport:", vp)
    hwnd_cap = vp["hwnd"] if vp else root
    img = native_shot.grab(hwnd_cap)
    ruta = native_shot.save(img, etiqueta)
    print(f"imagen: {ruta}  {img.size[0]}x{img.size[1]}")

    rs = agrupa(lineas(img))
    texto = " ".join(r["texto"] for r in rs)
    print("marca_ficha:", bool(MARCA_FICHA.search(texto)))
    print("--- renglones ---")
    for r in rs:
        if r["y"] > 400:
            continue
        print(f"{r['y']:4d} | x {r['x0']:4d}..{r['x1']:4d} | {r['texto'][:95]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
