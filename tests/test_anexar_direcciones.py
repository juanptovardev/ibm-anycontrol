"""tools/anexar_direcciones.py: anade al FINAL sin tocar las que ya estan."""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import anexar_direcciones as ax  # noqa: E402


class TestAnexar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="anexar_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.csv = self.tmp / "direcciones.csv"
        with open(self.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["parte1", "parte2", "ficha"])
            w.writerow(["CR 1", "1-1", "Cuenta: 1 | EDIFICIO X"])
            w.writerow(["CR 2", "2-2", ""])

    def _filas(self):
        with open(self.csv, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    def test_anade_al_final_y_conserva_las_fichas(self):
        n = ax.anexar(["CR 3 3-3"], self.csv)
        self.assertEqual(n, 1)
        filas = self._filas()
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0]["ficha"], "Cuenta: 1 | EDIFICIO X")
        self.assertEqual(filas[-1]["parte1"], "CR 3")
        self.assertEqual(filas[-1]["parte2"], "3-3")
        self.assertEqual(filas[-1]["ficha"], "")

    def test_no_duplica(self):
        self.assertEqual(ax.anexar(["CR 1 1-1"], self.csv), 0)
        self.assertEqual(len(self._filas()), 2)

    def test_no_separa_lo_que_no_encaja(self):
        self.assertEqual(ax.anexar(["ZT 9 9-9"], self.csv), 0)
        self.assertEqual(len(self._filas()), 2)

    def test_dry_no_escribe(self):
        antes = self.csv.read_bytes()
        self.assertEqual(ax.anexar(["CR 3 3-3"], self.csv, dry=True), 1)
        self.assertEqual(self.csv.read_bytes(), antes)

    def test_respeta_el_formato(self):
        ax.anexar(["CR 3 3-3"], self.csv)
        raw = self.csv.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))          # BOM
        self.assertNotIn(b"\n\n", raw)
        texto = raw.decode("utf-8-sig")
        self.assertTrue(texto.startswith("parte1;parte2;ficha\r\n"))

    def test_hace_respaldo_antes_de_escribir(self):
        antes = set(p.name for p in self.tmp.iterdir())
        ax.anexar(["CR 3 3-3"], self.csv)
        despues = set(p.name for p in self.tmp.iterdir())
        self.assertTrue(any("backup" in n for n in despues - antes))


if __name__ == "__main__":
    unittest.main()
