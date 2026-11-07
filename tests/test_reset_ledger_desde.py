"""reset_ledger --desde=ID: pone en pendiente las direcciones de ese id en adelante.

Sirve cuando una direccion quedo mal pegada (el cursor se fue al final de la
hoja) y hay que rehacerla desde la pagina 1. Las de antes se dejan como estan.
"""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import reset_ledger as rl  # noqa: E402


class TestReiniciaDesde(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.ledger = self.tmp / "ledger.csv"
        with open(self.ledger, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(rl.CABECERA)
            for i, estado in ((1, "ok"), (2, "ok"), (3, "error"), (4, "en_curso")):
                f = {c: "" for c in rl.CABECERA}
                f["id"] = f"D{i:02d}"
                f["estado"] = estado
                f["paginas_vistas"] = "7"
                f["filas_copiadas"] = "105"
                w.writerow([f[c] for c in rl.CABECERA])

    def _leer(self):
        with open(self.ledger, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    def test_deja_intactas_las_anteriores(self):
        n = rl.reinicia_desde(rl.CABECERA, "D03", self.ledger)
        self.assertEqual(n, 2)
        filas = self._leer()
        self.assertEqual(filas[0]["estado"], "ok")
        self.assertEqual(filas[0]["paginas_vistas"], "7")
        self.assertEqual(filas[2]["estado"], "error")
        self.assertEqual(filas[2]["paginas_vistas"], "0")
        self.assertEqual(filas[2]["filas_copiadas"], "0")
        self.assertEqual(filas[3]["estado"], "error")
        self.assertEqual(filas[3]["paginas_vistas"], "0")

    def test_reinicia_todas_desde_D01(self):
        n = rl.reinicia_desde(rl.CABECERA, "D01", self.ledger)
        self.assertEqual(n, 4)
        for f in self._leer():
            self.assertEqual(f["estado"], "error")
            self.assertEqual(f["paginas_vistas"], "0")

    def test_no_deja_temporal(self):
        rl.reinicia_desde(rl.CABECERA, "D02", self.ledger)
        self.assertEqual(list(self.tmp.glob("*.tmp")), [])

    def test_guarda_el_formato_del_repo(self):
        rl.reinicia_desde(rl.CABECERA, "D02", self.ledger)
        crudo = self.ledger.read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n\n", crudo)
        with open(self.ledger, encoding="utf-8-sig", newline="") as fh:
            self.assertEqual(next(csv.reader(fh, delimiter=";")), rl.CABECERA)


if __name__ == "__main__":
    unittest.main()
