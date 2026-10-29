"""0.2: la macro de busqueda limpia el Nombre con la secuencia del operador.

Secuencia (28/10, indicada por el operador): clic en la celda 1 del campo
Nombre, flecha derecha, flecha izquierda, Suprimir y el '+' del bloque
numerico, que limpia el campo y salta al siguiente (Calle). Sustituye al
truco de sobrescribir con 24 espacios.
"""
import asyncio
import os
import sys
import unittest
from unittest.mock import patch

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import loop  # noqa: E402


def _det():
    return [
        {"field_x": 531, "cy": 136},   # 0 NOMBRE
        {"field_x": 531, "cy": 158},   # 1 CALLE
        {"field_x": 531, "cy": 179},   # 2 CASA
    ]


class TestSecuenciaDeBusqueda(unittest.TestCase):
    def _correr(self):
        llamadas = []

        async def step(s, label, name, args=None):
            llamadas.append((label, name, args or {}))

        async def sleep(_seg):
            return None

        with patch.object(loop.pf, "step", step), \
                patch.object(loop.asyncio, "sleep", sleep):
            asyncio.run(loop.buscar(object(), 1, _det(), "CR 17B", "175-77"))
        return llamadas

    def test_secuencia_de_limpieza_del_nombre(self):
        llamadas = self._correr()
        etiquetas = [c[0] for c in llamadas]
        self.assertEqual(etiquetas[:9], [
            "nombre_clic", "nombre_derecha", "nombre_izquierda",
            "nombre_suprimir", "nombre_mas", "calle_clic", "calle_derecha",
            "calle_izquierda", "calle_suprimir",
        ])
        por_etiqueta = {c[0]: c for c in llamadas}
        self.assertEqual(por_etiqueta["nombre_derecha"][2]["keys"], ["right"])
        self.assertEqual(por_etiqueta["nombre_izquierda"][2]["keys"], ["left"])
        self.assertEqual(por_etiqueta["nombre_suprimir"][2]["keys"], ["delete"])
        self.assertEqual(por_etiqueta["nombre_mas"][2]["keys"], ["add"])

    def test_el_clic_va_en_la_celda_1_del_campo(self):
        llamadas = self._correr()
        por_etiqueta = {c[0]: c for c in llamadas}
        # Celda 1 = borde izquierdo del subrayado (field_x + 2).
        self.assertEqual(por_etiqueta["nombre_clic"][2],
                         {"x": 531 + 2, "y": 136})
        self.assertEqual(por_etiqueta["calle_clic"][2],
                         {"x": 531 + 2, "y": 158})

    def test_no_escribe_espacios_para_limpiar(self):
        for label, name, args in self._correr():
            if name == "write_to_anydesk":
                self.assertNotEqual(args.get("command", "").strip(), "",
                                    f"{label} escribe solo espacios")

    def test_la_escritura_de_las_partes_no_cambia(self):
        llamadas = self._correr()
        writings = [(l, a.get("command")) for l, n, a in llamadas
                    if n == "write_to_anydesk"]
        self.assertEqual(writings, [
            ("step1", "CR 17B"), ("step2", "175-77"),
            ("bog", "BOG"), ("tvc", "TVC"),
        ])

    def test_el_mas_del_bloque_numerico_entre_partes(self):
        etiquetas = [c[0] for c in self._correr()]
        self.assertEqual(etiquetas[9:], [
            "step1", "plus1", "step2", "plus2", "bog", "plus3", "tvc",
        ])


if __name__ == "__main__":
    unittest.main()
