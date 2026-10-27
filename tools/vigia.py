"""Vigia de la conexion AnyDesk: detecta el corte de licencia y pulsa Repetir.

Medido en vivo (27/10/2026) sobre la ventana raiz 132724 'AnyDesk':

    child ad_modal_dlg_bg#284  'modal-dialog-bg'
    child ad_modal_dlg#283     'Conexion finalizada'
    child basic_button#285     'Suscribirse...'
    child basic_button#286     'Repetir'      <-- este
    child basic_button#287     'OK'

El dialogo es LOCAL (vive en la maquina del operador, no en la remota), asi que
se puede pulsar con un clic local. Los botones de AnyDesk son dibujados a mano
(clase `basic_button#N`), por eso NO se usa BM_CLICK: se mueve el cursor al
centro del boton, se hace clic y se devuelve el cursor a donde estaba.

Uso:
  python tools/vigia.py <hwnd>             # solo informa (no toca nada)
  python tools/vigia.py <hwnd> --repetir   # pulsa Repetir y espera que cierre
"""
import sys
import time

import win32api
import win32con
import win32gui

# Medido: tras pulsar Repetir el dialogo puede tardar ~10-30 s en cerrar
# mientras AnyDesk renegocia la sesion. 8 s daba falso negativo.
ESPERA_DIALOGO = 25.0
PASO_SONDEO = 0.5
ETIQUETAS = ("Repetir", "Suscribirse", "OK")
CLASE_MODAL = "ad_modal_dlg"


def _hijos(hwnd: int) -> list[tuple[int, str, str]]:
    salida: list[tuple[int, str, str]] = []

    def cb(k, _):
        salida.append((k, win32gui.GetClassName(k), win32gui.GetWindowText(k)))

    win32gui.EnumChildWindows(hwnd, cb, None)
    return salida


def raiz(hwnd: int) -> int:
    """Ventana raiz de AnyDesk: la que se le pasa o la primera que aparezca."""
    if hwnd and win32gui.IsWindow(hwnd):
        return win32gui.GetAncestor(hwnd, win32con.GA_ROOT)

    hallado = []

    def cb(h, _):
        cls = win32gui.GetClassName(h)
        if win32gui.IsWindowVisible(h) and cls.startswith("ad_win"):
            hallado.append(h)

    win32gui.EnumWindows(cb, None)
    return hallado[0] if hallado else 0


def dialogo(hwnd_raiz: int) -> dict:
    """Dialogo modal de AnyDesk, si esta abierto.

    Returns:
        {"hwnd": int, "titulo": str, "botones": {texto: hwnd}} o {} si no hay.
    """
    hijos = _hijos(hwnd_raiz)
    modal = next((h for h, c, _t in hijos if c.startswith(CLASE_MODAL + "#")
                  and not c.startswith(CLASE_MODAL + "_bg")), 0)
    if not modal:
        return {}
    botones = {t.strip(): h for h, c, t in hijos
               if c.startswith("basic_button#") and t.strip()
               and t.strip() in ETIQUETAS}
    return {"hwnd": modal, "titulo": win32gui.GetWindowText(modal),
            "botones": botones}


def boton(dlg: dict, etiqueta: str = "Repetir") -> int:
    """Handle del boton por su texto (comparacion sin distinguir mayusculas)."""
    for texto, h in (dlg.get("botones") or {}).items():
        if texto.lower() == etiqueta.lower():
            return h
    return 0


def _traer_al_frente(hwnd: int) -> None:
    """AnyDesk tiene que estar delante: un clic fisico cae en la ventana de arriba."""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
    except Exception:  # noqa: BLE001 - Windows a veces niega el foco, se sigue
        pass


def clic_fisico(hwnd_boton: int) -> dict:
    """Clic real en el centro del boton, devolviendo el cursor a su sitio."""
    raiz_ = win32gui.GetAncestor(hwnd_boton, win32con.GA_ROOT)
    _traer_al_frente(raiz_)
    x0, y0, x1, y1 = win32gui.GetWindowRect(hwnd_boton)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    previo = win32api.GetCursorPos()
    win32api.SetCursorPos((cx, cy))
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.2)
    win32api.SetCursorPos(previo)
    return {"via": "fisico", "x": cx, "y": cy, "cursor_previo": previo}


def clic_mensaje(hwnd_boton: int) -> dict:
    """Clic por mensaje directo al control (los botones de AnyDesk son propios)."""
    x0, y0, x1, y1 = win32gui.GetWindowRect(hwnd_boton)
    lparam = win32api.MAKELONG((x1 - x0) // 2, (y1 - y0) // 2)
    win32gui.SendMessage(hwnd_boton, win32con.WM_LBUTTONDOWN,
                         win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(hwnd_boton, win32con.WM_LBUTTONUP, 0, lparam)
    return {"via": "mensaje"}


def reconecta(hwnd_raiz: int, etiqueta: str = "Repetir",
              espera: float = ESPERA_DIALOGO) -> dict:
    """Pulsa Repetir y espera a que el dialogo desaparezca.

    Dos estrategias en orden: clic fisico (con AnyDesk al frente) y, si el
    dialogo sigue, mensaje directo al control.
    """
    dlg = dialogo(hwnd_raiz)
    if not dlg:
        return {"ok": False, "motivo": "no hay dialogo de licencia abierto"}
    h = boton(dlg, etiqueta)
    if not h:
        return {"ok": False, "motivo": f"sin boton {etiqueta!r}",
                "botones": list(dlg["botones"])}

    intentos = []
    for estrategia in (clic_fisico, clic_mensaje):
        clic = estrategia(h)
        t0 = time.time()
        while time.time() - t0 < espera:
            if not dialogo(hwnd_raiz):
                return {"ok": True, "boton": etiqueta, "clic": clic,
                        "segundos": round(time.time() - t0, 2),
                        "intentos": intentos + [estrategia.__name__]}
            time.sleep(PASO_SONDEO)
        intentos.append(estrategia.__name__)
    return {"ok": False, "motivo": f"el dialogo sigue abierto tras {espera}s",
            "intentos": intentos}


def main(argv: list[str]) -> int:
    hwnd = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 0
    r = raiz(hwnd)
    if not r:
        print("no hay ventana de AnyDesk", file=sys.stderr)
        return 2
    dlg = dialogo(r)
    print(f"raiz={r} titulo={win32gui.GetWindowText(r)!r}")
    if not dlg:
        print("sin dialogo de licencia")
        return 0
    print(f"dialogo={dlg['titulo']!r} botones={list(dlg['botones'])}")
    if "--repetir" in argv:
        res = reconecta(r)
        print(res)
        return 0 if res.get("ok") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
