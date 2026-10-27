"""Tests de la clasificacion pura (texto -> estado). Sin OCR ni red."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import estado  # noqa: E402

FORM = (
    "C46453101 CONSULTA EDIFICIO-CUENTA MATRIZ Fecha: 26/10/26\n"
    "Nombre :\nCalle : CR 17B\nNo.Casa : 175-77\n"
    "Comunidad : BOG\nDivision : TVC\n"
    "F3=Fin F5=Busca Cll F10=Buscar Direccion\n"
)
UNIDADES = (
    "CONSULTA UNIDADES CUENTA MATRIZ\n"
    "DIRECCION        APTO    COM  DIV  SUSCRIPT\n"
    "CL 175 BLACACIAS 178-10  CASA1  BOG  TVC  XT121E\n"
    "CL 175 BLACACIAS 178-10  CASA2  BOG  TVC  NFE700\n"
)


class TestReglas(unittest.TestCase):
    def test_formulario(self):
        self.assertEqual(estado.reglas(FORM)["estado"], "formulario")

    def test_cuenta_matriz(self):
        self.assertEqual(estado.reglas(UNIDADES)["estado"], "cuenta_matriz")

    def test_sin_coincidencia(self):
        texto = FORM + "La calle no se encuentra en el archivo de calles.."
        self.assertEqual(estado.reglas(texto)["estado"], "sin_coincidencia")

    def test_error_duro(self):
        texto = FORM + "El cursor esta en un area protegida de la pantalla"
        self.assertEqual(estado.reglas(texto)["estado"], "error")

    def test_aviso_duro_gana_sobre_no_encontrado(self):
        texto = FORM + "Codigo comunidad no esta en el archivo."
        self.assertEqual(estado.reglas(texto)["estado"], "error")

    def test_no_encontrado_sin_formulario_no_es_sin_coincidencia(self):
        texto = UNIDADES + "NO SE ENCUENTRA"
        self.assertNotEqual(estado.reglas(texto)["estado"], "sin_coincidencia")

    def test_sin_senales_devuelve_none(self):
        self.assertIsNone(estado.reglas("texto cualquiera sin pistas")["estado"])

    def test_lineas_suscriptor_cuenta_lineas_no_codigos(self):
        texto = UNIDADES + "CL 175 OTRA 170-10  CASA3  BOG  TVC  50867551 25420919\n"
        senales = estado.reglas(texto)["senales"]
        self.assertEqual(senales["lineas_suscriptor"], 3)

    def test_numeros_sueltos_no_marcan_suscriptores(self):
        # Un telefono de 10 digitos no es un suscriptor y una sola linea con
        # codigo no basta: el umbral son 2 lineas distintas.
        texto = "CONSULTA UNIDADES CUENTA MATRIZ\nTelefono 6012345678\n"
        senales = estado.reglas(texto)["senales"]
        self.assertEqual(senales["lineas_suscriptor"], 0)
        self.assertFalse(senales["lineas_suscriptor"] >= 2)

    def test_codigos_en_minusculas_siguen_contando(self):
        texto = "CONSULTA UNIDADES CUENTA MATRIZ\ncasax xt121e\ncasax nfe700\n"
        self.assertEqual(estado.reglas(texto)["senales"]["lineas_suscriptor"], 2)


if __name__ == "__main__":
    unittest.main()
