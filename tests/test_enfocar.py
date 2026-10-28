"""Modulo de foco: Guarantee que AnyDesk queda delante antes de inyectar."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import enfocar


class TestEnfocar(unittest.TestCase):
    def setUp(self):
        enfocar.set_objetivo(None)

    def tearDown(self):
        enfocar.set_objetivo(None)

    def test_sin_objetivo_no_estorba(self):
        """Sin objetivo fijado el camino caliente no toca nada."""
        self.assertTrue(enfocar.asegura())

    def test_sin_ventana_devuelve_error_explicito(self):
        with patch.object(enfocar, "raiz", lambda h=None: None):
            r = enfocar.enfocar()
        self.assertFalse(r["ok"])
        self.assertIn("no hay ventana", r["error"])

    def test_ya_delante_no_hace_trabajo(self):
        with patch.object(enfocar, "raiz", lambda h=None: 123), \
                patch.object(enfocar, "delante", lambda h=None: True):
            self.assertTrue(enfocar.asegura(123))

    def test_reintenta_hasta_que_entra(self):
        llamadas = {"n": 0}

        def fg():
            llamadas["n"] += 1
            return 999 if llamadas["n"] == 1 else 123

        with patch.object(enfocar, "raiz", lambda h=None: 123), \
                patch.object(enfocar.win32gui, "GetForegroundWindow", fg), \
                patch.object(enfocar.win32gui, "IsIconic", lambda h: False):
            r = enfocar.enfocar(123, intentos=3, espera=0)
        self.assertTrue(r["ok"])
        self.assertEqual(r["intentos"], 2)

    def test_si_no_puede_devuelve_el_error(self):
        with patch.object(enfocar, "raiz", lambda h=None: 123), \
                patch.object(enfocar.win32gui, "GetForegroundWindow",
                             lambda: 999), \
                patch.object(enfocar.win32gui, "IsIconic", lambda h: False):
            r = enfocar.enfocar(123, intentos=2, espera=0)
        self.assertFalse(r["ok"])
        self.assertIsNotNone(r["error"])

    def test_asegura_usa_el_objetivo_global(self):
        with patch.object(enfocar, "raiz", lambda h=None: 123), \
                patch.object(enfocar, "delante", lambda h=None: False), \
                patch.object(enfocar, "enfocar") as mock:
            mock.return_value = {"ok": True}
            enfocar.set_objetivo(123)
            self.assertTrue(enfocar.asegura())
            mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
