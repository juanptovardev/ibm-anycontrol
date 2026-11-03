"""Ciclo unico del 5250: 7 abajo -> Shift+Clic -> copiar -> Alt+Tab -> pegar
-> desplazar. Termina y deja el resultado para que lo confirme el operador.

Orden (validado por el operador, sin inventar pasos):
  1. 7 x Abajo (sin Shift)                     -> cursor en la primera fila
  2. Shift + CLIC en la ultima celda Suscript  -> selecciona el bloque
  3. Ctrl+C                                    -> copia al portapapeles remoto
  4. Alt+Tab                                   -> pasa a la hoja
  5. Ctrl+Shift+V                              -> pega sin formato
  6. Ctrl+Abajo + Abajo                        -> deja la celda lista para el siguiente

Antes de seleccionar se comprueba si la pagina tiene suscriptores: cuando la
columna Suscript viene vacia NO se copia ni se pega nada y se devuelve
"vacia" para que el bucle avance de pagina (orden del operador, 27/10).

No verifica el marco amarillo: esa medicion dio falsos negativos con el clic
que el operador valido. Las puertas que si quedan: G0 (pantalla = listado),
G2 (tras Alt+Tab la pantalla NO es IBM) y G3 (el pegado se ve en la hoja).

Uso:
    python tools/ciclo.py <hwnd>
    python tools/ciclo.py <hwnd> --dry     # solo selecciona y mide, sin copiar
"""
import asyncio
import sys

import cp
import preflight_auto as pf
import perfil
from click_sel import pagina_vacia, target_celda_fallback
from estado import ocr_completo


async def extrae(s, hwnd: int, dry: bool = False, bajar: bool = True,
                 previo: dict | None = None) -> str:
    """Extrae un bloque. Devuelve "ok" o "vacia".

    bajar=False en paginas siguientes: el cursor del 5250 conserva su punto al
    paginar, asi que repetir las 7 bajadas desalinea la seleccion (regla del
    operador, 27/10).

    `previo` es la captura ya leida que dejo `pagina.avanza` (imagen, texto y
    palabras). Se reutiliza para no pagar otra captura ni otro OCR de la MISMA
    pantalla.
    """
    if bajar:
        await pf.step(s, "bajar_inicio", "press_keys",
                      {"keys": ["down"] * cp.BAJAR_INICIO,
                       "key_delay_ms": perfil.key_delay_ms()})
    else:
        print("A0 pagina siguiente: sin 7 bajadas (el cursor ya esta en su punto)",
              flush=True)
    if previo:
        img, texto, words = previo["img"], previo["texto"], previo["words"]
        print("A0 reutilizo la captura de la pagina (sin OCR nuevo)", flush=True)
    else:
        img = pf.shot(hwnd, "ciclo-antes")
        texto, words = ocr_completo(img)
    t = target_celda_fallback(img, words)
    if not t:
        raise pf.Halt("A1 no se encontro la cabecera Suscript ni sus codigos")
    print(f"A1 clic en x={t['x']} y={t['y']} (col {t['col_left']}..{t['col_right']}, "
          f"ultima fila {t['fila_top']}, barra {t['barra']}, "
          f"suscriptores {t['suscriptores']})", flush=True)
    vacia, motivo = pagina_vacia(img, t, texto)
    if vacia:
        print(f"A1 pagina sin suscriptores ({motivo}): no se copia", flush=True)
        return "vacia"
    await pf.step(s, "shift_click", "click_point",
                  {"x": t["x"], "y": t["y"], "shift": True})
    await asyncio.sleep(0.5)
    img = pf.shot(hwnd, "ciclo-sel")
    caja, alto = cp.sel_box(img)
    print(f"A2 seleccion caja={caja} alto={alto} (informativo)", flush=True)
    if dry:
        await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
        print("DRY: seleccionada, sin copiar", flush=True)
        return "ok"
    await cp._copiar(s)
    await cp._pegar(s, hwnd)
    await cp._posicionar(s, hwnd)
    return "ok"


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
            await extrae(s, hwnd, dry)
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
