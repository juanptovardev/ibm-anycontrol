"""Tests del bucle de paginacion con capturas y MCP simulados (cero input real)."""
import io
import json
import os
import sys
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import paginar  # noqa: E402


def pagina(estado_nombre, texto, lineas_suscriptor=0, error=None):
    return {
        "estado": estado_nombre,
        "texto": texto,
        "error": error,
        "senales": {"lineas_suscriptor": lineas_suscriptor, "lineas": 8},
    }


@asynccontextmanager
async def fake_connect():
    yield None


async def fake_call(session, name, args=None):
    return {"isError": False, "text": "ok"}


def fake_capturas(secuencia):
    """Devuelve una capturar_estado que entrega la secuencia en orden."""
    pasos = iter(secuencia)

    async def _capturar(hwnd, usar_jev=False):
        return next(pasos)

    return _capturar


async def correr(secuencia, max_paginas=20):
    salida = io.StringIO()
    with patch.object(paginar, "connect", fake_connect), \
         patch.object(paginar, "call", fake_call), \
         patch.object(paginar, "capturar_estado", fake_capturas(secuencia)), \
         redirect_stdout(salida):
        codigo = await paginar.main(198526, max_paginas)
    return codigo, json.loads(salida.getvalue().strip())


class TestPaginar(unittest.IsolatedAsyncioTestCase):
    async def test_pagina_1_ya_tiene_suscriptores(self):
        codigo, out = await correr([pagina("cuenta_matriz", "CONSULTA UNIDADES", 3)])
        self.assertEqual(codigo, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["paginas"], 1)
        self.assertEqual(out["motivo"], "encontrados")

    async def test_fin_de_libro(self):
        codigo, out = await correr([
            pagina("cuenta_matriz", "p1 pagina 1"),
            pagina("cuenta_matriz", "p1 pagina 1"),
        ])
        self.assertEqual(codigo, 1)
        self.assertFalse(out["ok"])
        self.assertEqual(out["motivo"], "fin del libro")

    async def test_tope_de_paginas(self):
        codigo, out = await correr([pagina("cuenta_matriz", "p1")], max_paginas=1)
        self.assertEqual(codigo, 1)
        self.assertEqual(out["motivo"], "tope de paginas")

    async def test_estado_ambiguo_no_se_reporta_como_salida(self):
        codigo, out = await correr([
            pagina("cuenta_matriz", "p1"),
            pagina(None, "p2 ruido", error="timeout"),
        ])
        self.assertEqual(codigo, 1)
        self.assertEqual(out["motivo"], "estado ambiguo (no clasificado)")

    async def test_salida_real_del_listado(self):
        codigo, out = await correr([
            pagina("cuenta_matriz", "p1"),
            pagina("formulario", "CONSULTA EDIFICIO"),
        ])
        self.assertEqual(codigo, 1)
        self.assertEqual(out["motivo"], "salio del listado (formulario)")

    async def test_pantalla_inicial_que_no_es_listado(self):
        codigo, out = await correr([pagina("formulario", "CONSULTA EDIFICIO")])
        self.assertEqual(codigo, 1)
        self.assertFalse(out["ok"])
        self.assertIn("formulario", out["motivo"])

    async def test_avanza_hasta_encontrar(self):
        codigo, out = await correr([
            pagina("cuenta_matriz", "p1"),
            pagina("cuenta_matriz", "p2", 1),
            pagina("cuenta_matriz", "p3", 4),
        ])
        self.assertEqual(codigo, 0)
        self.assertEqual(out["paginas"], 3)
        self.assertEqual(out["lineas_suscriptor"], 4)

    def test_umbral_de_dos_lineas(self):
        self.assertFalse(paginar.hay_suscriptores(pagina("cuenta_matriz", "x", 1)))
        self.assertTrue(paginar.hay_suscriptores(pagina("cuenta_matriz", "x", 2)))


if __name__ == "__main__":
    unittest.main()
