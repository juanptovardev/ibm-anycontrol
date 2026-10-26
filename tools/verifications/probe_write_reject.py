"""Probe: verify write_to_anydesk rejects newlines BEFORE focus/injection.

Safe: validation happens before focus_and_verify, so nothing is injected
and no window is touched. Exit 0 = constraint holds live. Exit 1 = FAIL.
Single exit mechanism: main() returns bool, SystemExit only at module level.
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.environ.get(
    "MCP_ANYDESK_REPO", r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")


async def main():
    if not os.path.isfile(PY):
        print(json.dumps({"probe_pass": False,
                          "error": f"venv python missing: {PY}"}))
        return False
    params = StdioServerParameters(
        command=PY, args=["-m", "mcp_anydesk_server"], cwd=REPO)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool(
                "write_to_anydesk", {"command": "PARTE1\nPARTE2"})
            texts = [c.text for c in res.content if getattr(c, "text", None)]
            if not texts:
                print(json.dumps({"probe_pass": False,
                                  "error": "empty tool content"}))
                return False
            try:
                data = json.loads(texts[0])
            except ValueError:
                print(json.dumps({"probe_pass": False,
                                  "raw": texts[0][:200]}))
                return False
            ok = (data.get("status") == "error"
                  and "Multi-line" in data.get("note", "")
                  and data.get("char_count") == 0
                  and data.get("elapsed_ms") == 0)
            print(json.dumps({"probe_pass": ok, **data}, ensure_ascii=False))
            return ok


raise SystemExit(0 if asyncio.run(main()) else 1)
