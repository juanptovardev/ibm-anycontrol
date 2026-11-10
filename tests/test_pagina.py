"""Tests de la decision de paginacion (pura, sin MCP ni capturas)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import pagina  # noqa: E402


class TestDecide(unittest.TestCase):
    def test_listado_normal_sigue(self):
        self.assertEqual(pagina.decide("cuenta_matriz"), "seguir")

    def test_fin_de_libro_termina(self):
        self.assertEqual(pagina.decide("fin_libro"), "fin")

    def test_pantalla_no_ibm_aborta(self):
        self.assertEqual(pagina.decide(None, no_ibm=True), "abortar")

    def test_sin_clasificar_aborta(self):
        self.assertEqual(pagina.decide(None), "abortar")

    def test_formulario_inesperado_aborta(self):
        # Si AvPág devolvio al formulario, la posicion se perdio: no se sigue.
        self.assertEqual(pagina.decide("formulario"), "abortar")

    def test_error_aborta(self):
        self.assertEqual(pagina.decide("error"), "abortar")

    def test_fin_gana_sobre_no_ibm_ausente(self):
        self.assertEqual(pagina.decide("fin_libro", no_ibm=False), "fin")

    def test_pagina_repetida_aborta(self):
        # Pantalla sin cambio + listado = la MISMA pagina: copiarla seria
        # duplicar, asi que se aborta (el ledger guarda el punto).
        self.assertEqual(pagina.decide("cuenta_matriz", sin_cambio=True),
                         "abortar")

    def test_fin_gana_sobre_sin_cambio(self):
        self.assertEqual(pagina.decide("fin_libro", sin_cambio=True), "fin")


class TestAvanzaSinCambio(unittest.TestCase):
    """avanza() nunca debe devolver None (crasheaba con AttributeError)."""

    def test_sin_cambio_clasifica_y_no_revienta(self):
        from unittest.mock import AsyncMock, patch
        import asyncio

        async def corre():
            with patch.object(pagina.pf, "step", new=AsyncMock()), \
                 patch.object(pagina.pf, "shot", return_value="IMG"), \
                 patch.object(pagina.pf, "changed_px", return_value=0), \
                 patch.object(pagina, "ocr_completo",
                              return_value=("txt", [])), \
                 patch.object(pagina, "clasificar_texto",
                              return_value={"estado": "fin_libro",
                                            "confianza": 0.95,
                                            "senales": {"fin": True}}), \
                 patch.object(pagina.asyncio, "sleep", new=AsyncMock()):
                return await pagina.avanza(None, 1, prev=object())
        st = asyncio.run(corre())
        self.assertIsInstance(st, dict)
        self.assertEqual(st["estado"], "fin_libro")
        self.assertTrue(st["sin_cambio"])
        self.assertTrue(pagina.ULTIMA["sin_cambio"])

    def test_sin_lectura_devuelve_dict_vacio(self):
        from unittest.mock import AsyncMock, patch
        import asyncio

        async def corre():
            with patch.object(pagina.pf, "step", new=AsyncMock()), \
                 patch.object(pagina.pf, "shot", return_value="IMG"), \
                 patch.object(pagina.pf, "changed_px", return_value=10 ** 6), \
                 patch.object(pagina, "ocr_completo", return_value=("", [])), \
                 patch.object(pagina, "clasificar_texto",
                              return_value={"estado": None, "senales": {}}), \
                 patch.object(pagina.asyncio, "sleep", new=AsyncMock()):
                return await pagina.avanza(None, 1, prev=object())
        st = asyncio.run(corre())
        self.assertIsInstance(st, dict)
        self.assertIsNone(st["estado"])


if __name__ == "__main__":
    unittest.main()
