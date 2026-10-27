"""Press special keys on the pinned AnyDesk window, in ONE MCP session.

Why one session: the pin and the focus-click override are process-local, so
disabling the auto-click and pressing must happen in the same server
process. Without the override, focus_and_verify() clicks the window centre
on every call and the keystrokes land in the wrong field (PILOTO-01).

Sends input. Requires operator approval per the hard rules.

Usage: python tools/press_step.py <hwnd> <key> [key...]
Example: python tools/press_step.py 198526 f10
         python tools/press_step.py 198526 shift f4
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report


async def main(hwnd: int, keys: list) -> int:
    rc = 0
    async with connect() as s:
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        rc |= report("press", await call(s, "press_keys", {"keys": keys}))
    return rc


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=" <key> [key...]")
    pressed = sys.argv[2:]
    if not pressed:
        print("usage: press_step.py <hwnd> <key> [key...]", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(window, pressed)))
