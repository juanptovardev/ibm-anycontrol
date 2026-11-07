"""Entra al formulario desde el menu, prellena BOG/TVC y dispara F10 + Shift+F4.

Secuencia del operador para llegar al formulario (primer inicio tras login):
    1 ENTER, ESC, 1 ENTER, 1 ENTER

Prellenado que solo hace falta la primera vez en la sesion, antes de F10:
    parte1, +, parte2, +, BOG, +, TVC

Despues el flujo normal: F10 -> ficha del edificio -> Shift+F4 -> listado.

Uso:
    python tools/nav_prefill.py 132724 "CR 17B" "175-77"
    python tools/nav_prefill.py 132724 "CR 17B" "175-77" --no-nav
    python tools/nav_prefill.py 132724 "CR 17B" "175-77" --dry
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight_auto as pf
import rows as rowdet
from _mcp import connect
from estado import clasificar

NAV = [
    ("nav_1", "write_to_anydesk", {"command": "1"}),
    ("nav_enter_1", "press_enter", None),
    ("nav_esc", "press_keys", {"keys": ["escape"]}),
    ("nav_1b", "write_to_anydesk", {"command": "1"}),
    ("nav_enter_2", "press_enter", None),
    ("nav_1c", "write_to_anydesk", {"command": "1"}),
    ("nav_enter_3", "press_enter", None),
]

NOMBRE, CALLE, CASA, COMUNIDAD, DIVISION = 0, 1, 2, 3, 4
ESPERA = 0.8


def estado_de(img):
    return clasificar(img, usar_jev=False)


async def espera_form(s, hwnd, intentos=8):
    img, r = None, {}
    for i in range(intentos):
        img = pf.shot(hwnd, f"nav-{i}")
        r = estado_de(img)
        print(f"  estado[{i}]: {r.get('estado')} conf={r.get('confianza')}")
        if r.get("estado") == "formulario":
            return img, r
        await asyncio.sleep(ESPERA)
    return img, r


async def _run(s, hwnd, p1, p2, nav=True, dry=False, dy=0, fresh=False):
    await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
    await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})

    if fresh:
        await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
        await pf.step(s, "salir", "press_keys", {"keys": ["f3"]})
        await asyncio.sleep(ESPERA)

    if nav:
        for label, tool, args in NAV:
            await pf.step(s, label, tool, args)
            await asyncio.sleep(ESPERA)

    _, r = await espera_form(s, hwnd)
    if r.get("estado") != "formulario":
        raise pf.Halt(f"no se llego al formulario (estado={r.get('estado')})")

    _, _, filas = rowdet.detect(hwnd)
    if len(filas) < 5:
        raise pf.Halt(f"filas detectadas insuficientes: {len(filas)}")
    print(f"  calle cy={filas[CALLE]['cy']} + dy={dy} field_x={filas[CALLE]['field_x']}")

    await pf.place(s, filas[CALLE], dy=dy, home=False, x_off=2)
    await pf.step(s, "step1", "write_to_anydesk", {"command": p1})
    await pf.step(s, "plus1", "press_keys", {"keys": ["add"]})
    await pf.step(s, "step2", "write_to_anydesk", {"command": p2})
    await pf.step(s, "plus2", "press_keys", {"keys": ["add"]})
    await pf.step(s, "bog", "write_to_anydesk", {"command": "BOG"})
    await pf.step(s, "plus3", "press_keys", {"keys": ["add"]})
    await pf.step(s, "tvc", "write_to_anydesk", {"command": "TVC"})

    img = pf.shot(hwnd, "prefill")
    nombres = ("nombre", "calle", "casa", "comunidad", "division")
    tinta = {n: pf.ink(img, filas[i]) for i, n in enumerate(nombres)}
    print("  tinta:", tinta)
    if tinta["nombre"] > pf.INK_MIN:
        raise pf.Halt("el texto cayo en Nombre")
    if tinta["calle"] <= pf.INK_MIN or tinta["casa"] <= pf.INK_MIN:
        raise pf.Halt(f"calle o casa vacias: {tinta}")
    if tinta["comunidad"] <= pf.INK_MIN or tinta["division"] <= pf.INK_MIN:
        raise pf.Halt(f"comunidad o division vacias: {tinta}")

    if dry:
        print("  --dry: no se pulsa F10")
        return 0

    pre = pf.shot(hwnd, "pre-f10")
    await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
    await asyncio.sleep(1.0)
    post = pf.shot(hwnd, "post-f10")
    print(f"  diff_f10={pf.changed_px(pre, post)}")
    r2 = estado_de(post)
    print(f"  estado tras F10: {r2.get('estado')} conf={r2.get('confianza')}")

    if r2.get("estado") == "ficha":
        await pf.step(s, "shift_f4", "press_keys", {"keys": ["shift", "f4"]})
        await asyncio.sleep(1.0)
        post2 = pf.shot(hwnd, "post-shift-f4")
        r3 = estado_de(post2)
        print(f"  estado tras Shift+F4: {r3.get('estado')} conf={r3.get('confianza')}")
    elif r2.get("estado") == "cuenta_matriz":
        print("  F10 llevo directo al listado (sin ficha)")
    else:
        raise pf.Halt(f"F10 no llevo a ficha ni a listado (estado={r2.get('estado')})")
    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        print("uso: nav_prefill.py <hwnd> <parte1> <parte2> [--no-nav] [--dry]",
              file=sys.stderr)
        return 2
    try:
        hwnd = int(args[0])
    except ValueError:
        print(f"hwnd invalido: {args[0]}", file=sys.stderr)
        return 2
    p1, p2 = args[1], args[2]
    nav = "--no-nav" not in argv
    dry = "--dry" in argv
    fresh = "--fresh" in argv
    dy = 0
    for a in argv:
        if a.startswith("--dy="):
            dy = int(a.split("=", 1)[1])

    async def go():
        async with connect() as s:
            try:
                return await _run(s, hwnd, p1, p2, nav, dry, dy, fresh)
            except pf.Halt as e:
                print(f"  halt: {e}")
                return 1

    return asyncio.run(go())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
