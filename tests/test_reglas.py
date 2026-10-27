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

    def test_jev_con_confianza_baja_no_clasifica(self):
        # Una pagina web dio "formulario" con 0.35: con ese veredicto se
        # teclearia en el navegador. Confianza baja = sin clasificar.
        from unittest.mock import patch
        from PIL import Image

        with patch.object(estado, "ask", return_value={
                "ok": True, "choice": "formulario", "confidence": 0.35,
                "probabilities": {"formulario": 0.51, "error": 0.45}}):
            r = estado.clasificar(Image.new("RGB", (40, 20), "black"), usar_jev=True)
        self.assertIsNone(r["estado"])
        self.assertEqual(r["fuente"], "jev")
        self.assertIn("confianza baja", r["error"])

    def test_jev_con_confianza_alta_si_clasifica(self):
        from unittest.mock import patch
        from PIL import Image

        # Pantalla con marcadores del 5250 (sin cabecera CONSULTA): la regla no
        # decide, Jev si, y el veredicto se acepta porque hay marcador real.
        with patch.object(estado, "ocr_text", return_value="Cuenta Edificio : 34377 F10=Buscar Direccion"), \
                patch.object(estado, "ask", return_value={
                    "ok": True, "choice": "cuenta_matriz", "confidence": 0.9,
                    "probabilities": {"cuenta_matriz": 0.9}}):
            r = estado.clasificar(Image.new("RGB", (40, 20), "black"), usar_jev=True)
        self.assertEqual(r["estado"], "cuenta_matriz")
        self.assertEqual(r["confianza"], 0.9)

    def test_hoja_de_calculo_no_es_cuenta_matriz(self):
        # Medido en vivo: la hoja LIMPIEZA RR (misma tabla de direcciones y
        # suscriptores) hizo que Jev dijera 'cuenta_matriz' con 0.83. Es el
        # DESTINO del pegado, no el listado del IBM: no se clasifica.
        hoja = (
            "LIMPIEZA RR - Google Sheets  Ask Gemini\n"
            "DIRECCION EDIFICIO DIRECCION SUSCRIPTOR\n"
            "CL 175 BLACACIAS 178-10 CASA1 BOG TVC XT121E 50867551\n"
            "CL 175 BLACACIAS 178-10 CASA2 BOG TVC XT121E 25420919\n"
        )
        r = estado.reglas(hoja)
        self.assertIsNone(r["estado"])
        self.assertTrue(r["senales"]["no_ibm"])
        self.assertIn("no IBM", r["error"])

    def test_jev_no_clasifica_sin_marcadores_ibm(self):
        from unittest.mock import patch
        from PIL import Image

        with patch.object(estado, "ocr_text", return_value="tabla de direcciones y suscriptores"), \
                patch.object(estado, "ask", return_value={
                    "ok": True, "choice": "cuenta_matriz", "confidence": 0.9,
                    "probabilities": {"cuenta_matriz": 0.9}}):
            r = estado.clasificar(Image.new("RGB", (40, 20), "black"), usar_jev=True)
        self.assertIsNone(r["estado"])
        self.assertIn("sin marcadores IBM", r["error"])

    def test_codigos_en_minusculas_siguen_contando(self):
        texto = "CONSULTA UNIDADES CUENTA MATRIZ\ncasax xt121e\ncasax nfe700\n"
        self.assertEqual(estado.reglas(texto)["senales"]["lineas_suscriptor"], 2)

    def test_fin_de_libro_gana_sobre_cuenta_matriz(self):
        # El listado sigue en pantalla, pero el 5250 avisa que no hay mas
        # registros: se deja de extraer.
        texto = (UNIDADES +
                 "F12=Anterior\n"
                 "Giro hacia arriba o hacia abajo mas alla del primer o ultimo "
                 "registro en el archivo.")
        r = estado.reglas(texto)
        self.assertEqual(r["estado"], "fin_libro")
        self.assertTrue(r["senales"]["fin"])

    def test_fin_de_libro_tolera_acentos_del_ocr(self):
        texto = UNIDADES + "Giro hacia arriba o hacia abajo más allá del último registro"
        self.assertEqual(estado.reglas(texto)["estado"], "fin_libro")

    def test_f12_anterior_solo_no_es_fin_de_libro(self):
        # F12=Anterior puede estar en la barra de funciones sin que la matriz
        # se haya terminado: la senal es la FRASE, no la tecla.
        texto = UNIDADES + "F3=Fin F12=Anterior F10=Buscar Direccion\n"
        r = estado.reglas(texto)
        self.assertEqual(r["estado"], "cuenta_matriz")
        self.assertFalse(r["senales"]["fin"])

    def test_fin_de_libro_no_aplica_a_la_hoja(self):
        hoja = "LIMPIEZA RR - Google Sheets\nGiro hacia arriba mas alla del ultimo registro"
        r = estado.reglas(hoja)
        self.assertIsNone(r["estado"])
        self.assertTrue(r["senales"]["no_ibm"])


if __name__ == "__main__":
    unittest.main()

class TestDesconectado(unittest.TestCase):
    def test_dialogo_de_licencia_no_es_error_del_5250(self):
        # Dialogo real de AnyDesk (medido): tapa la pantalla remota.
        texto = ("Conexion finalizada\nLa conexion de red se cerro debido a la "
                 "limitacion de la licencia\nSuscribirse... Repetir OK")
        r = estado.reglas(texto)
        self.assertEqual(r["estado"], "desconectado")
        self.assertTrue(r["senales"]["desconectado"])

    def test_suscribirse_solo_no_basta(self):
        # 'Suscribirse' puede estar en la interfaz del cliente sin que la
        # sesion se haya cortado: la senal es la frase del dialogo.
        texto = "CONSULTA UNIDADES CUENTA MATRIZ\nSuscribirse a la version completa"
        self.assertNotEqual(estado.reglas(texto)["estado"], "desconectado")
