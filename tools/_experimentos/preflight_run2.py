"""Preflight retry: reset, clear the stray text, fill both fields.

What went wrong in run 1: click Y-coords were ~15px low (eyeballed from a
zoom). click_calle(450,132) actually hit No.Casa, so "CR 17B" landed there;
click_casa(480,150) hit a protected row -> inhibited keyboard (X) + error.

This run uses scanned underline rows (field_scan.py): Nombre 104,
Calle 119, No.Casa 134. Clicks aim at text-row centre (underline - 6).

Sequence (one MCP session): esc (Reset: unlock + clear error) ->
click end of No.Casa -> 6x backspace (delete "CR 17B") -> click Calle ->
write parte1 -> add (+) -> write parte2. NO search yet.

Usage: python tools/preflight_run2.py <hwnd> <calle> <nocasa>
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report

CALLE = (600, 113)
CASA_END = (500, 128)


async def main(hwnd: int, calle: str, nocasa: str) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("reset", await call(s, "press_keys", {"keys": ["esc"]}))
        rc |= report("click_casa_end", await call(s, "click_point", {"x": CASA_END[0], "y": CASA_END[1]}))
        rc |= report("clear_casa", await call(s, "press_keys", {"keys": ["backspace"] * 6}))
        rc |= report("click_calle", await call(s, "click_point", {"x": CALLE[0], "y": CALLE[1]}))
        rc |= report("write_calle", await call(s, "write_to_anydesk", {"command": calle, "wrap": False}))
        rc |= report("plus", await call(s, "press_keys", {"keys": ["add"]}))
        rc |= report("write_casa", await call(s, "write_to_anydesk", {"command": nocasa, "wrap": False}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=' <calle> <nocasa>')
    if len(sys.argv) < 4:
        print("usage: preflight_run2.py <hwnd> <calle> <nocasa>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2], sys.argv[3])))
