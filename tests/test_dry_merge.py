"""El resumen y el dossier deben reflejar lo que la corrida hizo, no el ledger viejo.

En `--dry` el ledger NO se escribe, asi que sin el overlay en memoria el
resumen y el dossier releian el ledger de la corrida anterior y reportaban
"nada hecho" aunque el dry hubiera recorrido todo.
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import autonomo


class _SessFalsa:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return False


async def _pre_vuelo_ok(s, hwnd):
    return True


async def _por_direccion_falsa(s, hwnd, filas, dry, solo_ficha=False):
    return [{"id": "D01", "estado": "ok", "paginas_vistas": 2,
             "filas_copiadas": 30, "notas": "dry"}]


class TestMergeEnDry(unittest.TestCase):
    def _corre(self, dry):
        fila = {"id": "D01", "parte1": "CR 17B", "parte2": "175-77"}
        capturado = {}

        def dossier_falso(hwnd, filas, hechos, dry_flag):
            capturado["hechos"] = hechos
            capturado["filas"] = filas
            return Path("dossier.md")

        async def pf_step(s, label, name, args=None):
            return {"status": "ok"}

        with patch.object(autonomo, "connect", lambda: _SessFalsa()), \
                patch.object(autonomo, "pf") as pf, \
                patch.object(autonomo, "pre_vuelo", _pre_vuelo_ok), \
                patch.object(autonomo, "por_direccion", _por_direccion_falsa), \
                patch.object(autonomo, "escribe_dossier", dossier_falso), \
                patch.object(autonomo.enfocar, "set_objetivo"), \
                patch.object(autonomo.L, "merge_fichas_pendientes", return_value=0), \
                patch.object(autonomo.L, "lee_direcciones", return_value=[fila]), \
                patch.object(autonomo.L, "ledger_leido", return_value={}), \
                patch.object(autonomo.L, "ledger_escribe") as escribe:
            pf.step = pf_step
            codigo = asyncio.run(autonomo.corre(123, None, dry))
        return codigo, capturado, escribe

    def test_en_dry_no_se_escribe_el_ledger(self):
        codigo, capturado, escribe = self._corre(dry=True)
        self.assertEqual(codigo, 0)
        escribe.assert_not_called()

    def test_el_dossier_muestra_los_resultados_en_memoria(self):
        codigo, capturado, escribe = self._corre(dry=True)
        self.assertEqual(codigo, 0)
        hechos = capturado["hechos"]
        self.assertIn("D01", hechos)
        self.assertEqual(hechos["D01"]["estado"], "ok")
        self.assertEqual(hechos["D01"]["paginas_vistas"], 2)
        self.assertEqual(hechos["D01"]["filas_copiadas"], 30)


class TestLedgerEnDry(unittest.IsolatedAsyncioTestCase):
    """Control positivo: en REAL se escribe el ledger, en DRY no.

    Sin este control, la asercion "en dry no se escribe" podria pasar por
    vacio (si el camino real tampoco escribiera nunca).
    """

    async def _por_direccion(self, dry):
        fila = {"id": "D01", "direccion_parte1": "CR 17B",
                "direccion_parte2": "175-77"}
        resultado = {"id": "D01", "estado": "ok", "paginas_vistas": 1,
                     "filas_copiadas": 15}

        async def procesa(f, hwnd, s, dry=False, desde_pagina=0, solo_ficha=False):
            return resultado

        async def entrar(s, hwnd):
            return True

        with patch.object(autonomo.L, "procesa", procesa), \
                patch.object(autonomo.L, "entrar_formulario", entrar), \
                patch.object(autonomo.L, "ledger_en_curso", return_value={}), \
                patch.object(autonomo.L, "ledger_escribe") as escribe:
            await autonomo.por_direccion(object(), 123, [fila], dry)
        return escribe

    async def test_en_real_se_escribe_el_ledger(self):
        escribe = await self._por_direccion(dry=False)
        escribe.assert_called_once()

    async def test_en_dry_no_se_escribe_el_ledger(self):
        escribe = await self._por_direccion(dry=True)
        escribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
