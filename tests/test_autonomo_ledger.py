"""El ledger se escribe en cuanto hay resultado: sin esto el resumen y el
dossier releen datos viejos y una re-corrida puede duplicar pegadas.
"""
import asyncio
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import autonomo
import loop as L


class FakeTraza:
    def evento(self, *a, **k):
        pass


class TestPorDireccionPersiste(unittest.TestCase):
    def test_cada_resultado_se_escribe_en_el_ledger(self):
        escritas = []

        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0):
            return {"id": fila["id"], "estado": "ok", "paginas_vistas": 2,
                    "filas_copiadas": 30, "notas": "2 bloques x 15 filas",
                    "hora_inicio": "10:00:00", "hora_fin": "",
                    "evidencia": "D01-fin.png", "reintentos": 0,
                    "direccion_parte1": "CR 17B", "direccion_parte2": "175-77",
                    "comuna": "BOG", "cuenta_matriz_esperada": "", "ficha": "f"}

        async def fake_entrar(s, hwnd):
            return True

        def fake_ledger(fila):
            escritas.append(dict(fila))

        filas = [{"id": "D01"}, {"id": "D02"}]
        with patch.object(L, "procesa", fake_procesa), \
             patch.object(L, "ledger_escribe", fake_ledger), \
             patch.object(L, "entrar_formulario", fake_entrar), \
             patch.object(L, "ledger_leido", lambda: {}), \
             patch.object(autonomo, "traza_segura", lambda *a, **k: None):
            res = asyncio.run(autonomo.por_direccion(None, 1, filas, False))

        self.assertEqual(len(escritas), 2)
        self.assertEqual([e["id"] for e in escritas], ["D01", "D02"])
        self.assertTrue(all(e["hora_fin"] for e in escritas))
        self.assertEqual(len(res), 2)

    def test_en_dry_no_se_escribe_el_ledger(self):
        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0):
            return {"id": fila["id"], "estado": "ok"}

        async def fake_entrar(s, hwnd):
            return True

        with patch.object(L, "procesa", fake_procesa), \
             patch.object(L, "ledger_escribe",
                          lambda f: self.fail("en dry no se escribe el ledger")), \
             patch.object(L, "entrar_formulario", fake_entrar), \
             patch.object(L, "ledger_leido", lambda: {}), \
             patch.object(autonomo, "traza_segura", lambda *a, **k: None):
            asyncio.run(autonomo.por_direccion(None, 1, [{"id": "D01"}], True))


class TestEscribeFicha(unittest.TestCase):
    def test_conserva_bom_y_tildes_y_solo_pisa_la_columna_ficha(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "direcciones.csv"
            ruta.write_text(
                "parte1;parte2;ficha\r\nCR 17B;175-77;\r\nCR 103D;86-55;\r\n",
                encoding="utf-8")
            ficha = "Cuenta: 34377\nEDIFICIO ÑANDÚ ÁLAMEDA II\nCL 175 17B-10"
            L.escribe_ficha("D01", ficha, ruta)

            self.assertTrue(ruta.read_bytes().startswith(b"\xef\xbb\xbf"),
                            "el CSV debe llevar BOM para que Excel lo lea como UTF-8")
            with open(ruta, encoding="utf-8-sig", newline="") as fh:
                filas = list(csv.DictReader(fh, delimiter=";"))
            self.assertEqual(filas[0]["ficha"], ficha)
            self.assertEqual(filas[0]["parte1"], "CR 17B")
            self.assertEqual(filas[0]["parte2"], "175-77")
            self.assertEqual(filas[1]["ficha"], "")
            self.assertEqual(filas[1]["parte1"], "CR 103D")


class TestMotivoEnNotas(unittest.TestCase):
    def test_el_motivo_queda_en_notas_porque_motivo_no_existe_en_el_ledger(self):
        async def fake_entrar(s, hwnd):
            return False

        with patch.object(L, "reconecta_si_hace_falta", lambda h: True), \
             patch.object(L, "entrar_formulario", fake_entrar), \
             patch.object(L, "ledger_leido", lambda: {}), \
             patch.object(L, "captura", lambda h: (None, None)), \
             patch.object(L, "clasificar",
                          lambda img, usar_jev=False: {
                              "estado": "cuenta_matriz", "confianza": 0.9,
                              "senales": {}}), \
             patch.object(L, "traza", FakeTraza()):
            res = asyncio.run(L.procesa(
                {"id": "D01", "direccion_parte1": "a", "direccion_parte2": "b"},
                1, None, True))

        self.assertNotIn("motivo", res)
        self.assertIn("B1 pantalla", res["notas"])
        self.assertEqual(set(res), set(L.CAMPOS_LEDGER))


if __name__ == "__main__":
    unittest.main()
