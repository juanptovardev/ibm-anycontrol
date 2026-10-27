"""Tests de la traza y del semaforo (contrato de etapas y resultados)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import traza  # noqa: E402


class TestPolicia(unittest.TestCase):
    def test_camino_feliz(self):
        self.assertEqual(traza.accion("entorno", "ok"), "pin")
        self.assertEqual(traza.accion("pin", "ok"), "estado")
        self.assertEqual(traza.accion("estado", "formulario"), "buscar")
        self.assertEqual(traza.accion("buscar", "ok"), "extraer")
        self.assertEqual(traza.accion("extraer", "ok"), "volver")
        self.assertEqual(traza.accion("volver", "ok"), "pagina")

    def test_fin_de_libro_cierra(self):
        self.assertEqual(traza.accion("estado", "fin_libro"), "cierre")
        self.assertEqual(traza.accion("pagina", "fin_libro"), "cierre")
        self.assertEqual(traza.accion("cierre", "ok"), "siguiente")

    def test_pagina_llena_sigue_extrayendo(self):
        self.assertEqual(traza.accion("pagina", "cuenta_matriz"), "extraer")

    def test_sin_coincidencia_pasa_al_siguiente(self):
        self.assertEqual(traza.accion("buscar", "sin_coincidencia"), "siguiente")

    def test_fallos_detienen(self):
        for etapa, resultado in [("estado", "error"), ("estado", "desconocido"),
                                 ("buscar", "fallo"), ("extraer", "fallo"),
                                 ("volver", "fallo"), ("pin", "fallo"),
                                 ("entorno", "fallo")]:
            self.assertEqual(traza.accion(etapa, resultado), "detener",
                             f"{etapa}/{resultado} deberia detener")

    def test_desconocido_detiene(self):
        self.assertEqual(traza.accion("etapa_inventada", "ok"), "detener")
        self.assertEqual(traza.accion("estado", "inventado"), "detener")


class TestTraza(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        self.t = traza.Traza(jsonl=raiz / "traza.jsonl", md=raiz / "traza.md",
                             run="test-run")

    def tearDown(self):
        self.tmp.cleanup()

    def test_evento_escribe_jsonl_y_md(self):
        self.t.evento("estado", "formulario", detalle="conf 0.90")
        lineas = self.t.jsonl.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lineas), 1)
        ev = json.loads(lineas[0])
        self.assertEqual(ev["etapa"], "estado")
        self.assertEqual(ev["resultado"], "formulario")
        self.assertEqual(ev["accion"], "buscar")
        self.assertEqual(ev["run"], "test-run")
        md = self.t.md.read_text(encoding="utf-8")
        self.assertIn("| estado | formulario | buscar | conf 0.90 |", md)

    def test_punto_es_el_ultimo_evento(self):
        self.t.evento("estado", "formulario")
        self.t.evento("buscar", "ok", detalle="CR 17B")
        self.assertEqual(self.t.punto["etapa"], "buscar")
        self.assertEqual(self.t.punto["accion"], "extraer")

    def test_rechaza_resultado_invalido(self):
        with self.assertRaises(ValueError):
            self.t.evento("estado", "volando")
        with self.assertRaises(ValueError):
            self.t.evento("etapa_falsa", "ok")

    def test_resumen_dice_el_punto_actual(self):
        self.t.evento("estado", "cuenta_matriz", detalle="conf 0.95")
        self.t.evento("extraer", "ok", detalle="bloque 1")
        texto = self.t.resumen()
        self.assertIn("estado=cuenta_matriz -> extraer", texto)
        self.assertIn("extraer=ok -> volver", texto)
        self.assertIn("PUNTO ACTUAL: etapa extraer", texto)

    def test_resumen_sin_eventos(self):
        self.assertEqual(self.t.resumen(), "sin eventos de traza")

    def test_linea_cortada_no_rompe_la_lectura(self):
        self.t.evento("estado", "formulario")
        with open(self.t.jsonl, "a", encoding="utf-8") as fh:
            fh.write('{"etapa": "busc')
        self.assertEqual(len(self.t.leer()), 1)

    def test_leer_devuelve_los_ultimos_n(self):
        for etapa, resultado in [("entorno", "ok"), ("pin", "ok"),
                                 ("estado", "formulario")]:
            self.t.evento(etapa, resultado)
        ultimos = self.t.leer(2)
        self.assertEqual([e["etapa"] for e in ultimos], ["pin", "estado"])


if __name__ == "__main__":
    unittest.main()
