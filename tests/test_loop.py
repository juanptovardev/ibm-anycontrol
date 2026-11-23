"""Tests del ledger: idempotencia y trazabilidad (B6/B7)."""
import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import loop  # noqa: E402
import matriz_ficha  # noqa: E402


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.dir.name) / "ledger.csv"

    def tearDown(self):
        self.dir.cleanup()

    def test_escribe_cabecera_y_fila(self):
        loop.ledger_escribe({"id": "P1", "direccion_parte1": "CR 17B",
                              "direccion_parte2": "175-77", "estado": "ok",
                              "filas_copiadas": 14, "paginas_vistas": 2,
                              "hora_inicio": "10:00:00", "hora_fin": "10:00:12",
                              "notas": "14 filas", "reintentos": 0}, self.ruta)
        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter=";"))
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], "P1")
        self.assertEqual(filas[0]["estado"], "ok")
        self.assertEqual(filas[0]["filas_copiadas"], "14")
        self.assertEqual(list(filas[0].keys()), loop.CAMPOS_LEDGER)

    def test_anade_sin_duplicar_cabecera(self):
        for i in range(3):
            loop.ledger_escribe({"id": f"P{i}", "estado": "ok"}, self.ruta)
        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter=";"))
        self.assertEqual(len(filas), 3)
        self.assertEqual([f["id"] for f in filas], ["P0", "P1", "P2"])

    def test_lectura_toma_la_ultima_fila_del_id(self):
        loop.ledger_escribe({"id": "P1", "estado": "error", "reintentos": 0}, self.ruta)
        loop.ledger_escribe({"id": "P1", "estado": "ok", "reintentos": 1}, self.ruta)
        leido = loop.ledger_leido(self.ruta)
        self.assertEqual(leido["P1"]["estado"], "ok")
        self.assertEqual(leido["P1"]["reintentos"], "1")

    def test_ledger_inexistente_no_rompe(self):
        self.assertEqual(loop.ledger_leido(self.ruta), {})


class TestLeeDireccionesContrato(unittest.TestCase):
    """Un solo contrato de entrada: direcciones.csv, 3 columnas con ';'."""

    def test_tres_columnas_id_acentos_y_ficha(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            ruta.write_text(
                "parte1;parte2;ficha\n"
                "CR 17B;175-77;\n"
                "CLL 45;12-34;Apto 201 Torre Á\n",
                encoding="utf-8",
            )
            filas = matriz_ficha.lee_direcciones(ruta)
        self.assertEqual([f["id"] for f in filas], ["D01", "D02"])
        self.assertEqual(filas[1]["direccion_parte1"], "CLL 45")
        self.assertEqual(filas[1]["direccion_parte2"], "12-34")
        self.assertEqual(filas[1]["ficha"], "Apto 201 Torre Á")
        self.assertEqual(filas[0]["comuna"], "BOG")


if __name__ == "__main__":
    unittest.main()
