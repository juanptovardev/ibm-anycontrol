"""Recorre el libro de la cuenta matriz con AvPag hasta hallar suscriptores.

El listado de unidades es paginado: la primera pagina puede no traer ningun
suscriptor aunque mas adelante si. Se avanza con PAGEDOWN y se para cuando
aparecen codigos, cuando la pagina deja de cambiar (fin del libro) o al tope.

La columna SUSCRIPTOR no esta calibrada contra una captura real, asi que el
conteo de lineas con codigo es una senal DEBIL: se exigen MIN_LINEAS distintas
para no cortar por un numero de cuenta o un telefono suelto.

Uso: python tools/paginar.py <hwnd> [max_paginas]
Salida: una linea JSON con paginas recorridas, suscriptores y motivo de parada.
"""
import asyncio
import json
import sys

from _mcp import call, connect, need_hwnd
from estado import captura, clasificar, normaliza

MAX_PAGINAS = 20
MIN_LINEAS = 2


async def capturar_estado(hwnd: int, usar_jev: bool = False) -> dict:
    img, _ = captura(hwnd)
    return clasificar(img, usar_jev=usar_jev)


def hay_suscriptores(resultado: dict) -> bool:
    """Senal debil: varias lineas distintas con codigo, no un numero suelto."""
    return resultado["senales"].get("lineas_suscriptor", 0) >= MIN_LINEAS


async def recorre(hwnd: int, max_paginas: int, s) -> dict:
    """Recorre paginas hasta hallar suscriptores. Reusable por el ciclo.

    Devuelve {"ok", "paginas", "lineas_suscriptor", "motivo", "estado"}.
    """
    primero = await capturar_estado(hwnd, usar_jev=True)
    if primero["estado"] != "cuenta_matriz":
        return {"ok": False, "paginas": 0, "lineas_suscriptor": 0,
                "motivo": f"pantalla {primero['estado']}", "estado": primero["estado"],
                "error": primero.get("error")}

    anterior = normaliza(primero["texto"])
    pagina, encontrado, motivo = 1, hay_suscriptores(primero), "encontrados"
    lineas_suscriptor = primero["senales"].get("lineas_suscriptor", 0)

    while not encontrado:
        if pagina >= max_paginas:
            motivo = "tope de paginas"
            break
        await call(s, "press_keys", {"keys": ["pagedown"]})
        await asyncio.sleep(0.4)
        actual = await capturar_estado(hwnd)
        if actual["estado"] is None:
            motivo = "estado ambiguo (no clasificado)"
            break
        if actual["estado"] != "cuenta_matriz":
            motivo = f"salio del listado ({actual['estado']})"
            break
        texto = normaliza(actual["texto"])
        if texto == anterior:
            motivo = "fin del libro"
            break
        anterior = texto
        pagina += 1
        lineas_suscriptor = actual["senales"].get("lineas_suscriptor", 0)
        encontrado = hay_suscriptores(actual)

    return {"ok": bool(encontrado), "paginas": pagina,
            "lineas_suscriptor": lineas_suscriptor, "motivo": motivo,
            "estado": "cuenta_matriz"}


async def main(hwnd: int, max_paginas: int) -> int:
    async with connect() as s:
        await call(s, "set_focus_click_mode", {"enabled": False})
        await call(s, "select_anydesk_window", {"hwnd": hwnd})
        out = await recorre(hwnd, max_paginas, s)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    args = sys.argv
    try:
        tope = int(args[2]) if len(args) > 2 else MAX_PAGINAS
    except ValueError:
        print(f"usage: {args[0]} <hwnd> [max_paginas]", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(need_hwnd(args), tope)))
