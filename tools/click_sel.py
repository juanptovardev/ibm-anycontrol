"""Plan A del pegado: 7 abajo + Shift+Clic en la ultima celda de Suscript.

La receta del operador para el plan B gasta 93 pulsaciones (~8 s con
key_delay_ms=45). Esta version sustituye las 86 pulsaciones de seleccion por
un solo gesto: mantener Shift y hacer clic en la ultima celda del bloque
(ultima fila, columna Suscript). El emulador extiende la seleccion desde el
cursor hasta la celda clicada.

El resto del flujo se reutiliza tal cual de cp.py (regla del 80%): copiar,
Alt+Tab, Ctrl+Shift+V, verificar el cambio y posicionar la celda siguiente.

Las coordenadas NO son constantes: se miden sobre la captura 1:1 fresca
(la ventana cambia de tamano y el listado cambia de alto).

Uso:
    python tools/click_sel.py <hwnd> --dry   # solo selecciona y mide
    python tools/click_sel.py <hwnd>         # selecciona, copia y pega
"""
import asyncio
import re
import sys

import pytesseract

import cp
import preflight_auto as pf
from cp import SEL_MIN_ALTO, SEL_MIN_ANCHO, sel_box

_CLICK_MARGEN_X = 4      # px hacia dentro desde el borde derecho medido
_DATA_TOP_PAD = 6        # px por debajo de la cabecera empiezan los datos


def _words(img) -> list[tuple[str, int, int, int, int]]:
    """Palabras del listado con su caja: [(texto, x, y, ancho, alto)]."""
    d = pytesseract.image_to_data(img, config="--psm 6",
                                  output_type=pytesseract.Output.DICT)
    out = []
    for i, texto in enumerate(d["text"]):
        texto = (texto or "").strip()
        if not texto:
            continue
        out.append((texto, d["left"][i], d["top"][i], d["width"][i], d["height"][i]))
    return out


def _es_cabecera(texto: str) -> bool:
    """Cabecera de la columna del suscriptor (OCR la lee como Suscript/Suseript)."""
    up = texto.upper()
    return len(up) >= 4 and up.startswith(("SUS", "SUC"))


def _es_digitos(texto: str) -> bool:
    """Codigo de suscriptor: solo digitos, largo plausible."""
    return bool(re.fullmatch(r"\d{5,}", texto))


def target_celda(words) -> dict | None:
    """Ultima celda de la columna Suscript en coordenadas de la captura.

    Reglas puras (testeables sin OCR):
      - la cabecera es la palabra que empieza por SUS/SUC;
      - los datos son las palabras por debajo de la cabecera;
      - la fila objetivo es la mas baja con texto (ultima fila visible);
      - el borde derecho de la columna es el x+ancho maximo de los codigos
        de suscriptor (los valores van alineados a la derecha).

    Returns:
        {"x", "y", "col_right", "fila_top"} o None si no se reconoce.
    """
    cab = [w for w in words if _es_cabecera(w[0])]
    if not cab:
        return None
    _, hx, hy, hw, hh = cab[0]
    techo = hy + hh + _DATA_TOP_PAD
    datos = [w for w in words if w[2] >= techo]
    if not datos:
        return None
    codigos = [w for w in datos if _es_digitos(w[0]) and w[1] >= hx - 20]
    if codigos:
        col_right = max(w[1] + w[3] for w in codigos)
    else:
        col_right = hx + hw
    fila = max(datos, key=lambda w: w[2] + w[4])
    y = fila[2] + fila[4] // 2
    x = col_right - _CLICK_MARGEN_X
    return {"x": x, "y": y, "col_right": col_right, "fila_top": fila[2]}


async def _seleccionar(s, hwnd: int, dry: bool) -> tuple:
    """7 abajo sin Shift y luego Shift+Clic en la ultima celda de Suscript."""
    await pf.step(s, "bajar_inicio", "press_keys",
                  {"keys": ["down"] * cp.BAJAR_INICIO, "key_delay_ms": cp.KEY_DELAY_MS})
    img = pf.shot(hwnd, "sel-sin-seleccion")
    t = target_celda(_words(img))
    if not t:
        raise pf.Halt("A1 no se encontro la cabecera Suscript ni sus codigos")
    print(f"A1 objetivo x={t['x']} y={t['y']} col_right={t['col_right']}", flush=True)
    await pf.step(s, "shift_click", "click_point",
                  {"x": t["x"], "y": t["y"], "shift": True})
    await asyncio.sleep(0.3)
    img = pf.shot(hwnd, "sel-shift-click-dry" if dry else "sel-shift-click")
    caja, alto_sel = sel_box(img)
    ancho = (caja[2] - caja[0]) if caja else 0
    print(f"A2 sel caja={caja} ancho={ancho} alto={alto_sel}", flush=True)
    if not caja:
        raise pf.Halt("A2 el Shift+Clic no dejo seleccion visible (amarillo)")
    if not (caja[0] <= t["x"] <= caja[2] and caja[1] <= t["y"] <= caja[3]):
        raise pf.Halt("A2 el clic cayo fuera del rectangulo seleccionado")
    if ancho < SEL_MIN_ANCHO:
        raise pf.Halt(f"A2 seleccion angosta: {ancho}px (se esperan >={SEL_MIN_ANCHO})")
    if alto_sel < SEL_MIN_ALTO:
        raise pf.Halt(f"A2 seleccion de {alto_sel}px de alto (se esperan >={SEL_MIN_ALTO})")
    print(f"A2 primera linea: {cp.texto_superior(img, caja)!r}", flush=True)
    return img, caja


async def _secuencia(hwnd: int, dry: bool) -> bool:
    from _mcp import connect

    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            st = cp.clasificar(cp.captura(hwnd)[0], usar_jev=False)
            print(f"G0 pantalla: estado={st['estado']} conf={st.get('confianza')}", flush=True)
            if st["estado"] != "cuenta_matriz":
                raise pf.Halt(f"G0 se esperaba el listado, hay {st['estado']}")
            pf.shot(hwnd, "sel-antes")
            await _seleccionar(s, hwnd, dry)
            if dry:
                await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
                print("DRY: seleccion medida, no se copio nada", flush=True)
                return True
            await cp._copiar(s)
            await cp._pegar(s, hwnd)
            await cp._posicionar(s, hwnd)
        except pf.Halt as exc:
            # Dentro del context manager: si sale, anyio lo envuelve en
            # ExceptionGroup y se pierde el motivo.
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    from _mcp import need_hwnd

    dry = "--dry" in argv
    args = [a for a in argv if a != "--dry"]
    hwnd = need_hwnd(args)
    ok = asyncio.run(_secuencia(hwnd, dry))
    if not ok:
        return 1
    print("OK" + (" (dry)" if dry else ": copiado y pegado"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
