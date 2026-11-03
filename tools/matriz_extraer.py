"""Modulo 3: extraer y pegar un bloque de suscriptores del listado.

Un bloque = una pagina de 15 filas del listado CONSULTA UNIDADES. El flujo:
las 7 bajadas (solo la primera vez), Shift+clic en la ultima celda de la
columna Suscript, Ctrl+C, cambio a la hoja, Ctrl+Shift+V y desplazamiento.
"""

import ciclo


async def extrae_bloque(s, hwnd: int, dry: bool = False,
                         bajar: bool = True, previo=None) -> str:
    """Extrae y pega un bloque. Devuelve "ok" o "vacia"."""
    return await ciclo.extrae(s, hwnd, dry, bajar=bajar, previo=previo)
