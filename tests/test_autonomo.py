"""autonomo: las funciones puras y el arbitraje de Jev.

Run: python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import autonomo

MENU = (
    "TCMENGEN SISTEMA GESTION DE CLIENTES\n"
    "Seleccione una de las siguientes opciones\n"
    "1. Menu Modulo Edificios\n"
    "2. Menu Opciones Telefonia\n"
    "4. Menu Otras Consultas\n"
    "6. Menu Bogota\n"
    "15. Parametros envio E-mails\n"
    "F3=Salir F4=Solicitud F12=Cancelar\n"
)


class TestOpcionesMenu(unittest.TestCase):
    def test_extrae_numero_y_descripcion(self):
        ops = autonomo.opciones_menu(MENU)
        self.assertEqual(ops["1"], "Menu Modulo Edificios")
        self.assertEqual(ops["6"], "Menu Bogota")
        self.assertEqual(ops["15"], "Parametros envio E-mails")

    def test_no_toma_la_barra_de_teclas(self):
        ops = autonomo.opciones_menu(MENU)
        # El menu real no tiene opcion 3, pero su barra dice "F3=Salir":
        # si la barra se parseara, apareceria "3" y "12" (de "F12=Cancelar").
        self.assertNotIn("3", ops)
        self.assertNotIn("12", ops)
        # ... y las opciones que SI existen se leen bien.
        self.assertIn("4", ops)

    def test_texto_sin_menu_devuelve_vacio(self):
        self.assertEqual(autonomo.opciones_menu("CONSULTA UNIDADES CUENTA MATRIZ\nCL 175 178-10"), {})
        self.assertEqual(autonomo.opciones_menu(""), {})


class TestJevElige(unittest.TestCase):
    def test_confianza_alta_devuelve_la_opcion(self):
        with patch.object(autonomo._jev, "ask",
                          return_value={"ok": True, "choice": "6",
                                        "confidence": 0.82, "confianza": 0.82}):
            opcion, nota = autonomo.jev_elige("texto", ["1", "6"], "instruccion")
        self.assertEqual(opcion, "6")
        self.assertIn("0.82", nota)

    def test_confianza_baja_no_es_veredicto(self):
        with patch.object(autonomo._jev, "ask",
                          return_value={"ok": True, "choice": "6",
                                        "confidence": 0.3, "confianza": 0.3}):
            opcion, nota = autonomo.jev_elige("texto", ["1", "6"], "instruccion")
        self.assertIsNone(opcion)
        self.assertIn("no es veredicto", nota)

    def test_fallo_de_jev_no_rompe(self):
        with patch.object(autonomo._jev, "ask",
                          return_value={"ok": False, "error": "http 429"}):
            opcion, nota = autonomo.jev_elige("texto", ["1"], "instruccion")
        self.assertIsNone(opcion)
        self.assertIn("429", nota)


class TestJevOpcionMenu(unittest.TestCase):
    def test_elige_el_numero_de_la_opcion(self):
        with patch.object(autonomo, "jev_elige",
                          return_value=("1. Menu Modulo Edificios", "jev: 1")):
            num, nota = autonomo.jev_opcion_menu(MENU)
        self.assertEqual(num, "1")

    def test_pantalla_sin_menu_no_pregunta(self):
        num, nota = autonomo.jev_opcion_menu("CONSULTA UNIDADES CUENTA MATRIZ")
        self.assertIsNone(num)
        self.assertIn("menu", nota.lower())


class TestResumen(unittest.TestCase):
    def test_resumen_suma_filas(self):
        filas = [{"id": "D01"}, {"id": "D02"}]
        hechos = {
            "D01": {"estado": "ok", "paginas_vistas": "10", "filas_copiadas": "150",
                    "notas": "10 bloques x 15 filas"},
            "D02": {"estado": "no_encontrado", "paginas_vistas": "0",
                    "filas_copiadas": "0", "notas": "sin coincidencia"},
        }
        txt = autonomo.resumen(filas, hechos)
        self.assertIn("D01: ok", txt)
        self.assertIn("150", txt)
        self.assertIn("TOTAL filas pegadas: 150", txt)


if __name__ == "__main__":
    unittest.main()
