"""Tests del parser del listado, con el OCR REAL de una captura del 5250."""
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import tabla  # noqa: E402

FIXTURE = os.path.join(RAIZ, "tests", "fixtures", "unidades_ocr.txt")


def texto_fixture():
    with open(FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class TestNormaliza(unittest.TestCase):
    def test_codigo_con_ruido_se_mapea(self):
        # El OCR metio una O de mas: el mapeo la vuelve digito, pero no se
        # inventa el valor real (NFE700 -> leido NFE7O0O).
        self.assertEqual(tabla.normaliza_codigo("NFE7O0O"), "NFE7000")
        self.assertNotIn("O", tabla.normaliza_codigo("NFE7O0O"))

    def test_palabra_mas_sufijo(self):
        self.assertEqual(tabla.normaliza_apto("CASAL"), "CASA1")
        self.assertEqual(tabla.normaliza_apto("ADMINi"), "ADMIN1")
        self.assertEqual(tabla.normaliza_apto("CASAIO"), "CASA10")

    def test_palabras_de_calle_no_se_tocan(self):
        self.assertEqual(tabla.normaliza_direccion("BLACACIAS"), "BLACACIAS")
        self.assertEqual(tabla.normaliza_direccion("CL"), "CL")

    def test_numero_con_ruido(self):
        self.assertEqual(tabla.normaliza_direccion("17B-10"), "178-10")

    def test_digitos_puros(self):
        valor, ok = tabla.normaliza_token("50867551")
        self.assertEqual(valor, "50867551")
        self.assertTrue(ok)


class TestParseRow(unittest.TestCase):
    def test_fila_con_suscriptor(self):
        fila = tabla.parse_row("CL 175 BLACACIAS 178-10 CASA3 BOG TVC XT121E 50867551 S$")
        self.assertIsNotNone(fila)
        self.assertEqual(fila["direccion"], "CL 175 BLACACIAS 178-10")
        self.assertEqual(fila["apto"], "CASA3")
        self.assertEqual(fila["com"], "BOG")
        self.assertEqual(fila["div"], "TVC")
        self.assertEqual(fila["nodo"], "XT121E")
        self.assertEqual(fila["suscriptor"], "50867551")
        self.assertEqual(fila["est"], "S$")
        self.assertEqual(fila["confianza"], "alta")

    def test_fila_sin_suscriptor(self):
        fila = tabla.parse_row("CL 175 BLACACIAS 17B-10 ADMIN BOG TVC XT121E D")
        self.assertIsNotNone(fila)
        self.assertEqual(fila["suscriptor"], "")
        self.assertEqual(fila["direccion"], "CL 175 BLACACIAS 178-10")
        self.assertEqual(fila["est"], "D")

    def test_suscriptor_con_letras_queda_confianza_media(self):
        fila = tabla.parse_row("CL 175 BLACACIAS 178-10 CASA4 BOG TVC XT121E 25420919 S")
        self.assertEqual(fila["suscriptor"], "25420919")
        self.assertEqual(fila["confianza"], "alta")

    def test_cabecera_no_es_fila(self):
        self.assertIsNone(tabla.parse_row("vireccion Apto Lom Viv NodO esuscript cst"))

    def test_linea_rusa_no_es_fila(self):
        self.assertIsNone(tabla.parse_row("F3=Fin F5=Bsca Cll F10=Buscar Direccion"))


class TestParseTabla(unittest.TestCase):
    def setUp(self):
        self.filas = tabla.parse_tabla(texto_fixture())

    def test_saca_todas_las_filas_de_datos(self):
        # La captura real tiene 15 lineas: 1 cabecera + 14 de datos.
        self.assertEqual(len(self.filas), 14)

    def test_cabecera_excluida(self):
        for fila in self.filas:
            self.assertNotIn("DIRECCION", fila["direccion"])

    def test_suscriptores_encontrados(self):
        sus = [f["suscriptor"] for f in self.filas if f["suscriptor"]]
        self.assertIn("50867551", sus)
        self.assertIn("25420919", sus)
        self.assertIn("93896161", sus)

    def test_todas_las_filas_tienen_com_y_div(self):
        for fila in self.filas:
            self.assertEqual(fila["com"], "BOG")
            self.assertEqual(fila["div"], "TVC")

    def test_todas_las_filas_confianza_alta_o_media(self):
        for fila in self.filas:
            self.assertIn(fila["confianza"], ("alta", "media"))


if __name__ == "__main__":
    unittest.main()
