"""Paso 1 verificado: UN clic en la celda 1 de Calle, escribir, medir la tinta.

No pulsa F10. Devuelve por stdout en que fila cayo el texto para decidir con
evidencia (antes se pulsaba F10 a ciegas y el 5250 quedaba inhibido).

Uso: python tools/paso1.py <hwnd> [parte1] [--f10]
"""
import asyncio
import sys

import preflight_auto as pf
import rows as rowdet
from _mcp import connect, need_hwnd

PARTE1 = "CR 17B"
NOMBRE, CALLE, CASA = 0, 1, 2


def es_texto(c):
    """Pixel de glifo: brillante pero ni la barra cyan ni la linea roja de debug."""
    r, g, b = c[0], c[1], c[2]
    if b > 200 and g > 200 and r < 80:      # barra cyan de seleccion
        return False
    if r > 200 and g < 80 and b < 80:       # linea roja dibujada por --draw
        return False
    return (r + g + b) > 200


def tinta(img, row):
    x0 = row["field_x"] + 2
    y0, y1 = row["cy"] - 7, row["cy"] + 7
    ancho = min(480, img.width - x0)
    if ancho <= 0:
        return 0
    crop = img.crop((x0, y0, x0 + ancho, y1))
    return sum(1 for c in crop.getdata() if es_texto(c))


async def main(hwnd: int, parte1: str, pulsar_f10: bool) -> int:
    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        _, _, det = rowdet.detect(hwnd)
        calle = det[CALLE]
        # UN solo clic, pegado al borde izquierdo del subrayado = celda 1.
        await pf.step(s, "clic_celda1", "click_point",
                      {"x": calle["field_x"] + 2, "y": calle["cy"]})
        await asyncio.sleep(0.2)
        await pf.step(s, "derecha", "press_keys", {"keys": ["right"]})
        await pf.step(s, "izquierda", "press_keys", {"keys": ["left"]})
        await pf.step(s, "escribir", "write_to_anydesk", {"command": parte1})
        img = pf.shot(hwnd, "paso1")
        medidas = {n: tinta(img, det[i]) for i, n in ((NOMBRE, "nombre"), (CALLE, "calle"), (CASA, "casa"))}
        print("tinta: " + " ".join(f"{k}={v}" for k, v in medidas.items()))
        if medidas["calle"] <= pf.INK_MIN:
            print("FALLO: la tinta no quedo en Calle (teclado inhibido o clic perdido)")
            return 1
        if medidas["nombre"] > pf.INK_MIN:
            print("FALLO: la tinta cayo en Nombre")
            return 1
        if pulsar_f10:
            await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
            pf.shot(hwnd, "paso1-post-f10")
            print("F10 pulsado")
    print("OK: texto en Calle")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    f10 = "--f10" in argv
    argv = [a for a in argv if a != "--f10"]
    sys.exit(asyncio.run(main(need_hwnd([sys.argv[0]] + argv),
                              argv[1] if len(argv) > 1 else PARTE1, f10)))
