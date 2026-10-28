"""Flujo definitivo: reanudacion por direccion, guard de pantalla negra y merge P0."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            self.assertEqual(n, 3)  # cuenta escrituras ok, no ids distintos
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
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(L, "PENDIENTES", Path(tmp) / "no_existe.csv"):
                self.assertEqual(L.merge_fichas_pendientes(), 0)

    def test_fallo_parcial_conserva_solo_las_fallidas(self):
        """El respaldo no se borra si alguna ficha no se pudo escribir."""
        with tempfile.TemporaryDirectory() as tmp:
            pend = Path(tmp) / "fichas_pendientes.csv"
            pend.write_text(
                "D01;Cuenta: 1 | UNO | CL 1\n"
                "D02;Cuenta: 2 | DOS | CL 2\n",
                encoding="utf-8")

            def escribe(id_, ficha):
                return "" if id_ == "D01" else "CSV bloqueado"

            with patch.object(L, "PENDIENTES", pend), \
                    patch.object(L, "escribe_ficha", escribe):
                n = L.merge_fichas_pendientes()
            self.assertEqual(n, 1)
            self.assertTrue(pend.exists())
            quedan = pend.read_text(encoding="utf-8")
            self.assertIn("D02", quedan)
            self.assertNotIn("D01", quedan)


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


class TestLedgerEnCurso(unittest.TestCase):
    """El punto de reanudacion es la ultima fila en_curso, no la ultima fila."""

    def test_un_error_posterior_no_borra_el_punto_de_reanudacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "ledger.csv"
            ruta.write_text(
                "id,direccion_parte1,direccion_parte2,estado,paginas_vistas\n"
                "D02,CR 84A,145-94,en_curso,7\n"
                "D02,CR 84A,145-94,en_curso,8\n"
                "D02,CR 84A,145-94,error,0\n",
                encoding="utf-8")
            hechos = L.ledger_en_curso(ruta)
            self.assertEqual(hechos["D02"]["paginas_vistas"], "8")
            self.assertEqual(L.reanuda_desde(hechos, _fila()), 8)


class TestSoloFicha(unittest.IsolatedAsyncioTestCase):
    """--solo-ficha: guarda la ficha en la columna 3 y no entra al listado."""

    async def test_solo_ficha_guarda_y_no_extrae(self):
        escritas = []
        copias = {"n": 0}
        extraidos = {"n": 0}

        async def fake_step(s, label, name, args=None):
            if name == "copy_clipboard":
                copias["n"] += 1
            return {"ok": True}

        async def fake_entrar(s, hwnd):
            return True

        async def fake_buscar(s, hwnd, det, p1, p2):
            return None

        async def fake_verifica(hwnd):
            return True, ""

        estados = ["ficha", "cuenta_matriz"]

        async def fake_espera(hwnd, objetivos, intentos=8, delay=0.7):
            st = estados.pop(0) if estados else "cuenta_matriz"
            return {"estado": st, "senales": {}, "texto": "", "confianza": 0.95}

        async def fake_login(s, hwnd, img=None):
            return False

        async def fake_sleep(*_a, **_k):
            return None

        async def fake_extrae(*_a, **_k):
            extraidos["n"] += 1
            return "ok"

        filas = [{"field_x": 531, "cy": 100 + i} for i in range(8)]
        with patch.object(L, "captura", lambda h: ("IMG", {})), \
                patch.object(L, "clasificar", lambda img, usar_jev=False:
                             {"estado": "formulario", "senales": {"form": True},
                              "confianza": 0.9, "texto": ""}), \
                patch.object(L, "entrar_formulario", fake_entrar), \
                patch.object(L, "rowdet") as rowdet, \
                patch.object(L, "buscar", fake_buscar), \
                patch.object(L, "verifica_texto", fake_verifica), \
                patch.object(L, "espera_estado", fake_espera), \
                patch.object(L, "hay_dialogo", lambda h: False), \
                patch.object(L, "reconecta_si_hace_falta", lambda h: True), \
                patch.object(L, "login_si_hace_falta", fake_login), \
                patch.object(L, "anydesk_vivo", lambda h: True), \
                patch.object(L.recepcion, "bloque_de",
                             lambda t: "Cuenta: 1 | EDIFICIO UNO | CL 1"), \
                patch.object(L.recepcion, "_portapapeles", lambda: ""), \
                patch.object(L, "escribe_ficha",
                             lambda i, f: escritas.append((i, f)) or ""), \
                patch.object(L.ciclo, "extrae", fake_extrae), \
                patch.object(L.traza, "evento", lambda *a, **k: None), \
                patch.object(L.pf, "step", fake_step), \
                patch.object(L.asyncio, "sleep", fake_sleep):
            rowdet.detect.return_value = ("IMG", {}, filas)
            res = await L.procesa(_fila(), 123, object(), solo_ficha=True)

        self.assertEqual(res["estado"], "ok")
        self.assertEqual(res["paginas_vistas"], 0)
        self.assertIn("solo ficha", res["notas"])
        self.assertEqual(len(escritas), 1)
        self.assertEqual(escritas[0][0], "D02")
        self.assertIn("EDIFICIO UNO", escritas[0][1])
        self.assertEqual(copias["n"], 1)
        self.assertEqual(extraidos["n"], 0)


class TestPaginasVistas(unittest.IsolatedAsyncioTestCase):
    """paginas_vistas cuenta las paginas AVANZADAS (pegadas + saltadas)."""

    async def _corre(self):
        filas_ledger = []
        llamadas = {"extrae": 0}

        async def fake_step(s, label, name, args=None):
            return {"ok": True}

        async def fake_entrar(s, hwnd):
            return True

        async def fake_buscar(s, hwnd, det, p1, p2):
            return None

        async def fake_verifica(hwnd):
            return True, ""

        async def fake_espera(hwnd, objetivos, intentos=8, delay=0.7):
            return {"estado": "cuenta_matriz", "senales": {"unidades": True},
                    "texto": "", "confianza": 0.95}

        async def fake_extrae(s, hwnd, dry=False, bajar=True, previo=None):
            llamadas["extrae"] += 1
            # primera pagina vacia (se salta), segunda con datos (se pega)
            return "vacia" if llamadas["extrae"] == 1 else "ok"

        async def fake_volver(s, hwnd, intentos=3, sondeos=4):
            return True

        async def fake_avanza(s, hwnd):
            return {"estado": "cuenta_matriz", "senales": {}}

        async def fake_sleep(*_a, **_k):
            return None

        filas = [{"field_x": 531, "cy": 100 + i} for i in range(8)]
        with patch.object(L, "captura", lambda h: (MagicMock(), {})), \
                patch.object(L, "clasificar", lambda img, usar_jev=False:
                             {"estado": "formulario", "senales": {"form": True},
                              "confianza": 0.9, "texto": ""}), \
                patch.object(L, "entrar_formulario", fake_entrar), \
                patch.object(L, "rowdet") as rowdet, \
                patch.object(L, "buscar", fake_buscar), \
                patch.object(L, "verifica_texto", fake_verifica), \
                patch.object(L, "espera_estado", fake_espera), \
                patch.object(L.pf, "step", fake_step), \
                patch.object(L, "traza") as traza, \
                patch.object(L, "ciclo") as ciclo, \
                patch.object(L, "pagina") as pagina, \
                patch.object(L, "escribe_ficha", lambda i, f: ""), \
                patch.object(L, "ledger_escribe", filas_ledger.append), \
                patch.object(L, "volver_formulario", fake_entrar), \
                patch.object(L, "hay_dialogo", lambda h: False), \
                patch.object(L, "reconecta_si_hace_falta", lambda h: True), \
                patch.object(L, "obedece", lambda: "seguir"), \
                patch.object(L.asyncio, "sleep", fake_sleep):
            rowdet.detect.return_value = (MagicMock(), {}, filas)
            traza.evento = lambda *a, **k: None
            ciclo.extrae = fake_extrae
            pagina.volver = fake_volver
            pagina.avanza = fake_avanza
            decisiones = {"n": 0}

            def fake_decide(estado, no_ibm):
                # 1a pagina (vacia) -> seguir; 2a (pegada) -> fin
                decisiones["n"] += 1
                return "fin" if decisiones["n"] >= 2 else "seguir"

            pagina.decide = fake_decide
            await L.procesa(_fila(), 123, object())
        return filas_ledger

    async def test_una_pagina_vacia_cuenta_para_reanudar(self):
        filas = await self._corre()
        en_curso = [f for f in filas if f.get("estado") == "en_curso"]
        self.assertTrue(en_curso)
        # 1 pagina saltada + 1 pegada = 2 paginas avanzadas
        self.assertEqual(en_curso[0]["paginas_vistas"], 2)
        # las filas copiadas solo cuentan las pegadas
        self.assertEqual(en_curso[0]["filas_copiadas"], 15)


if __name__ == "__main__":
    unittest.main()
