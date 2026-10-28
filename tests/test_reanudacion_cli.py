"""Reanudacion del CLI de loop.py y limpieza del portapapeles tras el login.

Los dos casos que pidio el review:
  - loop.main debe pasar desde_pagina cuando el ledger dice 'en_curso'
    (si no, esta via de CLI vuelve a pegar desde la pagina 1).
  - login.entrar debe borrar la clave del portapapeles cuando ya la cogio
    el 5250 (AnyDesk sincroniza ese portapapeles al PC remoto).
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

import login  # noqa: E402
import loop as L  # noqa: E402


async def _noop_step(*args, **kwargs):
    return {"status": "ok"}


async def _noop_sleep(*args, **kwargs):
    return None


class _SesionFalsa:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


class TestCliReanuda(unittest.TestCase):
    def test_en_curso_reanuda_desde_la_pagina_registrada(self):
        filas = [{"id": "D01", "direccion_parte1": "CR 17B",
                  "direccion_parte2": "175-77", "comuna": "BOG",
                  "cuenta_matriz_esperada": ""}]
        ledger = {"D01": {"estado": "en_curso", "paginas_vistas": "2"}}
        llamadas = []

        async def fake_procesa(fila, hwnd, s, dry=False, desde_pagina=0):
            llamadas.append(desde_pagina)
            return {"id": "D01", "estado": "ok", "paginas_vistas": desde_pagina,
                    "filas_copiadas": desde_pagina * 15, "notas": "",
                    "hora_inicio": "", "hora_fin": "", "evidencia": "",
                    "reintentos": 0}

        async def fake_entrar_formulario(s, hwnd):
            return True

        with patch.object(L, "lee_direcciones", lambda: filas), \
                patch.object(L, "ledger_leido", lambda: ledger), \
                patch.object(L, "procesa", fake_procesa), \
                patch.object(L, "ledger_escribe", lambda res: None), \
                patch.object(L, "entrar_formulario", fake_entrar_formulario), \
                patch.object(L, "traza"), \
                patch.object(L, "connect", lambda: _SesionFalsa()), \
                patch.object(L.pf, "step", _noop_step):
            asyncio.run(L.main(123, None, False))
        self.assertEqual(llamadas, [2])

    def test_estado_ok_se_sigue_saltando(self):
        filas = [{"id": "D01", "direccion_parte1": "CR 17B",
                  "direccion_parte2": "175-77", "comuna": "BOG",
                  "cuenta_matriz_esperada": ""}]
        ledger = {"D01": {"estado": "ok", "paginas_vistas": "10"}}
        with patch.object(L, "lee_direcciones", lambda: filas), \
                patch.object(L, "ledger_leido", lambda: ledger), \
                patch.object(L, "procesa", _no_debe_llamar), \
                patch.object(L, "connect", lambda: _SesionFalsa()):
            self.assertEqual(asyncio.run(L.main(123, None, False)), 0)


async def _no_debe_llamar(*args, **kwargs):
    raise AssertionError("procesa no debe llamarse con una direccion ya 'ok'")


class TestLoginLimpiaClipboard(unittest.TestCase):
    def test_entrar_borra_la_clave_del_portapapeles(self):
        puestos = []
        with patch.object(login, "pon_clipboard",
                          lambda t: puestos.append(t) or True), \
                patch.object(login, "campo_usuario", lambda img: (100, 50)), \
                patch.object(login, "captura", lambda hwnd: ("IMG", None)), \
                patch.object(login.pytesseract, "image_to_string",
                             lambda img, config=None: "menu principal"), \
                patch.object(login.pf, "step", _noop_step), \
                patch.object(login, "asyncio", type("A", (), {"sleep": _noop_sleep})):
            ok = asyncio.run(login.entrar(None, 1, "usuario", "clave"))
        self.assertTrue(ok)
        self.assertEqual(puestos[0], "usuario\r\nclave")
        self.assertEqual(puestos[-1], "")


if __name__ == "__main__":
    unittest.main()
