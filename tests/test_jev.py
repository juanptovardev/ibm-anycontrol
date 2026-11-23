"""Tests del cliente Jev: fallos de clave/red/forma nunca lanzan excepcion."""
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import _jev  # noqa: E402


def curl(stdout: str, code: int = 0):
    return subprocess.CompletedProcess(args=["curl.exe"], returncode=code,
                                       stdout=stdout.encode("utf-8"), stderr=b"")


OPCIONES = ["formulario", "cuenta_matriz", "sin_coincidencia", "error"]


class TestJev(unittest.TestCase):
    def setUp(self):
        # El cliente se prueba aislado de la politica de despliegue: aqui Jev
        # esta habilitado; `disponible()` se prueba aparte.
        self._hab = patch.object(_jev, "habilitado", return_value=True)
        self._hab.start()
        self.addCleanup(self._hab.stop)

    def test_sin_clave(self):
        with patch.object(_jev, "_key", return_value=""):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertFalse(r["ok"])
        self.assertIn("clave", r["error"])

    def test_http_distinto_de_200(self):
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", return_value=curl('{"e":1}\n__HTTP__429')):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertFalse(r["ok"])
        self.assertEqual(r["http_status"], 429)

    def test_sin_answers_estado(self):
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", return_value=curl('{"answers":{}}\n__HTTP__200')):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertFalse(r["ok"])
        self.assertIn("answers.estado", r["error"])

    def test_respuesta_valida(self):
        cuerpo = json.dumps({"answers": {"estado": {
            "choice": "formulario", "confidence": 0.9, "probabilities": {"formulario": 0.9}}}})
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", return_value=curl(cuerpo + "\n__HTTP__200")):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertTrue(r["ok"])
        self.assertEqual(r["choice"], "formulario")
        self.assertEqual(r["confidence"], 0.9)
        self.assertEqual(r["confianza"], 0.9)

    def test_confianza_viene_de_probabilities_no_del_campo_confidence(self):
        # Medido el 28/10 contra la API real: 'confidence'=0 con
        # probabilities {vacia: 0.5, con_datos: 0.5}. La metrica fiable es
        # probabilities[choice].
        cuerpo = json.dumps({"answers": {"estado": {
            "choice": "vacia", "confidence": 0,
            "probabilities": {"vacia": 0.5, "con_datos": 0.5}}}})
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", return_value=curl(cuerpo + "\n__HTTP__200")):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertEqual(r["confidence"], 0)
        self.assertEqual(r["confianza"], 0.5)

    def test_sin_probabilities_usa_confidence(self):
        cuerpo = json.dumps({"answers": {"estado": {
            "choice": "formulario", "confidence": 0.75}}})
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", return_value=curl(cuerpo + "\n__HTTP__200")):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertEqual(r["confianza"], 0.75)

    def test_curl_ausente_no_lanza(self):
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", side_effect=FileNotFoundError("curl.exe")):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertFalse(r["ok"])
        self.assertIn("FileNotFoundError", r["error"])


class TestDisponible(unittest.TestCase):
    def test_apagado_por_defecto(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MATRIZ_JEV", None)
            os.environ.pop("MATRIZ_JEV_KEY", None)
            with patch.object(_jev, "_key", return_value="k"):
                self.assertFalse(_jev.disponible())

    def test_encendido_requiere_clave(self):
        with patch.dict(os.environ, {"MATRIZ_JEV": "1"}, clear=False):
            with patch.object(_jev, "_key", return_value=""):
                self.assertFalse(_jev.disponible())
            with patch.object(_jev, "_key", return_value="k"):
                self.assertTrue(_jev.disponible())

    def test_cero_manda_sobre_config(self):
        with patch.dict(os.environ, {"MATRIZ_JEV": "0"}, clear=False):
            with patch.object(_jev, "_key", return_value="k"), \
                 patch.object(_jev, "ENABLED", True):
                self.assertFalse(_jev.disponible())

    def test_sin_env_usa_config(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MATRIZ_JEV", None)
            with patch.object(_jev, "_key", return_value="k"), \
                 patch.object(_jev, "ENABLED", True):
                self.assertTrue(_jev.disponible())


if __name__ == "__main__":
    unittest.main()
