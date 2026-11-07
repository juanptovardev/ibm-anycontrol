"""El supervisor debe pasar IDs a la vuelta, no filas del CSV.

Bug real (03/11): `pendientes()` devuelve FILAS (con id) y el filtro del
supervisor comparaba la fila entera contra un set de ids ->
`TypeError: cannot use 'dict' as a set element (unhashable type: 'dict')`.
El supervisor moria antes de lanzar la primera vuelta y solo dejaba el
informe final. Ningun test lo cazaba porque T7 nunca se ejecuto en vivo.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import supervisor as sup  # noqa: E402


class TestPendientes(unittest.TestCase):
    """El contrato: `pendientes` devuelve FILAS con id, ya filtradas."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "direcciones.csv"
        self.ruta.write_text(
            "parte1;parte2;ficha\r\nCR 1;1-1;\r\nCR 2;2-2;\r\nCR 3;3-3;\r\n",
            encoding="utf-8")

    def test_devuelve_filas_con_id_y_solo_las_no_terminales(self):
        est = {"D01": {"estado": "error"},
               "D02": {"estado": "ok"},
               "D03": {"estado": "no_encontrado"}}
        filas = sup.pendientes(est, self.ruta)
        self.assertEqual([f["id"] for f in filas], ["D01"])

    def test_una_direccion_sin_registro_esta_pendiente(self):
        filas = sup.pendientes({}, self.ruta)
        self.assertEqual([f["id"] for f in filas], ["D01", "D02", "D03"])


class TestCorrePasaIds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.datos = Path(self.tmp.name)
        self.direcciones = self.datos / "direcciones.csv"
        self.direcciones.write_text(
            "parte1;parte2;ficha\r\nCR 1;1-1;\r\nCR 2;2-2;\r\n", encoding="utf-8")

    def _corre(self, filas, ids=None):
        recibidos = []

        def fake_lanza(vuelta, dry, ids_csv, perf, teclas):
            recibidos.append(ids_csv)
            return None, SimpleNamespace(name="supervisor-vuelta-X.log")

        with patch.object(sup, "DATOS", self.datos), \
             patch.object(sup, "DIRECCIONES", self.direcciones), \
             patch.object(sup, "LOCK", self.datos / "supervisor.lock"), \
             patch.object(sup, "estados", lambda *a, **k: {}), \
             patch.object(sup, "pendientes", lambda e, *a, **k: filas), \
             patch.object(sup, "control", lambda *a, **k: None), \
             patch.object(sup, "escribe_estado", lambda **k: None), \
             patch.object(sup, "lanza", fake_lanza), \
             patch.object(sup, "vigila", lambda *a, **k: (0, "termino")), \
             patch.object(sup, "excel_bloquea", lambda *a, **k: False), \
             patch.object(sup, "anydesk_vivo", lambda *a, **k: True), \
             patch.object(sup, "hay_credenciales", lambda *a, **k: True), \
             patch.object(sup, "resumen", lambda *a, **k: "resumen"):
            sup.corre(dry=False, ids=ids, max_vueltas=1, max_sin_avance=2,
                      horas=0.01, sin_progreso=1, tope_vuelta=1,
                      perf=None, teclas=None)
        return recibidos

    def test_lanza_recibe_los_ids_pendientes(self):
        recibidos = self._corre([{"id": "D01"}, {"id": "D02"}])
        self.assertEqual(recibidos, ["D01,D02"])

    def test_filtrar_por_ids_del_cli(self):
        recibidos = self._corre([{"id": "D01"}, {"id": "D02"}], ids="D02")
        self.assertEqual(recibidos, ["D02"])

    def test_una_fila_sin_id_se_ignora(self):
        recibidos = self._corre([{"parte1": "CR 1"}])
        self.assertEqual(recibidos, [])


if __name__ == "__main__":
    unittest.main()
