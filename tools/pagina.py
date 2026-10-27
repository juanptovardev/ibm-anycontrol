"""Volver a IBM y avanzar de pagina en el listado.

Secuencia del operador (congelada):
  1. Despues de pegar y desplazar en la hoja, Alt+Tab regresa al 5250.
  2. Se pulsa AvPág una vez: el listado pasa a la pagina siguiente.
  3. Se mira la pantalla:
       - sale "F12=Anterior / Giro hacia arriba o hacia abajo mas alla del
         primer o ultimo registro en el archivo"  -> la matriz se acabo
       - no sale                                    -> hay otra pagina: se
         vuelve a extraer (seleccionar, copiar, tabular, pegar, desplazar)

El letrero se detecta con las reglas de `estado.py` (estado `fin_libro`); Jev
solo entra si el OCR queda dudoso. `F12=Anterior` a secas NO se usa como
senal: puede estar presente en la barra de teclas de funcion.
"""
import asyncio
import sys

import preflight_auto as pf
from _mcp import connect, need_hwnd
from estado import captura, clasificar

ESPERA_TAB = 0.9
ESPERA_PAGINA = 1.2
# Estados que significan "seguimos dentro del listado del 5250".
IBM_OK = {"cuenta_matriz", "fin_libro"}


def decide(estado: str | None, no_ibm: bool = False) -> str:
    """Accion pura a partir del estado de la pantalla: seguir | fin | abortar."""
    if no_ibm:
        return "abortar"
    if estado == "fin_libro":
        return "fin"
    if estado == "cuenta_matriz":
        return "seguir"
    return "abortar"


async def volver(s, hwnd: int) -> dict:
    """Alt+Tab de regreso al 5250 y verificacion de que es la pantalla IBM."""
    await pf.step(s, "volver_alt_tab", "press_keys", {"keys": ["alt", "tab"]})
    await asyncio.sleep(ESPERA_TAB)
    st = clasificar(captura(hwnd)[0], usar_jev=False)
    no_ibm = bool((st.get("senales") or {}).get("no_ibm"))
    print(f"VOLVER pantalla: estado={st['estado']} no_ibm={no_ibm}", flush=True)
    if no_ibm or st["estado"] not in IBM_OK:
        raise pf.Halt(f"volver: no se llego al listado (estado {st['estado']})")
    return st


async def avanza(s, hwnd: int) -> dict:
    """AvPág + clasificacion. Devuelve el estado con la senal de fin de archivo."""
    await pf.step(s, "avpag", "press_keys", {"keys": ["pagedown"]})
    await asyncio.sleep(ESPERA_PAGINA)
    img = pf.shot(hwnd, "pagina")
    st = clasificar(img, usar_jev=True)
    senales = st.get("senales") or {}
    print(f"PAGINA estado={st['estado']} conf={st.get('confianza')} "
          f"senal_fin={senales.get('fin')} error={st.get('error')}", flush=True)
    return st


async def _run(hwnd: int) -> bool:
    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            await volver(s, hwnd)
            st = await avanza(s, hwnd)
            decision = decide(st["estado"],
                              bool((st.get("senales") or {}).get("no_ibm")))
            print(f"DECISION: {decision}", flush=True)
            if decision == "abortar":
                raise pf.Halt(f"pagina: estado inesperado {st['estado']}")
        except pf.Halt as exc:
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    hwnd = need_hwnd(argv)
    if not asyncio.run(_run(hwnd)):
        return 1
    print("OK pagina", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
