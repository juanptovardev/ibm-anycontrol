"""Captura read-only del estado AnyDesk: lista ventanas + health. No inyecta nada."""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk"
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")


async def call(session, name, args=None):
    res = await session.call_tool(name, args or {})
    texts = [c.text for c in res.content if getattr(c, "text", None)]
    return {"isError": res.isError, "text": "\n".join(texts)}


async def main():
    params = StdioServerParameters(command=PY, args=["-m", "mcp_anydesk_server"], cwd=REPO)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for n in ["select_anydesk_window", "check_health"]:
                r = await call(session, n)
                print(f"--- {n} ---")
                print(json.dumps(r, ensure_ascii=False)[:900])


asyncio.run(main())
