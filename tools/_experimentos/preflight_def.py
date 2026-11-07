"""Preflight definitivo v3: ventana redimensionada (viewport 1255x663).

El usuario amplio la ventana para dar mas spacing entre filas. TODO
re-medido sobre mira-nueva (1255x663):
  Calle   y=168 (texto '175-77' highlighted, campo inicia x~460)
  No.Casa y=199 (texto '175-77CR 1', inicia x~463)
Nombre trae basura 'CR 17B' pero NO se toca (regla del usuario: no borrar
de mas; el F10 anterior fallo por la calle, no por Nombre... si el search
vuelve a quejarse, se limpia Nombre en el siguiente intento).
HALT: cualquier paso con error detiene la secuencia.
F10 con reintento unico si diff < 500 px.

Usage: python tools/preflight_def.py <hwnd> <parte1> <parte2>
"""
import asyncio
import sys
import time

import native_shot
from _mcp import REPO, call, connect, need_hwnd, report

sys.path.insert(0, REPO)
from mcp_anydesk_server import window_manager as W  # noqa: E402
from PIL import ImageChops  # noqa: E402

CALLE = (480, 168)
CASA = (490, 198)


class _Halt(Exception):
    pass


def snap(label):
    vp = W.find_viewport(HWND)
    img = native_shot.grab(vp["hwnd"])
    path = native_shot.save(img, label)
    print(f"shot {label}: {vp['hwnd']} -> {path}", flush=True)
    return img


def changed_px(a, b, tol=30):
    h = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L").histogram()
    return sum(h[tol + 1:])


async def do(s, label, name, args):
    rc = report(label, await call(s, name, args))
    if rc:
        raise _Halt(f"{label} fallo: secuencia detenida")
    return rc


async def main(hwnd: int, p1: str, p2: str) -> int:
    global HWND
    HWND = hwnd
    try:
        async with connect() as s:
            await do(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await do(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            await do(s, "esc", "press_keys", {"keys": ["esc"]})
            # Nombre NO se toca (trae basura vieja pero el search no se queja de el)
            # 1. Calle
            await do(s, "click_calle", "click_point", {"x": CALLE[0], "y": CALLE[1]})
            await do(s, "seat", "press_keys", {"keys": ["left", "right", "home"]})
            await do(s, "clear_calle", "press_keys", {"keys": ["delete"] * 8})
            await do(s, "write_calle", "write_to_anydesk", {"command": p1, "wrap": False})
            await do(s, "plus1", "press_keys", {"keys": ["add"]})
            # 2. No.Casa (clic explicito: el auto-avance del + no es de fiar)
            await do(s, "click_casa", "click_point", {"x": CASA[0], "y": CASA[1]})
            await do(s, "seat2", "press_keys", {"keys": ["left", "right", "home"]})
            await do(s, "clear_casa", "press_keys", {"keys": ["delete"] * 12})
            await do(s, "write_casa", "write_to_anydesk", {"command": p2, "wrap": False})
            await do(s, "plus2", "press_keys", {"keys": ["add"]})
            # 3. F10 con reintento unico por diff
            pre = await asyncio.to_thread(snap, "pre-f10")
            await do(s, "f10", "press_keys", {"keys": ["f10"]})
            await asyncio.sleep(1.2)
            post = await asyncio.to_thread(snap, "post-f10a")
            n = await asyncio.to_thread(changed_px, pre, post)
            print(f"diff f10a: {n} px", flush=True)
            if n < 500:
                print("f10 sin efecto visible: reintento unico", flush=True)
                await do(s, "f10_retry", "press_keys", {"keys": ["f10"]})
                await asyncio.sleep(1.2)
                post = await asyncio.to_thread(snap, "post-f10b")
                n = await asyncio.to_thread(changed_px, pre, post)
                print(f"diff f10b: {n} px", flush=True)
            # 4. Shift+F4
            await do(s, "shift_f4", "press_keys", {"keys": ["shift", "f4"]})
            await asyncio.sleep(1.2)
            await asyncio.to_thread(snap, "post-shiftf4")
    except _Halt as exc:
        print(str(exc), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=" <parte1> <parte2>")
    if len(sys.argv) < 4:
        print("usage: preflight_def.py <hwnd> <parte1> <parte2>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2], sys.argv[3])))
