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

ESTADOS = ["formulario", "ficha", "cuenta_matriz", "fin_libro", "desconectado",
           "sin_coincidencia", "error"]
# Jev con poca confianza NO es un veredicto: se deja sin clasificar para que
# el bucle aborte (medido en vivo: una pagina web dio "formulario" con 0.35).
UMBRAL_JEV = 0.6
INSTRUCCION_JEV = (
    "Clasifica la pantalla del sistema IBM 5250. 'formulario' es el buscador "
    "CONSULTA EDIFICIO-CUENTA MATRIZ con los campos Nombre/Calle/No.Casa vacios o "
    "llenos y sin listado. 'cuenta_matriz' es un listado de unidades con columnas "
    "de direccion, apto y suscriptor. 'fin_libro' es ese mismo listado cuando "
    "abajo aparece un aviso de que se intento pasar mas alla del primer o ultimo "
    "registro del archivo (giro hacia arriba o hacia abajo). 'sin_coincidencia' "
    "es el mismo formulario con un mensaje de que la calle o el edificio no "
    "existe. 'desconectado' es el dialogo de AnyDesk avisando que la conexion "
    "se cerro por la limitacion de la licencia. 'error' es cualquier aviso que "
    "impide continuar."
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
# Ficha del edificio: pantalla intermedia entre el formulario y el listado.
# Comparte cabecera con el formulario ("CONSULTA EDIFICIO-CUENTA MATRIZ"), asi
# que se detecta por su contenido propio. Medido en vivo tras F10: trae
# "Otras Direcciones", "MULTI-EDIFICIO", "Total Unidades VT/RR" y la renta.
RE_FICHA = re.compile(
    r"OTRAS\s+DIRECCIONES|TOTAL\s+UNIDADES|MULTI-?EDIFICIO|ULTIMO\s+TRABAJO",
    re.IGNORECASE,
)
RE_SUSCRIPTOR = re.compile(r"\b(?:[A-Z]{2,4}\d{3,5}[A-Z]?|\d{7,9})\b", re.IGNORECASE)
# Fin de archivo: el 5250 avisa al intentar paginar mas alla del ultimo registro.
# Se busca la FRASE, no "F12=Anterior": esa tecla puede estar en la barra de
# funciones sin que la matriz se haya terminado. Se compara sobre el texto
# normalizado (sin acentos) porque el OCR devuelve "MAS ALLA" / "ULTIMO".
RE_FIN = re.compile(
    r"GIRO\s+HACIA\s+(?:ARRIBA|ABAJO)|"
    r"MAS\s+ALLA\s+DEL\s+(?:PRIMER|ULTIMO)\s+REGISTRO|"
    r"(?:PRIMER|ULTIMO)\s+REGISTRO\s+EN\s+EL\s+ARCHIVO",
    re.IGNORECASE,
)
# AnyDesk corta la sesion por la licencia gratuita y dibuja su propio dialogo
# LOCAL encima de la pantalla remota (medido: modal 'Conexion finalizada' con
# los botones Suscribirse / Repetir / OK). No es un error del 5250: se puede
# reconectar y seguir.
RE_DESCONECTADO = re.compile(
    r"CONEXION\s+FINALIZADA|LIMITACION\s+DE\s+LA\s+LICENCIA|"
    r"NO\s+SE\s+PUEDE\s+CONECTAR",
    re.IGNORECASE,
)

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


def ocr_completo(img: Image.Image) -> tuple[str, list[tuple]]:
    """Texto Y palabras con su caja en UNA sola pasada de Tesseract.

    Medido: una llamada de pantalla completa cuesta ~2.2 s. El ciclo necesita
    el texto (para clasificar) y las palabras (para localizar la columna
    Suscript); hacerlo en dos llamadas costaba ~2.2 s de mas por pagina.

    Returns:
        (texto, words) con words = [(texto, x, y, ancho, alto)].
    """
    d = pytesseract.image_to_data(img.convert("L"), config="--psm 6",
                                  output_type=pytesseract.Output.DICT)
    lineas: dict[tuple, list[str]] = {}
    words: list[tuple] = []
    for i, t in enumerate(d["text"]):
        t = (t or "").strip()
        if not t:
            continue
        words.append((t, d["left"][i], d["top"][i], d["width"][i], d["height"][i]))
        clave = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        lineas.setdefault(clave, []).append(t)
    texto = "\n".join(" ".join(v) for v in lineas.values())
    return texto, words


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
    fin = RE_FIN.search(normaliza(texto))
    desconectado = RE_DESCONECTADO.search(normaliza(texto))
    senales = {
        "form": bool(RE_FORM.search(texto)),
        "ficha": bool(RE_FICHA.search(texto)),
        "unidades": bool(RE_UNIDADES.search(texto)),
        "fin": bool(fin),
        "desconectado": bool(desconectado),
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
    # El corte de licencia tapa la pantalla: no hay nada que leer ni teclear.
    if senales["desconectado"]:
        return {"estado": "desconectado", "fuente": "regla", "confianza": 0.95,
                "senales": senales, "error": "sesion AnyDesk cortada (licencia)"}
    if senales["aviso"]:
        return {"estado": "error", "fuente": "regla", "confianza": 1.0, "senales": senales}
    # Fin de archivo gana sobre 'cuenta_matriz': el listado sigue en pantalla,
    # pero ya no hay paginas que extraer.
    if senales["fin"]:
        return {"estado": "fin_libro", "fuente": "regla", "confianza": 0.95,
                "senales": senales}
    if senales["unidades"]:
        return {"estado": "cuenta_matriz", "fuente": "regla", "confianza": 0.95, "senales": senales}
    # Ficha del edificio: se llega con F10 y todavia NO hay suscriptores; el
    # listado aparece con Shift+F4. Va antes de 'formulario' porque comparte
    # la cabecera CONSULTA EDIFICIO-CUENTA MATRIZ.
    if senales["ficha"]:
        return {"estado": "ficha", "fuente": "regla", "confianza": 0.95, "senales": senales}
    if senales["no_encontrado"] and senales["form"]:
        return {"estado": "sin_coincidencia", "fuente": "regla", "confianza": 0.9, "senales": senales}
    if senales["form"]:
        return {"estado": "formulario", "fuente": "regla", "confianza": 0.9, "senales": senales}
    return {"estado": None, "fuente": None, "confianza": 0.0, "senales": senales}


def clasificar(img: Image.Image, usar_jev: bool = True) -> dict:
    """Estado final: regla si es clara; si no, Jev sobre el texto del OCR."""
    return clasificar_texto(ocr_text(img), usar_jev)


def clasificar_texto(texto: str, usar_jev: bool = True) -> dict:
    """Igual que `clasificar` pero partiendo de un texto ya leido.

    Deja reutilizar el OCR de `ocr_completo`: el ciclo no vuelve a pagar los
    ~2.2 s de Tesseract sobre una pantalla que ya se leyo.
    """
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


def clasificar_rapido(img: Image.Image, usar_jev: bool = False) -> dict:
    """Clasificacion barata mirando solo la franja superior.

    Medido: recortar a (0, 0, w, 220) decide navegador vs 5250 en ~0.6 s
    (frente a ~2.2 s de pantalla completa) con 100% de acierto en las capturas
    probadas. Solo se usa para "es IBM?" / "no es IBM?"; si la franja no
    decide, se cae a la clasificacion completa.
    """
    franja = img.crop((0, 0, img.width, min(img.height, 220)))
    r = clasificar(franja, usar_jev=False)
    if r["estado"] is not None or (r.get("senales") or {}).get("no_ibm"):
        return r
    return clasificar(img, usar_jev=usar_jev)


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
