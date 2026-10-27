"""click_sel: eleccion de la celda objetivo (sin OCR ni input real)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import click_sel  # noqa: E402

CAB = ("Suscript", 800, 100, 70, 14)


def _fila(y, codigo=None):
    words = [("CL", 244, y, 20, 12), ("175", 270, y, 30, 12),
             ("BLACACIAS", 305, y, 90, 12), ("ADMIN", 420, y, 60, 12)]
    if codigo:
        words.append((codigo, 860, y, 60, 12))
        words.append(("S", 930, y, 10, 12))
    return words


class TestTargetCelda(unittest.TestCase):
    def test_sin_cabecera_no_adivina(self):
        self.assertIsNone(click_sel.target_celda(_fila(120, "50867551")))

    def test_cabecera_sin_datos(self):
        self.assertIsNone(click_sel.target_celda([CAB]))

    def test_apunta_al_borde_derecho_del_suscriptor(self):
        words = [CAB] + _fila(120, "50867551") + _fila(140, "25420919")
        t = click_sel.target_celda(words)
        self.assertEqual(t["col_right"], 920)
        self.assertEqual(t["x"], 916)

    def test_fila_objetivo_es_la_mas_baja(self):
        words = [CAB] + _fila(120, "50867551") + _fila(160)
        t = click_sel.target_celda(words)
        self.assertEqual(t["y"], 166)

    def test_codigos_a_la_izquierda_se_ignoran(self):
        words = [CAB, ("12345678", 100, 130, 60, 12), ("1234", 250, 140, 30, 12)]
        t = click_sel.target_celda(words)
        self.assertEqual(t["col_right"], 870)  # x0+ancho de la cabecera (800+70)

    def test_prioriza_digitos_sobre_cabecera(self):
        words = [CAB] + _fila(120, "50867551")
        t = click_sel.target_celda(words)
        self.assertGreater(t["col_right"], 800 + 70)


if __name__ == "__main__":
    unittest.main()
