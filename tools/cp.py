"""Copia un bloque del listado 5250 y lo pega en la hoja de limpieza.

FLUJO DEL OPERADOR (congelado, no reinterpretar):
  1. En el listado CONSULTA UNIDADES, el cursor esta en su posicion inicial.
  2. 7 abajo SIN shift, luego Shift + 72 derecha + 14 abajo -> bloque de 72
     caracteres (Direccion .. Suscriptor) por 15 filas.
  3. Se suelta Shift. Ctrl+C.
  4. Alt+Tab a la hoja. Ctrl+Shift+V (pegar sin formato).
  5. Ctrl+Abajo y luego un Abajo -> celda lista para el siguiente pegado.

El bloque copiado no se puede leer desde aqui: el portapapeles vive en la
maquina REMOTA. La unica prueba de que el pegado ocurrio es la diferencia de
pixeles en la captura posterior.

PUERTAS (si una falla, se aborta; no se reintenta a ciegas):
  G0  la pantalla es el listado (estado == cuenta_matriz)
  G1  la seleccion es un rectangulo macizo (densidad y tamano plausibles)
  G2  tras Alt+Tab la pantalla NO es IBM (es la hoja)
  G3  tras Ctrl+V hubo cambio visible (un reintento y nada mas)

Uso:
  python tools/cp.py <hwnd> --dry   # solo selecciona y mide; NO copia
  python tools/cp.py <hwnd>         # copia y pega una vez
"""
import asyncio
import sys

from PIL import Image

import preflight_auto as pf
from _mcp import connect, need_hwnd
from estado import captura, clasificar, clasificar_rapido, ocr_text

# Bloque del operador: 7 abajo, 72 derecha, 14 abajo (15 filas x 72 columnas).
BAJAR_INICIO = 7
ANCHO = 72
ALTO = 14
KEY_DELAY_MS = 35  # 93 teclas -> ~6 s; por debajo se pierden pulsaciones

SEL_MIN_ANCHO = 500   # medido: el bloque de 72 columnas mide 690 px de ancho
SEL_ROW_MIN = 300     # fila de borde: 683 px medidos en captura real
SEL_COL_MIN = 100     # columna de borde: 309 px medidos en captura real
SEL_MIN_ALTO = 150    # 15 filas ~320 px; 150 px = piso de 8 filas
PASTE_MIN_DIFF = 3000  # pixeles cambiados para aceptar que el pegado ocurrio


def _es_borde(r: int, g: int, b: int) -> bool:
    """Color medido del borde de seleccion del 5250: amarillo apagado."""
    return r > 150 and g > 150 and 60 < b < 170


def sel_box(img: Image.Image) -> tuple[tuple | None, int]:
    """Rectangulo de seleccion del 5250 medido por sus cuatro bordes.

    El emulador dibuja un marco amarillo apagado. Medido sobre captura real:
    dos filas densas (212 y 612 px de ancho) y dos columnas densas (x=244 y
    x=934). Buscar corridas contiguas falla porque el texto rompe la linea.

    El diff entre capturas tampoco sirve: el reloj de la barra inferior
    ensancha la caja a toda la pantalla (densidad medida 0.01).

    Returns:
        (bbox, alto): bbox (x0, y0, x1, y1) o None, y alto en pixeles.
    """
    rgb = img.convert("RGB")
    px = rgb.load()
    ancho, alto = rgb.size
    y_ini, y_fin = 140, min(alto, 635)

    filas: list[int] = []
    for y in range(y_ini, y_fin):
        if sum(1 for x in range(ancho) if _es_borde(*px[x, y])) >= SEL_ROW_MIN:
            filas.append(y)
    if len(filas) < 2:
        return None, 0

    columnas: list[int] = []
    for x in range(ancho):
        if sum(1 for y in range(y_ini, y_fin) if _es_borde(*px[x, y])) >= SEL_COL_MIN:
            columnas.append(x)
    if len(columnas) < 2:
        return None, 0

    caja = (min(columnas), min(filas), max(columnas) + 1, max(filas) + 1)
    return caja, caja[3] - caja[1]


def texto_superior(img: Image.Image, caja: tuple) -> str:
    """OCR de la primera banda de la seleccion: dice si arriba hay cabecera."""
    x0, y0, _x1, y1 = caja
    banda = img.crop((x0, y0, caja[2], y0 + max(12, (y1 - y0) // 15)))
    texto = ocr_text(banda).strip()
    return texto.splitlines()[0] if texto else ""


async def _seleccionar(s, hwnd: int, dry: bool) -> tuple:
    """7 abajo SIN shift, luego Shift + 72 derecha + 14 abajo.

    El shift empieza DESPUES de bajar 7: las bajadas iniciales mueven el
    cursor, no la seleccion. Si se pulsan con shift, se marca una columna
    vertical antes de tiempo y el bloque sale corrido.
    """
    await pf.step(s, "bajar_inicio", "press_keys",
                  {"keys": ["down"] * BAJAR_INICIO, "key_delay_ms": KEY_DELAY_MS})
    teclas = ["shift"] + ["right"] * ANCHO + ["down"] * ALTO
    await pf.step(s, "seleccion", "press_keys",
                  {"keys": teclas, "key_delay_ms": KEY_DELAY_MS})
    await asyncio.sleep(0.3)
    img = pf.shot(hwnd, "cp-sel" if not dry else "cp-sel-dry")
    caja, alto_sel = sel_box(img)
    ancho = (caja[2] - caja[0]) if caja else 0
    print(f"G1 sel caja={caja} ancho={ancho} alto={alto_sel}", flush=True)
    if not caja:
        raise pf.Halt("G1 no hay seleccion visible (amarillo)")
    if ancho < SEL_MIN_ANCHO:
        raise pf.Halt(f"G1 seleccion angosta: {ancho}px (se esperan >={SEL_MIN_ANCHO})")
    if alto_sel < SEL_MIN_ALTO:
        raise pf.Halt(f"G1 seleccion de {alto_sel}px de alto (se esperan >={SEL_MIN_ALTO})")
    print(f"G1 primera linea: {texto_superior(img, caja)!r}", flush=True)
    return img, caja


async def _copiar(s) -> None:
    await pf.step(s, "ctrl_c", "copy_clipboard", {})
    await asyncio.sleep(0.25)


async def _pegar(s, hwnd: int) -> None:
    await pf.step(s, "alt_tab", "press_keys", {"keys": ["alt", "tab"]})
    await asyncio.sleep(0.45)
    st = clasificar_rapido(captura(hwnd)[0])
    no_ibm = bool((st.get("senales") or {}).get("no_ibm"))
    print(f"G2 pantalla destino: estado={st['estado']} no_ibm={no_ibm} "
          f"error={st.get('error')}", flush=True)
    if st["estado"] is not None:
        raise pf.Halt("G2 tras Alt+Tab sigue siendo la pantalla IBM: no se pega")
    if not no_ibm:
        raise pf.Halt("G2 la ventana tras Alt+Tab no parece navegador/hoja: no se pega")
    antes = pf.shot(hwnd, "cp-pre-paste")
    await pf.step(s, "ctrl_shift_v", "paste_clipboard", {"shift": True})
    await asyncio.sleep(0.6)
    despues = pf.shot(hwnd, "cp-post-paste")
    diff = pf.changed_px(antes, despues)
    if diff < PASTE_MIN_DIFF:
        print(f"G3 sin cambio visible ({diff}px): un reintento", flush=True)
        await pf.step(s, "ctrl_shift_v_retry", "paste_clipboard", {"shift": True})
        await asyncio.sleep(0.6)
        despues = pf.shot(hwnd, "cp-post-paste-retry")
        diff = pf.changed_px(antes, despues)
    print(f"G3 diff={diff}px", flush=True)
    if diff < PASTE_MIN_DIFF:
        raise pf.Halt("G3 el pegado no se ve: Ctrl+C no llego al portapapeles remoto")


async def _posicionar(s, hwnd: int) -> None:
    await pf.step(s, "ctrl_down", "press_keys", {"keys": ["ctrl", "down"]})
    await pf.step(s, "abajo", "press_keys", {"keys": ["down"]})
    pf.shot(hwnd, "cp-listo")


async def _secuencia(hwnd: int, dry: bool) -> bool:
    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            st = clasificar(captura(hwnd)[0], usar_jev=False)
            print(f"G0 pantalla: estado={st['estado']} conf={st.get('confianza')}", flush=True)
            if st["estado"] != "cuenta_matriz":
                raise pf.Halt(f"G0 se esperaba el listado, hay {st['estado']}")
            pf.shot(hwnd, "cp-antes")
            await _seleccionar(s, hwnd, dry)
            if dry:
                await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
                print("DRY: seleccion medida, no se copio nada", flush=True)
                return True
            await _copiar(s)
            await _pegar(s, hwnd)
            await _posicionar(s, hwnd)
        except pf.Halt as exc:
            # Se captura DENTRO del context manager: si sale de el, anyio lo
            # envuelve en ExceptionGroup y se pierde el motivo.
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    args = [a for a in argv if a != "--dry"]
    hwnd = need_hwnd(args)
    ok = asyncio.run(_secuencia(hwnd, dry))
    if not ok:
        return 1
    print("OK" + (" (dry)" if dry else ": copiado y pegado"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
