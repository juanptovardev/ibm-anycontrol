import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import loop as L


class TestEsCorte(unittest.TestCase):
    """_es_corte decide si un fallo es recuperable (corte de AnyDesk)."""

    def test_g2_no_llego_a_la_hoja_es_corte(self):
        self.assertTrue(L._es_corte(
            {"estado": "error", "notas": "halt: G2 no se pudo llegar a la hoja: no se pega"}))

    def test_b0_sin_conexion_es_corte(self):
        self.assertTrue(L._es_corte(
            {"estado": "error", "notas": "B0 sin conexion AnyDesk (dialogo de licencia)"}))

    def test_b3_estado_es_corte(self):
        self.assertTrue(L._es_corte(
            {"estado": "error", "notas": "B3 estado error"}))

    def test_foco_perdido_es_corte(self):
        self.assertTrue(L._es_corte(
            {"estado": "error", "notas": "halt: ctrl_c: AnyDesk no esta en primer plano"}))

    def test_no_encontrado_no_es_corte(self):
        self.assertFalse(L._es_corte({"estado": "no_encontrado", "notas": "sin coincidencia"}))

    def test_ok_no_es_corte(self):
        self.assertFalse(L._es_corte({"estado": "ok", "notas": "1 bloques, 15 filas"}))

    def test_b2_no_es_corte(self):
        self.assertFalse(L._es_corte({"estado": "error", "notas": "B2 el texto quedo en Nombre"}))

    def test_pegado_dudoso_no_es_corte(self):
        self.assertFalse(L._es_corte({"estado": "pegado_dudoso", "notas": "halt: G3 pegado no visto"}))


if __name__ == "__main__":
    unittest.main()