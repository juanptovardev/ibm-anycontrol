"""Cambio de ventana del escritorio remoto por icono de la taskbar.

Por que existe: el 03/11 el Alt+Tab dejo de cambiar de ventana (medido con
la sonda de teclas: la pantalla seguia igual tras pulsar alt+tab, tanto desde
el 5250 como desde Chrome). El emulador 5250 y Chrome estan ambos
maximizados y la tecla de sistema no llega al escritorio remoto.

La alternativa que si funciona (medida el 03/11): hacer clic en el icono de
la ventana destino en la taskbar de Windows del escritorio remoto. Los
iconos se localizan por imagen (matchTemplate multiescala) para que no
dependan de una coordenada fija: si el operador redimensiona la ventana de
AnyDesk, el grupo de iconos se recentra y las coordenadas cambian.
"""
import asyncio
from pathlib import Path

import cv2
import numpy as np

import preflight_auto as pf
from estado import captura, tipo_pixeles

ICONOS = Path(__file__).resolve().parent / "iconos"

DESTINO_IBM = "ibm"
DESTINO_NAVEGADOR = "navegador"

PLANTILLAS = {DESTINO_NAVEGADOR: "chrome", DESTINO_IBM: "emulador5250"}

UMBRAL = 0.70
ESCALAS = (0.85, 0.92, 1.0, 1.08, 1.18)
BANDA = 48


def _plantilla(nombre: str):
    ruta = ICONOS / f"{nombre}.png"
    if not ruta.exists():
        return None
    return cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)


def buscar_icono(img, nombre: str, banda: int = BANDA):
    """(x, y) del centro del icono en la taskbar, o None si no aparece."""
    tpl = _plantilla(nombre)
    if tpl is None:
        return None
    gris = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    alto, ancho = gris.shape
    y0 = max(0, alto - banda)
    region = gris[y0:, :]
    mejor = None
    for esc in ESCALAS:
        t = tpl if esc == 1.0 else cv2.resize(tpl, None, fx=esc, fy=esc)
        th, tw = t.shape
        if th > region.shape[0] or tw > region.shape[1]:
            continue
        res = cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(res)
        if mejor is None or maxv > mejor[0]:
            mejor = (maxv, maxloc[0] + tw // 2, y0 + maxloc[1] + th // 2)
    if mejor and mejor[0] >= UMBRAL:
        return mejor[1], mejor[2]
    return None


async def ir_a(s, hwnd: int, destino: str, intentos: int = 3,
              espera: float = 1.2) -> bool:
    """Lleva el escritorio remoto a la ventana destino. True si lo logro.

    Antes de actuar comprueba que ya no esta ahi (clic en un icono de
    ventana Maximizada la MINIMIZARIA). Si no encuentra el icono por
    imagen, prueba el Alt+Tab como ultimo recurso.
    """
    nombre = PLANTILLAS.get(destino)
    if nombre is None:
        return False
    for intento in range(intentos):
        img, _ = captura(hwnd)
        if tipo_pixeles(img) == destino:
            return True
        pos = buscar_icono(img, nombre)
        if pos is None:
            await pf.step(s, f"alt_tab_{intento}", "press_keys",
                          {"keys": ["alt", "tab"]})
        else:
            await pf.step(s, f"clic_icono_{intento}", "click_point",
                          {"x": int(pos[0]), "y": int(pos[1])})
        await asyncio.sleep(espera)
    img, _ = captura(hwnd)
    return tipo_pixeles(img) == destino


async def main(hwnd: int, destino: str) -> int:
    from _mcp import connect
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        ok = await ir_a(s, hwnd, destino)
        img, _ = captura(hwnd)
        print(f"destino={destino} ok={ok} pixeles={tipo_pixeles(img)}")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    h = int(sys.argv[1])
    d = sys.argv[2] if len(sys.argv) > 2 else DESTINO_IBM
    sys.exit(asyncio.run(main(h, d)))
