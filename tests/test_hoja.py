"""Contrato de columnas de la hoja (T3)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import click_sel  # noqa: E402
import hoja  # noqa: E402


def _w(texto, x=100, y=10, w=60, h=14):
    return (texto, x, y, w, h)


CABECERA_OK = [_w("DIRECCION", 40), _w("EDIFICIO", 300),
               _w("DIRECCION", 420), _w("SUSCRIPTOR", 700)]


class TestVerifica(unittest.TestCase):
    def test_hoja_correcta_pasa(self):
        with patch.object(click_sel, "_words", return_value=CABECERA_OK):
            ok, nota = hoja.verifica(object())
        self.assertTrue(ok)
        self.assertIn("cabecera ok", nota)

    def test_falta_una_cabecera_bloquea(self):
        words = [_w("DIRECCION", 40), _w("EDIFICIO", 300)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.verifica(object())
        self.assertFalse(ok)
        self.assertIn("SUSCRIPTOR", nota)

    def test_ocr_vacio_no_bloquea(self):
        with patch.object(click_sel, "_words", return_value=[]):
            ok, nota = hoja.verifica(object())
        self.assertTrue(ok)
        self.assertIn("fallo abierto", nota)

    def test_sin_captura_no_bloquea(self):
        ok, nota = hoja.verifica(None)
        self.assertTrue(ok)
        self.assertIn("fallo abierto", nota)

    def test_otra_pestana_sin_cabeceras_no_bloquea(self):
        words = [_w("Hola"), _w("Mundo"), _w("Borrador"), _w("temp")]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.verifica(object())
        self.assertTrue(ok)
        self.assertIn("fallo abierto", nota)

    def test_cabeceras_en_filas_distintas_bloquea(self):
        words = [_w("DIRECCION", 40, 10), _w("EDIFICIO", 300, 500),
                 _w("SUSCRIPTOR", 700, 900)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.verifica(object())
        self.assertFalse(ok)
        self.assertIn("misma fila", nota)

    def test_tolera_tilde_y_minusculas(self):
        words = [_w("dirección", 40), _w("Edificio", 300),
                 _w("Suscriptor", 700)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.verifica(object())
        self.assertTrue(ok)

    def test_esperadas_configurables(self):
        words = [_w("TITULO", 40)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.verifica(object(), esperadas=("TITULO",))
        self.assertTrue(ok)


class TestClave(unittest.TestCase):
    def test_limpia_ruido(self):
        self.assertEqual(hoja._clave("DIRECCIÓN."), "DIRECCIÓN")
        self.assertEqual(hoja._clave("_Suscriptor_"), "SUSCRIPTOR")


if __name__ == "__main__":
    unittest.main()
