"""Contrato de columnas de la hoja destino (T3 del plan).

Antes de pegar hay que saber que la ventana activa es la hoja LIMPIEZA RR y
no otra pestana de Chrome. Se comprueba por la fila de cabecera: la hoja
tiene que traer DIRECCION, EDIFICIO y SUSCRIPTOR.

Fallo abierto a proposito: si el OCR no lee nada legible (pantalla en
transicion, zoom raro, la hoja todavia no ha pintado) NO se bloquea el
pegado. Solo se bloquea cuando se leyo una hoja y su cabecera NO es la
esperada: ahi pegar 15 filas en la pestana equivocada es el peor fallo
posible del sistema.

Reutiliza el OCR por palabras de click_sel (regla del 80%: una sola
implementacion de OCR de pantalla).
"""

# Import diferido a proposito: click_sel importa cp y cp importa hoja, asi que
# un import de modulo aqui cerraria un ciclo (cp -> hoja -> click_sel -> cp).
# La funcion se resuelve en cada llamada, que es lo que se necesita.

ESPERADAS = ("DIRECCION", "EDIFICIO", "SUSCRIPTOR")
PREFIJOS = 6        # "DIRECCION" -> "DIRECCI" (tolera tilde y mayusculas)
BANDA = 24          # px: las cabeceras deben caer en la misma franja


def _clave(texto: str) -> str:
    """Texto normalizado para comparar cabeceras."""
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


def verifica(img, esperadas=ESPERADAS, banda: int = BANDA) -> tuple[bool, str]:
    """(ok, nota) - ok False significa NO pegar en esta pantalla."""
    if img is None:
        return True, "sin captura: se deja pasar (fallo abierto)"
    from click_sel import _words
    words = _words(img)
    if not words:
        return True, "OCR vacio: se deja pasar (fallo abierto)"
    halladas = _coincidentes(words, esperadas)
    if not halladas:
        return True, "no se lee ninguna cabecera conocida: se deja pasar (fallo abierto)"
    faltan = [e for e in esperadas if e not in halladas]
    if faltan:
        return False, (f"la hoja no es la esperada: faltan "
                       f"{', '.join(faltan)} (leidas: "
                       f"{', '.join(sorted(halladas))})")
    ys = [y for v in halladas.values() for (_t, _x, y) in v]
    if ys and (max(ys) - min(ys)) > banda:
        return False, ("las cabeceras no estan en la misma fila: "
                       "puede ser otra pestana o otra hoja")
    return True, f"cabecera ok ({', '.join(sorted(halladas))})"
