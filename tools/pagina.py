"""Volver a IBM y avanzar de pagina en el listado.

Secuencia del operador (congelada):
  1. Despues de pegar y desplazar en la hoja, Alt+Tab regresa al 5250.
  2. Se pulsa AvPag una vez: el listado pasa a la pagina siguiente.
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
from estado import captura, clasificar_rapido, clasificar_texto, ocr_completo

ESPERA_TAB = 0.8
ESPERA_PAGINA = 0.65
# Estados que significan "seguimos dentro del listado del 5250".
IBM_OK = {"cuenta_matriz", "fin_libro"}
# Ultima captura de avanza(): el ciclo la reutiliza y no repite el OCR.
ULTIMA = None


def decide(estado: str | None, no_ibm: bool = False) -> str:
    """Accion pura a partir del estado de la pantalla: seguir | fin | abortar."""
    if no_ibm:
        return "abortar"
    if estado == "fin_libro":
        return "fin"
    if estado == "cuenta_matriz":
        return "seguir"
    return "abortar"


async def volver(s, hwnd: int, intentos: int = 3, sondeos: int = 4) -> dict:
    """Alt+Tab de regreso al 5250 y verificacion de que es la pantalla IBM.

    Medido el 28/10: el remoto tarda 1-3 s en procesar el Alt+Tab, asi que una
    espera fija no basta. Se sondea la pantalla y, si sigue en el navegador, se
    reenvia el Alt+Tab.
    """
    for i in range(intentos):
        await pf.step(s, f"volver_alt_tab_{i}", "press_keys", {"keys": ["alt", "tab"]})
        for _ in range(sondeos):
            await asyncio.sleep(ESPERA_TAB)
            st = clasificar_rapido(captura(hwnd)[0])
            senales = st.get("senales") or {}
            estado = st.get("estado")
            if estado in IBM_OK:
                print(f"VOLVER pantalla: estado={estado} (alt+tab {i + 1})", flush=True)
                return st
            if not senales.get("no_ibm"):
                # Ya se esta en el 5250, pero no en el listado.
                print(f"VOLVER pantalla: estado={estado} no_ibm=False", flush=True)
                raise pf.Halt(f"volver: no se llego al listado (estado {estado})")
    raise pf.Halt("volver: el remoto sigue en el navegador tras varios Alt+Tab")


async def avanza(s, hwnd: int) -> dict:
    """AvPag + clasificacion. Devuelve el estado con la senal de fin de archivo.

    La captura y el OCR quedan en `ULTIMA`: el ciclo los reutiliza para medir
    la columna Suscript sin volver a capturar ni re-ejecutar Tesseract sobre la
    misma pantalla.
    """
    global ULTIMA
    await pf.step(s, "avpag", "press_keys", {"keys": ["pagedown"]})
    await asyncio.sleep(ESPERA_PAGINA)
    img = pf.shot(hwnd, "pagina")
    texto, words = ocr_completo(img)
    st = clasificar_texto(texto, usar_jev=True)
    ULTIMA = {"img": img, "texto": texto, "words": words}
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
