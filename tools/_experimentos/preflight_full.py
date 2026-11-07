"""Preflight completo sin borrado: click Calle + seat + write + add + write + add + F10 + Shift+F4.

Los writes repiten los valores ya en pantalla (modo reemplazo desde el
inicio del campo = idempotente). Sin deletes, sin esc: el operador prohibio
borrar. Todo en UNA sesion MCP (pin + override son process-local).

Usage: python tools/preflight_full.py <hwnd> <parte1> <parte2>
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report


async def main(hwnd: int, p1: str, p2: str) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("click_calle", await call(s, "click_point", {"x": 450, "y": 113}))
        rc |= report("seat", await call(s, "press_keys", {"keys": ["left", "right"]}))
        rc |= report("write_calle", await call(s, "write_to_anydesk", {"command": p1, "wrap": False}))
        rc |= report("plus1", await call(s, "press_keys", {"keys": ["add"]}))
        rc |= report("write_casa", await call(s, "write_to_anydesk", {"command": p2, "wrap": False}))
        rc |= report("plus2", await call(s, "press_keys", {"keys": ["add"]}))
        rc |= report("f10", await call(s, "press_keys", {"keys": ["f10"]}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=" <parte1> <parte2>")
    if len(sys.argv) < 4:
        print("usage: preflight_full.py <hwnd> <parte1> <parte2>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2], sys.argv[3])))
