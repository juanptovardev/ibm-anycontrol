"""Fix Calle leading blanks: clear field, rewrite from field start.

Calle currently holds blanks + "CR 17B" (typed from mid-field). This clicks
the field end, backspaces 30x (covers blanks+text; overrun into the empty
Nombre field is harmless), clicks field start, retypes. No.Casa untouched.

Usage: python tools/fix_calle.py <hwnd> <calle>
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report

CALLE_END = (775, 113)
CALLE_START = (455, 113)


async def main(hwnd: int, calle: str) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("click_end", await call(s, "click_point", {"x": CALLE_END[0], "y": CALLE_END[1]}))
        rc |= report("clear", await call(s, "press_keys", {"keys": ["backspace"] * 30}))
        rc |= report("click_start", await call(s, "click_point", {"x": CALLE_START[0], "y": CALLE_START[1]}))
        rc |= report("write", await call(s, "write_to_anydesk", {"command": calle, "wrap": False}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=' <calle>')
    if len(sys.argv) < 3:
        print("usage: fix_calle.py <hwnd> <calle>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2])))
