"""en_ibm / ir_al_5250: la via de vuelta del navegador al 5250.

El 03/11 el Alt+Tab dejo de llegar al escritorio remoto, asi que la via
principal es el icono de la taskbar (ventana.ir_a) y el Alt+Tab queda como
ultimo recurso.
"""
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
    def _correr(self, vuelve_por_icono, ir_a_ok=True, arranca_en_ibm=False):
        teclas = []
        llamadas_icono = []
        estado = {"ibm": arranca_en_ibm}

        def _clasificar(img, usar_jev=True):
            return FORMULARIO if estado["ibm"] else NAVEGADOR

        def _captura(hwnd):
            return (None, None)

        async def _step(s, label, name, args=None):
            teclas.append((label, name, args))
            return {}

        async def _sleep(t):
            return None

        async def _ir_a(s, hwnd, destino, intentos=3, espera=0.4):
            llamadas_icono.append(destino)
            estado["ibm"] = vuelve_por_icono
            return ir_a_ok

        class Sesion:
            async def call(self, tool, args):
                return {"isError": False, "content": []}

        with patch.object(L, "clasificar", _clasificar), \
             patch.object(L, "captura", _captura), \
             patch.object(L.pf, "step", _step), \
             patch.object(L.asyncio, "sleep", _sleep), \
             patch.object(L.ventana, "ir_a", _ir_a):
            ok = asyncio.run(L.ir_al_5250(Sesion(), 1))
        return ok, teclas, llamadas_icono

    def test_vuelve_con_el_icono_de_la_taskbar(self):
        ok, teclas, iconos = self._correr(vuelve_por_icono=True)
        self.assertTrue(ok)
        self.assertEqual(iconos, [L.ventana.DESTINO_IBM])
        self.assertEqual(teclas, [])  # no hace falta el Alt+Tab

    def test_si_el_icono_no_sirve_cae_al_altab(self):
        ok, teclas, iconos = self._correr(vuelve_por_icono=False,
                                          ir_a_ok=False)
        self.assertFalse(ok)
        self.assertTrue(teclas)
        self.assertTrue(all(t[1] == "press_keys" for t in teclas))
        self.assertEqual(teclas[0][2]["keys"], ["alt", "tab"])

    def test_si_ya_esta_en_el_5250_no_pulsa_nada(self):
        ok, teclas, iconos = self._correr(vuelve_por_icono=True,
                                          arranca_en_ibm=True)
        self.assertTrue(ok)
        self.assertEqual(teclas, [])
        self.assertEqual(iconos, [])


if __name__ == "__main__":
    unittest.main()
