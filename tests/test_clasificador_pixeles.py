"""Clasificador por pixeles: 5250 vs navegador, sin pagar el OCR.

Medido el 03/11 sobre 228 capturas reales de evidencia/:
  - 5250 (fondo negro con texto verde): 79,7..82,2 por ciento de pixeles
    casi negros y 0,3..9,5 de casi blancos.
  - Hoja de Google en Chrome: 3,6..3,8 de casi negros y 79,0..82,7 de
    casi blancos.
Los dos grupos no se solapan: con el umbral del 40 por ciento el margen es
de 4x. Aqui se comprueba con imagenes sinteticas.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from PIL import Image

import estado


class TestPixelesPantalla(unittest.TestCase):
    def test_negro_total(self):
        self.assertEqual(estado.pixeles_pantalla(Image.new("RGB", (40, 30), (0, 0, 0))),
                         (100, 0))

    def test_blanco_total(self):
        self.assertEqual(estado.pixeles_pantalla(Image.new("RGB", (40, 30), (255, 255, 255))),
                         (0, 100))

    def test_verde_sobre_negro_no_cuenta_como_blanco(self):
        img = Image.new("RGB", (40, 30), (0, 0, 0))
        for y in range(0, 30, 3):
            for x in range(0, 40, 4):
                img.putpixel((x, y), (0, 254, 0))
        negros, blancos = estado.pixeles_pantalla(img)
        self.assertGreater(negros, 70)
        self.assertEqual(blancos, 0)


class TestTipoPixeles(unittest.TestCase):
    def test_fondo_negro_es_ibm(self):
        self.assertEqual(estado.tipo_pixeles(Image.new("RGB", (40, 30), (0, 0, 0))),
                         "ibm")

    def test_fondo_blanco_es_navegador(self):
        self.assertEqual(
            estado.tipo_pixeles(Image.new("RGB", (40, 30), (255, 255, 255))),
            "navegador")

    def test_gris_no_concluye(self):
        self.assertIsNone(
            estado.tipo_pixeles(Image.new("RGB", (40, 30), (128, 128, 128))))

    def test_mezcla_deja_la_decision_al_ocr(self):
        # 50 % negro + 50 % blanco: ni una regla ni la otra.
        img = Image.new("RGB", (40, 30), (0, 0, 0))
        for y in range(15):
            for x in range(40):
                img.putpixel((x, y), (255, 255, 255))
        self.assertIsNone(estado.tipo_pixeles(img))

    def test_umbral_de_40_por_ciento(self):
        self.assertEqual(estado._UMBRAL_PIXELES, 40)


if __name__ == "__main__":
    unittest.main()
