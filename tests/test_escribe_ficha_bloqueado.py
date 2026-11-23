"""escribe_ficha con el CSV bloqueado por Excel: no tumba el item y no pierde la ficha."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import loop
import matriz_ficha


class TestEscribeFichaBloqueado(unittest.TestCase):
    def _csv(self, tmp: Path) -> Path:
        ruta = tmp / "direcciones.csv"
        with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["parte1", "parte2", "ficha"])
            w.writerow(["CR 17B", "175-77", ""])
            w.writerow(["CR 103D", "86-55", ""])
        return ruta

    def test_escribe_ok_devuelve_vacio_y_mantiene_tildes(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = self._csv(Path(d))
            aviso = loop.escribe_ficha("D01", "Cuenta: 34377\nEDIFICIO ÑANDÚ", ruta)
            self.assertEqual(aviso, "")
            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                filas = list(csv.DictReader(fh, delimiter=";"))
            self.assertIn("ÑANDÚ", filas[0]["ficha"])
            self.assertEqual(filas[1]["ficha"], "")
            self.assertFalse((Path(d) / "fichas_pendientes.csv").exists())

    def test_csv_bloqueado_no_tumba_y_deja_respaldo(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = self._csv(Path(d))
            # Excel bloquea el destino: el temporal se escribe, pero
            # os.replace falla y el original queda intacto.
            with patch.object(matriz_ficha.csvio.os, "replace",
                              side_effect=PermissionError(13, "Permission denied", str(ruta))):
                with patch.object(loop.time, "sleep", lambda s: None):
                    aviso = loop.escribe_ficha("D01", "Cuenta: 34377", ruta)

            self.assertIn("bloqueado", aviso)
            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                filas_csv = list(csv.DictReader(fh, delimiter=";"))
            self.assertEqual(filas_csv[0]["ficha"], "")
            self.assertEqual(filas_csv[1]["ficha"], "")
            respaldo = Path(d) / "fichas_pendientes.csv"
            self.assertTrue(respaldo.exists())
            with open(respaldo, encoding="utf-8", newline="") as fh:
                filas = list(csv.reader(fh, delimiter=";"))
            # El respaldo guarda id + direccion + ficha: el id es posicional y
            # sin la direccion no se puede saber a que edificio pertenece.
            self.assertEqual(len(filas[0]), 4)
            self.assertEqual(filas[0][0], "D01")
            self.assertEqual(filas[0][1], "CR 17B")
            self.assertEqual(filas[0][2], "175-77")
            self.assertIn("34377", filas[0][3])

    def test_id_fuera_de_ids_no_escribe(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = self._csv(Path(d))
            self.assertIn("no esta en ids", loop.escribe_ficha("D99", "x", ruta))
            self.assertIn("no esta en ids", loop.escribe_ficha("ZZZ", "x", ruta))
            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                filas = list(csv.DictReader(fh, delimiter=";"))
            self.assertEqual([f["ficha"] for f in filas], ["", ""])


if __name__ == "__main__":
    unittest.main()
