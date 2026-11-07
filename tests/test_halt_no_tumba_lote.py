"""Un Halt puntual no puede tumbar el lote.

Medido el 28/10: el guard de foco de `preflight_auto.step` lanzo Halt dentro
del reencuadre y eso mato la corrida entera (D05 nunca arranco). Estos tests
cierran los dos caminos que quedaban abiertos: `loop.main` (CLI) y
`autonomo.pre_vuelo` (preparacion del lote).
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import autonomo
import loop as L
import preflight_auto as pf


class _Sesion:
    """Sustituto de `connect()`: un async context manager vacio."""

    async def __aenter__(self):
        return object()

    async def __aexit__(self, *a):
        return False


class TestLoopMainNoSeTumba(unittest.IsolatedAsyncioTestCase):
    async def _corre(self, entrar):
        procesadas = []

        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0,
                               solo_ficha=False):
            procesadas.append(fila["id"])
            return {"id": fila["id"], "estado": "error", "notas": "x"}

        async def fake_step(s, label, name, args=None):
            return {"isError": False, "text": ""}

        filas = [{"id": "D01", "direccion_parte1": "A", "direccion_parte2": "1"},
                 {"id": "D02", "direccion_parte1": "B", "direccion_parte2": "2"},
                 {"id": "D03", "direccion_parte1": "C", "direccion_parte2": "3"}]
        with patch.object(L, "connect", lambda: _Sesion()), \
                patch.object(L, "procesa", fake_procesa), \
                patch.object(L, "entrar_formulario", entrar), \
                patch.object(L, "lee_direcciones", lambda: filas), \
                patch.object(L, "ledger_leido", lambda: {}), \
                patch.object(L, "ledger_en_curso", lambda: {}), \
                patch.object(L, "ledger_escribe", lambda res: None), \
                patch.object(L, "enfocar") as enf, \
                patch.object(L, "traza") as traza, \
                patch.object(L.pf, "step", fake_step):
            enf.set_objetivo = lambda h: None
            traza.evento = lambda *a, **k: None
            await L.main(123, None, False)
        return procesadas

    async def test_halt_en_el_reencuadre_procesa_todas_las_filas(self):
        async def fake_entrar(s, hwnd):
            raise pf.Halt("AnyDesk no esta en primer plano")

        procesadas = await self._corre(fake_entrar)
        self.assertEqual(procesadas, ["D01", "D02", "D03"])

    async def test_excepcion_no_halt_tambien_procesa_todas_las_filas(self):
        async def fake_entrar(s, hwnd):
            raise RuntimeError("PrintWindow fallo")

        procesadas = await self._corre(fake_entrar)
        self.assertEqual(procesadas, ["D01", "D02", "D03"])


class TestPreVueloNoSeTumba(unittest.IsolatedAsyncioTestCase):
    async def test_halt_no_propaga_y_el_bucle_sigue(self):
        intentos = []

        async def fake_entrar(s, hwnd):
            intentos.append(1)
            raise pf.Halt("AnyDesk no esta en primer plano")

        async def fake_sleep(*a, **k):
            return None

        with patch.object(autonomo, "vigia") as vigia, \
                patch.object(autonomo, "_captura_limpia",
                             lambda h: ("IMG", "texto", {"estado": "cuenta_matriz",
                                                         "senales": {},
                                                         "confianza": 0.9})), \
                patch.object(autonomo.L, "entrar_formulario", fake_entrar), \
                patch.object(autonomo.asyncio, "sleep", fake_sleep):
            vigia.raiz.return_value = 1
            vigia.dialogo.return_value = {}
            ok = await autonomo.pre_vuelo(object(), 123, intentos=3)
        self.assertFalse(ok)
        self.assertEqual(len(intentos), 3)


if __name__ == "__main__":
    unittest.main()
