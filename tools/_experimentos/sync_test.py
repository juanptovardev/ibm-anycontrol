"""Prueba de sincronizacion de portapapeles local -> remoto.

paso 1: Alt+Tab y captura (para ubicar una celda vacia)
paso 2: pone el marcador en el portapapeles LOCAL, clic en (x,y) y Ctrl+V

Uso:
    python tools/_experimentos/sync_test.py <hwnd> --paso1
    python tools/_experimentos/sync_test.py <hwnd> --paso2 900 300
"""
import asyncio
import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import preflight_auto as pf  # noqa: E402
from _mcp import connect, need_hwnd  # noqa: E402

MARCA = "PRUEBA-SYNC-123"
CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def pon_clipboard(texto: str) -> bool:
    datos = ctypes.create_unicode_buffer(texto)
    tam = ctypes.sizeof(datos)
    h = kernel32.GlobalAlloc(0x0042, tam)
    if not h:
        return False
    ptr = kernel32.GlobalLock(h)
    ctypes.memmove(ptr, datos, tam)
    kernel32.GlobalUnlock(ctypes.c_void_p(h))
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        return bool(user32.SetClipboardData(CF_UNICODETEXT, h))
    finally:
        user32.CloseClipboard()


async def _run(hwnd, paso, xy):
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        await pf.step(s, "alt_tab", "press_keys", {"keys": ["alt", "tab"]})
        pf.shot(hwnd, "sync-paso1")
        if paso == 1:
            print("paso1 listo: revisa la captura")
            return 0
        print("clipboard local:", pon_clipboard(MARCA), repr(MARCA))
        await pf.step(s, "clic", "click_point", {"x": xy[0], "y": xy[1]})
        await pf.step(s, "ctrl_v", "paste_clipboard", {})
        pf.shot(hwnd, "sync-paso2")
        print("paso2 listo: revisa si aparece", MARCA)
    return 0


def main(argv):
    hwnd = need_hwnd(argv, pos=1)
    paso = 2 if "--paso2" in argv else 1
    xy = (0, 0)
    if paso == 2:
        i = argv.index("--paso2")
        xy = (int(argv[i + 1]), int(argv[i + 2]))
    return asyncio.run(_run(hwnd, paso, xy))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
