"""Fiabilidad de los datos: sin doble pegado, ledger con filas reales y
reanudacion que no salta paginas.

Hallazgos de la auditoria del 03/11:
  * G3 reintentaba el Ctrl+Shift+V cuando el diff era pequeno. Si el primer
    pegado SI habia funcionado y el remoto solo tardo en pintarlo, el bloque
    se pegaba DOS VECES (medido el 27/10: D03 quedo duplicada).
  * `filas_copiadas = bloques * 15` inflaba el ledger: la ultima pagina de un
    edificio casi nunca trae 15 filas.
  * Entre el pegado y su registro en el ledger habia una ventana ciega: un
    corte ahi repetia (o saltaba) una pagina sin dejar rastro.
  * `loop.main` solo saltaba las 'ok', asi que reintentaba en cada pasada las
    direcciones 'no_encontrado' (que son definitivas).
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import cp
import loop as L


class TestG3SinReintento(unittest.TestCase):
    def test_el_pegado_no_se_reintenta_nunca(self):
        """Reintentar el Ctrl+Shift+V es lo que duplicaba el bloque."""
        src = Path(cp.__file__).read_text(encoding="utf-8")
        self.assertNotIn("ctrl_shift_v_retry", src)

    def test_aceptar_es_menos_exigente_que_dar_por_bueno(self):
        self.assertLess(cp.PASTE_MIN_CAMBIO, cp.PASTE_MIN_DIFF)

    def test_el_piso_de_aceptacion_cubre_un_bloque_de_una_fila(self):
        # Un bloque de 1 fila cambia menos pixeles que 15; con el umbral de
        # exito (3000) se habria dado por fallido y (antes) se habria repegado.
        self.assertGreaterEqual(cp.PASTE_MIN_CAMBIO, 500)


class TestPaginaIncierta(unittest.TestCase):
    def test_pegando_requiere_revision_y_no_se_reanuda_automaticamente(self):
        self.assertFalse(L.es_resumable({"estado": "pegando",
                                         "paginas_vistas": "0"}))
        self.assertFalse(L.es_resumable({"estado": "requiere_revision",
                                         "paginas_vistas": "3"}))

    def test_paginas_cero_no_escribe_estado_pegando(self):
        src = Path(L.__file__).read_text(encoding="utf-8")
        self.assertIn('guarda["estado"] = "pegando"', src)
        self.assertIn('"en curso; confirmar resultado antes de reanudar"', src)
        self.assertIn('estado_previo == "pegando"', src)

    def test_no_encontrado_no_es_resumible(self):
        self.assertFalse(L.es_resumable({"estado": "no_encontrado",
                                         "paginas_vistas": "0"}))

    def test_reanuda_desde_no_confunde_pagina_incierta_con_confirmada(self):
        fila = {"id": "D07", "direccion_parte1": "CR 17B",
                "direccion_parte2": "175-77"}
        hechos = {"D07": {"estado": "requiere_revision", "paginas_vistas": "2",
                          "direccion_parte1": "CR 17B",
                          "direccion_parte2": "175-77"}}
        self.assertEqual(L.reanuda_desde(hechos, fila), 0)


class _Sesion:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *a):
        return False


class TestMainSaltaNoEncontrado(unittest.IsolatedAsyncioTestCase):
    async def test_no_encontrado_no_se_reintenta(self):
        procesadas = []

        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0,
                               solo_ficha=False):
            procesadas.append(fila["id"])
            return {"id": fila["id"], "estado": "ok", "notas": ""}

        async def fake_entrar(s, hwnd):
            return True

        async def fake_step(s, label, name, args=None):
            return {"isError": False, "text": ""}

        filas = [{"id": "D01", "direccion_parte1": "A", "direccion_parte2": "1"},
                 {"id": "D02", "direccion_parte1": "B", "direccion_parte2": "2"}]
        hechos = {"D01": {"estado": "no_encontrado", "paginas_vistas": "0"}}
        with patch.object(L, "connect", lambda: _Sesion()), \
                patch.object(L, "procesa", fake_procesa), \
                patch.object(L, "entrar_formulario", fake_entrar), \
                patch.object(L, "lee_direcciones", lambda: filas), \
                patch.object(L, "ledger_leido", lambda: hechos), \
                patch.object(L, "ledger_en_curso", lambda: {}), \
                patch.object(L, "ledger_escribe", lambda res: None), \
                patch.object(L, "enfocar") as enf, \
                patch.object(L, "traza") as traza, \
                patch.object(L.pf, "step", fake_step):
            enf.set_objetivo = lambda h: None
            traza.evento = lambda *a, **k: None
            await L.main(123, None, False)
        self.assertEqual(procesadas, ["D02"])


class TestFilasReales(unittest.TestCase):
    def test_ciclo_expone_las_filas_reales(self):
        import ciclo
        self.assertTrue(hasattr(ciclo, "ULTIMAS_FILAS"))
        self.assertGreaterEqual(ciclo.ULTIMAS_FILAS, 0)

    def test_un_reintento_no_hereda_filas_de_la_copia_anterior(self):
        import ciclo

        async def fake_step(*_args, **_kwargs):
            return {"status": "ok"}

        ciclo.ULTIMAS_FILAS = 15
        with patch.object(ciclo.pf, "step", fake_step), \
                patch.object(ciclo.pf, "shot", return_value=object()), \
                patch.object(ciclo, "ocr_completo", return_value=("", [])), \
                patch.object(ciclo, "target_celda_fallback", return_value=None):
            with self.assertRaises(ciclo.pf.Halt):
                asyncio.run(ciclo.extrae(object(), 123))
        self.assertEqual(ciclo.ULTIMAS_FILAS, 0)

    def test_el_ledger_no_supone_quince_por_bloque(self):
        """`bloques * 15` era la cifra inflada; ahora se acumula lo copiado."""
        src = Path(L.__file__).read_text(encoding="utf-8")
        self.assertNotIn("bloques * FILAS_POR_BLOQUE", src)
        self.assertIn("filas_total", src)

    def test_procesa_no_inventa_filas_si_el_portapapeles_devuelve_cero(self):
        # Cero no significa que se hayan pegado 15 filas: el ciclo debe abortar
        # antes del pegado, y el ledger no puede aplicar un fallback ficticio.
        src = Path(L.__file__).read_text(encoding="utf-8")
        self.assertIn("filas_bloque = ciclo.ULTIMAS_FILAS", src)
        self.assertIn("filas_total += filas_bloque", src)
        self.assertNotIn("ciclo.ULTIMAS_FILAS or FILAS_POR_BLOQUE", src)


if __name__ == "__main__":
    unittest.main()
