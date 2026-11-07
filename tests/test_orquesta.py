"""Orquesta: la API publica del agente."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import loop as L  # noqa: E402
import orquesta as O  # noqa: E402


class TestSiguientePaso(unittest.TestCase):
    def test_delega_en_el_semaforo(self):
        self.assertEqual(O.siguiente_paso("estado", "formulario"), "buscar")
        self.assertEqual(O.siguiente_paso("estado", "fin_libro"), "cierre")
        self.assertEqual(O.siguiente_paso("desconocido", "x"), "detener")


class TestDelegacion(unittest.TestCase):
    def test_procesa_delega_en_loop(self):
        llamadas = []

        async def fake(fila, hwnd, s, dry=False, desde_pagina=0,
                       solo_ficha=False):
            llamadas.append((fila, hwnd, desde_pagina, solo_ficha))
            return {"id": fila.get("id"), "ok": True}

        with patch.object(L, "procesa", fake):
            import asyncio
            out = asyncio.run(O.procesa({"id": "D01"}, 1, None))
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(llamadas[0][0]["id"], "D01")
        self.assertEqual(out["id"], "D01")

    def test_main_delega_en_loop(self):
        llamadas = []

        async def fake(hwnd, solo_id=None, dry=False, solo_ficha=False):
            llamadas.append(hwnd)
            return 0

        with patch.object(L, "main", fake):
            import asyncio
            code = asyncio.run(O.main(1))
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(code, 0)

    def test_los_tres_modulos_existen(self):
        import matriz_buscar
        import matriz_extraer
        import matriz_ficha
        self.assertTrue(hasattr(matriz_buscar, "buscar"))
        self.assertTrue(hasattr(matriz_buscar, "verifica_texto"))
        self.assertTrue(hasattr(matriz_ficha, "escribe_ficha"))
        self.assertTrue(hasattr(matriz_ficha, "merge_fichas_pendientes"))
        self.assertTrue(hasattr(matriz_extraer, "extrae_bloque"))


if __name__ == "__main__":
    unittest.main()
