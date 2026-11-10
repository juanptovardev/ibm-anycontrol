"""Pegado dudoso: si el bloque no se ve, la direccion NO se reintenta.

Medido el 27/10: D03 quedo pegada dos veces porque el primer Ctrl+Shift+V si
funciono, el remoto tardo en pintarlo y el reintento automatico lo duplico. Con
miles de filas en la hoja Chrome tarda mas: el riesgo crece con el tamano de
la corrida, asi que el pegado que no se ve deja la direccion para revision
(estado terminal) en vez de reintentarla a ciegas.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import cp
import loop as L
import supervisor as sup


class _Sesion:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *a):
        return False


class TestMarca(unittest.TestCase):
    def test_la_marca_existe(self):
        self.assertTrue(cp.MARCA_PEGADO_DUDOSO)

    def test_el_halt_del_pegado_la_usa(self):
        src = (Path(__file__).resolve().parent.parent / "tools" / "cp.py").read_text(
            encoding="utf-8")
        self.assertIn("MARCA_PEGADO_DUDOSO", src)

    def test_loop_convierte_el_halt_en_estado_terminal(self):
        src = (Path(__file__).resolve().parent.parent / "tools" / "loop.py").read_text(
            encoding="utf-8")
        self.assertIn('res["estado"] = "pegado_dudoso"', src)


class TestSupervisorNoLoReintenta(unittest.TestCase):
    def test_es_terminal(self):
        self.assertIn("pegado_dudoso", sup.TERMINALES)
        self.assertIn("requiere_revision", sup.TERMINALES)

    def test_no_cuenta_como_pendiente(self):
        est = {"D01": {"id": "D01", "estado": "pegado_dudoso"},
               "D02": {"id": "D02", "estado": "ok"},
               "D03": {"id": "D03", "estado": "error"},
               "D04": {"id": "D04", "estado": "requiere_revision"}}
        pendientes = [f.get("id") for f in sup.pendientes(est)]
        self.assertNotIn("D01", pendientes)
        self.assertNotIn("D04", pendientes)
        self.assertIn("D03", pendientes)


class TestLoopMainNoLoRepite(unittest.IsolatedAsyncioTestCase):
    async def test_una_direccion_pegada_dudosa_no_se_reprocesa(self):
        procesadas = []

        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0,
                               solo_ficha=False):
            procesadas.append(fila["id"])
            return {"id": fila["id"], "estado": "error", "notas": "x"}

        async def fake_step(s, label, name, args=None):
            return {"isError": False, "text": ""}

        async def fake_entrar(s, hwnd):
            return True

        filas = [{"id": "D01", "direccion_parte1": "A", "direccion_parte2": "1"},
                 {"id": "D02", "direccion_parte1": "B", "direccion_parte2": "2"}]
        ledger = {"D01": {"id": "D01", "estado": "pegado_dudoso"}}
        with patch.object(L, "connect", lambda: _Sesion()), \
                patch.object(L, "procesa", fake_procesa), \
                patch.object(L, "entrar_formulario", fake_entrar), \
                patch.object(L, "lee_direcciones", lambda: filas), \
                patch.object(L, "ledger_leido", lambda: ledger), \
                patch.object(L, "ledger_en_curso", lambda: {}), \
                patch.object(L, "ledger_escribe", lambda res: None), \
                patch.object(L, "enfocar") as enf, \
                patch.object(L, "traza") as traza, \
                patch.object(L.pf, "step", fake_step):
            enf.set_objetivo = lambda h: None
            traza.evento = lambda *a, **k: None
            await L.main(123, None, False)
        self.assertEqual(procesadas, ["D02"])


if __name__ == "__main__":
    unittest.main()
