"""Pinea ventana + captura screenshot a disco. Read-only: no inyecta teclas."""
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
    tag = sys.argv[2] if len(sys.argv) > 2 else "p1"
    params = StdioServerParameters(command=PY, args=["-m", "mcp_anydesk_server"], cwd=REPO)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await call(session, "select_anydesk_window", {"hwnd": hwnd})
            print("PIN:", json.dumps(r, ensure_ascii=False)[:300])
            r = await call(session, "initialize_session")
            print("INIT:", json.dumps(r, ensure_ascii=False)[:300])
            r = await call(session, "capture_screenshot", {"scale_percent": 100})
            print("SHOT:", json.dumps(r, ensure_ascii=False)[:500])
            print("TAG:", tag)


asyncio.run(main())
