"""Identidad de la hoja destino (T3 del plan).

Antes de pegar hay que saber que la ventana activa es la hoja LIMPIEZA RR,
pestana `temp borrador`, y no otra pestana de Chrome. Se comprueba por:
  1. Titulo de la pestana (por defecto "LIMPIEZA RR").
  2. URL visible (por defecto "docs.google.com").
  3. Nombre de la pestana (por defecto "temp borrador").
  4. Cabeceras DIRECCION / EDIFICIO / SUSCRIPTOR en la misma fila.

Fallo cerrado por defecto: sin captura, OCR vacio o senales incompletas NO se
pega. `HOJA_FAIL_OPEN=1` restaura el comportamiento viejo (solo diagnostico;
no usar en produccion).

Reutiliza el OCR por palabras de click_sel (regla del 80%: una sola
implementacion de OCR de pantalla).
"""
import os
import unicodedata

# Import diferido a proposito: click_sel importa cp y cp importa hoja, asi que
# un import de modulo aqui cerraria un ciclo (cp -> hoja -> click_sel -> cp).
# La funcion se resuelve en cada llamada, que es lo que se necesita.

ESPERADAS = ("DIRECCION", "EDIFICIO", "SUSCRIPTOR")
PREFIJOS = 6        # "DIRECCION" -> "DIRECCI" (tolera tilde y mayusculas)
BANDA = 24          # px: las cabeceras deben caer en la misma franja
TOP = 120           # px: titulo + barra de direcciones del navegador


def _env(nombre: str, default: str) -> str:
    return (os.environ.get(nombre) or default).strip()


def _bool_env(nombre: str, default: bool = False) -> bool:
    valor = (os.environ.get(nombre) or "").strip().lower()
    if not valor:
        return default
    return valor not in ("0", "false", "off", "no")


def _norm(texto: str) -> str:
    """Mayusculas sin tildes y con espacios colapsados, para comparar OCR."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _clave(texto: str) -> str:
    """Texto normalizado para comparar cabeceras (conserva tildes)."""
    return texto.strip("_-.,:;*()[]").upper()


def _coincidentes(words, esperadas) -> dict:
    """{esperada: [(texto, x, y)]} de las palabras que laecase."""
    salida: dict = {}
    for esperada in esperadas:
        pre = _clave(esperada)[:PREFIJOS]
        encontrados = []
        for texto, x, y, _w, _h in words:
            clave = _clave(texto)
            if clave.startswith(pre):
                encontrados.append((texto, x, y))
        if encontrados:
            salida[esperada] = encontrados
    return salida


def _texto_superior(words, top: int = TOP) -> str:
    """Palabras de la franja del navegador (titulo + URL)."""
    return " ".join(texto for texto, _x, y, _w, _h in words if y <= top)


def identidad(img, esperadas=ESPERADAS, banda: int = BANDA,
              titulo: str | None = None, url: str | None = None,
              nombre: str | None = None, fail_open: bool | None = None,
              top: int = TOP) -> tuple[bool, str]:
    """(ok, nota) - ok False significa NO pegar en esta pantalla."""
    if fail_open is None:
        fail_open = _bool_env("HOJA_FAIL_OPEN", False)
    if img is None:
        if fail_open:
            return True, "sin captura: fail-open (HOJA_FAIL_OPEN=1)"
        return False, "sin captura: fail-closed"
    from click_sel import _words
    words = _words(img)
    if not words:
        if fail_open:
            return True, "OCR vacio: fail-open (HOJA_FAIL_OPEN=1)"
        return False, "OCR vacio: fail-closed"

    esperado_titulo = _norm(titulo or _env("HOJA_TITULO", "LIMPIEZA RR"))
    esperada_url = _norm(url or _env("HOJA_URL", "DOCS.GOOGLE.COM"))
    esperada_pestana = _norm(nombre or _env("HOJA_NOMBRE", "TEMP BORRADOR"))
    superior = _norm(_texto_superior(words, top))
    completo = _norm(" ".join(texto for texto, _x, _y, _w, _h in words))

    if esperado_titulo and esperado_titulo not in superior:
        return False, (f"no se lee el titulo '{esperado_titulo}' en la barra "
                       "del navegador")
    if esperada_url and esperada_url.replace(" ", "") not in superior.replace(" ", ""):
        return False, (f"no se lee la URL '{esperada_url}' en la barra del "
                       "navegador")
    if esperada_pestana and esperada_pestana not in completo:
        return False, f"no se lee la pestana '{esperada_pestana}'"

    halladas = _coincidentes(words, esperadas)
    if not halladas:
        return False, "no se lee ninguna cabecera conocida: fail-closed"
    faltan = [e for e in esperadas if e not in halladas]
    if faltan:
        return False, (f"la hoja no es la esperada: faltan "
                       f"{', '.join(faltan)} (leidas: "
                       f"{', '.join(sorted(halladas))})")
    ys = [y for v in halladas.values() for (_t, _x, y) in v]
    if ys and (max(ys) - min(ys)) > banda:
        return False, ("las cabeceras no estan en la misma fila: "
                       "puede ser otra pestana u otra hoja")
    return True, (f"identidad ok: titulo, URL, pestana y cabecera "
                  f"({', '.join(sorted(halladas))})")


# Compatibilidad con el nombre viejo usado por versiones anteriores.
verifica = identidad
