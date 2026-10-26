"""OCR read-only de la ventana pineada. No inyecta nada."""
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
            r = await call(session, "read_from_anydesk", {"mode": "ocr"})
            print(json.dumps(r, ensure_ascii=False)[:3000])


asyncio.run(main())
