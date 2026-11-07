"""Tests de las funciones puras de cp.py (sin MCP, sin pantalla).

Run: python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from PIL import Image, ImageDraw

import cp

AMARILLO = (213, 214, 92)   # color medido del borde/texto seleccionado en el 5250
VERDE = (0, 254, 0)         # texto normal del terminal


def lienzo(w=1255, h=663, color=(0, 0, 0)):
    return Image.new("RGB", (w, h), color)


class TestSelBox(unittest.TestCase):
    def test_pantalla_sin_seleccion_devuelve_none(self):
        caja, alto = cp.sel_box(lienzo())
        self.assertIsNone(caja)
        self.assertEqual(alto, 0)

    def test_texto_verde_normal_no_es_seleccion(self):
        img = lienzo()
        d = ImageDraw.Draw(img)
        for y in range(200, 520, 12):
            d.line([(250, y), (930, y)], fill=VERDE, width=2)
        caja, alto = cp.sel_box(img)
        self.assertIsNone(caja)
        self.assertEqual(alto, 0)

    def test_bloque_seleccionado_amarillo_se_detecta(self):
        img = lienzo()
        d = ImageDraw.Draw(img)
        d.rectangle([245, 208, 935, 530], outline=AMARILLO, width=2)
        for y in range(220, 520, 20):
            d.line([(250, y), (930, y)], fill=AMARILLO, width=6)
        caja, alto = cp.sel_box(img)
        self.assertIsNotNone(caja)
        self.assertGreaterEqual(caja[2] - caja[0], cp.SEL_MIN_ANCHO)
        self.assertGreaterEqual(alto, cp.SEL_MIN_ALTO)

    def test_banda_angosta_no_es_seleccion(self):
        img = lienzo()
        d = ImageDraw.Draw(img)
        d.rectangle([245, 208, 400, 530], outline=AMARILLO, width=2)
        for y in range(220, 520, 20):
            d.line([(250, y), (395, y)], fill=AMARILLO, width=6)
        caja, alto = cp.sel_box(img)
        self.assertIsNone(caja)
        self.assertEqual(alto, 0)

    def test_cabecera_y_barra_de_tareas_se_ignoran(self):
        img = lienzo()
        d = ImageDraw.Draw(img)
        d.line([(0, 100), (1254, 100)], fill=AMARILLO, width=4)    # cabecera
        d.line([(0, 650), (1254, 650)], fill=AMARILLO, width=4)    # barra inferior
        caja, alto = cp.sel_box(img)
        self.assertIsNone(caja)
        self.assertEqual(alto, 0)


class TestConstantesDelOperador(unittest.TestCase):
    def test_bloque_congelado(self):
        """7 abajo, 72 derecha, 14 abajo: si cambia, es una decision, no un typo."""
        self.assertEqual(cp.BAJAR_INICIO, 7)
        self.assertEqual(cp.ANCHO, 72)
        self.assertEqual(cp.ALTO, 14)

    def test_puertas_declaradas(self):
        self.assertEqual(cp.SEL_MIN_ANCHO, 500)
        self.assertEqual(cp.SEL_MIN_ALTO, 150)
        self.assertEqual(cp.SEL_ROW_MIN, 300)
        self.assertEqual(cp.SEL_COL_MIN, 100)
        self.assertEqual(cp.PASTE_MIN_DIFF, 3000)


if __name__ == "__main__":
    unittest.main()
