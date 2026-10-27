"""Ciclo unico del 5250: 7 abajo -> Shift+Clic -> copiar -> Alt+Tab -> pegar
-> desplazar. Termina y deja el resultado para que lo confirme el operador.

Orden (validado por el operador, sin inventar pasos):
  1. 7 x Abajo (sin Shift)                     -> cursor en la primera fila
  2. Shift + CLIC en la ultima celda Suscript  -> selecciona el bloque
  3. Ctrl+C                                    -> copia al portapapeles remoto
  4. Alt+Tab                                   -> pasa a la hoja
  5. Ctrl+Shift+V                              -> pega sin formato
  6. Ctrl+Abajo + Abajo                        -> deja la celda lista para el proximo bloque

No verifica el marco amarillo: esa medicion dio falsos negativos con el clic
que el operador valido. Las puertas que si quedan: G0 (pantalla = listado),
G2 (tras Alt+Tab la pantalla NO es IBM) y G3 (el pegado se ve en la hoja).

Uso:
    python tools/ciclo.py <hwnd>
    python tools/ciclo.py <hwnd> --dry     # solo selecciona y mide, sin copiar
"""
import asyncio
import sys

import click_sel
import cp
import preflight_auto as pf
from click_sel import _words, target_celda


async def _ciclo(s, hwnd: int, dry: bool) -> None:
    await pf.step(s, "bajar_inicio", "press_keys",
                  {"keys": ["down"] * cp.BAJAR_INICIO, "key_delay_ms": cp.KEY_DELAY_MS})
    img = pf.shot(hwnd, "ciclo-antes")
    t = target_celda(_words(img))
    if not t:
        raise pf.Halt("A1 no se encontro la cabecera Suscript ni sus codigos")
    print(f"A1 clic en x={t['x']} y={t['y']} (col {t['col_left']}..{t['col_right']}, "
          f"ultima fila {t['fila_top']}, barra {t['barra']})", flush=True)
    await pf.step(s, "shift_click", "click_point",
                  {"x": t["x"], "y": t["y"], "shift": True})
    await asyncio.sleep(0.6)
    img = pf.shot(hwnd, "ciclo-sel")
    caja, alto = cp.sel_box(img)
    print(f"A2 seleccion caja={caja} alto={alto} (informativo)", flush=True)
    if dry:
        await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
        print("DRY: seleccionada, sin copiar", flush=True)
        return
    await cp._copiar(s)
    await cp._pegar(s, hwnd)
    await cp._posicionar(s, hwnd)


async def _run(hwnd: int, dry: bool) -> bool:
    from _mcp import connect

    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            st = cp.clasificar(cp.captura(hwnd)[0], usar_jev=False)
            print(f"G0 pantalla: estado={st['estado']} conf={st.get('confianza')}", flush=True)
            if st["estado"] != "cuenta_matriz":
                raise pf.Halt(f"G0 se esperaba el listado, hay {st['estado']}")
            await _ciclo(s, hwnd, dry)
        except pf.Halt as exc:
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    from _mcp import need_hwnd

    dry = "--dry" in argv
    args = [a for a in argv if a != "--dry"]
    hwnd = need_hwnd(args)
    if not asyncio.run(_run(hwnd, dry)):
        return 1
    print("FIN DEL CICLO. Esperando confirmacion del operador.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
