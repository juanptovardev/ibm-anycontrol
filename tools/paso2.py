"""Paso 2 verificado: '+' -> parte2 -> '+' -> F10 -> Shift+F4, midiendo cada salto.

Se usa despues de paso1.py (Calle ya escrita y verificada). Corta si la tinta no
aparece donde debe: nunca pulsa F10 con el texto en el campo equivocado.

Uso: python tools/paso2.py <hwnd> [parte2]
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd
from paso1 import CASA, CALLE, NOMBRE, tinta

PARTE2 = "175-77"


async def main(hwnd: int, parte2: str) -> int:
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        _, _, det = rowdet.detect(hwnd)
        await pf.step(s, "plus1", "press_keys", {"keys": ["add"]})
        await pf.step(s, "escribir2", "write_to_anydesk", {"command": parte2})
        img = pf.shot(hwnd, "paso2")
        m = {n: tinta(img, det[i]) for i, n in ((NOMBRE, "nombre"), (CALLE, "calle"), (CASA, "casa"))}
        print("tinta: " + " ".join(f"{k}={v}" for k, v in m.items()))
        if m["casa"] <= pf.INK_MIN:
            print("FALLO: la parte2 no quedo en No.Casa")
            return 1
        if m["calle"] <= pf.INK_MIN:
            print("FALLO: Calle se vacio al avanzar con '+'")
            return 1
        await pf.step(s, "plus2", "press_keys", {"keys": ["add"]})
        pre = pf.shot(hwnd, "paso2-pre-f10")
        await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
        await asyncio.sleep(0.6)
        post = pf.shot(hwnd, "paso2-post-f10")
        diff = pf.changed_px(pre, post)
        print(f"diff_f10={diff}")
        if diff < pf.F10_MIN_DIFF:
            # La primera pulsacion tras recuperar foco puede perderse: 1 reintento.
            print("F10 sin efecto: reintento unico")
            await pf.step(s, "f10b", "press_keys", {"keys": ["f10"]})
            await asyncio.sleep(0.6)
            post = pf.shot(hwnd, "paso2-post-f10b")
            diff = pf.changed_px(pre, post)
            print(f"diff_f10b={diff}")
            if diff < pf.F10_MIN_DIFF:
                print("FALLO: F10 no produjo cambio de pantalla")
                return 1
        await pf.step(s, "shift_f4", "press_keys", {"keys": ["shift", "f4"]})
        await asyncio.sleep(0.6)
        pf.shot(hwnd, "paso2-post-shiftf4")
        print("shift+f4 pulsado")
    return 0


if __name__ == "__main__":
    argv = sys.argv
    sys.exit(asyncio.run(main(need_hwnd(argv), argv[2] if len(argv) > 2 else PARTE2)))
