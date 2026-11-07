"""Tests del vigia: busqueda del boton por texto (puro, sin ventanas)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import vigia  # noqa: E402


def dlg(botones):
    return {"hwnd": 1, "titulo": "Conexion finalizada", "botones": botones}


class TestBoton(unittest.TestCase):
    def test_encuentra_repetir(self):
        self.assertEqual(vigia.boton(dlg({"Repetir": 286, "OK": 287}), "Repetir"), 286)

    def test_sin_distinguir_mayusculas(self):
        self.assertEqual(vigia.boton(dlg({"REPETIR": 286}), "repetir"), 286)

    def test_etiqueta_ausente(self):
        self.assertEqual(vigia.boton(dlg({"OK": 287}), "Repetir"), 0)

    def test_dialogo_vacio(self):
        self.assertEqual(vigia.boton({}, "Repetir"), 0)

    def test_no_confunde_ok_con_repetir(self):
        self.assertEqual(vigia.boton(dlg({"OK": 287, "Repetir": 286}), "OK"), 287)


if __name__ == "__main__":
    unittest.main()
