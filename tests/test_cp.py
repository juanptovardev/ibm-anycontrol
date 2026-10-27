"""Tests de las funciones puras de cp.py (sin MCP, sin pantalla).

Run: python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from PIL import Image, ImageDraw

import cp


def lienzo(w=200, h=100, color=(0, 0, 0)):
    return Image.new("RGB", (w, h), color)


class TestBboxCambio(unittest.TestCase):
    def test_sin_cambios_devuelve_none(self):
        a = lienzo()
        caja, densidad = cp.bbox_cambio(a, a.copy())
        self.assertIsNone(caja)
        self.assertEqual(densidad, 0.0)

    def test_rectangulo_macizo(self):
        a = lienzo()
        b = a.copy()
        ImageDraw.Draw(b).rectangle([20, 10, 119, 59], fill=(255, 255, 255))
        caja, densidad = cp.bbox_cambio(a, b)
        self.assertEqual(caja, (20, 10, 120, 60))
        self.assertGreater(densidad, 0.95)

    def test_cambio_disperso_baja_la_densidad(self):
        a = lienzo()
        b = a.copy()
        d = ImageDraw.Draw(b)
        for x in range(0, 200, 20):
            d.point((x, x % 100), fill=(255, 255, 255))
        caja, densidad = cp.bbox_cambio(a, b)
        self.assertIsNotNone(caja)
        self.assertLess(densidad, 0.10)

    def test_ruido_bajo_el_umbral_se_ignora(self):
        a = lienzo()
        b = lienzo(color=(cp.DIFF_UMBRAL - 5, cp.DIFF_UMBRAL - 5, cp.DIFF_UMBRAL - 5))
        caja, _densidad = cp.bbox_cambio(a, b)
        self.assertIsNone(caja)


class TestConstantesDelOperador(unittest.TestCase):
    def test_bloque_congelado(self):
        """7 abajo, 72 derecha, 14 abajo: si cambia, es una decision, no un typo."""
        self.assertEqual(cp.BAJAR_INICIO, 7)
        self.assertEqual(cp.ANCHO, 72)
        self.assertEqual(cp.ALTO, 14)


if __name__ == "__main__":
    unittest.main()
