"""Calibra el mapeo clic -> fila del 5250 escribiendo un caracter de prueba.

Clic en (field_x+20, y objetivo), seat der/izq, home, escribe UN caracter y
captura: se mide en que fila quedo la tinta. Sirve para descubrir el desfase
que mete AnyDesk entre el pixel local y el pixel remoto.

Uso: python tools/calib.py <hwnd> <y_objetivo> [caracter]
"""
import asyncio
import sys

import native_shot
import preflight_auto as pf
import rows as rowdet
from _mcp import call, connect, need_hwnd

DELAY_SHOT = 0.4


async def main(hwnd: int, y: int, ch: str) -> int:
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        _, vp, det = rowdet.detect(hwnd)
        fx = det[1]["field_x"]
        print("filas:", [(i, r["cy"]) for i, r in enumerate(det)])
        await pf.step(s, "click", "click_point", {"x": fx + 20, "y": y})
        await pf.step(s, "seat", "press_keys", {"keys": ["right", "left"]})
        await pf.step(s, "home", "press_keys", {"keys": ["home"]})
        await pf.step(s, "write", "write_to_anydesk", {"command": ch})
        await asyncio.sleep(DELAY_SHOT)
        img = pf.shot(hwnd, f"calib-y{y}")
        print(f"objetivo y={y}")
        for i, r in enumerate(det):
            print(f"  fila {i} cy={r['cy']} tinta={pf.ink(img, r)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: calib.py <hwnd> <y> [char]", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(need_hwnd(sys.argv), int(sys.argv[2]),
                              sys.argv[3] if len(sys.argv) > 3 else "9")))
