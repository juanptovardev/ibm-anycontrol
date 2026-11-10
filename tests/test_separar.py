"""separar: las reglas del separador de direcciones, portadas del scaffold TS."""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import separar


class TestParse(unittest.TestCase):
    def test_los_cinco_ejemplos_del_contrato(self):
        casos = [
            ("CR 6SUR 22C-19", "CR 6SUR", "22C-19"),
            ("CL 81BISSUR 8C-6", "CL 81BISSUR", "8C-6"),
            ("TR 3C 51A-8", "TR 3C", "51A-8"),
            ("CL 81 BIS SUR 8C-6", "CL 81BISSUR", "8C-6"),
            ("CR 2A ESTE SUR 24A-63", "CR 2AESTESUR", "24A-63"),
        ]
        for entrada, parte1, parte2 in casos:
            r = separar.parse(entrada)
            self.assertEqual(r["estado"], "parsed", entrada)
            self.assertEqual(r["parte1"], parte1, entrada)
            self.assertEqual(r["parte2"], parte2, entrada)

    def test_el_caso_del_operador(self):
        r = separar.parse("CR 18 113-47")
        self.assertEqual((r["parte1"], r["parte2"]), ("CR 18", "113-47"))

    def test_minusculas_y_espacios_de_mas(self):
        r = separar.parse("  cr   18    113-47 ")
        self.assertEqual((r["parte1"], r["parte2"]), ("CR 18", "113-47"))

    def test_parte2_se_conserva_tal_cual(self):
        r = separar.parse("CL 131C 126 - 72")
        self.assertEqual(r["parte1"], "CL 131C")
        self.assertEqual(r["parte2"], "126 - 72")

    def test_falta_el_segundo_componente(self):
        self.assertEqual(separar.parse("CL 81BISSUR")["estado"], "unparsed")

    def test_prefijos_no_soportados(self):
        # KR, AK, AV siguen fuera a proposito (documentado como pendiente).
        # DG y TV ya entraron: salieron en la lista real de 121 del operador.
        for malo in ("KR 8 CL 22-10", "AK 45 12-3", "AV 68 20-11"):
            self.assertEqual(separar.parse(malo)["estado"], "unparsed", malo)

    def test_dg_y_tv_separan(self):
        for buena, p1, p2 in (("DG 82C 75A-21", "DG 82C", "75A-21"),
                              ("TV 2 114A-25", "TV 2", "114A-25")):
            r = separar.parse(buena)
            self.assertEqual(r["estado"], "parsed", buena)
            self.assertEqual(r["parte1"], p1)
            self.assertEqual(r["parte2"], p2)

    def test_corta_la_direccion_pegada_en_parte2(self):
        # Celdas del operador con varias direcciones o sufijos detras del numero
        # de casa: solo el primer numero de casa va a parte2 (medido el 09/11:
        # D117, D488, D1052, D1235 y ~30 mas traian media lista en parte2 y el
        # F10 no encontraba nada).
        casos = [
            ("CR 92A 70B-59 CL 71BIS 91-72 CL 71BIS 92A-20", "CR 92A", "70B-59"),
            ("CR 94F 134-34 BLQ 14 CR 94F 134-04 BLQ 15", "CR 94F", "134-34"),
            ("CL 127BBIS 53-68 BLQ 5", "CL 127BBIS", "53-68"),
            ("CR 72ASUR 62D-10 MZA 1_ENT 5", "CR 72ASUR", "62D-10"),
            ("CR 24BSUR 13BIS-27", "CR 24BSUR", "13BIS-27"),
            ("CR 79BSUR 58PBIS-05", "CR 79BSUR", "58PBIS-05"),
        ]
        for entrada, p1, p2 in casos:
            r = separar.parse(entrada)
            self.assertEqual(r["estado"], "parsed", entrada)
            self.assertEqual(r["parte1"], p1, entrada)
            self.assertEqual(r["parte2"], p2, entrada)

    def test_numero_plano_se_conserva(self):
        # Sin guion el numero es legitimo (viene de las direcciones con dos
        # calles reescritas): no se toca.
        r = separar.parse("CL 23 41")
        self.assertEqual((r["parte1"], r["parte2"]), ("CL 23", "41"))

    def test_vacia(self):
        for malo in ("", "   ", None):
            self.assertEqual(separar.parse(malo)["estado"], "unparsed")

    def test_sufijo_pegado_desconocido_es_ambiguo(self):
        r = separar.parse("CL 81XYZ 8C-6")
        self.assertEqual(r["estado"], "ambiguous")
        self.assertIn("XYZ", r["motivo"])

    def test_segundo_componente_no_numerico_es_ambiguo(self):
        self.assertEqual(separar.parse("CL 81 BIS SUR KR 3")["estado"], "ambiguous")

    def test_no_inventa_con_dos_vias_en_palabras(self):
        self.assertEqual(
            separar.parse("CL 18 A SUR KR 3 ESTE-02")["estado"], "ambiguous")


class TestSeparaYArchivo(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_separa_mezcla_y_reporta(self):
        ok, mal = separar.separa(["CR 18 113-47", "", "   ", "KR 8 CL 22-10",
                                  "CL 81 BIS SUR 8C-6"])
        self.assertEqual(len(ok), 2)
        self.assertEqual(len(mal), 1)
        self.assertEqual(mal[0]["estado"], "unparsed")
        self.assertEqual(ok[0], {"parte1": "CR 18", "parte2": "113-47", "ficha": ""})

    def test_escribe_el_contrato_del_repo(self):
        ruta = separar.escribe(
            [{"parte1": "CR 18", "parte2": "113-47", "ficha": ""}],
            self.dir / "direcciones.csv")
        b = ruta.read_bytes()
        self.assertTrue(b.startswith(b"\xef\xbb\xbf"), "falta el BOM")
        self.assertEqual(b.count(b"\n"), b.count(b"\r\n"), "hay LF sueltos")
        lineas = b.decode("utf-8-sig").splitlines()
        self.assertEqual(lineas[0], "parte1;parte2;ficha")
        self.assertEqual(lineas[1], "CR 18;113-47;")
        self.assertFalse((self.dir / "direcciones.tmp").exists())

    def test_lee_txt(self):
        p = self.dir / "lista.txt"
        p.write_text("CR 18 113-47\n\nCL 81 BIS SUR 8C-6\n", encoding="utf-8")
        self.assertEqual(len(separar.lee_archivo(p)), 3)

    def test_lee_csv_por_columna(self):
        p = self.dir / "hoja.csv"
        p.write_text("direccion\nCR 18 113-47\n", encoding="utf-8")
        self.assertEqual(separar.lee_archivo(p), ["CR 18 113-47"])

    def test_un_csv_ya_separado_no_se_toca(self):
        p = self.dir / "direcciones.csv"
        p.write_text("parte1;parte2;ficha\nCR 18;113-47;\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            separar.lee_archivo(p)

    def test_main_no_escribe_si_no_hay_ninguna_valida(self):
        p = self.dir / "malas.txt"
        p.write_text("KR 8 CL 22-10\n", encoding="utf-8")
        salida = self.dir / "salida.csv"
        rc = separar.main(["separar.py", str(p), f"--salida={salida}"])
        self.assertEqual(rc, 1)
        self.assertFalse(salida.exists())


if __name__ == "__main__":
    unittest.main()
