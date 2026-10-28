"""en_ibm / ir_al_5250: la via de vuelta del navegador al 5250."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import loop as L

NAVEGADOR = {"estado": None, "senales": {"no_ibm": True, "ibm": False}}
FORMULARIO = {"estado": "formulario", "senales": {"no_ibm": False, "ibm": True}}


class TestEnIbm(unittest.TestCase):
    def test_el_formulario_es_ibm(self):
        self.assertTrue(L.en_ibm(FORMULARIO))

    def test_el_navegador_no_es_ibm(self):
        self.assertFalse(L.en_ibm(NAVEGADOR))

    def test_un_menu_es_ibm_por_la_senal(self):
        # Los menus del 5250 no son un estado conocido pero tienen marcador IBM.
        self.assertTrue(L.en_ibm({"estado": None, "senales": {"ibm": True}}))

    def test_pantalla_desconocida_sin_senales_no_es_ibm(self):
        self.assertFalse(L.en_ibm({"estado": None, "senales": {}}))

    def test_el_estado_desconectado_cuenta_como_ibm(self):
        self.assertTrue(L.en_ibm({"estado": "desconectado", "senales": {}}))


class TestIrAl5250(unittest.TestCase):
    def _correr(self, estados):
        teclas = []

        def _clasificar(img, usar_jev=True):
            return estados[min(len(teclas), len(estados) - 1)]

        def _captura(hwnd):
            return (None, None)

        async def _step(s, label, name, args=None):
            teclas.append((label, name, args))
            return {}

        async def _sleep(t):
            return None

        class Sesion:
            async def call(self, tool, args):
                return {"isError": False, "content": []}

        with patch.object(L, "clasificar", _clasificar), \
             patch.object(L, "captura", _captura), \
             patch.object(L.pf, "step", _step), \
             patch.object(L.asyncio, "sleep", _sleep):
            ok = asyncio.run(L.ir_al_5250(Sesion(), 1))
        return ok, teclas

    def test_altab_hasta_encontrar_el_5250(self):
        ok, teclas = self._correr([NAVEGADOR, NAVEGADOR, FORMULARIO])
        self.assertTrue(ok)
        self.assertEqual(len(teclas), 2)
        self.assertEqual(teclas[0][1], "press_keys")
        self.assertEqual(teclas[0][2]["keys"], ["alt", "tab"])

    def test_si_no_vuelve_devuelve_false(self):
        ok, teclas = self._correr([NAVEGADOR, NAVEGADOR, NAVEGADOR, NAVEGADOR])
        self.assertFalse(ok)
        self.assertEqual(len(teclas), 4)

    def test_si_ya_esta_en_el_5250_no_pulsa_nada(self):
        ok, teclas = self._correr([FORMULARIO])
        self.assertTrue(ok)
        self.assertEqual(teclas, [])


if __name__ == "__main__":
    unittest.main()
