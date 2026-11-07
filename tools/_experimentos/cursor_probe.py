"""Mide donde cae de verdad el cursor 5250 tras un click_point.

El cursor del terminal parpadea: dos capturas separadas ~600ms difieren
solo en su celda (y en el reloj). El bloque pequeno que cambia es el
cursor, asi que sirve para calibrar el mapeo click -> pixel sin teclear
nada y sin ensuciar el formulario.

Uso: python tools/cursor_probe.py <hwnd> <x> <y>
"""
import asyncio
import sys
import time

import native_shot
import rows as rowdet
from _mcp import call, connect, need_hwnd


def clusters(a, b, max_area=400, max_dim=40):
    """Cajas de pixeles distintos entre dos capturas (filtra el reloj)."""
    if a.size != b.size:
        return []
    pa, pb = a.load(), b.load()
    seen = set()
    boxes = []
    for y in range(a.height):
        for x in range(a.width):
            if pa[x, y] == pb[x, y] or (x, y) in seen:
                continue
            x0 = x1 = x
            y0 = y1 = y
            stack = [(x, y)]
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                x0, x1 = min(x0, cx), max(x1, cx)
                y0, y1 = min(y0, cy), max(y1, cy)
                if (x1 - x0) > max_dim or (y1 - y0) > max_dim:
                    break
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if not (0 <= nx < a.width and 0 <= ny < a.height):
                            continue
                        if (nx, ny) in seen:
                            continue
                        if pa[nx, ny] != pb[nx, ny]:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
            area = (x1 - x0 + 1) * (y1 - y0 + 1)
            if 4 <= area <= max_area:
                boxes.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1,
                              "cx": (x0 + x1) // 2, "cy": (y0 + y1) // 2,
                              "area": area})
    return boxes


async def main(hwnd: int, x: int, y: int) -> int:
    async with connect() as s:
        for label, name, args in (
            ("focus_click_off", "set_focus_click_mode", {"enabled": False}),
            ("pin", "select_anydesk_window", {"hwnd": hwnd}),
            ("click", "click_point", {"x": x, "y": y}),
        ):
            res = await call(s, name, args)
            print(f"{label}: {'FAIL ' + res['text'] if res['isError'] else 'ok'}")
            if res["isError"]:
                return 1

        _, vp, det = rowdet.detect(hwnd)
        print(f"viewpoint vp={vp['hwnd']} img={vp['width']}x{vp['height']} filas={len(det)}")
        a = native_shot.grab(vp["hwnd"])
        time.sleep(0.65)
        b = native_shot.grab(vp["hwnd"])
        native_shot.save(a, "probe-a")
        native_shot.save(b, "probe-b")
        boxes = clusters(a, b)
        print(f"clusters={len(boxes)}")
        for c in boxes:
            print(f"  box x={c['x0']}..{c['x1']} y={c['y0']}..{c['y1']} "
                  f"centro=({c['cx']},{c['cy']}) area={c['area']}")
        if boxes:
            cur = min(boxes, key=lambda c: c["area"])
            print(f"click pedido=({x},{y}) cursor medido=({cur['cx']},{cur['cy']}) "
                  f"delta=({cur['cx'] - x},{cur['cy'] - y})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: cursor_probe.py <hwnd> <x> <y>", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))))
