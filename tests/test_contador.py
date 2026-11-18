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


def _corre(objetivo, cambios, fin_en=None):
    """reanudar() con capturas simuladas. Devuelve (real, nota, avpags).

    `cambios` = lo que devuelve changed_px en cada AvPag (en orden). `fin_en` =
    numero de AvPag tras el cual la pantalla pasa a fin de archivo.
    """
    cola = list(cambios)
    estado = {"avpag": 0}

    async def fake_step(_s, label, name, args=None):
        if name == "press_keys" and (args or {}).get("keys") == ["pagedown"]:
            estado["avpag"] += 1

    async def fake_sleep(_seg):
        return None

    def fake_changed(_a, _b):
        return cola.pop(0) if cola else 9999

    def fake_clasifica(_img):
        if fin_en is not None and estado["avpag"] >= fin_en:
            return {"estado": "fin_libro", "senales": {"fin": True}}
        return {"estado": "cuenta_matriz", "senales": {}}

    with patch.object(pagina, "captura", lambda _h: (_Img(), {})), \
            patch.object(pagina, "clasificar_rapido", fake_clasifica), \
            patch.object(pagina, "pf") as mock_pf, \
            patch.object(pagina.asyncio, "sleep", fake_sleep):
        mock_pf.step = fake_step
        mock_pf.changed_px = fake_changed
        real, nota = asyncio.run(pagina.reanudar(None, 132724, objetivo,
                                                 espera=0))
    return real, nota, estado["avpag"]


class TestReanudar(unittest.TestCase):
    def test_objetivo_1_no_avanza(self):
        self.assertEqual(_corre(1, []), (1, "", 0))

    def test_avanza_objetivo_menos_1(self):
        real, nota, avpags = _corre(3, [9999, 9999])
        self.assertEqual((real, avpags), (3, 2))
        self.assertEqual(nota, "")

    def test_un_avpag_perdido_se_reintenta(self):
        # El primer AvPag no mueve la pantalla (0 px): se reintenta el mismo.
        real, _nota, avpags = _corre(2, [0, 9999])
        self.assertEqual((real, avpags), (2, 2))

    def test_sin_cambio_aborta_sin_seguir(self):
        real, nota, avpags = _corre(3, [0, 0, 0, 0])
        self.assertIsNone(real)
        self.assertEqual(avpags, 4)  # agoto los intentos del primer paso
        self.assertIn("sin cambio visible", nota)

    def test_fin_de_archivo_en_el_camino_aborta(self):
        real, nota, avpags = _corre(4, [9999, 9999, 9999], fin_en=1)
        self.assertIsNone(real)
        self.assertEqual(avpags, 1)
        self.assertIn("fin de archivo", nota)


class TestLoopUsaReanudar(unittest.TestCase):
    def test_loop_llama_a_reanudar(self):
        src = (Path(__file__).resolve().parent.parent / "tools" /
               "loop.py").read_text(encoding="utf-8")
        self.assertIn("pagina.reanudar(", src)


if __name__ == "__main__":
    unittest.main()
