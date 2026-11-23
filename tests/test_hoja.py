"""Identidad de la hoja destino (T3): titulo, URL, pestana y cabeceras."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import click_sel  # noqa: E402
import hoja  # noqa: E402


def _w(texto, x=100, y=200, w=60, h=14):
    return (texto, x, y, w, h)


TOP_OK = [_w("LIMPIEZA RR", 20, 8), _w("docs.google.com", 300, 60),
          _w("temp borrador", 100, 740)]

CABECERA_OK = [_w("DIRECCION", 40), _w("EDIFICIO", 300),
               _w("DIRECCION", 420), _w("SUSCRIPTOR", 700)]

PANTALLA_OK = TOP_OK + CABECERA_OK


class TestIdentidad(unittest.TestCase):
    def test_hoja_correcta_pasa(self):
        with patch.object(click_sel, "_words", return_value=PANTALLA_OK):
            ok, nota = hoja.identidad(object())
        self.assertTrue(ok)
        self.assertIn("identidad ok", nota)

    def test_falta_una_cabecera_bloquea(self):
        words = TOP_OK + [_w("DIRECCION", 40), _w("EDIFICIO", 300)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("SUSCRIPTOR", nota)

    def test_ocr_vacio_bloquea(self):
        with patch.object(click_sel, "_words", return_value=[]):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("fail-closed", nota)

    def test_sin_captura_bloquea(self):
        ok, nota = hoja.identidad(None)
        self.assertFalse(ok)
        self.assertIn("fail-closed", nota)

    def test_otra_pestana_sin_cabeceras_bloquea(self):
        words = TOP_OK + [_w("Hola"), _w("Mundo"), _w("Borrador"), _w("temp")]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("ninguna cabecera", nota)

    def test_cabeceras_en_filas_distintas_bloquea(self):
        words = TOP_OK + [_w("DIRECCION", 40, 200), _w("EDIFICIO", 300, 500),
                          _w("SUSCRIPTOR", 700, 900)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("misma fila", nota)

    def test_tolera_tilde_y_minusculas(self):
        words = TOP_OK + [_w("dirección", 40, 200), _w("Edificio", 300, 210),
                          _w("Suscriptor", 700, 205)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertTrue(ok)

    def test_esperadas_configurables(self):
        words = TOP_OK + [_w("TITULO", 40)]
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object(), esperadas=("TITULO",))
        self.assertTrue(ok)

    def test_titulo_incorrecto_bloquea(self):
        words = [_w("OTRA HOJA", 20, 8), _w("docs.google.com", 300, 60),
                 _w("temp borrador", 100, 740)] + CABECERA_OK
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("titulo", nota)

    def test_url_incorrecta_bloquea(self):
        words = [_w("LIMPIEZA RR", 20, 8), _w("example.com", 300, 60),
                 _w("temp borrador", 100, 740)] + CABECERA_OK
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("URL", nota)

    def test_pestana_incorrecta_bloquea(self):
        words = [_w("LIMPIEZA RR", 20, 8), _w("docs.google.com", 300, 60)] + CABECERA_OK
        with patch.object(click_sel, "_words", return_value=words):
            ok, nota = hoja.identidad(object())
        self.assertFalse(ok)
        self.assertIn("pestana", nota)

    def test_fail_open_restaura(self):
        with patch.object(click_sel, "_words", return_value=[]):
            ok, nota = hoja.identidad(object(), fail_open=True)
        self.assertTrue(ok)
        self.assertIn("fail-open", nota)

    def test_env_fail_open(self):
        with patch.dict(os.environ, {"HOJA_FAIL_OPEN": "1"}), \
                patch.object(click_sel, "_words", return_value=[]):
            ok, nota = hoja.identidad(object())
        self.assertTrue(ok)
        self.assertIn("fail-open", nota)


class TestClave(unittest.TestCase):
    def test_limpia_ruido(self):
        self.assertEqual(hoja._clave("DIRECCIÓN."), "DIRECCIÓN")
        self.assertEqual(hoja._clave("_Suscriptor_"), "SUSCRIPTOR")


if __name__ == "__main__":
    unittest.main()
