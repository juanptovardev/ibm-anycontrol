"""enfocar: garantia de que AnyDesk esta delante antes de cada inyeccion."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import enfocar
import preflight_auto as pf


class TestEnfocar(unittest.TestCase):
    def test_sin_objetivo_no_estorba(self):
        with patch.object(enfocar, "OBJETIVO", None):
            self.assertTrue(enfocar.asegura())
            self.assertTrue(enfocar.asegura(123))

    def test_sin_ventana_da_error(self):
        with patch.object(enfocar, "OBJETIVO", 123), \
                patch.object(enfocar, "vigia") as vigia:
            vigia.raiz.return_value = None
            res = enfocar.enfocar(123)
        self.assertFalse(res["ok"])
        self.assertIn("no hay ventana", res["error"])

    def test_ya_delante_no_hace_trabajo(self):
        with patch.object(enfocar, "OBJETIVO", 123), \
                patch.object(enfocar, "vigia") as vigia, \
                patch.object(enfocar, "win32gui") as gui:
            vigia.raiz.return_value = 999
            gui.GetForegroundWindow.return_value = 999
            with patch.object(enfocar, "enfocar") as enf:
                self.assertTrue(enfocar.asegura())
        enf.assert_not_called()

    def test_reintenta_hasta_que_entra(self):
        # OJO: cada intento consume DOS llamadas a GetForegroundWindow (la
        # comprobacion del principio y la del hilo para AttachThreadInput).
        with patch.object(enfocar, "OBJETIVO", 123), \
                patch.object(enfocar, "vigia") as vigia, \
                patch.object(enfocar, "win32gui") as gui, \
                patch.object(enfocar, "win32api") as api, \
                patch.object(enfocar, "time") as t:
            vigia.raiz.return_value = 999
            gui.GetForegroundWindow.side_effect = [111, 222, 333, 444, 999]
            gui.IsIconic.return_value = False
            api.GetCurrentThreadId.return_value = 5
            res = enfocar.enfocar(123, intentos=6, espera=0.01)
        self.assertTrue(res["ok"])
        self.assertEqual(res["intentos"], 3)
        t.sleep.assert_called()

    def test_si_no_puede_devuelve_el_error(self):
        with patch.object(enfocar, "OBJETIVO", 123), \
                patch.object(enfocar, "vigia") as vigia, \
                patch.object(enfocar, "win32gui") as gui, \
                patch.object(enfocar, "win32api") as api, \
                patch.object(enfocar, "time") as t:
            vigia.raiz.return_value = 999
            gui.GetForegroundWindow.return_value = 111
            gui.IsIconic.return_value = False
            api.GetCurrentThreadId.return_value = 5
            gui.SetForegroundWindow.side_effect = OSError("Acceso denegado.")
            res = enfocar.enfocar(123, intentos=2, espera=0.01)
        self.assertFalse(res["ok"])
        self.assertIn("Acceso denegado", res["error"])
        self.assertEqual(res["intentos"], 2)

    def test_usa_el_objetivo_global(self):
        with patch.object(enfocar, "OBJETIVO", 777), \
                patch.object(enfocar, "vigia") as vigia:
            enfocar.raiz()
        vigia.raiz.assert_called_once_with(777)


class TestStepConFoco(unittest.IsolatedAsyncioTestCase):
    """step() es el punto unico de inyeccion: si el foco no se recupera, corta."""

    async def test_halt_si_no_se_puede_enfocar(self):
        with patch.object(pf, "enfocar") as enf:
            enf.asegura.return_value = False
            with self.assertRaises(pf.Halt) as ctx:
                await pf.step(object(), "ctrl_c", "copy_clipboard", {})
        self.assertIn("AnyDesk no esta en primer plano", str(ctx.exception))

    async def test_no_llama_a_la_herramienta_si_el_foco_falla(self):
        with patch.object(pf, "enfocar") as enf, \
                patch.object(pf, "call") as call:
            enf.asegura.return_value = False
            with self.assertRaises(pf.Halt):
                await pf.step(object(), "ctrl_c", "copy_clipboard", {})
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
