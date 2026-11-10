"""Contador de pagina del 5250 (NN/NNN): reanudar sabiendo donde esta el listado.

Antes de esto la reanudacion pulsaba AvPag x N a ciegas. Si un AvPag se perdia
(licencia, latencia, frame sin procesar) el bloque siguiente se duplicaba o
dejaba un hueco, y el ledger no podia detectarlo.
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import pagina

ALTO = 703
ANCHO = 1255
CONT = ("08/031", 1150, 660, 40, 12)


class _Img:
    width = ANCHO
    height = ALTO


class TestContador(unittest.TestCase):
    def test_lee_el_de_la_esquina_inferior_derecha(self):
        self.assertEqual(pagina.contador([CONT], ANCHO, ALTO), (8, 31))

    def test_ignora_uno_que_no_esta_abajo_a_la_derecha(self):
        self.assertEqual(pagina.contador([("08/031", 600, 300, 40, 12)],
                                         ANCHO, ALTO), (None, None))

    def test_ignora_numeros_que_no_son_contador(self):
        self.assertEqual(pagina.contador([("12345678", 1150, 660, 40, 12)],
                                         ANCHO, ALTO), (None, None))
        self.assertEqual(pagina.contador([("175-77", 1150, 660, 40, 12)],
                                         ANCHO, ALTO), (None, None))

    def test_elige_el_mas_abajo_a_la_derecha(self):
        dos = [("02/031", 1100, 640, 40, 12), ("09/031", 1180, 680, 40, 12)]
        self.assertEqual(pagina.contador(dos, ANCHO, ALTO), (9, 31))

    def test_corrige_las_confusiones_del_ocr(self):
        # Tesseract lee la O por 0 y la l por 1 en el contador.
        self.assertEqual(pagina.contador([("OB/03l", 1150, 660, 40, 12)],
                                         ANCHO, ALTO), (8, 31))

    def test_sin_palabras(self):
        self.assertEqual(pagina.contador([], ANCHO, ALTO), (None, None))
        self.assertEqual(pagina.contador(None, ANCHO, ALTO), (None, None))


class TestPasos(unittest.TestCase):
    def test_faltan(self):
        self.assertEqual(pagina.pasos_reanudar(1, 4), 3)

    def test_ya_esta(self):
        self.assertEqual(pagina.pasos_reanudar(4, 4), 0)

    def test_ya_paso(self):
        self.assertEqual(pagina.pasos_reanudar(6, 4), -2)

    def test_sin_contador(self):
        self.assertIsNone(pagina.pasos_reanudar(None, 4))


def _corre(lecturas, objetivo):
    """reanudar() con capturas y OCR simulados. Devuelve (real, nota, avpags).

    `lecturas` son las words que devuelve cada OCR: la primera ANTES de pulsar
    nada y una mas por cada AvPag.
    """
    cola = list(lecturas)
    estado = {"i": 0, "avpag": 0}

    def fake_ocr(_img):
        return "texto", cola[min(estado["i"], len(cola) - 1)]

    async def fake_step(_s, label, name, args=None):
        if name == "press_keys" and (args or {}).get("keys") == ["pagedown"]:
            estado["avpag"] += 1
            estado["i"] += 1

    async def fake_sleep(_seg):
        return None

    with patch.object(pagina, "captura", lambda _h: (_Img(), {})), \
            patch.object(pagina, "ocr_completo", fake_ocr), \
            patch.object(pagina, "pf") as mock_pf, \
            patch.object(pagina.asyncio, "sleep", fake_sleep):
        mock_pf.step = fake_step
        real, nota = asyncio.run(pagina.reanudar(None, 132724, objetivo,
                                                 espera=0))
    return real, nota, estado["avpag"]


class TestReanudar(unittest.TestCase):
    def test_ya_esta_en_la_pagina(self):
        real, nota, avpags = _corre([[("04/031", 1150, 660, 40, 12)]], 4)
        self.assertEqual((real, nota, avpags), (4, "", 0))

    def test_avanza_justo_lo_que_falta(self):
        real, nota, avpags = _corre([[("01/031", 1150, 660, 40, 12)],
                                     [("02/031", 1150, 660, 40, 12)],
                                     [("03/031", 1150, 660, 40, 12)]], 3)
        self.assertEqual((real, avpags), (3, 2))
        self.assertEqual(nota, "")

    def test_un_avpag_perdido_no_se_pasa(self):
        # El primero no mueve la pantalla (sigue en 02): se vuelve a pulsar.
        real, _nota, avpags = _corre([[("02/031", 1150, 660, 40, 12)],
                                      [("02/031", 1150, 660, 40, 12)],
                                      [("03/031", 1150, 660, 40, 12)]], 3)
        self.assertEqual((real, avpags), (3, 2))

    def test_si_ya_paso_no_retrocede(self):
        real, nota, avpags = _corre([[("06/031", 1150, 660, 40, 12)]], 4)
        self.assertEqual((real, avpags), (6, 0))
        self.assertIn("no se retrocede", nota)

    def test_sin_contador_aborta_sin_avanzar_a_ciegas(self):
        real, nota, avpags = _corre([[("nada", 0, 0, 10, 10)]], 3)
        self.assertIsNone(real)
        self.assertEqual(avpags, 0)
        self.assertIn("sin contador", nota)

    def test_si_se_agota_no_miente(self):
        # Nunca llega a la 5: el contador se queda en 2.
        real, nota, _ = _corre([[("01/031", 1150, 660, 40, 12)],
                                [("02/031", 1150, 660, 40, 12)]], 5)
        self.assertEqual(real, 2)
        self.assertIn("no se llego", nota)


class TestLoopUsaElContador(unittest.TestCase):
    def test_loop_ya_no_pagina_a_ciegas(self):
        src = (Path(__file__).resolve().parent.parent / "tools" /
               "loop.py").read_text(encoding="utf-8")
        self.assertIn("pagina.reanudar(", src)
        self.assertNotIn('"resuma_avpag_', src)


class TestSinAvanceCiego(unittest.TestCase):
    def test_contador_ilegible_no_inyecta_avpag(self):
        from unittest.mock import AsyncMock, patch

        async def corre():
            with patch.object(pagina, "captura", lambda _h: (_Img(), {})), \
                    patch.object(pagina, "ocr_completo", return_value=("", [])), \
                    patch.object(pagina.pf, "step", new=AsyncMock()) as step, \
                    patch.object(pagina.asyncio, "sleep", new=AsyncMock()):
                resultado = await pagina.reanudar(None, 1, 4, espera=0)
                return resultado, step

        (real, nota), step = asyncio.run(corre())
        self.assertIsNone(real)
        self.assertIn("abortada sin AvPag", nota)
        step.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
