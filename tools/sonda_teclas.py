"""Sonda de teclas: pulsa una secuencia y captura+clasifica tras cada tecla.

Sirve para mapear la navegacion de menus del 5250 sin adivinar: se ve que
pantalla aparece tras cada pulsacion.

Uso: python tools/sonda_teclas.py <hwnd> 1 enter escape 1 enter
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import native_shot
import preflight_auto as pf
from _mcp import connect, need_hwnd


async def main(hwnd: int, teclas: list[str]) -> int:
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        for i, t in enumerate(teclas, 1):
            if t == "enter":
                await pf.step(s, f"k{i}_enter", "press_enter", {})
            else:
                await pf.step(s, f"k{i}_{t}", "press_keys", {"keys": [t]})
            await asyncio.sleep(1.1)
            img = pf.shot(hwnd, f"sonda-tecla-{i}-{t}")
            import estado
            r = estado.clasificar(img, usar_jev=False)
            print(f"[{i}] {t:<10} estado={r['estado']} conf={r['confianza']} "
                  f"err={r.get('error')}", flush=True)
            texto = (r.get("texto") or "").replace("\n", " | ")
            print(f"      {texto[:220]}", flush=True)
    return 0


if __name__ == "__main__":
    h = need_hwnd(sys.argv)
    teclas = sys.argv[2:]
    sys.exit(asyncio.run(main(h, teclas)))
