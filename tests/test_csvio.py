"""Contrato de escritura atomica de direcciones.csv (WP-03)."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import csvio
import recepcion


class TestCsvio(unittest.TestCase):
    def test_bom_sep_crlf_backup_y_multilinea(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            original = b"parte1;parte2;ficha\r\nVIEJO;1;x\r\n"
            ruta.write_bytes(original)
            filas = [{"parte1": "CR 17B", "parte2": "175-77",
                      "ficha": "Cuenta: 1\nEDIFICIO ÑANDÚ"}]
            csvio.escribe_direcciones(filas, ruta)

            raw = ruta.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"CR 17B;175-77;", raw)
            self.assertEqual((Path(d) / "direcciones.csv.bak").read_bytes(),
                             original)

            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh, delimiter=";"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["parte1"], "CR 17B")
            self.assertIn("ÑANDÚ", rows[0]["ficha"])
            self.assertEqual(len(rows[0]["ficha"].splitlines()), 2)

    def test_replace_fallido_conserva_original_y_limpia_temporal(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            original = b"parte1;parte2;ficha\r\nA;1;\r\n"
            ruta.write_bytes(original)
            with patch.object(csvio.os, "replace",
                              side_effect=PermissionError(13, "locked", str(ruta))):
                with self.assertRaises(PermissionError):
                    csvio.escribe_direcciones(
                        [{"parte1": "B", "parte2": "2", "ficha": "x"}], ruta)
            self.assertEqual(ruta.read_bytes(), original)
            self.assertEqual(list(Path(d).glob("*.tmp")), [])

    def test_round_trip_2168_filas_206_fichas(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            filas = []
            for i in range(1, 2169):
                ficha = "Cuenta: 1\nEDIFICIO ÑANDÚ" if i <= 206 else ""
                filas.append({"parte1": f"CR {i}", "parte2": f"{i}-1",
                              "ficha": ficha})
            csvio.escribe_direcciones(filas, ruta)
            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh, delimiter=";"))
            self.assertEqual(len(rows), 2168)
            self.assertEqual(sum(1 for r in rows if r["ficha"]), 206)
            self.assertIn("ÑANDÚ", rows[0]["ficha"])
            self.assertEqual(rows[-1]["parte1"], "CR 2168")

    def test_recepcion_escribe_usa_el_mismo_contrato(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            filas = [{"parte1": "A", "parte2": "1",
                      "ficha": "linea1\nlinea2"},
                     {"parte1": "B", "parte2": "2", "ficha": ""}]
            recepcion.escribe(filas, ruta)
            raw = ruta.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"A;1;", raw)
            leidas = recepcion.lee(ruta)
            self.assertEqual(len(leidas), 2)
            self.assertEqual(leidas[0]["ficha"], "linea1\nlinea2")


if __name__ == "__main__":
    unittest.main()
