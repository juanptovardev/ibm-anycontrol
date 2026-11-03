"""Bloque de UNA sola fila: el cursor NO debe ir con Ctrl+Abajo.

Medido el 03/11: la direccion CR 14 119-33 tenia una segunda pagina con una
sola direccion con suscriptor. Se copio esa linea, y al hacer Ctrl+Abajo el
cursor se fue al FINAL de la hoja (en Google Sheets Ctrl+Abajo salta al
siguiente bloque de datos de la columna, o al final de la hoja si ya no hay
mas). Los pegados siguientes se fueron para alla.

Regla: con un bloque de UNA fila basta un Abajo. Con varias filas sigue
haciendo falta Ctrl+Abajo + Abajo (comportamiento historico).
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import cp  # noqa: E402


class _S:
    def __init__(self):
        self.steps = []


def _fake_step(sess, label, name, args=None):
    sess.steps.append((label, name, args))
    return {"status": "ok"}


class TestPosicionar(unittest.TestCase):
    def _pasos(self, filas):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        async def fake_shot(hwnd, label):
            return None

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp.pf, "shot", fake_shot):
            asyncio.run(cp._posicionar(s, 1, filas))
        return [st[0] for st in s.steps]

    def test_una_fila_solo_abajo(self):
        self.assertEqual(self._pasos(1), ["abajo"])

    def test_varias_filas_ctrl_abajo_mas_abajo(self):
        self.assertEqual(self._pasos(15), ["ctrl_down", "abajo"])

    def test_sin_dato_mantiene_el_comportamiento_historico(self):
        self.assertEqual(self._pasos(0), ["ctrl_down", "abajo"])


class TestCopiar(unittest.TestCase):
    def test_cuenta_solo_las_lineas_con_datos(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._portapapeles.return_value = "linea 1\n\nlinea 2\r\nlinea 3\n"
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 3)

    def test_una_sola_linea(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._portapapeles.return_value = "CL 131C 126-72 CASA3 BOG TVC 50867551"
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 1)

    def test_si_no_se_puede_leer_devuelve_cero(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._portapapeles.side_effect = RuntimeError("sin portapapeles")
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
