"""Cargar un lote nuevo de direcciones: anadir al final o sustituir la lista.

Con 1000 direcciones nuevas el operador no quiere acumular sobre las
anteriores: sustituye la lista entera (con copia de seguridad antes) y el
dedup pasa a contar solo dentro del lote nuevo.
"""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import anexar_direcciones as ax

NUEVAS = ["CR 18 113-47", "CL 80 8-10"]
VIEJAS = ["CL 122 45A-92", "CR 14 119-61"]


class _Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.ruta = self.dir / "direcciones.csv"
        with open(self.ruta, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=ax.CABECERA, delimiter=";")
            w.writeheader()
            for p1, p2 in [("CL 122", "45A-92"), ("CR 14", "119-61")]:
                w.writerow({"parte1": p1, "parte2": p2, "ficha": "vieja"})

    def filas(self):
        with open(self.ruta, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))


class TestReemplazar(_Base):
    def test_sustituye_la_lista_entera(self):
        n = ax.anexar(NUEVAS, ruta=self.ruta, reemplazar=True)
        self.assertEqual(n, 2)
        filas = self.filas()
        self.assertEqual([f["parte1"] for f in filas], ["CR 18", "CL 80"])
        self.assertTrue(all(f["ficha"] == "" for f in filas))

    def test_anadir_conserva_las_viejas(self):
        n = ax.anexar(NUEVAS, ruta=self.ruta)
        self.assertEqual(n, 2)
        filas = self.filas()
        self.assertEqual(len(filas), 4)
        self.assertEqual(filas[0]["ficha"], "vieja")

    def test_reemplazar_hace_copia_de_seguridad(self):
        ax.anexar(NUEVAS, ruta=self.ruta, reemplazar=True)
        backups = list(self.dir.glob("direcciones_backup_*.csv"))
        self.assertEqual(len(backups), 1)

    def test_dry_no_escribe(self):
        antes = self.ruta.read_bytes()
        n = ax.anexar(NUEVAS, ruta=self.ruta, dry=True, reemplazar=True)
        self.assertEqual(n, 2)
        self.assertEqual(self.ruta.read_bytes(), antes)

    def test_una_linea_mala_no_tira_el_archivo(self):
        n = ax.anexar(["no es una direccion"], ruta=self.ruta, reemplazar=True)
        self.assertEqual(n, 0)
        self.assertEqual(len(self.filas()), 2)

    def test_dedup_solo_dentro_del_lote_nuevo(self):
        n = ax.anexar(["CR 18 113-47", "CR 18 113-47"], ruta=self.ruta,
                      reemplazar=True)
        self.assertEqual(n, 1)
        self.assertEqual(len(self.filas()), 1)

    def test_repetida_que_ya_esta_en_el_csv_antiguo(self):
        # "CL 122 45A-92" ya estaba: sin --reemplazar se salta.
        self.assertEqual(ax.anexar(VIEJAS[:1], ruta=self.ruta), 0)
        # Con --reemplazar entra (el lote nuevo manda).
        self.assertEqual(ax.anexar(VIEJAS[:1], ruta=self.ruta, reemplazar=True), 1)


if __name__ == "__main__":
    unittest.main()
