"""Retry Calle with the operator's glitch trick.

The 5250 client mis-seats the cursor after a click: always press
left-arrow then right-arrow before typing. Numpad "+" (add) auto-jumps
Calle -> No.Casa. Delete clears from cursor, so 30x from field start
wipes the stale text regardless of what is there.

Sequence: esc -> click Calle start -> left,right -> delete x30 ->
write calle -> add -> write casa. No F-keys here; caller verifies
with a capture before firing F10.

Usage: python tools/retry_calle.py <hwnd> <calle> <casa>
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report

CALLE_START = (450, 113)


async def main(hwnd: int, calle: str, casa: str) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("reset", await call(s, "press_keys", {"keys": ["esc"]}))
        rc |= report("click_calle", await call(s, "click_point", {"x": CALLE_START[0], "y": CALLE_START[1]}))
        rc |= report("seat", await call(s, "press_keys", {"keys": ["left", "right"]}))
        rc |= report("clear", await call(s, "press_keys", {"keys": ["delete"] * 30}))
        rc |= report("write_calle", await call(s, "write_to_anydesk", {"command": calle, "wrap": False}))
        rc |= report("plus", await call(s, "press_keys", {"keys": ["add"]}))
        rc |= report("write_casa", await call(s, "write_to_anydesk", {"command": casa, "wrap": False}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=" <calle> <casa>")
    if len(sys.argv) < 4:
        print("usage: retry_calle.py <hwnd> <calle> <casa>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, sys.argv[2], sys.argv[3])))
