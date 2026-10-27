"""Clasifica la pantalla del 5250: regla OCR primero, Jev solo si el texto duda.

Jev no ve imagenes: lee el TEXTO que saca Tesseract y decide entre estados.
La regla es instantanea y determinista; Jev (~300 ms) cubre el caso ambiguo.

Uso:
  python tools/estado.py <hwnd>           # captura viva del viewport
  python tools/estado.py --img <png>      # clasifica una captura guardada

Salida: una linea JSON con estado, fuente, confianza, senales y texto crudo.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pytesseract
from PIL import Image

import native_shot
from _mcp import REPO, need_hwnd
from _jev import ask

sys.path.insert(0, REPO)
from mcp_anydesk_server import window_manager as W  # noqa: E402

ESTADOS = ["formulario", "cuenta_matriz", "sin_coincidencia", "error"]
# Jev con poca confianza NO es un veredicto: se deja sin clasificar para que
# el bucle aborte (medido en vivo: una pagina web dio "formulario" con 0.35).
UMBRAL_JEV = 0.6
INSTRUCCION_JEV = (
    "Clasifica la pantalla del sistema IBM 5250. 'formulario' es el buscador "
    "CONSULTA EDIFICIO-CUENTA MATRIZ con los campos Nombre/Calle/No.Casa vacios o "
    "llenos y sin listado. 'cuenta_matriz' es un listado de unidades con columnas "
    "de direccion, apto y suscriptor. 'sin_coincidencia' es el mismo formulario con "
    "un mensaje de que la calle o el edificio no existe. 'error' es cualquier aviso "
    "que impide continuar."
)

RE_DURO = re.compile(
    r"AREA\s+PROTEGIDA|REQUIERE\s+CARACTERES|CODIGO\s+COMUNIDAD|NO\s+PERMITIDA",
    re.IGNORECASE,
)
RE_NO_ENCONTRADO = re.compile(
    r"NO\s+SE\s+ENCUENTRA|NO\s+ESTA\s+EN\s+EL\s+ARCHIVO", re.IGNORECASE
)
RE_FORM = re.compile(r"CONSULTA\s+EDIFICIO", re.IGNORECASE)
RE_UNIDADES = re.compile(r"CONSULTA\s+UNIDADES", re.IGNORECASE)
RE_SUSCRIPTOR = re.compile(r"\b(?:[A-Z]{2,4}\d{3,5}[A-Z]?|\d{7,9})\b", re.IGNORECASE)

# Negativo duro: marcadores de navegador/hoja de calculo. Una hoja con la MISMA
# tabla de direcciones y suscriptores se parece demasiado al listado 5250 (medido
# en vivo: Jev la clasifico 'cuenta_matriz' con 0.83 y habria tecleado encima).
RE_NO_IBM = re.compile(
    r"GOOGLE\s+SHEETS|ASK\s+GEMINI|LIMPIEZA\s+RR|CHROME|FIREFOX|"
    r"HTTPS?://|WWW\.",
    re.IGNORECASE,
)
# Positivo minimo: sin un marcador real del 5250 no se acepta veredicto de Jev.
RE_IBM = re.compile(
    r"CUENTA\s+EDIFICIO|CONSULTA\s+(?:EDIFICIO|UNIDADES)|F(?:3|5|6|8|10|13|14|16)\s*=",
    re.IGNORECASE,
)


def normaliza(text: str) -> str:
    """Mayusculas, sin acentos, espacios colapsados: comparaciones estables."""
    sin = unicodedata.normalize("NFKD", text)
    sin = "".join(c for c in sin if not unicodedata.combining(c))
    return re.sub(r"[ \t]+", " ", sin.upper())


def ocr_text(img: Image.Image) -> str:
    """OCR del 5250. Sin reescalar: medido, x1 da 10/10 tokens; ampliar mete ruido."""
    return pytesseract.image_to_string(img.convert("L"), config="--psm 6")


def captura(hwnd: int) -> tuple[Image.Image, dict]:
    """Captura 1:1 del viewport remoto (no del marco de AnyDesk)."""
    vp = W.find_viewport(hwnd)
    if not vp:
        raise SystemExit(f"sin viewport para hwnd {hwnd}")
    return native_shot.grab(vp["hwnd"]), vp


def reglas(texto: str) -> dict:
    """Clasificacion determinista. Devuelve estado o None si no se atreve.

    Orden importante: un aviso duro (campo inhibido, comunidad corrupta) gana
    sobre 'no encontrado', y 'sin coincidencia' solo aplica al formulario, nunca
    al listado de unidades.
    """
    lineas = [l for l in texto.splitlines() if l.strip()]
    # Señal DEBIL: cuenta lineas con al menos un codigo, no codigos sueltos.
    # Sin captura real de CONSULTA UNIDADES no se puede afirmar que sea la
    # columna SUSCRIPTOR, por eso el umbral lo pone quien consume la senal.
    lineas_suscriptor = sum(1 for l in lineas if RE_SUSCRIPTOR.search(l))
    duro = RE_DURO.search(texto)
    faltante = RE_NO_ENCONTRADO.search(texto)
    senales = {
        "form": bool(RE_FORM.search(texto)),
        "unidades": bool(RE_UNIDADES.search(texto)),
        "aviso": duro.group(0).upper() if duro else None,
        "no_encontrado": faltante.group(0).upper() if faltante else None,
        "no_ibm": bool(RE_NO_IBM.search(texto)),
        "ibm": bool(RE_IBM.search(texto)),
        "lineas": len(lineas),
        "lineas_suscriptor": lineas_suscriptor,
    }
    # Una hoja de calculo con la misma tabla no es el listado del 5250: si hay
    # marcadores de navegador, no se clasifica (None = no teclear).
    if senales["no_ibm"]:
        return {"estado": None, "fuente": "regla", "confianza": 0.0,
                "senales": senales, "error": "pantalla no IBM (navegador/hoja)"}
    if senales["aviso"]:
        return {"estado": "error", "fuente": "regla", "confianza": 1.0, "senales": senales}
    if senales["unidades"]:
        return {"estado": "cuenta_matriz", "fuente": "regla", "confianza": 0.95, "senales": senales}
    if senales["no_encontrado"] and senales["form"]:
        return {"estado": "sin_coincidencia", "fuente": "regla", "confianza": 0.9, "senales": senales}
    if senales["form"]:
        return {"estado": "formulario", "fuente": "regla", "confianza": 0.9, "senales": senales}
    return {"estado": None, "fuente": None, "confianza": 0.0, "senales": senales}


def clasificar(img: Image.Image, usar_jev: bool = True) -> dict:
    """Estado final: regla si es clara; si no, Jev sobre el texto del OCR."""
    texto = ocr_text(img)
    base = reglas(texto)
    resultado = {
        "estado": base["estado"],
        "fuente": base["fuente"],
        "confianza": base["confianza"],
        "senales": base["senales"],
    }
    if base.get("error"):
        resultado["error"] = base["error"]
    if resultado["estado"] is None and usar_jev and not base["senales"]["no_ibm"]:
        recorte = "\n".join(l for l in texto.splitlines() if l.strip())[:2000]
        decision = ask(recorte or "(pantalla vacia)", INSTRUCCION_JEV, ESTADOS)
        if decision.get("ok"):
            confianza = decision.get("confidence") or 0.0
            if confianza < UMBRAL_JEV:
                resultado.update(estado=None, fuente="jev", confianza=confianza,
                                 error=f"jev con confianza baja ({confianza})")
            elif not base["senales"]["ibm"]:
                # Un veredicto alto sobre una pantalla sin marcadores del 5250 es
                # exactamente el caso de la hoja de calculo: no se acepta.
                resultado.update(estado=None, fuente="jev", confianza=confianza,
                                 error="jev sin marcadores IBM en pantalla")
            else:
                resultado.update(
                    estado=decision["choice"],
                    fuente="jev",
                    confianza=confianza,
                    probabilidades=decision.get("probabilities"),
                )
        else:
            # Fallo de red/clave no es "la pantalla dice error": queda sin
            # clasificar para que el bucle decida (pausar, no seguir a ciegas).
            resultado.update(estado=None, fuente="jev", error=decision.get("error"))
    resultado["texto"] = texto[:4000]
    return resultado


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--img"]:
        if len(argv) < 3:
            print("falta la ruta: --img <png>", file=sys.stderr)
            return 2
        ruta = Path(argv[2])
        if not ruta.exists():
            print(f"no existe {ruta}", file=sys.stderr)
            return 2
        with Image.open(ruta) as img:
            resultado = clasificar(img.convert("RGB"))
    else:
        hwnd = need_hwnd(argv, extra=" | --img <png>")
        img, vp = captura(hwnd)
        resultado = clasificar(img)
        resultado["viewport"] = vp
    print(json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
