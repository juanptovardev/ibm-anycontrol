"""Envia una tecla al 5250 pineado (una sola, con auditoria del server).

Uso:
    python tools/tecla.py <hwnd> enter
    python tools/tecla.py <hwnd> f3
    python tools/tecla.py <hwnd> shift f4
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight_auto as pf  # noqa: E402
from _mcp import connect, need_hwnd  # noqa: E402


async def _run(hwnd, teclas):
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        if teclas == ["enter"]:
            await pf.step(s, "enter", "press_enter", {})
        else:
            await pf.step(s, "teclas", "press_keys", {"keys": teclas})
        pf.shot(hwnd, "tecla-" + "_".join(teclas))
    return 0


def main(argv):
    hwnd = need_hwnd(argv, pos=1)
    return asyncio.run(_run(hwnd, [a.lower() for a in argv[2:]]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
