"""OCR read-only de la ventana pineada. No inyecta nada."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _mcp import call, connect, need_hwnd, report


async def main():
    hwnd = need_hwnd(sys.argv)
    failed = 0
    async with connect() as session:
        failed |= report("PIN", await call(session, "select_anydesk_window", {"hwnd": hwnd}), limit=300)
        if failed:
            sys.exit(failed)
        failed |= report("INIT", await call(session, "initialize_session"), limit=300)
        if failed:
            sys.exit(failed)
        failed |= report("OCR", await call(session, "read_from_anydesk", {"mode": "ocr"}), limit=3000)
    sys.exit(failed)


asyncio.run(main())
