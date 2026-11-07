"""Guardas de seguridad de tools/separar.py.

Contexto: el 03/11 se ejecuto `separar.py nuevo.txt --salida nuevas.csv` (con
espacio). La ruta se ignoraba en silencio porque solo se parseaba
`--salida=ruta`, asi que el destino se quedaba en el CSV de PRODUCCION y se
estuvo a punto de sobrescribir las 121 direcciones del operador con 3. Solo lo
salvo el bloqueo de Excel (os.replace dio WinError 5).

Estos tests fijan:
  - `--salida=ruta` y `--salida ruta` funcionan los dos.
  - `--salida` sin valor y los argumentos de mas se rechazan (exit 2).
  - El CSV de produccion exige `--produccion`.
  - El CSV de produccion no se degrada: si las filas nuevas son menos que las
    que hay, no se escribe nada.
"""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import separar as sep  # noqa: E402


class TestSepararSeguridad(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sepseg_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.txt = self.tmp / "entrada.txt"
        self.txt.write_text("CR 14B 119-61\n", encoding="utf-8")

    def _csv(self, ruta, partes):
        with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(sep.CABECERA)
            for p in partes:
                w.writerow([p, "1", ""])

    def _filas(self, ruta):
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    # ---------------------------------------------------------------- salida
    def test_salida_con_igual_se_usa(self):
        dest = self.tmp / "out.csv"
        rc = sep.main(["separar.py", str(self.txt), f"--salida={dest}"])
        self.assertEqual(rc, 0)
        self.assertTrue(dest.exists())
        self.assertEqual(len(self._filas(dest)), 1)

    def test_salida_con_espacio_se_usa_y_no_pisa_produccion(self):
        dest = self.tmp / "out2.csv"
        prod = self.tmp / "produccion.csv"
        self._csv(prod, ["CR 1", "CR 2"])
        with patch.object(sep, "PRODUCCION", prod):
            rc = sep.main(["separar.py", str(self.txt), "--salida", str(dest)])
        self.assertEqual(rc, 0)
        self.assertTrue(dest.exists())
        self.assertEqual(len(self._filas(prod)), 2)   # intacto

    def test_salida_sin_valor_se_rechaza(self):
        rc = sep.main(["separar.py", str(self.txt), "--salida"])
        self.assertEqual(rc, 2)

    def test_argumentos_de_mas_se_rechazan(self):
        rc = sep.main(["separar.py", str(self.txt), "sobra.txt"])
        self.assertEqual(rc, 2)

    # ------------------------------------------------------------ produccion
    def test_produccion_exige_el_flag(self):
        prod = self.tmp / "produccion.csv"
        self._csv(prod, ["CR 1", "CR 2"])
        with patch.object(sep, "PRODUCCION", prod):
            rc = sep.main(["separar.py", str(self.txt), f"--salida={prod}"])
        self.assertEqual(rc, 2)
        self.assertEqual(len(self._filas(prod)), 2)   # intacto

    def test_produccion_no_se_degrada(self):
        prod = self.tmp / "produccion.csv"
        self._csv(prod, ["CR 1", "CR 2", "CR 3", "CR 4", "CR 5"])
        with patch.object(sep, "PRODUCCION", prod):
            rc = sep.main(["separar.py", str(self.txt), f"--salida={prod}",
                           "--produccion"])
        self.assertEqual(rc, 2)
        self.assertEqual(len(self._filas(prod)), 5)   # intacto

    def test_produccion_con_tantas_filas_si_escribe(self):
        prod = self.tmp / "produccion.csv"
        self._csv(prod, ["CR 1"])
        with patch.object(sep, "PRODUCCION", prod):
            rc = sep.main(["separar.py", str(self.txt), f"--salida={prod}",
                           "--produccion"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._filas(prod)), 1)

    def test_el_destino_por_defecto_no_es_produccion(self):
        self.assertNotEqual(sep.SALIDA.resolve(), sep.PRODUCCION.resolve())


if __name__ == "__main__":
    unittest.main()
