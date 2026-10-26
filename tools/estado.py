"""Captura read-only del estado AnyDesk: lista ventanas + health. No inyecta nada."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _mcp import call, connect, report


async def main():
    failed = 0
    async with connect() as session:
        for n in ["select_anydesk_window", "check_health"]:
            failed |= report(n, await call(session, n))
    sys.exit(failed)


asyncio.run(main())
