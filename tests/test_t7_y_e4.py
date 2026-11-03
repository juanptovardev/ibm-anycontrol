"""T7 (tope de reintentos por direccion) y E4 (fuera el sel_box del camino caliente).

T7: una direccion que falla y vuelve a fallar se congela al tercer fallo, para
que el supervisor no gaste el lote con un caso que no se resuelve solo.

E4: `ciclo.extrae` ya no mide el marco amarillo (`cp.sel_box`, 178 ms) ni hace
la captura "ciclo-sel": medido que el detector da falsos negativos con el clic
x=917, asi que era un dato poco fiable en el camino caliente.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import supervisor as sup  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestNuevosCongelados(unittest.TestCase):
    def test_un_error_empieza_a_contar(self):
        fallos = {}
        nuevos = sup.nuevos_congelados({"D01": {"estado": "error"}}, fallos)
        self.assertEqual(nuevos, [])
        self.assertEqual(fallos["D01"], 1)

    def test_al_tercer_fallo_se_congela(self):
        fallos = {"D01": 2}
        nuevos = sup.nuevos_congelados({"D01": {"estado": "error"}}, fallos)
        self.assertEqual(nuevos, ["D01"])
        self.assertEqual(fallos["D01"], 3)

    def test_los_estados_buenos_no_cuentan(self):
        fallos = {}
        est = {"D01": {"estado": "ok"}, "D02": {"estado": "no_encontrado"},
               "D03": {"estado": "en_curso"}}
        self.assertEqual(sup.nuevos_congelados(est, fallos), [])
        self.assertEqual(fallos, {})

    def test_ledger_vacio_o_none(self):
        self.assertEqual(sup.nuevos_congelados({}, {}), [])
        self.assertEqual(sup.nuevos_congelados(None, {}), [])

    def test_tope_configurable(self):
        fallos = {}
        est = {"D01": {"estado": "error"}}
        self.assertEqual(sup.nuevos_congelados(est, fallos, max_fallos=1), ["D01"])


class TestE4SinSelBox(unittest.TestCase):
    """El detector del marco amarillo no vuelve al camino caliente."""

    def _ciclo(self):
        return (RAIZ / "tools" / "ciclo.py").read_text(encoding="utf-8")

    def test_ciclo_no_llama_a_sel_box(self):
        # Se busca la LLAMADA, no la palabra: el codigo puede (y debe) seguir
        # hablando del detector en los comentarios.
        self.assertNotIn("cp.sel_box(", self._ciclo())

    def test_ciclo_no_hace_la_captura_ciclo_sel(self):
        self.assertNotIn('"ciclo-sel"', self._ciclo())

    def test_ciclo_sigue_pasting_y_desplazando(self):
        txt = self._ciclo()
        self.assertIn("cp._copiar(s)", txt)
        self.assertIn("cp._pegar(s, hwnd)", txt)
        self.assertIn("cp._posicionar(s, hwnd, filas)", txt)


if __name__ == "__main__":
    unittest.main()
