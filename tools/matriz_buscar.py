"""Modulo 1: buscar la direccion en el formulario del 5250.

Reglas del emulador que aqui estan codificadas (medidas, no supuestas):
- el campo Nombre se limpia con la secuencia del operador: clic en la celda 1,
  derecha, izquierda, Suprimir y el + del bloque numerico (que deja el cursor
  en Calle);
- el + del BLOQUE NUMERICO (numpad add) es el avance de campo;
- `home` NO va al inicio del campo (salta al primer campo del registro) y
  `delete` no borra de forma fiable: por eso no se usan;
- la busqueda escribe parte1, parte2, Comunidad y Division antes del F10.
"""

import asyncio
import os
import time

import preflight_auto as pf
import rows as rowdet
from estado import captura, ocr_text

NOMBRE = 0
CALLE = 1
CASA = 2
INK_MIN = pf.INK_MIN
# Verbosidad: con MATRIZ_VERBOSE=1 se lee el formulario entero antes del F10.
# La constante vivia en loop.py y al mover verifica_texto a este modulo se
# quedo atras: el NameError solo aparecia en vivo (ningun test ejecutaba esta
# funcion de verdad). El chequeo estatico de nombres libres lo detecta.
VERBOSE = os.environ.get("MATRIZ_VERBOSE") == "1"

async def buscar(s, hwnd: int, det: list, parte1: str, parte2: str) -> None:
    """Macro de busqueda validada: clic, flechas, step1, +, step2, +, F10.

    Limpieza del campo Nombre con la secuencia del operador (28/10): un clic
    en la celda 1, flecha derecha, flecha izquierda, Suprimir y el '+' del
    bloque numerico. Eso limpia el campo y salta al siguiente (Calle). Antes se
    sobrescribia con 24 espacios: 5.5 s por direccion y fragil.
    """
    nombre = det[NOMBRE]
    calle = det[CALLE]
    # UN solo clic pegado al borde izquierdo del subrayado (= celda 1). Dos clics
    # al mismo punto se leen como DOBLE CLIC, seleccionan el campo entero y dejan
    # el teclado inhibido (bug medido el 27/10). No reintroducir el segundo clic.
    await pf.step(s, "nombre_clic", "click_point",
                  {"x": nombre["field_x"] + 2, "y": nombre["cy"]})
    await asyncio.sleep(0.2)
    # derecha + izquierda + Suprimir en UNA sola llamada: el MCP cobra por
    # llamada (foco + latencia ~150 ms) y la secuencia es la misma.
    await pf.step(s, "nombre_sentar", "press_keys",
                  {"keys": ["right", "left", "delete"]})
    # El '+' del bloque numerico (Field Exit) deja el cursor en Calle.
    await pf.step(s, "nombre_mas", "press_keys", {"keys": ["add"]})
    await asyncio.sleep(0.2)
    await pf.step(s, "calle_clic", "click_point",
                  {"x": calle["field_x"] + 2, "y": calle["cy"]})
    await asyncio.sleep(0.2)
    await pf.step(s, "calle_sentar", "press_keys",
                  {"keys": ["right", "left", "delete"]})
    await pf.step(s, "step1", "write_to_anydesk", {"command": parte1})
    await pf.step(s, "plus1", "press_keys", {"keys": ["add"]})
    await pf.step(s, "step2", "write_to_anydesk", {"command": parte2})
    await pf.step(s, "plus2", "press_keys", {"keys": ["add"]})
    # Prellenado del bloque, validado en vivo el 27/10: tras el "+" el cursor
    # cae en Comunidad (BOG) y su "+" hace el ultimo salto a Division (TVC).
    # Sin esto F10 busca con Comunidad/Division vacias y no encuentra nada.
    await pf.step(s, "bog", "write_to_anydesk", {"command": "BOG"})
    await pf.step(s, "plus3", "press_keys", {"keys": ["add"]})
    await pf.step(s, "tvc", "write_to_anydesk", {"command": "TVC"})


async def verifica_texto(hwnd: int) -> tuple[bool, str]:
    """B2: el texto quedo en Calle.

    No se exige Nombre vacio: el formulario conserva texto de busquedas
    anteriores y este emulador no borra (delete no borra, home salta al primer
    campo). Si Calle tiene tinta, la escritura llego donde tenia que llegar.

    El OCR del formulario entero se paga SOLO cuando algo va mal (o con
    MATRIZ_VERBOSE=1): leerlo costaba ~1 s por direccion y era un print.
    """
    img, _vp, det = rowdet.detect(hwnd)
    if len(det) < 3:
        return False, "no se detectaron filas del formulario"
    tinta_calle = pf.ink(img, det[CALLE])
    if tinta_calle < INK_MIN or VERBOSE:
        # Un residuo en No.Casa o Comunidad solo se descubre asi.
        print(f"FORMULARIO antes de F10: {ocr_text(img)[:400]}", flush=True)
    if tinta_calle < INK_MIN:
        return False, f"Calle vacio (tinta {tinta_calle})"
    return True, f"Calle ok (tinta {tinta_calle})"


