"""PILOTO-01 pasos 1-2 (aprobado por operador en chat 2026-10-26).
CR 17B -> verifica -> [+] numpad -> 175-77 -> verifica + OCR.
No presiona Enter en ningun punto."""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk"
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")


async def call(session, name, args=None):
    res = await session.call_tool(name, args or {})
    texts = [c.text for c in res.content if getattr(c, "text", None)]
    return {"isError": res.isError, "text": "\n".join(texts)}


async def main():
    hwnd = int(sys.argv[1]) if len(sys.argv) > 1 else 198526
    params = StdioServerParameters(command=PY, args=["-m", "mcp_anydesk_server"], cwd=REPO)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await call(session, "select_anydesk_window", {"hwnd": hwnd})
            await call(session, "initialize_session")

            r = await call(session, "write_to_anydesk", {"command": "CR 17B", "wrap": False})
            print("WRITE1:", json.dumps(r, ensure_ascii=False)[:300])
            r = await call(session, "capture_screenshot", {"scale_percent": 100})
            print("SHOT_A:", json.dumps(r, ensure_ascii=False)[:400])

            r = await call(session, "press_keys", {"keys": ["add"]})
            print("PLUS:", json.dumps(r, ensure_ascii=False)[:300])

            r = await call(session, "write_to_anydesk", {"command": "175-77", "wrap": False})
            print("WRITE2:", json.dumps(r, ensure_ascii=False)[:300])
            r = await call(session, "capture_screenshot", {"scale_percent": 100})
            print("SHOT_B:", json.dumps(r, ensure_ascii=False)[:400])
            r = await call(session, "read_from_anydesk", {"mode": "ocr"})
            print("OCR:", json.dumps(r, ensure_ascii=False)[:1200])


asyncio.run(main())
