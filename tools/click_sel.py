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

import _jev
import cp
import preflight_auto as pf
from cp import SEL_MIN_ALTO, SEL_MIN_ANCHO, sel_box

_CLICK_MARGEN_X = 7      # px hacia dentro desde el borde DERECHO (x validado por el operador)
_DATA_TOP_PAD = 6        # px por debajo de la cabecera empiezan los datos
_EXTRA_CHARS = 0        # celdas extra (0 = la seleccion del clic ya es la buena)


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
    """Cabecera de la columna del suscriptor (OCR la lee como Suscript/Suseript).

    En escala de grises Tesseract puede devolver `_Suscript` con guion bajo
    inicial (medido: 31/31 capturas reales con el strip marcan bien la columna).
    """
    up = texto.strip("_-.,:;").upper()
    return len(up) >= 4 and up.startswith(("SUS", "SUC"))


def _es_barra(texto: str) -> bool:
    """Barra de teclas de funcion o linea de comando: no son filas del listado."""
    up = texto.upper()
    return bool(re.match(r"^F\d{1,2}=", up)) or up.startswith("MA_")


def _es_digitos(texto: str) -> bool:
    """Codigo de suscriptor: solo digitos, largo plausible."""
    return bool(re.fullmatch(r"\d{5,}", texto))


def target_celda(words) -> dict | None:
    """Ultima celda de la columna Suscript en coordenadas de la captura.

    Reglas puras (testeables sin OCR):
      - la cabecera es la palabra que empieza por SUS/SUC;
      - los datos son las palabras entre la cabecera y la barra de teclas
        de funcion (F3=, F5=, MA_): esa barra NO es una fila del listado;
      - la fila objetivo es la mas baja del listado;
      - el clic va al borde IZQUIERDO de los codigos de suscriptor: los
        valores van alineados a la derecha y el borde derecho roza Est.

    Returns:
        {"x", "y", "col_left", "col_right", "fila_top", "barra"} o None.
    """
    cab = [w for w in words if _es_cabecera(w[0])]
    if not cab:
        return None
    _, hx, hy, hw, hh = cab[0]
    techo = hy + hh + _DATA_TOP_PAD
    barra = min((w[2] for w in words if _es_barra(w[0])), default=10 ** 6)
    datos = [w for w in words if techo <= w[2] < barra]
    if not datos:
        return None
    codigos = [w for w in datos if _es_digitos(w[0]) and w[1] >= hx - 20]
    if codigos:
        col_left = min(w[1] for w in codigos)
        col_right = max(w[1] + w[3] for w in codigos)
    else:
        col_left = col_right = hx
    fila = max(datos, key=lambda w: w[2] + w[4])
    y = fila[2] + fila[4] // 2
    x = col_right - _CLICK_MARGEN_X
    return {"x": x, "y": y, "col_left": col_left, "col_right": col_right,
            "fila_top": fila[2], "barra": barra,
            # `suscriptores` = cuantos codigos numericos hay en la columna. Con
            # 0 la pagina puede estar vacia: no se debe seleccionar nada.
            "suscriptores": len(codigos),
            "cabecera": (hx, hy, hw, hh)}


# Medido sobre 22 capturas reales del listado: pagina vacia = 0 px verdes;
# pagina con 1 suscriptor = 237..305 px. El hueco es enorme: umbral seguro.
_TINTA_VACIA = 40


def tinta_suscript(img, celda: dict) -> int:
    """Pixeles verdes dentro de la caja de datos de la columna Suscript."""
    hx, hy, hw, hh = celda["cabecera"]
    x0, y0 = max(0, hx - 5), max(0, hy + hh + 6)
    x1 = min(img.width, hx + hw + 10)
    y1 = min(img.height, celda["barra"] - 4)
    px = img.convert("RGB").load()
    n = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y][:3]
            if g > 140 and r < 130 and b < 130:
                n += 1
    return n


def pagina_vacia(img, celda: dict, texto: str = "") -> tuple[bool, str]:
    """Decide si la pagina del listado no trae ningun suscriptor.

    Regla (medida, no supuesta):
      - si el OCR encontro codigos en la columna -> hay datos;
      - si no hay codigos Y la tinta verde de la columna es < 40 px -> vacia
        (determinista y sin costo);
      - si no hay codigos pero SI hay tinta (codigo garbleado por el OCR) se
        pide una segunda opinion a Jev; solo si Jev confirma 'vacia' con
        confianza >= 0.6 se salta. Si Jev no esta, se asume CON datos: nunca
        se salta una pagina que podria tener informacion.
    """
    if celda.get("suscriptores"):
        return False, f"{celda['suscriptores']} codigos OCR"
    tinta = tinta_suscript(img, celda)
    if tinta < _TINTA_VACIA:
        return True, f"0 codigos OCR y tinta={tinta}"
    decision = _jev.ask(
        (texto or "(sin texto)")[:800],
        "Responde 'vacia' si la columna de suscriptores del listado no tiene "
        "ningun codigo, y 'con_datos' si tiene al menos uno.",
        ["vacia", "con_datos"],
    )
    conf = decision.get("confidence") or 0.0
    if decision.get("ok") and decision.get("choice") == "vacia" and conf >= 0.6:
        return True, f"jev vacia (tinta={tinta} conf={conf})"
    return False, f"tinta={tinta} sin codigos OCR (se asume con datos)"


async def _seleccionar(s, hwnd: int, dry: bool, force: bool = False) -> tuple:
    """7 abajo sin Shift y luego Shift+Clic en la ultima celda de Suscript."""
    await pf.step(s, "bajar_inicio", "press_keys",
                  {"keys": ["down"] * cp.BAJAR_INICIO, "key_delay_ms": cp.KEY_DELAY_MS})
    img = pf.shot(hwnd, "sel-sin-seleccion")
    t = target_celda(_words(img))
    if not t:
        # El listado pudo quedar scrolleado por las bajadas previas: se limpia
        # la seleccion y se vuelve a mirar una vez.
        await pf.step(s, "limpiar_sel", "press_keys", {"keys": ["escape"]})
        await asyncio.sleep(0.5)
        img = pf.shot(hwnd, "sel-sin-seleccion-b")
        t = target_celda(_words(img))
    if not t:
        raise pf.Halt("A1 no se encontro la cabecera Suscript ni sus codigos")
    print(f"A1 objetivo x={t['x']} y={t['y']} col={t['col_left']}..{t['col_right']} "
          f"fila_top={t['fila_top']} barra={t['barra']}", flush=True)
    await pf.step(s, "shift_click", "click_point",
                  {"x": t["x"], "y": t["y"], "shift": True})
    await asyncio.sleep(0.6)
    img = pf.shot(hwnd, "sel-shift-click-dry" if dry else "sel-shift-click")
    caja, alto_sel = sel_box(img)
    if not caja:
        # El remoto pinta el marco con retraso: una segunda mirada, sin repetir
        # el clic (repetirlo extenderia la seleccion).
        await asyncio.sleep(0.6)
        img = pf.shot(hwnd, "sel-shift-click-b")
        caja, alto_sel = sel_box(img)
    ancho = (caja[2] - caja[0]) if caja else 0
    print(f"A2 sel caja={caja} ancho={ancho} alto={alto_sel}", flush=True)
    if not caja:
        if not force:
            raise pf.Halt("A2 el Shift+Clic no dejo seleccion visible (amarillo)")
        print("A2 aviso: marco no detectado, sigo porque el clic fue validado", flush=True)
        return img, (0, 0, 0, 0)
    if not (caja[0] <= t["x"] <= caja[2] and caja[1] <= t["y"] <= caja[3]):
        raise pf.Halt("A2 el clic cayo fuera del rectangulo seleccionado")
    if ancho < SEL_MIN_ANCHO:
        raise pf.Halt(f"A2 seleccion angosta: {ancho}px (se esperan >={SEL_MIN_ANCHO})")
    if alto_sel < SEL_MIN_ALTO:
        raise pf.Halt(f"A2 seleccion de {alto_sel}px de alto (se esperan >={SEL_MIN_ALTO})")
    # El clic cae en el ultimo caracter que Windows alcanza a resolver; el
    # campo Suscript llega un par de celdas mas alla (~9.6 px por caracter).
    # Se completa con Shift+Derecha, que extiende la seleccion ya creada.
    destino = t["col_right"] + _EXTRA_CHARS * 9
    if _EXTRA_CHARS and caja[2] and caja[2] < destino:
        await pf.step(s, "extender", "press_keys",
                      {"keys": ["shift"] + ["right"] * _EXTRA_CHARS,
                       "key_delay_ms": cp.KEY_DELAY_MS})
        await asyncio.sleep(0.5)
        img = pf.shot(hwnd, "sel-extendida")
        caja2, alto2 = sel_box(img)
        print(f"A3 extendida caja={caja2} alto={alto2}", flush=True)
        if not caja2 or caja2[2] <= caja[2]:
            raise pf.Halt("A3 Shift+Derecha no extendio la seleccion")
        caja, alto_sel = caja2, alto2
    print(f"A2 primera linea: {cp.texto_superior(img, caja)!r}", flush=True)
    return img, caja


async def _secuencia(hwnd: int, dry: bool, force: bool = False) -> bool:
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
            await _seleccionar(s, hwnd, dry, force)
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
    force = "--force" in argv
    args = [a for a in argv if a not in ("--dry", "--force")]
    hwnd = need_hwnd(args)
    ok = asyncio.run(_secuencia(hwnd, dry, force))
    if not ok:
        return 1
    print("OK" + (" (dry)" if dry else ": copiado y pegado"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
