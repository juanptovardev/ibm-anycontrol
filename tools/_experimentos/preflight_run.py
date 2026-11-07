"""Preflight: fill Calle + No.Casa on the CONSULTA form, in ONE MCP session.

Approved by the operator for the supervised preflight run. Does NOT search
(F10) and does NOT advance — those come after visual verification.

Coordinates are viewport-relative (click_point origin = viewport child).
From the 1:1 field map (native 1022x471): Calle input y~=132, No.Casa y~=150.

Usage: python tools/preflight_run.py <hwnd> <calle> <nocasa>
Example: python tools/preflight_run.py 198526 "CR 17B" "175-77"
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report

CALLE = (450, 132)
NOCASA = (480, 150)


async def main(hwnd: int, calle: str, nocasa: str) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("click_calle", await call(s, "click_point", {"x": CALLE[0], "y": CALLE[1]}))
        rc |= report("write_calle", await call(s, "write_to_anydesk", {"command": calle, "wrap": False}))
        rc |= report("plus", await call(s, "press_keys", {"keys": ["add"]}))
        rc |= report("click_casa", await call(s, "click_point", {"x": NOCASA[0], "y": NOCASA[1]}))
        rc |= report("write_casa", await call(s, "write_to_anydesk", {"command": nocasa, "wrap": False}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=' <calle> <nocasa>')
    if len(sys.argv) < 4:
        print("usage: preflight_run.py <hwnd> <calle> <nocasa>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2], sys.argv[3])))
