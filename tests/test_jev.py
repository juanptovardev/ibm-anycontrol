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

    def test_curl_ausente_no_lanza(self):
        with patch.object(_jev, "_key", return_value="k"), \
             patch.object(_jev.subprocess, "run", side_effect=FileNotFoundError("curl.exe")):
            r = _jev.ask("texto", "instruccion", OPCIONES)
        self.assertFalse(r["ok"])
        self.assertIn("FileNotFoundError", r["error"])


if __name__ == "__main__":
    unittest.main()
