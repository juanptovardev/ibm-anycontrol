"""Mide el color real de la seleccion 5250 en una captura (solo lectura)."""
import sys
from collections import Counter

from PIL import Image

ruta = sys.argv[1]
img = Image.open(ruta).convert("RGB")
ancho, alto = img.size
px = img.load()

# Recorte util: fuera cabecera IBM (y<70) y fuera barra de tareas (y>640).
y0, y1 = 70, min(alto, 641)


def mascara(criterio):
    puntos = [(x, y) for y in range(y0, y1) for x in range(ancho)
              if criterio(*px[x, y])]
    return puntos


def caja(puntos):
    if not puntos:
        return None
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return (min(xs), min(ys), max(xs), max(ys))


def varias(criterios: dict):
    for nombre, crit in criterios.items():
        pts = mascara(crit)
        print(f"{nombre:16s} n={len(pts):7d} bbox={caja(pts)}")
        return pts
    return []


amarillo = varias({
    "amarillo_fuerte": lambda r, g, b: r > 180 and g > 180 and b < 120,
})

filas = Counter(p[1] for p in amarillo)
print("filas_con_amarillo:", len(filas))
print("filas_top:", sorted(filas.items(), key=lambda kv: -kv[1])[:6])

muestra = Counter(img.getpixel((x, y)) for y in range(200, 520, 4)
                  for x in range(250, 930, 4))
print("colores_dominantes:", muestra.most_common(6))
