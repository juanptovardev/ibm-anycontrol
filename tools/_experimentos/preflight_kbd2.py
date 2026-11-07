"""Preflight sin raton y sin borrados: exige formulario limpio.

Camino 5250 puro, sin clics ni deletes:
  esc -> '+' (avanza a Calle) -> escribir parte1 -> '+' (avanza a No.Casa)
      -> escribir parte2 -> F10 -> Shift+F4

Si Nombre/Calle/No.Casa no estan vacios al empezar, se detiene sin teclear:
no hay forma fiable de borrar en este emulador (delete no borra y home salta
al primer campo del registro).

Uso: python tools/preflight_kbd2.py <hwnd>
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd

PARTE1 = "CR 17B"
PARTE2 = "175-77"
ROW_NOMBRE, ROW_CALLE, ROW_CASA = 0, 1, 2
INK_SUCIO = 15


async def _sequence(s, hwnd: int) -> None:
    await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
    await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
    img, _, det = rowdet.detect(hwnd)
    if len(det) < 8:
        raise pf.Halt(f"no es el formulario ({len(det)} filas detectadas)")

    sucio = {n: pf.ink(img, det[i]) for n, i in
             (("nombre", ROW_NOMBRE), ("calle", ROW_CALLE), ("casa", ROW_CASA))}
    print(f"  previo: {sucio}")
    if any(v > INK_SUCIO for v in sucio.values()):
        raise pf.Halt("formulario sucio: no puedo borrar, limpialo y avisame")

    await pf.keys(s, "esc", ["escape"])
    await pf.step(s, "exit_nombre", "press_keys", {"keys": ["add"]})
    await pf.step(s, "write_p1", "write_to_anydesk", {"command": PARTE1})
    await pf.step(s, "exit_calle", "press_keys", {"keys": ["add"]})
    await pf.step(s, "write_p2", "write_to_anydesk", {"command": PARTE2})
    await pf.step(s, "exit_casa", "press_keys", {"keys": ["add"]})

    img = pf.shot(hwnd, "kbd2-pre-f10")
    nombre, calle, casa = (pf.ink(img, det[i]) for i in (ROW_NOMBRE, ROW_CALLE, ROW_CASA))
    print(f"  tinta nombre={nombre} calle={calle} casa={casa}")
    if nombre > INK_SUCIO:
        raise pf.Halt(f"texto cayo en Nombre (tinta {nombre})")
    if calle <= pf.INK_MIN or casa <= pf.INK_MIN:
        raise pf.Halt("texto no quedo en Calle/No.Casa")

    await pf.keys(s, "f10", ["f10"])
    post = pf.shot(hwnd, "kbd2-post-f10")
    diff = pf.changed_px(img, post)
    print(f"  diff f10 = {diff}px")
    if diff < pf.F10_MIN_DIFF:
        await pf.keys(s, "f10_retry", ["f10"])
        post = pf.shot(hwnd, "kbd2-post-f10b")
        print(f"  diff f10 retry = {pf.changed_px(img, post)}px")

    await pf.keys(s, "shift_f4", ["shift", "f4"])
    pf.shot(hwnd, "kbd2-post-shiftf4")


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
