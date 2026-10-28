"""Preflight Calle/No.Casa en UNA sesion MCP, con coordenadas medidas.

Orden (lo pedido por el operador, nada mas):
    clic -> flechas izq/der -> escribir parte1 -> '+' -> escribir parte2
    -> '+' -> F10 -> Shift+F4

Dos correcciones aprendidas con dano real:
  1. Las coordenadas NO se cachean: la ventana se redimensiona y las filas
     se detectan por pixeles sobre una captura 1:1 fresca (tools/rows.py).
  2. El clic NO va en la primera columna: con el cursor en la posicion 0 de
     Calle, la flecha izquierda salta al campo ANTERIOR (Nombre) y la
     derecha no regresa -> el texto acababa en Nombre. Se hace clic 2
     caracteres dentro del campo, luego izq/der (truco del operador) y
     `home` para volver a la columna 0 antes de escribir.

Se verifica por brillo de pixeles que el texto cayó en la fila correcta
ANTES de pulsar F10. Sin verificacion no se sigue.

Uso: python tools/preflight_auto.py <hwnd> [parte1] [parte2]
Env: MCP_ANYDESK_HWND, MCP_ANYDESK_REPO
"""
import asyncio
import sys

import enfocar
import native_shot
import rows as rowdet
from _mcp import call, connect, need_hwnd

PARTE1 = "CR 17B"
PARTE2 = "175-77"
ROW_NOMBRE, ROW_CALLE, ROW_CASA = 0, 1, 2
INK_MIN = 50         # px brillantes: por debajo la fila se considera vacia
F10_MIN_DIFF = 500   # px distintos; por debajo se asume que F10 no llego


class Halt(Exception):
    """Un paso fallo: se corta la secuencia para no teclear a ciegas."""


def changed_px(a, b) -> int:
    """Pixeles distintos entre dos capturas (exacto, vectorizado en C).

    Doble bucle en Python sobre 1255x663 costaba ~150 ms; con ImageChops baja
    a ~2 ms. Se toma el mayor de los tres canales para no perder diferencias
    que el gris promediaria a cero.
    """
    if a.size != b.size:
        return 10 ** 6
    from PIL import ImageChops
    dif = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    r, g, bch = dif.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), bch)
    return a.width * a.height - mx.histogram()[0]


def ink(img, row) -> int:
    """Pixeles brillantes dentro de un campo (texto escrito, no subrayado)."""
    px = img.load()
    x0 = row["field_x"] + 2
    x1 = min(img.width, x0 + 480)
    return sum(1 for x in range(x0, x1)
               for y in range(row["cy"] - 7, row["cy"] + 8)
               if sum(px[x, y][:3]) > 420)


def shot(hwnd, label):
    from mcp_anydesk_server import window_manager as W  # import tardio: usa REPO
    vp = W.find_viewport(hwnd)
    if not vp:
        raise Halt("viewport no encontrado")
    img = native_shot.grab(vp["hwnd"])
    native_shot.save(img, label)
    print(f"  shot {label}: {img.size} vp={vp['hwnd']}")
    return img


async def step(s, label, name, args=None):
    # Punto unico de inyeccion: si AnyDesk no es la ventana en primer plano, la
    # tecla o el clic se entregan a otra ventana (o Windows deniega
    # SetForegroundWindow con error 5 y el server aborta). Se comprueba antes de
    # CADA llamada porque el foco oscila solo entre bloques.
    if not enfocar.asegura():
        raise Halt(f"{label}: AnyDesk no esta en primer plano y no se pudo enfocar")
    res = await call(s, name, args or {})
    if res["isError"]:
        raise Halt(f"{label}: {res['text']}")
    print(f"  {label}: ok")
    return res


async def place(s, row, dy=0, home=True, x_off=20):
    """Clic dentro del campo, seat der/izq y opcionalmente home a columna 0.

    Orden mandado por el operador: primero FLECHA DERECHA y luego IZQUIERDA.
    Al reves, con el cursor en la columna 0, la izquierda salta al campo
    anterior (Nombre) y el texto acaba en la fila equivocada.

    `dy` corrige el clic cuando la fila medida queda por encima del campo real
    (el operador lo ve en el resaltado). `home=False` usa el patron validado de
    paso1: clic + derecha + izquierda, sin home.
    """
    await step(s, "click", "click_point",
               {"x": row["field_x"] + x_off, "y": row["cy"] + dy})
    await step(s, "seat", "press_keys", {"keys": ["right", "left"]})
    if home:
        await step(s, "home", "press_keys", {"keys": ["home"]})


async def keys(s, label, names):
    """press_keys con candado: F4 solo puede viajar junto a shift."""
    if "f4" in names and "shift" not in names:
        raise Halt(f"{label}: F4 sin shift cerraria la ventana del emulador")
    await step(s, label, "press_keys", {"keys": names})


async def clear(s, row, name):
    await place(s, row)
    await keys(s, name, ["delete"] * 30)


async def run(hwnd: int, p1: str, p2: str) -> int:
    async with connect() as s:
        try:
            await _sequence(s, hwnd, p1, p2)
        except Halt as exc:
            # Se atrapa aqui: si sale del context manager, anyio la envuelve
            # en un ExceptionGroup y se pierde el mensaje util.
            print(f"DETENIDO: {exc}", file=sys.stderr)
            return 1
    return 0


async def _sequence(s, hwnd: int, p1: str, p2: str) -> None:
    await step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
    await step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})

    _, vp, det = rowdet.detect(hwnd)
    if len(det) < 3:
        raise Halt(f"filas detectadas insuficientes: {len(det)}")
    nombre, calle, casa = det[ROW_NOMBRE], det[ROW_CALLE], det[ROW_CASA]
    for r in (nombre, calle, casa):
        if not r["field_x"]:
            raise Halt(f"campo sin inicio detectado: {r}")
    print(f"  medido vp={vp['hwnd']} nombre=({nombre['field_x']},{nombre['cy']}) "
          f"calle=({calle['field_x']},{calle['cy']}) "
          f"casa=({casa['field_x']},{casa['cy']})")

    # Limpieza: la pantalla puede traer texto de un intento anterior.
    await keys(s, "esc", ["escape"])
    await clear(s, nombre, "clear_nombre")
    await clear(s, calle, "clear_calle")
    check = shot(hwnd, "pre-write")
    if ink(check, nombre) > INK_MIN or ink(check, calle) > INK_MIN:
        raise Halt(f"no quedo limpio: nombre={ink(check, nombre)} "
                   f"calle={ink(check, calle)}")

    await place(s, calle)
    await step(s, "write_p1", "write_to_anydesk", {"command": p1})
    await keys(s, "add1", ["add"])
    await step(s, "write_p2", "write_to_anydesk", {"command": p2})
    await keys(s, "add2", ["add"])

    pre = shot(hwnd, "pre-f10")
    i_nombre, i_calle, i_casa = ink(pre, nombre), ink(pre, calle), ink(pre, casa)
    print(f"  tinta nombre={i_nombre} calle={i_calle} casa={i_casa}")
    if i_calle <= INK_MIN or i_casa <= INK_MIN:
        raise Halt(f"texto no quedo en Calle/No.Casa: {i_calle}/{i_casa}")
    if i_nombre > INK_MIN:
        raise Halt(f"texto cayo en Nombre (tinta={i_nombre}); clic impreciso")

    await keys(s, "f10", ["f10"])
    post = shot(hwnd, "post-f10")
    diff = changed_px(pre, post)
    print(f"  diff_f10={diff}")
    if diff < F10_MIN_DIFF:
        print("  F10 sin efecto visible -> reintento unico")
        pre2 = shot(hwnd, "pre-f10b")
        await keys(s, "f10_retry", ["f10"])
        post = shot(hwnd, "post-f10b")
        print(f"  diff_f10b={changed_px(pre2, post)}")

    await keys(s, "shift_f4", ["shift", "f4"])
    shot(hwnd, "post-shiftf4")


if __name__ == "__main__":
    window = need_hwnd(sys.argv, extra=" [parte1] [parte2]")
    a = sys.argv[2] if len(sys.argv) > 2 else PARTE1
    b = sys.argv[3] if len(sys.argv) > 3 else PARTE2
    sys.exit(asyncio.run(run(window, a, b)))
