"""Copia un bloque del listado 5250 y lo pega en la hoja de limpieza.

FLUJO DEL OPERADOR (congelado, no reinterpretar):
  1. En el listado CONSULTA UNIDADES, el cursor esta en su posicion inicial.
  2. Shift mantenido + 7 abajo + 72 derecha + 14 abajo -> bloque de 72
     caracteres (Direccion .. Suscriptor) por 15 filas.
  3. Se suelta Shift. Ctrl+C.
  4. Alt+Tab a la hoja. Ctrl+V.
  5. Ctrl+Shift+Abajo y luego un Abajo -> celda lista para el siguiente pegado.

El bloque copiado no se puede leer desde aqui: el portapapeles vive en la
maquina REMOTA. La unica prueba de que el pegado ocurrio es la diferencia de
pixeles en la captura posterior.

PUERTAS (si una falla, se aborta; no se reintenta a ciegas):
  G0  la pantalla es el listado (estado == cuenta_matriz)
  G1  la seleccion es un rectangulo macizo (densidad y tamano plausibles)
  G2  tras Alt+Tab la pantalla NO es IBM (es la hoja)
  G3  tras Ctrl+V hubo cambio visible (un reintento y nada mas)

Uso:
  python tools/cp.py <hwnd> --dry   # solo selecciona y mide; NO copia
  python tools/cp.py <hwnd>         # copia y pega una vez
"""
import asyncio
import sys

from PIL import Image, ImageChops

import preflight_auto as pf
from _mcp import connect, need_hwnd
from estado import captura, clasificar, ocr_text

# Bloque del operador: 7 abajo, 72 derecha, 14 abajo (15 filas x 72 columnas).
BAJAR_INICIO = 7
ANCHO = 72
ALTO = 14
KEY_DELAY_MS = 45  # 93 teclas -> ~8 s; mas rapido empieza a perder pulsaciones

DIFF_UMBRAL = 40      # nivel de gris para considerar un pixel cambiado
DENSIDAD_MIN = 0.30   # un bloque seleccionado cambia casi toda su area
PASTE_MIN_DIFF = 3000  # pixeles cambiados para aceptar que el pegado ocurrio


def bbox_cambio(a: Image.Image, b: Image.Image) -> tuple[tuple | None, float]:
    """Caja de pixeles cambiados entre dos capturas + densidad dentro de la caja."""
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
    mascara = diff.point(lambda p: 255 if p > DIFF_UMBRAL else 0)
    caja = mascara.getbbox()
    if not caja:
        return None, 0.0
    x0, y0, x1, y1 = caja
    recorte = mascara.crop(caja)
    pintados = sum(1 for v in recorte.getdata() if v)
    area = max(1, (x1 - x0) * (y1 - y0))
    return caja, pintados / area


def texto_superior(img: Image.Image, caja: tuple) -> str:
    """OCR de la primera banda de la seleccion: dice si arriba hay cabecera."""
    x0, y0, _x1, y1 = caja
    banda = img.crop((x0, y0, caja[2], y0 + max(12, (y1 - y0) // 15)))
    texto = ocr_text(banda).strip()
    return texto.splitlines()[0] if texto else ""


async def _seleccionar(s, hwnd: int, antes: Image.Image, dry: bool) -> tuple:
    """Shift + bajadas + derechas + bajadas, soltando el shift al final."""
    teclas = ["shift"] + ["down"] * BAJAR_INICIO + ["right"] * ANCHO + ["down"] * ALTO
    await pf.step(s, "seleccion", "press_keys",
                  {"keys": teclas, "key_delay_ms": KEY_DELAY_MS})
    await asyncio.sleep(0.3)
    img = pf.shot(hwnd, "cp-sel" if not dry else "cp-sel-dry")
    caja, densidad = bbox_cambio(antes, img)
    print(f"G1 caja={caja} densidad={densidad:.2f} "
          f"ancho={(caja[2] - caja[0]) if caja else 0} "
          f"alto={(caja[3] - caja[1]) if caja else 0}", flush=True)
    if not caja:
        raise pf.Halt("G1 no hay seleccion visible")
    if densidad < DENSIDAD_MIN:
        raise pf.Halt(f"G1 seleccion dispersa (densidad {densidad:.2f})")
    print(f"G1 primera linea: {texto_superior(img, caja)!r}", flush=True)
    return img, caja


async def _copiar(s) -> None:
    await pf.step(s, "ctrl_c", "copy_clipboard", {})
    await asyncio.sleep(0.5)


async def _pegar(s, hwnd: int) -> None:
    await pf.step(s, "alt_tab", "press_keys", {"keys": ["alt", "tab"]})
    await asyncio.sleep(1.0)
    st = clasificar(captura(hwnd)[0], usar_jev=False)
    print(f"G2 pantalla destino: estado={st['estado']} error={st.get('error')}", flush=True)
    if st["estado"] is not None:
        raise pf.Halt("G2 tras Alt+Tab sigue siendo la pantalla IBM: no se pega")
    antes = pf.shot(hwnd, "cp-pre-paste")
    await pf.step(s, "ctrl_v", "paste_clipboard", {})
    await asyncio.sleep(1.2)
    despues = pf.shot(hwnd, "cp-post-paste")
    diff = pf.changed_px(antes, despues)
    if diff < PASTE_MIN_DIFF:
        print(f"G3 sin cambio visible ({diff}px): un reintento", flush=True)
        await pf.step(s, "ctrl_v_retry", "paste_clipboard", {})
        await asyncio.sleep(1.2)
        despues = pf.shot(hwnd, "cp-post-paste-retry")
        diff = pf.changed_px(antes, despues)
    print(f"G3 diff={diff}px", flush=True)
    if diff < PASTE_MIN_DIFF:
        raise pf.Halt("G3 el pegado no se ve: Ctrl+C no llego al portapapeles remoto")


async def _posicionar(s, hwnd: int) -> None:
    await pf.step(s, "ctrl_shift_down", "press_keys", {"keys": ["ctrl", "shift", "down"]})
    await pf.step(s, "abajo", "press_keys", {"keys": ["down"]})
    pf.shot(hwnd, "cp-listo")


async def _secuencia(hwnd: int, dry: bool) -> bool:
    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            st = clasificar(captura(hwnd)[0], usar_jev=False)
            print(f"G0 pantalla: estado={st['estado']} conf={st.get('confianza')}", flush=True)
            if st["estado"] != "cuenta_matriz":
                raise pf.Halt(f"G0 se esperaba el listado, hay {st['estado']}")
            antes = pf.shot(hwnd, "cp-antes")
            await _seleccionar(s, hwnd, antes, dry)
            if dry:
                await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
                print("DRY: seleccion medida, no se copio nada", flush=True)
                return True
            await _copiar(s)
            await _pegar(s, hwnd)
            await _posicionar(s, hwnd)
        except pf.Halt as exc:
            # Se captura DENTRO del context manager: si sale de el, anyio lo
            # envuelve en ExceptionGroup y se pierde el motivo.
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    args = [a for a in argv if a != "--dry"]
    hwnd = need_hwnd([sys.argv[0]] + args)
    ok = asyncio.run(_secuencia(hwnd, dry))
    if not ok:
        return 1
    print("OK" + (" (dry)" if dry else ": copiado y pegado"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
