"""WP-08: el id es estable por hash de la direccion, no por posicion.

Reordenar o filtrar `direcciones.csv` no cambia el id de una direccion y la
ficha se escribe en la fila correcta. Editar una direccion falla cerrado.
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import matriz_ficha as mf  # noqa: E402


def _escribe(ruta: Path, filas) -> None:
    with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["parte1", "parte2", "ficha"])
        w.writerows(filas)


def _mapa(filas) -> dict:
    return {(f["direccion_parte1"], f["direccion_parte2"]): f["id"] for f in filas}


class TestIds(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        self.ruta = self.dir / "direcciones.csv"

    def tearDown(self):
        self.td.cleanup()

    def test_reordenar_no_cambia_id(self):
        _escribe(self.ruta, [("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", ""),
                             ("CR 103D", "86-55", "")])
        antes = _mapa(mf.lee_direcciones(self.ruta))
        self.assertEqual(antes[("CR 17B", "175-77")], "D01")
        self.assertEqual(antes[("CR 84A", "145-94")], "D02")
        self.assertEqual(antes[("CR 103D", "86-55")], "D03")

        _escribe(self.ruta, [("CR 103D", "86-55", ""),
                             ("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", "")])
        despues = _mapa(mf.lee_direcciones(self.ruta))
        self.assertEqual(antes, despues)

    def test_escribe_ficha_en_fila_correcta_tras_reordenar(self):
        _escribe(self.ruta, [("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", ""),
                             ("CR 103D", "86-55", "")])
        mf.lee_direcciones(self.ruta)
        _escribe(self.ruta, [("CR 103D", "86-55", ""),
                             ("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", "")])

        aviso = mf.escribe_ficha("D02", "FICHA-B", self.ruta)
        self.assertEqual(aviso, "")

        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter=";"))
        por_dir = {(f["parte1"], f["parte2"]): f["ficha"] for f in filas}
        self.assertEqual(por_dir[("CR 84A", "145-94")], "FICHA-B")
        self.assertEqual(por_dir[("CR 103D", "86-55")], "")
        self.assertEqual(por_dir[("CR 17B", "175-77")], "")

    def test_direccion_editada_falla_cerrado(self):
        _escribe(self.ruta, [("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", "")])
        mf.lee_direcciones(self.ruta)
        _escribe(self.ruta, [("CR 17B", "175-78", ""),
                             ("CR 84A", "145-94", "")])

        aviso = mf.escribe_ficha("D01", "NO-DEBE-PEGARSE", self.ruta)
        self.assertTrue(aviso)
        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter=";"))
        self.assertNotEqual(filas[0]["ficha"], "NO-DEBE-PEGARSE")
        self.assertNotEqual(filas[1]["ficha"], "NO-DEBE-PEGARSE")

    def test_ids_se_generan_si_no_existe(self):
        _escribe(self.ruta, [("CR 17B", "175-77", ""),
                             ("CR 84A", "145-94", "")])
        ids_ruta = self.dir / "ids.csv"
        self.assertFalse(ids_ruta.exists())

        filas = mf.lee_direcciones(self.ruta)

        self.assertTrue(ids_ruta.exists())
        ids = mf.lee_ids(ids_ruta)
        self.assertEqual([i["id"] for i in ids], ["D01", "D02"])
        self.assertEqual([f["id"] for f in filas], ["D01", "D02"])
        self.assertTrue(all(len(i["hash"]) == 12 for i in ids))


if __name__ == "__main__":
    unittest.main()
