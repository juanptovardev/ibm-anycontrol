"""Preflight sin raton: navega el 5250 con teclado.

ESC deja el cursor en el primer campo de entrada (Nombre). Desde ahi:
Enter? no. Se usa Field Exit (+) para avanzar de campo.

  esc -> limpiar Nombre -> '+' -> limpiar Calle -> escribir p1 -> '+'
      -> limpiar No.Casa -> escribir p2 -> F10 -> Shift+F4

Uso: python tools/preflight_kbd.py <hwnd>
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd

PARTE1 = "CR 17B"
PARTE2 = "175-77"
ROW_NOMBRE, ROW_CALLE, ROW_CASA = 0, 1, 2
INK_LIMPIO = 10
DEL = ["delete"] * 60


async def _wipe(s, label: str) -> None:
    """Borra del cursor al final del campo. NO usar home: en 5250 home salta
    al primer campo del registro (Nombre), no al inicio del campo actual."""
    await pf.step(s, f"del_{label}", "press_keys", {"keys": DEL})


async def _sequence(s, hwnd: int) -> None:
    await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
    await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
    _, _, det = rowdet.detect(hwnd)

    await pf.keys(s, "esc", ["escape"])
    await _wipe(s, "nombre")
    await pf.step(s, "exit_nombre", "press_keys", {"keys": ["add"]})
    await _wipe(s, "calle")
    await pf.step(s, "write_p1", "write_to_anydesk", {"command": PARTE1})
    await pf.step(s, "exit_calle", "press_keys", {"keys": ["add"]})
    await _wipe(s, "casa")
    await pf.step(s, "write_p2", "write_to_anydesk", {"command": PARTE2})

    img = pf.shot(hwnd, "kbd-pre-f10")
    nombre, calle, casa = (pf.ink(img, det[i]) for i in (ROW_NOMBRE, ROW_CALLE, ROW_CASA))
    print(f"  tinta nombre={nombre} calle={calle} casa={casa}")
    if nombre > INK_LIMPIO:
        raise pf.Halt(f"Nombre no quedo vacio (tinta {nombre})")
    if calle <= pf.INK_MIN or casa <= pf.INK_MIN:
        raise pf.Halt("texto no quedo en Calle/No.Casa")

    await pf.keys(s, "f10", ["f10"])
    post = pf.shot(hwnd, "kbd-post-f10")
    diff = pf.changed_px(img, post)
    print(f"  diff f10 = {diff}px")
    if diff < pf.F10_MIN_DIFF:
        await pf.keys(s, "f10_retry", ["f10"])
        post = pf.shot(hwnd, "kbd-post-f10b")
        print(f"  diff f10 retry = {pf.changed_px(img, post)}px")

    await pf.keys(s, "shift_f4", ["shift", "f4"])
    pf.shot(hwnd, "kbd-post-shiftf4")


async def main(hwnd: int) -> int:
    try:
        async with connect() as s:
            try:
                await _sequence(s, hwnd)
            except pf.Halt as exc:
                print(f"DETENIDO: {exc}")
                return 1
    except BaseExceptionGroup as exc:
        raise exc
    print("OK: secuencia completa")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(need_hwnd(sys.argv))))
