"""Tests de la decision de paginacion (pura, sin MCP ni capturas)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import pagina  # noqa: E402


class TestDecide(unittest.TestCase):
    def test_listado_normal_sigue(self):
        self.assertEqual(pagina.decide("cuenta_matriz"), "seguir")

    def test_fin_de_libro_termina(self):
        self.assertEqual(pagina.decide("fin_libro"), "fin")

    def test_pantalla_no_ibm_aborta(self):
        self.assertEqual(pagina.decide(None, no_ibm=True), "abortar")

    def test_sin_clasificar_aborta(self):
        self.assertEqual(pagina.decide(None), "abortar")

    def test_formulario_inesperado_aborta(self):
        # Si AvPág devolvio al formulario, la posicion se perdio: no se sigue.
        self.assertEqual(pagina.decide("formulario"), "abortar")

    def test_error_aborta(self):
        self.assertEqual(pagina.decide("error"), "abortar")

    def test_fin_gana_sobre_no_ibm_ausente(self):
        self.assertEqual(pagina.decide("fin_libro", no_ibm=False), "fin")


if __name__ == "__main__":
    unittest.main()
