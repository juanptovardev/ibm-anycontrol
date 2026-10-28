"""Contrato de formato de datos/direcciones.csv.

El formato lo fija Excel en espanol (separador ';', BOM, CRLF) y lo consume
`loop.escribe_ficha`. Este test lo fija para que nadie lo rompa al editar a mano.
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import regenerar_direcciones as reg


class TestFormatoDelCsv(unittest.TestCase):
    def _archivo(self, filas=None):
        tmp = tempfile.mkdtemp()
        ruta = Path(tmp) / "direcciones.csv"
        if filas is None:
            filas = [{"parte1": "CR 17B", "parte2": "175-77", "ficha": ""},
                     {"parte1": "CR 84A", "parte2": "145-94", "ficha": ""}]
        reg.escribir(filas, ruta)
        return ruta

    def test_roundtrip_respeta_el_formato(self):
        ruta = self._archivo()
        crudo = ruta.read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"), "falta el BOM")
        self.assertNotIn(b"\n\n", crudo)
        # Todos los saltos de linea son CRLF (ningun LF suelto).
        lf_sueltos = crudo.count(b"\n") - crudo.count(b"\r\n")
        self.assertEqual(lf_sueltos, 0, f"hay {lf_sueltos} LF sueltos")
        self.assertIn(b"\r\n", crudo)
        self.assertTrue(crudo.splitlines()[0].endswith(
            b"parte1;parte2;ficha"), "cabecera incorrecta")

    def test_la_columna_ficha_queda_vacia(self):
        ruta = self._archivo([{"parte1": "CR 17B", "parte2": "175-77",
                               "ficha": "Cuenta: 34377 | BOSQUES"}])
        reg.escribir([{"parte1": "CR 17B", "parte2": "175-77", "ficha": ""}], ruta)
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter=";"))
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["ficha"], "")
        self.assertEqual(filas[0]["parte1"], "CR 17B")

    def test_leer_devuelve_las_filas(self):
        ruta = self._archivo()
        filas = reg.leer(ruta)
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["parte1"], "CR 17B")
        self.assertEqual(filas[1]["parte2"], "145-94")

    def test_no_deja_el_temporal(self):
        ruta = self._archivo()
        self.assertFalse(ruta.with_suffix(ruta.suffix + ".tmp").exists())

    def test_sin_archivo_no_crea_uno_y_sale_con_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "direcciones.csv"
            with patch.object(reg, "RUTA", ruta):
                codigo = reg.main([])
            self.assertNotEqual(codigo, 0)
            self.assertFalse(ruta.exists())


if __name__ == "__main__":
    unittest.main()
