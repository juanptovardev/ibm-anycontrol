"""Extraccion de filas del listado CONSULTA UNIDADES CUENTA MATRIZ.

Layout real (medido en captura, no supuesto):
    Direccion  Apto  Com Div Nodo    Suscript  Est
    CL 175 BLACACIAS 178-10  CASA3  BOG TVC XT121E  50867551  S$

La columna SUSCRIPT es la penultima, antes de Est (D/S/E). El codigo de la
columna NODO se repite en todas las filas y NO es un suscriptor.

El OCR del 5250 confunde caracteres: L->1, O->0, B->8, S->5, I->1, Z->2.
Se normaliza solo lo que es codigo (sin vocales) o el sufijo de un campo
con palabra (CASA + L -> CASA1). Las palabras de calle no se tocan.

Ponytail: un solo archivo, un parser puro (testeable sin pantalla) y una
funcion viva que recorta la tabla, la amplia y la lee.
"""
import re

import pytesseract
from PIL import Image

from _mcp import REPO
from estado import captura

# OCR: O/Q->0, I/L->1, Z->2, S->5, B->8, G->6, T->7
MAPA_OCR = {"O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2",
            "S": "5", "B": "8", "G": "6", "T": "7"}
RE_EST = re.compile(r"^[DSE]{1,2}\$?$")
RE_APTO = re.compile(r"^(CASA|ADMIN|DEP|LOC|DPTO|PISO)[A-Z0-9]*$")
RE_CODIGO = re.compile(r"^[A-Z]{1,4}\d{1,6}[A-Z]?$")
RE_CORTO = re.compile(r"^[A-Z]{2,4}$")
RE_CABECERA = re.compile(r"irecci|apto", re.IGNORECASE)


def _map(t: str) -> str:
    return "".join(MAPA_OCR.get(c, c) for c in t)


def normaliza_token(tok: str) -> tuple[str, bool]:
    """Normaliza un token OCR. Devuelve (valor, determinista).

    Regla: solo se toca lo que tiene digitos. Una palabra sin digitos
    (CL, BLACACIAS) es texto legitimo y se deja intacta.
    """
    t = tok.upper()
    if t.isdigit():
        return t, True
    if any(ch.isdigit() for ch in t) and not re.search(r"[AEIOU]", t):
        return _map(t), True
    return t, False


def normaliza_direccion(tok: str) -> str:
    """Token de calle: solo se corrige si lleva digitos (17B-10 -> 178-10)."""
    t = tok.upper()
    if any(ch.isdigit() for ch in t) and not re.search(r"[AEIOU]", t):
        return _map(t)
    return t


PREFIJOS_APTO = ("CASA", "ADMIN", "DEP", "LOC", "DPTO", "PISO")


def normaliza_apto(tok: str) -> str:
    """Apto: palabra conocida + sufijo (CASAL -> CASA1, ADMINi -> ADMIN1)."""
    t = tok.upper()
    for pre in sorted(PREFIJOS_APTO, key=len, reverse=True):
        if t.startswith(pre) and len(t) > len(pre):
            return pre + _map(t[len(pre):])
    return t


def normaliza_codigo(tok: str) -> str:
    """Nodo o suscriptor: XT121E, NFE7O0O -> NFE700, 50867551."""
    t = tok.upper()
    if t.isdigit():
        return t
    if not re.search(r"[AEIOU]", t):
        return _map(t)
    m = re.match(r"^([A-Z]+)([A-Z0-9]+)$", t)
    if m:
        return m.group(1) + _map(m.group(2))
    return t


def parse_row(linea: str) -> dict | None:
    """Convierte una linea del listado en fila. None si no es una fila."""
    tokens = linea.split()
    if len(tokens) < 4:
        return None
    est = ""
    if RE_EST.fullmatch(tokens[-1].upper()):
        est = tokens.pop().upper()
    for i in range(len(tokens) - 1, -1, -1):
        apto_crudo = tokens[i].upper()
        if not RE_APTO.fullmatch(apto_crudo):
            continue
        resto = tokens[i + 1:]
        if len(resto) < 2:
            continue
        # Com y Div se validan en crudo: el 5250 los muestra en mayusculas y
        # asi la cabecera ("Apto Lom Viv ...") no cuela como fila.
        if not (RE_CORTO.fullmatch(resto[0]) and RE_CORTO.fullmatch(resto[1])):
            continue
        com, div = resto[0], resto[1]
        codigos = resto[2:]
        nodo = normaliza_codigo(codigos[0]) if codigos else ""
        sus = normaliza_codigo(codigos[1]) if len(codigos) > 1 else ""
        direccion = " ".join(normaliza_direccion(t) for t in tokens[:i])
        apto = normaliza_apto(apto_crudo)
        if sus and not sus.isdigit():
            confianza = "media"
        else:
            confianza = "alta"
        return {
            "direccion": direccion,
            "apto": apto,
            "com": com,
            "div": div,
            "nodo": nodo,
            "suscriptor": sus,
            "est": est,
            "confianza": confianza,
        }
    return None


def parse_tabla(texto: str) -> list[dict]:
    """Filas del listado a partir del OCR (cabeccera y ruido se descartan)."""
    filas = []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        if RE_CABECERA.search(linea) and "apto" in linea.lower():
            continue
        fila = parse_row(linea)
        if fila:
            filas.append(fila)
    return filas


def _y_cabecera(img: Image.Image) -> int | None:
    """Y (px) de la linea de cabecera 'Direccion Apto ...'."""
    datos = pytesseract.image_to_data(img, config="--psm 6",
                                      output_type=pytesseract.Output.DICT)
    for i, palabra in enumerate(datos["text"]):
        if palabra and re.search(r"irecci", palabra, re.IGNORECASE):
            return int(datos["top"][i])
    return None


def ocr_tabla(img: Image.Image) -> tuple[str, bool]:
    """OCR de la tabla: recorta desde la cabecera, amplia x2 y lee. Devuelve (texto, recortado)."""
    texto_plano = pytesseract.image_to_string(img.convert("L"), config="--psm 6")
    y = _y_cabecera(img)
    if y is None:
        return texto_plano, False
    recorte = img.crop((0, max(0, y - 8), img.width, img.height))
    grande = recorte.convert("L").resize((recorte.width * 2, recorte.height * 2), Image.LANCZOS)
    return pytesseract.image_to_string(grande, config="--psm 6"), True


def extrae(hwnd: int) -> dict:
    """Vivo: captura el viewport, lee la tabla y devuelve las filas."""
    img, vp = captura(hwnd)
    texto, recortado = ocr_tabla(img)
    filas = parse_tabla(texto)
    return {
        "filas": filas,
        "n_filas": len(filas),
        "recortado": recortado,
        "viewport": vp,
        "texto": texto[:4000],
    }
