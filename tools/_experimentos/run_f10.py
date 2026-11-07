"""Cierra el formulario ya escrito: '+' -> F10 -> Shift+F4.

No escribe, no borra, no hace clic. Solo valida que Calle y No.Casa ya tengan
contenido y que Nombre este vacio; despues dispara la busqueda.

Uso: python tools/run_f10.py <hwnd>
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd

ROW_NOMBRE, ROW_CALLE, ROW_CASA = 0, 1, 2
INK_SUCIO = 15


async def _sequence(s, hwnd: int) -> None:
    await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
    await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
    pre, _, det = rowdet.detect(hwnd)
    if len(det) < 8:
        raise pf.Halt(f"no es el formulario ({len(det)} filas)")

    nombre, calle, casa = (pf.ink(pre, det[i]) for i in (ROW_NOMBRE, ROW_CALLE, ROW_CASA))
    print(f"  estado: nombre={nombre} calle={calle} casa={casa}")
    if nombre > INK_SUCIO:
        raise pf.Halt("Nombre tiene texto: F10 intentaria Buscar Nombre")
    if calle <= pf.INK_MIN or casa <= pf.INK_MIN:
        raise pf.Halt("Calle/No.Casa vacios: primero hay que escribirlos")

    await pf.step(s, "exit_casa", "press_keys", {"keys": ["add"]})
    await pf.keys(s, "f10", ["f10"])
    post = pf.shot(hwnd, "f10-post")
    diff = pf.changed_px(pre, post)
    print(f"  diff f10 = {diff}px")
    if diff < pf.F10_MIN_DIFF:
        await pf.keys(s, "f10_retry", ["f10"])
        post = pf.shot(hwnd, "f10-post-b")
        print(f"  diff f10 retry = {pf.changed_px(pre, post)}px")

    await pf.keys(s, "shift_f4", ["shift", "f4"])
    pf.shot(hwnd, "f10-post-shiftf4")


async def main(hwnd: int) -> int:
    async with connect() as s:
        try:
            await _sequence(s, hwnd)
        except pf.Halt as exc:
            print(f"DETENIDO: {exc}")
            return 1
    print("OK: secuencia completa")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(need_hwnd(sys.argv))))
