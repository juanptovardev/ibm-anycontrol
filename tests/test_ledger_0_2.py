"""0.2: el ledger es una tabla (una fila por direccion) con el formato de Excel.

El ledger antes era append-only: una fila por pagina pegada, asi que la misma
direccion aparecia repetida hacia abajo y el fichero no se podia leer como
tabla. Ahora es el estado actual (upsert por id) y el historial queda en
datos/traza.jsonl.
"""
import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import loop  # noqa: E402


class TestLedgerComoTabla(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.dir.name) / "ledger.csv"

    def tearDown(self):
        self.dir.cleanup()

    def _filas(self):
        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    def test_una_fila_por_direccion(self):
        for _ in range(3):
            loop.ledger_escribe({"id": "D01", "estado": "en_curso",
                                  "paginas_vistas": 3}, self.ruta)
        filas = self._filas()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], "D01")
        self.assertEqual(filas[0]["paginas_vistas"], "3")

    def test_una_fila_por_direccion_no_es_una_lista_vertical(self):
        # 5 direcciones x 10 paginas: el fichero tiene 5 filas, no 50.
        for i in range(5):
            for pag in range(1, 11):
                loop.ledger_escribe({"id": f"D0{i + 1}", "estado": "en_curso",
                                      "paginas_vistas": pag}, self.ruta)
        filas = self._filas()
        self.assertEqual(len(filas), 5)
        self.assertEqual([f["id"] for f in filas],
                         ["D01", "D02", "D03", "D04", "D05"])

    def test_formato_excel_en_espanol(self):
        loop.ledger_escribe({"id": "D01", "estado": "ok"}, self.ruta)
        crudo = self.ruta.read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"), "falta el BOM")
        self.assertEqual(crudo.count(b"\n") - crudo.count(b"\r\n"), 0,
                         "hay LF sueltos")
        self.assertIn(b"\r\n", crudo)
        cabecera = crudo.splitlines()[0].replace(b"\xef\xbb\xbf", b"")
        self.assertTrue(cabecera.startswith(b"id;direccion_parte1;direccion_parte2"),
                        f"cabecera inesperada: {cabecera!r}")

    def test_el_upsert_reemplaza_la_fila_y_conserva_el_orden(self):
        loop.ledger_escribe({"id": "D01", "estado": "en_curso",
                              "paginas_vistas": 2}, self.ruta)
        loop.ledger_escribe({"id": "D02", "estado": "ok"}, self.ruta)
        loop.ledger_escribe({"id": "D01", "estado": "ok",
                              "paginas_vistas": 9}, self.ruta)
        filas = self._filas()
        self.assertEqual([f["id"] for f in filas], ["D01", "D02"])
        self.assertEqual(filas[0]["estado"], "ok")
        self.assertEqual(filas[0]["paginas_vistas"], "9")

    def test_ledger_en_curso_solo_las_a_medias(self):
        loop.ledger_escribe({"id": "D01", "estado": "en_curso",
                              "paginas_vistas": 8}, self.ruta)
        loop.ledger_escribe({"id": "D02", "estado": "ok"}, self.ruta)
        en_curso = loop.ledger_en_curso(self.ruta)
        self.assertEqual(list(en_curso.keys()), ["D01"])
        self.assertEqual(en_curso["D01"]["paginas_vistas"], "8")

    def test_lee_el_ledger_antiguo_con_coma(self):
        # Migracion: el fichero viejo (coma, sin BOM) se lee igual y la
        # siguiente escritura lo deja en el formato nuevo.
        with open(self.ruta, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(loop.CAMPOS_LEDGER)
            w.writerow(["D01", "CR 17B", "175-77", "BOG", "", "ok", "10",
                        "150", "", "", "", "", "0"])
            w.writerow(["D01", "CR 17B", "175-77", "BOG", "", "en_curso", "3",
                        "45", "", "", "", "", "0"])
        leido = loop.ledger_leido(self.ruta)
        self.assertEqual(list(leido.keys()), ["D01"])
        loop.ledger_escribe({"id": "D01", "estado": "ok"}, self.ruta)
        crudo = self.ruta.read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(len(self._filas()), 1)

    def test_no_deja_el_temporal(self):
        loop.ledger_escribe({"id": "D01", "estado": "ok"}, self.ruta)
        self.assertFalse(self.ruta.with_suffix(".csv.tmp").exists())


if __name__ == "__main__":
    unittest.main()
