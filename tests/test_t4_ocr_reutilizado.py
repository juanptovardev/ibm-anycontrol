"""T4': el OCR que ya se pago en espera_estado se reutiliza en el primer bloque.

Antes, cada direccion pagaba DOS OCR de la MISMA pantalla del listado: uno en
`estado.clasificar` (para saber que es el listado) y otro en `ciclo.extrae`
(para localizar la columna Suscript). Con T4' el primero se reutiliza.

Se cubre:
  - `clasificar` devuelve la imagen y las palabras del OCR que ya hizo.
  - `clasificar` no paga un segundo OCR (usa ocr_completo, no ocr_text).
  - `ciclo.extrae` con un previo bueno NO vuelve a capturar ni a leer.
  - `ciclo.extrae` con un previo inservible RECAPTURA (el previo es una
    optimisation, no la fuente de verdad).
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import ciclo  # noqa: E402
import estado  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestClasificarDevuelvePalabras(unittest.TestCase):
    def test_devuelve_la_imagen_y_las_palabras(self):
        img = object()
        with patch.object(estado, "ocr_completo",
                          return_value=("TEXTO", [("X", 1, 2, 3, 4)])):
            st = estado.clasificar(img, usar_jev=False)
        self.assertIs(st["img"], img)
        self.assertEqual(st["words"], [("X", 1, 2, 3, 4)])

    def test_no_paga_un_segundo_ocr(self):
        with patch.object(estado, "ocr_text",
                          side_effect=AssertionError("ocr_text no debe usarse")), \
             patch.object(estado, "ocr_completo", return_value=("T", [])):
            estado.clasificar(object(), usar_jev=False)


class TestCicloConPrevio(unittest.TestCase):
    """`ciclo.extrae` con un previo ya leido."""

    OBJETIVO = {"x": 917, "y": 521, "col_left": 849, "col_right": 924,
                "fila_top": 516, "barra": 538, "suscriptores": 3}

    def _mocks(self,Objetivo_por_llamada):
        async def fake_step(*a, **k):
            return {"status": "ok"}

        return {
            "step": patch.object(ciclo.pf, "step", side_effect=fake_step),
            "shot": patch.object(ciclo.pf, "shot", return_value="IMG"),
            "save": patch.object(ciclo.native_shot, "save", return_value=Path("x.png")),
            "target": patch.object(ciclo, "target_celda_fallback",
                                  side_effect=Objetivo_por_llamada),
            "vacia": patch.object(ciclo, "pagina_vacia", return_value=(False, "ok")),
            "ocr": patch.object(ciclo, "ocr_completo", return_value=("T", [])),
        }

    def test_previo_bueno_no_recaptura_ni_relee(self):
        m = self._mocks([self.OBJETIVO])
        previo = {"img": "IMG", "texto": "T", "words": []}
        with m["step"], m["shot"] as shot, m["save"] as save, m["target"] as tgt, \
             m["vacia"], m["ocr"] as ocr:
            res = asyncio.run(ciclo.extrae("s", 1, dry=True, bajar=False, previo=previo))
        self.assertEqual(res, "ok")
        shot.assert_not_called()          # no se vuelve a capturar
        ocr.assert_not_called()           # no se vuelve a leer
        self.assertEqual(tgt.call_count, 1)
        save.assert_called_once()         # pero la evidencia si se guarda

    def test_previo_inservible_recaptura(self):
        m = self._mocks([None, self.OBJETIVO])
        previo = {"img": "IMG", "texto": "T", "words": []}
        with m["step"], m["shot"] as shot, m["save"], m["target"] as tgt, \
             m["vacia"], m["ocr"]:
            res = asyncio.run(ciclo.extrae("s", 1, dry=True, bajar=False, previo=previo))
        self.assertEqual(res, "ok")
        self.assertEqual(shot.call_count, 1)   # una recaptura
        self.assertEqual(tgt.call_count, 2)    # dos intentos de deteccion


class TestLoopConstruyeElPrevio(unittest.TestCase):
    def test_el_bucle_reutiliza_la_lectura_del_listado(self):
        src = (RAIZ / "tools" / "loop.py").read_text(encoding="utf-8")
        self.assertIn("previo_inicial", src)
        self.assertIn("previo_inicial if desde_pagina == 0 else None", src)


if __name__ == "__main__":
    unittest.main()
