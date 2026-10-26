"""Read-only: disable focus-click, pin the window, print geometry.

Sends no keyboard or mouse input. Must run in ONE MCP session: the pin is
process-local, so pinning and clicking have to happen together.

Usage: python tools/geo.py [hwnd]
"""
import asyncio
import sys

from _mcp import call, connect, need_hwnd, report


async def main(hwnd: int) -> int:
    rc = 0
    async with connect() as s:
        # BEFORE pinning: select/pin focuses the window, and with the click
        # still enabled that would move the remote cursor to screen centre.
        rc |= report("focus_click_off", await call(s, "set_focus_click_mode", {"enabled": False}))
        rc |= report("pin", await call(s, "select_anydesk_window", {"hwnd": hwnd}))
        res = await call(s, "geometry")
        rc |= report("geometry", res, limit=2000)
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main(need_hwnd(sys.argv))))
