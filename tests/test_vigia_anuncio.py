"""Tests del cierre del anuncio de uso comercial de AnyDesk (con mocks).

El anuncio es un modal `ad_modal_dlg` sin botones Repetir/OK cuya «X» es
dibujada a mano, por eso se pulsa por coordenadas. Aqui no se toca ninguna
ventana real: se mockean dialogo/GetWindowRect/clic.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import vigia  # noqa: E402

LICENCIA = {"hwnd": 283, "titulo": "Conexion finalizada",
            "botones": {"Repetir": 286, "OK": 287}}
ANUNCIO = {"hwnd": 51, "titulo": "", "botones": {}}
RECT = (447, 243, 927, 627)


class _Base(unittest.TestCase):
    def setUp(self):
        for objetivo, attr, val in (
                (vigia.time, "sleep", lambda s: None),
                (vigia, "_traer_al_frente", lambda h: None),
                (vigia, "_clic_punto", lambda x, y: {"x": x, "y": y}),
                (vigia.win32gui, "GetWindowRect", lambda h: RECT)):
            p = mock.patch.object(objetivo, attr, val)
            p.start()
            self.addCleanup(p.stop)


class TestAnuncio(_Base):
    def test_sin_dialogo_no_es_anuncio(self):
        with mock.patch.object(vigia, "dialogo", lambda h: {}):
            self.assertEqual(vigia.anuncio(1), {})

    def test_licencia_no_es_anuncio(self):
        with mock.patch.object(vigia, "dialogo", lambda h: LICENCIA):
            self.assertEqual(vigia.anuncio(1), {})

    def test_sin_repetir_es_anuncio(self):
        with mock.patch.object(vigia, "dialogo", lambda h: ANUNCIO):
            self.assertEqual(vigia.anuncio(1), ANUNCIO)

    def test_punto_cierre_es_la_esquina_sup_derecha(self):
        self.assertEqual(vigia.punto_cierre(ANUNCIO), (910, 254))


class TestDespejaAnuncio(_Base):
    def test_sin_anuncio_no_hace_nada(self):
        with mock.patch.object(vigia, "dialogo", lambda h: {}):
            r = vigia.despeja_anuncio(1)
        self.assertTrue(r["ok"])
        self.assertEqual(r["segundos"], 0.0)

    def test_cierra_el_anuncio_en_el_punto_medido(self):
        puntos = []
        with mock.patch.object(vigia, "dialogo", side_effect=[ANUNCIO, {}]), \
             mock.patch.object(vigia, "_clic_punto",
                               lambda x, y: puntos.append((x, y)) or {}):
            r = vigia.despeja_anuncio(1, espera=0)
        self.assertTrue(r["ok"])
        self.assertEqual(puntos, [(910, 254)])

    def test_valida_que_se_cerro(self):
        with mock.patch.object(vigia, "dialogo", side_effect=[ANUNCIO, {}]), \
             mock.patch.object(vigia, "_clic_punto", lambda x, y: {}):
            r = vigia.despeja_anuncio(1, espera=0)
        self.assertTrue(r["ok"])
        self.assertIn("clic", r)

    def test_si_no_se_cierra_reporta_fallo(self):
        caja = {"t": 0.0}

        def reloj():
            caja["t"] += 100.0
            return caja["t"]

        with mock.patch.object(vigia, "dialogo", lambda h: ANUNCIO), \
             mock.patch.object(vigia.time, "time", reloj):
            r = vigia.despeja_anuncio(1, espera=0)
        self.assertFalse(r["ok"])


class TestReconectaConAnuncio(_Base):
    def test_solo_anuncio_delega_en_despeja(self):
        with mock.patch.object(vigia, "dialogo",
                               side_effect=[ANUNCIO, ANUNCIO, {}]):
            r = vigia.reconecta(1)
        self.assertTrue(r["ok"])

    def test_licencia_que_cierra_sin_anuncio(self):
        llamadas = {"n": 0}

        def dlg(h):
            llamadas["n"] += 1
            return LICENCIA if llamadas["n"] == 1 else {}

        with mock.patch.object(vigia, "dialogo", dlg), \
             mock.patch.object(vigia, "clic_fisico", lambda h: {"via": "fisico"}):
            r = vigia.reconecta(1)
        self.assertTrue(r["ok"])
        self.assertNotIn("anuncio", r)

    def test_licencia_que_deja_anuncio(self):
        # 1) dialogo de licencia, 2) anuncio (la sesion ya entro), 3) cerrado.
        seq = iter([LICENCIA, ANUNCIO, ANUNCIO, {}])
        with mock.patch.object(vigia, "dialogo", lambda h: next(seq)), \
             mock.patch.object(vigia, "clic_fisico", lambda h: {"via": "fisico"}):
            r = vigia.reconecta(1)
        self.assertTrue(r["ok"])
        self.assertIn("anuncio", r)


if __name__ == "__main__":
    unittest.main()
