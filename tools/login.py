"""Login del 5250 pegando usuario+clave en el campo Usuario.

Pega desde el portapapeles LOCAL (AnyDesk lo sincroniza): el texto trae
usuario, salto de linea y clave; el emulador reparte ambos campos.

Uso:
    python tools/login.py <hwnd> <usuario> <clave> [--dry]
    python tools/login.py <hwnd> <usuario>        (pregunta la clave)

--dry hace todo menos el Enter final.
No escribe credenciales en disco.
"""
import asyncio
import ctypes
import sys
import time
from pathlib import Path

import pytesseract

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight_auto as pf  # noqa: E402
from _mcp import connect, need_hwnd  # noqa: E402
from estado import captura  # noqa: E402

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


def campo_usuario(img):
    """Devuelve (x, y) del campo a la derecha de la etiqueta Usuario."""
    data = pytesseract.image_to_data(
        img, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT
    )
    for i, txt in enumerate(data["text"]):
        t = (txt or "").strip().lower()
        if t.startswith("usuario"):
            y = data["top"][i] + data["height"][i] // 2
            return data["left"][i] + data["width"][i] + 70, y
    return None


def hace_falta(img) -> bool:
    """True si la pantalla es la de login (tiene la etiqueta Usuario)."""
    return campo_usuario(img) is not None


async def entrar(s, hwnd, usuario, clave) -> bool:
    """Entra al 5250 con una sesion MCP YA ABIERTA.

    Pega usuario y clave desde el portapapeles local (AnyDesk lo sincroniza)
    y da Intro; si el sistema pide "Pulse Intro para continuar", da otro.
    """
    img, _ = captura(hwnd)
    xy = campo_usuario(img)
    if not xy:
        return False
    pon_clipboard(usuario + "\r\n" + clave)
    await pf.step(s, "clic_usuario", "click_point", {"x": xy[0], "y": xy[1]})
    await pf.step(s, "ctrl_v", "paste_clipboard", {})
    await pf.step(s, "intro", "press_enter", {})
    await asyncio.sleep(1.5)
    img2, _ = captura(hwnd)
    if "intro" in (pytesseract.image_to_string(img2, config="--psm 6") or "").lower():
        await pf.step(s, "intro2", "press_enter", {})
        await asyncio.sleep(1.5)
    # La clave no puede quedar en el portapapeles (que AnyDesk sincroniza al
    # PC remoto): se borra en cuanto el 5250 ya la ha cogido.
    pon_clipboard("")
    return True


async def _run(hwnd, usuario, clave, dry):
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        img = pf.shot(hwnd, "login-antes")
        xy = campo_usuario(img)
        if not xy:
            print("no encontre la etiqueta Usuario en pantalla")
            return 1
        print(f"campo usuario: {xy}")
        print("clipboard local:", pon_clipboard(usuario + "\r\n" + clave))
        await pf.step(s, "clic_usuario", "click_point", {"x": xy[0], "y": xy[1]})
        await pf.step(s, "ctrl_v", "paste_clipboard", {})
        pf.shot(hwnd, "login-pegado")
        if dry:
            print("DRY: sin Enter")
            return 0
        await pf.step(s, "enter", "press_enter", {})
        time.sleep(1.5)
        img = pf.shot(hwnd, "login-despues")
        if "intro" in (pytesseract.image_to_string(img, config="--psm 6") or "").lower():
            # El sistema pide "Pulse Intro para continuar" tras validar.
            await pf.step(s, "enter2", "press_enter", {})
            time.sleep(1.5)
            pf.shot(hwnd, "login-menu")
        pon_clipboard("")
        print("Enter enviado")
    return 0


def main(argv):
    hwnd = need_hwnd(argv, pos=1)
    usuario = argv[2] if len(argv) > 2 else input("usuario 5250: ")
    if len(argv) > 3:
        clave = argv[3]
    else:
        # Sin argv la clave no queda en el historial del shell ni en la linea
        # de comandos (que es visible para cualquier proceso del equipo).
        import getpass
        clave = getpass.getpass("clave 5250: ")
    return asyncio.run(_run(hwnd, usuario, clave, "--dry" in argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
