"""Pinea ventana + captura screenshot a disco. Read-only: no inyecta teclas."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _mcp import call, connect, need_hwnd, report


async def main():
    hwnd = need_hwnd(sys.argv, extra=" [tag]")
    tag = sys.argv[2] if len(sys.argv) > 2 else "p1"
    failed = 0
    async with connect() as session:
        failed |= report("PIN", await call(session, "select_anydesk_window", {"hwnd": hwnd}), limit=300)
        if failed:
            sys.exit(failed)
        failed |= report("INIT", await call(session, "initialize_session"), limit=300)
        if failed:
            sys.exit(failed)
        failed |= report("SHOT", await call(session, "capture_screenshot", {"scale_percent": 100}), limit=500)
        print("TAG:", tag)
    sys.exit(failed)


asyncio.run(main())
