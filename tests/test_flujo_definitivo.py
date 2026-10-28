"""Flujo definitivo: reanudacion por direccion, guard de pantalla negra y merge P0."""
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import loop as L


def _fila(id_="D02", p1="CR 84A", p2="145-94"):
    return {"id": id_, "direccion_parte1": p1, "direccion_parte2": p2}


class TestReanudaDesde(unittest.TestCase):
    """El id es posicional: reanudar solo si la direccion coincide."""

    def test_ledger_de_otra_direccion_no_reanuda(self):
        hechos = {"D02": {"estado": "en_curso", "paginas_vistas": "3",
                          "direccion_parte1": "CR 103D",
                          "direccion_parte2": "86-55"}}
        self.assertEqual(L.reanuda_desde(hechos, _fila()), 0)

    def test_misma_direccion_reanuda_las_paginas(self):
        hechos = {"D02": {"estado": "en_curso", "paginas_vistas": "3",
                          "direccion_parte1": "CR 84A",
                          "direccion_parte2": "145-94"}}
        self.assertEqual(L.reanuda_desde(hechos, _fila()), 3)

    def test_normaliza_espacios_y_puntos(self):
        hechos = {"D02": {"estado": "en_curso", "paginas_vistas": "2",
                          "direccion_parte1": " cr 84a ",
                          "direccion_parte2": "145.94"}}
        self.assertEqual(L.reanuda_desde(hechos, _fila()), 2)

    def test_estado_que_no_es_en_curso_no_reanuda(self):
        hechos = {"D02": {"estado": "ok", "paginas_vistas": "3",
                          "direccion_parte1": "CR 84A",
                          "direccion_parte2": "145-94"}}
        self.assertEqual(L.reanuda_desde(hechos, _fila()), 0)

    def test_paginas_vistas_roto_no_revienta(self):
        hechos = {"D02": {"estado": "en_curso", "paginas_vistas": "tres",
                          "direccion_parte1": "CR 84A",
                          "direccion_parte2": "145-94"}}
        self.assertEqual(L.reanuda_desde(hechos, _fila()), 0)


class TestMergeFichasPendientes(unittest.TestCase):
    """P0: el respaldo se vuelca al CSV; gana la ultima por id."""

    def test_upsert_gana_la_ultima_y_borra_el_respaldo(self):
        escritas = {}
        with tempfile.TemporaryDirectory() as tmp:
            pend = Path(tmp) / "fichas_pendientes.csv"
            pend.write_text(
                "D03;Cuenta: 1 | EDIFICIO UNO | CL 1\n"
                "D02;Cuenta: 2 | EDIFICIO DOS | CL 2\n"
                "D03;Cuenta: 3 | EDIFICIO TRES | CL 3\n",
                encoding="utf-8")
            with patch.object(L, "PENDIENTES", pend), \
                    patch.object(L, "escribe_ficha",
                                 lambda i, f: escritas.__setitem__(i, f) or ""):
                n = L.merge_fichas_pendientes()
            self.assertEqual(n, 3)
            self.assertFalse(pend.exists())
        self.assertEqual(escritas["D02"], "Cuenta: 2 | EDIFICIO DOS | CL 2")
        self.assertEqual(escritas["D03"], "Cuenta: 3 | EDIFICIO TRES | CL 3")

    def test_si_todas_fallan_no_borra_el_respaldo(self):
        with tempfile.TemporaryDirectory() as tmp:
            pend = Path(tmp) / "fichas_pendientes.csv"
            pend.write_text("D03;Cuenta: 1 | UNO | CL 1\n", encoding="utf-8")
            with patch.object(L, "PENDIENTES", pend), \
                    patch.object(L, "escribe_ficha",
                                 lambda i, f: "CSV bloqueado"):
                n = L.merge_fichas_pendientes()
            self.assertEqual(n, 0)
            self.assertTrue(pend.exists())

    def test_sin_respaldo_no_hace_nada(self):
        with patch.object(L, "PENDIENTES", Path(tempfile.gettempdir()) / "no_existe.csv"):
            self.assertEqual(L.merge_fichas_pendientes(), 0)


class TestPantallaNegra(unittest.IsolatedAsyncioTestCase):
    """Pantalla sin contenido: si AnyDesk vive se deja vacia; si no, se reconecta."""

    async def _corre(self, vivo: bool):
        llamadas = {"reconecta": 0, "login": 0}

        async def fake_step(s, label, name, args=None):
            return {"ok": True}

        async def fake_entrar(s, hwnd):
            return True

        async def fake_buscar(s, hwnd, det, p1, p2):
            return None

        async def fake_verifica(hwnd):
            return True, ""

        async def fake_espera(hwnd, objetivos, intentos=8, delay=0.7):
            return {"estado": None, "senales": {}, "texto": "", "confianza": 0.0}

        async def fake_login(s, hwnd, img=None):
            llamadas["login"] += 1
            return False

        def fake_reconecta(hwnd):
            llamadas["reconecta"] += 1
            return True

        async def fake_sleep(*_a, **_k):
            return None

        filas = [{"field_x": 531, "cy": 100 + i} for i in range(8)]
        with patch.object(L, "captura", lambda h: ("IMG", {})), \
                patch.object(L, "clasificar", lambda img, usar_jev=False:
                             {"estado": "formulario", "senales": {"form": True},
                              "confianza": 0.9, "texto": ""}), \
                patch.object(L, "entrar_formulario", fake_entrar), \
                patch.object(L, "buscar", fake_buscar), \
                patch.object(L, "verifica_texto", fake_verifica), \
                patch.object(L, "espera_estado", fake_espera), \
                patch.object(L.pf, "step", fake_step), \
                patch.object(L.pf, "shot", lambda h, et: "IMG"), \
                patch.object(L.rowdet, "detect", lambda h: ("IMG", {}, filas)), \
                patch.object(L.traza, "evento", lambda *a, **k: None), \
                patch.object(L, "login_si_hace_falta", fake_login), \
                patch.object(L, "reconecta_si_hace_falta", fake_reconecta), \
                patch.object(L, "hay_dialogo", lambda h: False), \
                patch.object(L, "anydesk_vivo", lambda h: vivo), \
                patch.object(L.asyncio, "sleep", fake_sleep):
            res = await L.procesa(_fila(), 123, object())
        return res, llamadas

    async def test_pantalla_negra_con_anydesk_vivo_es_sin_datos(self):
        res, llamadas = await self._corre(vivo=True)
        self.assertEqual(res["estado"], "sin_datos", res.get("notas"))
        self.assertEqual(llamadas["reconecta"], 1)
        self.assertIn("pantalla sin contenido", res["notas"])

    async def test_pantalla_negra_con_anydesk_caido_reconecta(self):
        res, llamadas = await self._corre(vivo=False)
        self.assertEqual(res["estado"], "revisar", res.get("notas"))
        self.assertEqual(llamadas["reconecta"], 2)
        self.assertIn("AnyDesk caido", res["notas"])


if __name__ == "__main__":
    unittest.main()
