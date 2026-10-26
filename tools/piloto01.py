"""PILOTO-01 pasos 1-2 (aprobado por operador en chat 2026-10-26).
CR 17B -> verifica -> [+] numpad -> 175-77 -> verifica + OCR.
No presiona Enter en ningun punto. Falla con exit!=0 si un paso falla."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _mcp import call, connect, need_hwnd, report


async def main():
    hwnd = need_hwnd(sys.argv)
    failed = 0
    async with connect() as session:
        for label, name, args, limit in [
            ("PIN", "select_anydesk_window", {"hwnd": hwnd}, 300),
            ("INIT", "initialize_session", None, 300),
            ("WRITE1", "write_to_anydesk", {"command": "CR 17B", "wrap": False}, 300),
            ("SHOT_A", "capture_screenshot", {"scale_percent": 100}, 400),
            ("PLUS", "press_keys", {"keys": ["add"]}, 300),
            ("WRITE2", "write_to_anydesk", {"command": "175-77", "wrap": False}, 300),
            ("SHOT_B", "capture_screenshot", {"scale_percent": 100}, 400),
            ("OCR", "read_from_anydesk", {"mode": "ocr"}, 1200),
        ]:
            failed |= report(label, await call(session, name, args), limit=limit)
            if failed:
                break
    sys.exit(failed)


asyncio.run(main())
