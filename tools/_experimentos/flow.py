"""Ciclo normal, sin capturas ni preflight:
UN clic en celda 1 de Calle -> derecha -> izquierda -> step1 -> '+' -> step2 -> '+' -> F10 -> Shift+F4.

Uso: python tools/flow.py <hwnd>

Un solo clic a proposito: el doble clic selecciona TODO el campo (barra cyan) en
vez de dejar el cursor en la celda 1, y entonces las flechas y la escritura no
arrancan donde deben. Para el ciclo con medicion usar paso1.py + paso2.py.
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd

PARTE1 = "CR 17B"
PARTE2 = "175-77"


async def main(hwnd: int) -> int:
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        _, _, det = rowdet.detect(hwnd)
        calle = det[1]
        punto = {"x": calle["field_x"] + 2, "y": calle["cy"]}
        await pf.step(s, "clic_celda1", "click_point", punto)
        await asyncio.sleep(0.2)
        await pf.step(s, "derecha", "press_keys", {"keys": ["right"]})
        await pf.step(s, "izquierda", "press_keys", {"keys": ["left"]})
        await pf.step(s, "step1", "write_to_anydesk", {"command": PARTE1})
        await pf.step(s, "plus1", "press_keys", {"keys": ["add"]})
        await pf.step(s, "step2", "write_to_anydesk", {"command": PARTE2})
        await pf.step(s, "plus2", "press_keys", {"keys": ["add"]})
        await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
        await pf.step(s, "shift_f4", "press_keys", {"keys": ["shift", "f4"]})
    print("OK: ciclo completo")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(need_hwnd(sys.argv))))
