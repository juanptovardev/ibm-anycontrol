"""Shared MCP stdio helper for matriz-ibm-agent live tools (read-only + pilot).

All scripts import from here: repo path (env-overridable), tool-call
wrapper, stdio connect helper, hwnd parsing, and failure reporting with
real exit codes so the agent loop can detect failed calls.
"""
import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.environ.get(
    "MCP_ANYDESK_REPO", r"C:\Users\juanp_8h8f07l\dev\mcp-anydesk"
)
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")


async def call(session, name, args=None):
    """Call one MCP tool. Returns {"isError": bool, "text": str}."""
    res = await session.call_tool(name, args or {})
    texts = [c.text for c in res.content if getattr(c, "text", None)]
    return {"isError": res.isError, "text": "\n".join(texts)}


@asynccontextmanager
async def connect():
    """Yield an initialized MCP session over stdio."""
    params = StdioServerParameters(
        command=PY, args=["-m", "mcp_anydesk_server"], cwd=REPO
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def need_hwnd(argv, pos=1, extra=""):
    """Parse hwnd from argv or MCP_ANYDESK_HWND. Usage error -> exit 2."""
    raw = argv[pos] if len(argv) > pos else os.environ.get("MCP_ANYDESK_HWND", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        print(f"usage: {argv[0]} <hwnd>{extra}  (o MCP_ANYDESK_HWND)", file=sys.stderr)
        sys.exit(2)


def report(label, result, limit=900):
    """Print a call result (full text on error, truncated on success).

    Returns 1 on failure, 0 on success — accumulate and sys.exit at the end.
    """
    text = result.get("text", "")
    if result.get("isError"):
        print(f"{label} FAILED: {text}", file=sys.stderr)
        return 1
    shown = text if len(text) <= limit else text[:limit] + "...[truncado]"
    print(f"{label}: {shown}")
    return 0
