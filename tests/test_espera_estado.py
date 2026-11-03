"""Espera de estado: solo clasifica cuando la pantalla ha cambiado.

Antes cada sondeo pagaba un OCR de pantalla completa (~0,93 s) y el primero
se gastaba siempre (el F10 tarda ~1 s en pintarse). Ahora un sondeo en espera
cuesta 40 ms (captura + diff) en vez de 960 ms.
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import loop as L  # noqa: E402


class TestEsperaEstado(unittest.TestCase):
    """Clasificacion diferida: el diff decide cuando pagar el OCR."""

    def _correr(self, cambios, estado="formulario"):
        """cambios: lista de valores que devuelve changed_px en cada sondeo."""
        llamadas = {"clasificar": [], "sleep": 0}
        valores = list(cambios)

        def fake_changed(a, b):
            return valores.pop(0) if valores else 0

        def fake_clasificar(img, usar_jev=False):
            llamadas["clasificar"].append(usar_jev)
            return {"estado": estado, "senales": {}, "img": img, "words": []}

        async def fake_sleep(seg):
            llamadas["sleep"] += 1

        with patch.object(L, "captura", lambda h: ("IMG", None)), \
             patch.object(L, "clasificar", fake_clasificar), \
             patch.object(L.pf, "changed_px", fake_changed), \
             patch("asyncio.sleep", fake_sleep):
            st = asyncio.run(L.espera_estado(1, {estado}))
        return st, llamadas

    def test_no_clasifica_mientras_la_pantalla_no_cambia(self):
        st, llam = self._correr([0, 0, 0])
        # 12 sondeos en espera + solo el fallback final con Jev.
        self.assertEqual(llam["sleep"], 12)
        self.assertEqual(llam["clasificar"], [True])

    def test_clasifica_en_cuanto_la_pantalla_cambia(self):
        st, llam = self._correr([0, 500, 0])
        self.assertEqual(llam["clasificar"], [False])
        self.assertEqual(st["estado"], "formulario")

    def test_devuelve_el_estado_buscado(self):
        st, llam = self._correr([500], estado="cuenta_matriz")
        self.assertEqual(st["estado"], "cuenta_matriz")
        self.assertEqual(llam["clasificar"], [False])

    def test_umbral_de_cambio_configurable(self):
        self.assertTrue(hasattr(L, "UMBRAL_CAMBIO"))
        self.assertEqual(L.UMBRAL_CAMBIO, 50)


if __name__ == "__main__":
    unittest.main()
