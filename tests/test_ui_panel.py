import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import ui  # noqa: E402


class TestUIPanel(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._orig_datos = ui.DATOS
        ui.DATOS = Path(self.td.name)

    def tearDown(self):
        ui.DATOS = self._orig_datos
        self.td.cleanup()

    def test_token_se_genera_y_persiste(self):
        os.environ.pop("MATRIZ_TOKEN", None)
        t1 = ui._token()
        t2 = ui._token()
        self.assertEqual(t1, t2)
        self.assertEqual(len(t1), 8)

    def test_token_desde_env(self):
        os.environ["MATRIZ_TOKEN"] = "secreto"
        self.assertEqual(ui._token(), "secreto")
        os.environ.pop("MATRIZ_TOKEN", None)

    def _handler(self, path, header=None):
        h = ui.Handler.__new__(ui.Handler)
        h.path = path
        h.headers = header or {}
        return h

    def test_autorizado_con_token_correcto(self):
        ui.TOKEN = "abc"
        self.assertTrue(self._handler("/api/estado?k=abc")._autorizado())

    def test_no_autorizado_sin_token(self):
        ui.TOKEN = "abc"
        self.assertFalse(self._handler("/api/estado")._autorizado())

    def test_no_autorizado_token_equivocado(self):
        ui.TOKEN = "abc"
        self.assertFalse(self._handler("/api/estado?k=malo")._autorizado())

    def test_autorizado_por_header(self):
        ui.TOKEN = "abc"
        self.assertTrue(self._handler("/img", {"X-Token": "abc"})._autorizado())


if __name__ == "__main__":
    unittest.main()