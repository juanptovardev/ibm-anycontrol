"""Arranque en frio: F12 hasta el inicio, login, formulario, prellenado, F10, Shift+F4.

Reproduce el flujo completo como si acabara de loguearse.

Uso:
    python tools/arranque.py 132724 <usuario> <clave>
    python tools/arranque.py 132724 <usuario> <clave> --f12 6
    python tools/arranque.py 132724 <usuario> <clave> --sin-login
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight_auto as pf
import login as L
import nav_prefill as NP
from _mcp import connect
from estado import clasificar, ocr_text

ESPERA = 0.8


def es_login(img):
    t = ocr_text(img).lower()
    return "usuario" in t or "clave" in t


def estado_de(img):
    r = clasificar(img, usar_jev=False)
    print(f"  -> estado={r.get('estado')} conf={r.get('confianza')}")
    return r


async def atras(hwnd, veces):
    """F12 cancela pantallas; cuando ya no hace nada (menu) se usa F2 (salir)."""
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        img = pf.shot(hwnd, "arranque-0")
        if es_login(img):
            print("  ya en login")
            return img
        for i in range(veces):
            await pf.step(s, f"f12_{i + 1}", "press_keys", {"keys": ["f12"]})
            await asyncio.sleep(ESPERA)
            img = pf.shot(hwnd, f"f12-{i + 1}")
            if es_login(img):
                print(f"  login tras f12 x{i + 1}")
                return img
            await pf.step(s, f"f2_{i + 1}", "press_keys", {"keys": ["f2"]})
            await asyncio.sleep(ESPERA + 0.4)
            img = pf.shot(hwnd, f"f2-{i + 1}")
            if es_login(img):
                print(f"  login tras f12+f2 x{i + 1}")
                return img
        return img


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        print("uso: arranque.py <hwnd> <usuario> <clave> [--f12 N] [--sin-login]",
              file=sys.stderr)
        return 2
    hwnd = int(args[0])
    usuario, clave = args[1], args[2]
    veces = 5
    for a in argv:
        if a.startswith("--f12="):
            veces = int(a.split("=", 1)[1])

    img = asyncio.run(atras(hwnd, veces))
    r = estado_de(img)

    ya_logueado = r.get("estado") is not None
    if not ya_logueado and "--sin-login" not in argv:
        print("  login:")
        code = asyncio.run(L._run(hwnd, usuario, clave, False))
        if code != 0:
            print("  login fallo")
            return code
    elif ya_logueado:
        print("  ya habia sesion: no se reloguea")

    print("  formulario:")
    return asyncio.run(NP._run(None, hwnd, "CR 17B", "175-77", True, False, 0, False))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
