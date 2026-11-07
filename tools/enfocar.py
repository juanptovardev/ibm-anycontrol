"""Foco del escritorio remoto: garantia de que AnyDesk esta delante antes de teclear.

Por que existe este modulo
--------------------------
Medido el 28/10 en las corridas run4/run5: las teclas de sistema (Alt+Tab) y el
portapapeles fallan de forma intermitente porque el foco de Windows oscila entre
la ventana local de AnyDesk y cualquier otra ventana (el propio terminal del
agente, un Excel, un navegador). Cuando eso pasa:

  - `SetForegroundWindow` devuelve `(5, 'Acceso denegado.')` y el server MCP
    aborta la inyeccion (`copy_clipboard`, `press_keys`, `click_point`).
  - O peor: la tecla se entrega a la ventana equivocada y el 5250 se queda sin
    recibirla, asi que la puerta G2/G3 aborta la direccion.

La regla es simple: **antes de cualquier inyeccion, AnyDesk tiene que ser la
ventana en primer plano**. Comprobarlo cuesta una llamada a `GetForegroundWindow`
(instantanea) y solo se hace el trabajo caro cuando de verdad no lo es.

Medicion posterior (corrida run6 del 28/10): con este modulo, el Alt+Tab de ida
al navegador y el de vuelta al 5250 acertaron a la primera en las 10 paginas de
D02, sin un solo reintento. Por eso NO se anadieron mas reintentos ni el
fallback `Alt+Shift+Tab`: el fix de foco habia resuelto la causa raiz.
"""
import time

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    _WIN32 = True
except ImportError:  # pragma: no cover - solo en maquinas sin pywin32
    _WIN32 = False

import vigia

OBJETIVO = None          # hwnd raiz de AnyDesk a mantener delante
INTENTOS = 6             # medido: 6 x 0.25 s cubre el peor caso observado
ESPERA = 0.25


def set_objetivo(hwnd) -> None:
    """Fija la ventana que hay que mantener en primer plano."""
    global OBJETIVO
    OBJETIVO = hwnd


def raiz(hwnd=None):
    """Raiz real de AnyDesk (el hwnd del proceso cambia en cada reconexion)."""
    objetivo = hwnd if hwnd is not None else OBJETIVO
    if objetivo is None:
        return None
    try:
        return vigia.raiz(objetivo)
    except Exception:  # noqa: BLE001 - sin ventana no hay foco que dar
        return None


def delante(hwnd=None) -> bool:
    """True si la raiz de AnyDesk ya es la ventana en primer plano."""
    if not _WIN32:
        return True
    r = raiz(hwnd)
    if r is None:
        return False
    try:
        return win32gui.GetForegroundWindow() == r
    except Exception:  # noqa: BLE001 - si falla, se intenta enfocar igual
        return False


def enfocar(hwnd=None, intentos: int = INTENTOS, espera: float = ESPERA) -> dict:
    """Trae AnyDesk al frente y confirma que lo esta.

    Devuelve {"ok", "intentos", "error"}. `ok` es la verdad medida
    (`GetForegroundWindow`), no la suposicion de que la llamada funciono.
    """
    r = raiz(hwnd)
    if r is None:
        return {"ok": False, "intentos": 0, "error": "no hay ventana de AnyDesk"}
    if not _WIN32:
        return {"ok": True, "intentos": 0, "error": None}
    ultimo = None
    intentos_real = 0
    for i in range(1, max(1, intentos) + 1):
        intentos_real = i
        if win32gui.GetForegroundWindow() == r:
            return {"ok": True, "intentos": i, "error": None}
        try:
            if win32gui.IsIconic(r):
                win32gui.ShowWindow(r, win32con.SW_RESTORE)
            # Truco clasico de Windows: una pulsacion de ALT ficticia concede al
            # proceso el derecho a poner una ventana en primer plano (el
            # bloqueo de primer plano se libera para quien recibe la ultima
            # entrada). Sin esto, un proceso lanzado desde un cmd.exe OCULTO no
            # puede robarle el foco a la terminal del operador y SetForeground-
            # Window falla con (5, 'Acceso denegado.').
            try:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32api.keybd_event(win32con.VK_MENU, 0,
                                     win32con.KEYEVENTF_KEYUP, 0)
            except Exception:  # noqa: BLE001 - es un truco, no un requisito
                pass
            # AttachThreadInput: sin esto Windows deniega SetForegroundWindow
            # cuando otra ventana tiene el bloqueo de primer plano (error 5).
            hilo_fg = win32process.GetWindowThreadProcessId(
                win32gui.GetForegroundWindow())[0]
            hilo_yo = win32api.GetCurrentThreadId()
            enganchado = False
            if hilo_fg and hilo_fg != hilo_yo:
                win32process.AttachThreadInput(hilo_fg, hilo_yo, True)
                enganchado = True
            try:
                win32gui.BringWindowToTop(r)
                win32gui.SetForegroundWindow(r)
            finally:
                if enganchado:
                    win32process.AttachThreadInput(hilo_fg, hilo_yo, False)
        except Exception as exc:  # noqa: BLE001 - se reintenta, no se propaga
            ultimo = str(exc)
        time.sleep(espera)
    ok = False
    try:
        ok = win32gui.GetForegroundWindow() == r
    except Exception:  # noqa: BLE001
        ok = False
    return {"ok": ok, "intentos": intentos_real,
            "error": None if ok else (ultimo or "no se pudo poner al frente")}


def asegura(hwnd=None, intentos: int = INTENTOS) -> bool:
    """Atajo para el camino caliente: solo hace trabajo si hace falta.

    Sin objetivo fijado devuelve True y no toca nada: asi las herramientas que
    usan `preflight_auto.step` sin pasar por el agente (tests, sondas) siguen
    funcionando igual.
    """
    objetivo = hwnd if hwnd is not None else OBJETIVO
    if objetivo is None:
        return True
    if delante(objetivo):
        return True
    return bool(enfocar(objetivo, intentos)["ok"])


if __name__ == "__main__":  # pragma: no cover - utilidad manual
    import sys
    from _mcp import need_hwnd
    hwnd = need_hwnd(sys.argv)
    print(f"delante: {delante(hwnd)}")
    print(enfocar(hwnd))
    print(f"delante tras enfocar: {delante(hwnd)}")
