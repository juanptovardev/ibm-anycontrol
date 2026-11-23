import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MATRIZ_TOKEN", None)
            t1 = ui._token()
            t2 = ui._token()
        self.assertEqual(t1, t2)
        self.assertGreaterEqual(len(t1), ui.TOKEN_MIN)

    def test_acl_falla_impide_crear_token_inseguro(self):
        with patch("ui.os.name", "nt"), patch.dict(os.environ, {"USERNAME": "test-user"}), \
                patch("ui.subprocess.run", return_value=type("R", (), {"returncode": 1, "stderr": "denied", "stdout": ""})()):
            with self.assertRaisesRegex(RuntimeError, "ACL"):
                ui._acl(Path(self.td.name) / "ui_token.txt")

    def test_token_corto_se_rota(self):
        p = Path(self.td.name) / "ui_token.txt"
        p.write_text("abc", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MATRIZ_TOKEN", None)
            token = ui._token()
        self.assertGreaterEqual(len(token), ui.TOKEN_MIN)
        self.assertEqual(p.read_text(encoding="utf-8"), token)
        self.assertNotEqual(token, "abc")

    def test_token_desde_env(self):
        with patch.dict(os.environ, {"MATRIZ_TOKEN": "t" * ui.TOKEN_MIN}):
            self.assertEqual(ui._token(), "t" * ui.TOKEN_MIN)

    def test_token_env_corto_se_ignora(self):
        with patch.dict(os.environ, {"MATRIZ_TOKEN": "secreto"}):
            token = ui._token()
        self.assertGreaterEqual(len(token), ui.TOKEN_MIN)
        self.assertNotEqual(token, "secreto")

    def _handler(self, path, header=None):
        h = ui.Handler.__new__(ui.Handler)
        h.path = path
        h.headers = header or {}
        return h

    def test_autorizado_con_token_correcto(self):
        ui.TOKEN = "abc"
        self.assertTrue(self._handler("/api/estado", {"X-Token": "abc"})._autorizado())

    def test_query_token_ya_no_autoriza(self):
        ui.TOKEN = "abc"
        self.assertFalse(self._handler("/api/estado?k=abc")._autorizado())

    def test_no_autorizado_sin_token(self):
        ui.TOKEN = "abc"
        self.assertFalse(self._handler("/api/estado")._autorizado())

    def test_no_autorizado_token_equivocado(self):
        ui.TOKEN = "abc"
        self.assertFalse(self._handler("/api/estado?k=malo")._autorizado())

    def test_autorizado_por_header(self):
        ui.TOKEN = "abc"
        self.assertTrue(self._handler("/img", {"X-Token": "abc"})._autorizado())

    def test_bind_local_por_defecto_y_lan_opt_in(self):
        with patch.dict(os.environ, {"MATRIZ_UI_BIND": ""}):
            self.assertEqual(ui.bind_host(), "127.0.0.1")
        with patch.dict(os.environ, {"MATRIZ_UI_BIND": "0.0.0.0"}):
            self.assertEqual(ui.bind_host(), "0.0.0.0")

    def test_rate_limit_20_por_minuto(self):
        ui._HITS.clear()
        for i in range(20):
            self.assertTrue(ui.rate_ok("192.0.2.1", ahora=100 + i))
        self.assertFalse(ui.rate_ok("192.0.2.1", ahora=120))
        self.assertTrue(ui.rate_ok("192.0.2.1", ahora=161))

    def test_matar_exige_confirmacion(self):
        self.assertTrue(ui.confirmado_matar("/api/matar?confirm=1"))
        self.assertFalse(ui.confirmado_matar("/api/matar"))
        self.assertFalse(ui.confirmado_matar("/api/matar?confirm=0"))

    def test_html_no_expone_token_en_url(self):
        self.assertNotIn("__TOKEN__", ui.HTML)
        self.assertNotIn("?k=", ui.HTML)

    def test_reanudar_usa_el_contrato_libre(self):
        self.assertEqual(ui.normaliza_accion("reanudar"), "libre")
        self.assertEqual(ui.normaliza_accion("pausar"), "pausar")
        self.assertEqual(ui.normaliza_accion("detener"), "detener")

    def test_accion_invalida_rechazada(self):
        with self.assertRaises(ValueError):
            ui.normaliza_accion("continuar")

    def test_ledger_expone_contador_de_reanudacion(self):
        import csv
        with (Path(self.td.name) / "ledger.csv").open(
                "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "estado", "paginas_vistas",
                                               "filas_copiadas"], delimiter=";")
            w.writeheader()
            w.writerow({"id": "D05", "estado": "en_curso",
                        "paginas_vistas": 7, "filas_copiadas": 45})
        row = ui.estado()["ledger"][0]
        self.assertEqual(row["paginas_vistas"], "7")
        self.assertEqual(row["filas_copiadas"], "45")


if __name__ == "__main__":
    unittest.main()
