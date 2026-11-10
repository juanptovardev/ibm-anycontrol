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
from unittest.mock import AsyncMock, patch

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

        def fake_shot(hwnd, label):
            return None

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp.pf, "shot", fake_shot):
            asyncio.run(cp._posicionar(s, 1, filas))
        return [st[0] for st in s.steps]

    def test_una_fila_solo_abajo(self):
        self.assertEqual(self._pasos(1), ["abajo"])

    def test_varias_filas_ctrl_abajo_mas_abajo(self):
        self.assertEqual(self._pasos(15), ["ctrl_down", "abajo"])

    def test_sin_dato_aborta_sin_mover_la_hoja(self):
        with self.assertRaises(cp.pf.Halt):
            self._pasos(0)


class TestPegarSeguro(unittest.IsolatedAsyncioTestCase):
    async def test_cero_lineas_no_pega_ni_mueve_el_cursor(self):
        s = _S()
        pegar = AsyncMock()
        posicionar = AsyncMock()
        with patch.object(cp, "_pegar", pegar), \
                patch.object(cp, "_posicionar", posicionar):
            with self.assertRaises(cp.pf.Halt):
                await cp._pegar_y_posicionar(s, 1, 0)
        pegar.assert_not_awaited()
        posicionar.assert_not_awaited()

    async def test_portapapeles_vacio_abortaria_sin_pegar(self):
        # Este es el camino de produccion: Ctrl+C devuelve cero porque no se
        # pudo leer el clipboard; Ctrl+Shift+V no debe reutilizar datos viejos.
        s = _S()
        with patch.object(cp, "_copiar", AsyncMock(return_value=0)), \
                patch.object(cp, "_pegar") as pegar:
            filas = await cp._copiar(s)
            with self.assertRaises(cp.pf.Halt):
                await cp._pegar_y_posicionar(s, 1, filas)
        pegar.assert_not_awaited()

    async def test_filas_validas_pega_y_posiciona(self):
        s = _S()
        pegar = AsyncMock()
        posicionar = AsyncMock()
        with patch.object(cp, "_pegar", pegar), \
                patch.object(cp, "_posicionar", posicionar):
            await cp._pegar_y_posicionar(s, 1, 7)
        pegar.assert_awaited_once_with(s, 1)
        posicionar.assert_awaited_once_with(s, 1, 7)


class TestCopiar(unittest.TestCase):
    def test_cuenta_lineas_si_clipboard_se_actualiza(self):
        s = _S()
        orden = []

        async def fake_step(sess, label, name, args=None):
            orden.append(label)
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._secuencia_portapapeles.side_effect = [10, 11]
            rec._portapapeles.return_value = "linea 1\n\nlinea 2\r\nlinea 3\n"
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 3)
        self.assertEqual(orden, ["ctrl_c"])

    def test_clipboard_que_no_cambia_se_rechaza(self):
        s = _S()
        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._secuencia_portapapeles.side_effect = [10] * 6
            rec._portapapeles.return_value = "bloque viejo no vacio"
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 0)
        self.assertEqual([x[0] for x in s.steps], ["ctrl_c"])

    def test_clipboard_igual_al_anterior_pero_con_nueva_secuencia_es_valido(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._secuencia_portapapeles.side_effect = [10, 11, 11]
            rec._portapapeles.return_value = "mismo contenido"
            n = asyncio.run(cp._copiar(s, intentos=1, espera=0))
        self.assertEqual(n, 1)

    def test_una_sola_linea(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp, "recepcion") as rec:
            rec._secuencia_portapapeles.side_effect = [10, 11]
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
            rec._secuencia_portapapeles.side_effect = [10, 11]
            rec._portapapeles.side_effect = RuntimeError("sin portapapeles")
            n = asyncio.run(cp._copiar(s))
        self.assertEqual(n, 0)

    def test_espera_actualizacion_tardia_del_clipboard(self):
        s = _S()

        async def fake_step(sess, label, name, args=None):
            sess.steps.append((label, name, args))
            return {"status": "ok"}

        with patch.object(cp.pf, "step", fake_step), \
                patch.object(cp.asyncio, "sleep", new=asyncio.sleep), \
                patch.object(cp, "recepcion") as rec:
            rec._secuencia_portapapeles.side_effect = [10, 10, 10, 11]
            rec._portapapeles.return_value = "bloque actualizado"
            n = asyncio.run(cp._copiar(s, intentos=4, espera=0))
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
