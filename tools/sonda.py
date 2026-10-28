"""Sonda de estado: busca la raiz de AnyDesk, el viewport y que pantalla hay.

Read-only. No toca la maquina remota.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import win32gui

import estado
import native_shot
import vigia


def raices():
    out = []
    win32gui.EnumWindows(
        lambda h, _p: out.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h)))
        if win32gui.GetClassName(h).startswith("ad_win") and win32gui.IsWindowVisible(h)
        else None,
        None,
    )
    return out


def main():
    for h, clase, titulo in raices():
        print(f"raiz hwnd={h} clase={clase} titulo={titulo!r}")
        dlg = vigia.dialogo(h)
        if dlg:
            print(f"  DIALOGO: {dlg['titulo']!r} botones={list(dlg['botones'])}")
        else:
            print("  sin dialogo")
        try:
            img, vp = estado.captura(h)
        except Exception as exc:
            print(f"  captura fallo: {exc}")
            continue
        st = estado.clasificar(img)
        print(f"  viewport={vp['hwnd']} {vp['width']}x{vp['height']} off={vp['offset']}")
        ruta = native_shot.save(img, "sonda")
        print(f"  captura: {ruta}")
        print("  ESTADO " + json.dumps({
            "estado": st["estado"], "fuente": st["fuente"],
            "confianza": st["confianza"], "error": st.get("error"),
            "senales": st["senales"],
        }, ensure_ascii=False))
        texto = st.get("texto", "")
        print("  --- texto OCR (400 chars) ---")
        print(texto[:400])


if __name__ == "__main__":
    main()
