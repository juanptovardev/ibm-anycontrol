"""Guardas de integridad de los modulos de tools/.

Dos cosas que la suite no cubria y por eso un bug llego a produccion:

1) `verifica_texto` se movio a `matriz_buscar` y alli quedaron sin definir la
   constante `VERBOSE` y el import de `ocr_text`. Todos los tests la
   PARCHEABAN, asi que nadie ejecutaba el codigo real: el fallo solo apareció
   en vivo (NameError antes del F10).

2) Un chequeo estatico de nombres libres por modulo: si al mover codigo se
   deja una constante o un import en el modulo viejo, salta aqui y no en la
   hoja del operador.
"""

import ast
import asyncio
import builtins
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

import matriz_buscar  # noqa: E402

MODULOS = ["matriz_buscar.py", "matriz_ficha.py", "matriz_extraer.py",
           "orquesta.py", "loop.py", "cp.py", "ciclo.py", "pagina.py",
           "ventana.py", "hoja.py", "supervisor.py", "autonomo.py",
           "estado.py", "perfil.py", "click_sel.py", "traza.py"]

DUNDERS = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
           "__loader__", "__builtins__", "__debug__"}


def nombres_libres_sin_definir(ruta: Path) -> set[str]:
    """Nombres que el modulo usa pero no define ni importa."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
    definidos = set(dir(builtins)) | DUNDERS
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definidos.add(nodo.name)
        elif isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store):
            definidos.add(nodo.id)
        elif isinstance(nodo, ast.arg):
            definidos.add(nodo.arg)
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            for a in nodo.names:
                definidos.add(a.asname or a.name.split(".")[0])
        elif isinstance(nodo, ast.ExceptHandler) and nodo.name:
            definidos.add(nodo.name)
        elif isinstance(nodo, ast.Global):
            definidos.update(nodo.names)
    faltan = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load):
            if nodo.id not in definidos:
                faltan.add(nodo.id)
    return faltan


class TestNombresLibres(unittest.TestCase):
    """Cada modulo debe tener definidos los nombres que usa."""

    def test_ningun_modulo_usa_nombres_sin_definir(self):
        rotos = {}
        for nombre in MODULOS:
            ruta = TOOLS / nombre
            if not ruta.exists():
                continue
            faltan = nombres_libres_sin_definir(ruta)
            if faltan:
                rotos[nombre] = sorted(faltan)
        self.assertEqual(rotos, {},
                         f"nombres usados y no definidos: {rotos}")

    def test_matriz_buscar_tiene_verbose_y_ocr_text(self):
        # los dos que se quedaron atras al mover verifica_texto
        self.assertTrue(hasattr(matriz_buscar, "VERBOSE"))
        self.assertTrue(callable(getattr(matriz_buscar, "ocr_text", None)))


class TestVerificaTextoReal(unittest.TestCase):
    """Ejecuta verifica_texto de verdad (no parcheada)."""

    def _det(self):
        return [{"field_x": 531, "cy": 100}, {"field_x": 531, "cy": 120},
                {"field_x": 531, "cy": 140}]

    def test_calle_con_tinta_devuelve_true(self):
        with patch.object(matriz_buscar.rowdet, "detect",
                          return_value=("IMG", None, self._det())), \
             patch.object(matriz_buscar.pf, "ink", return_value=200):
            ok, detalle = asyncio.run(matriz_buscar.verifica_texto(1))
        self.assertTrue(ok)
        self.assertIn("Calle ok", detalle)

    def test_calle_vacio_devuelve_false(self):
        with patch.object(matriz_buscar.rowdet, "detect",
                          return_value=("IMG", None, self._det())), \
             patch.object(matriz_buscar.pf, "ink", return_value=0), \
             patch.object(matriz_buscar, "ocr_text", return_value="FORMULARIO"):
            ok, detalle = asyncio.run(matriz_buscar.verifica_texto(1))
        self.assertFalse(ok)
        self.assertIn("Calle vacio", detalle)

    def test_sin_filas_devuelve_false(self):
        with patch.object(matriz_buscar.rowdet, "detect",
                          return_value=("IMG", None, self._det()[:2])):
            ok, detalle = asyncio.run(matriz_buscar.verifica_texto(1))
        self.assertFalse(ok)
        self.assertIn("no se detectaron filas", detalle)

    def test_verbose_imprime_el_formulario(self):
        original = matriz_buscar.VERBOSE
        matriz_buscar.VERBOSE = True
        try:
            with patch.object(matriz_buscar.rowdet, "detect",
                              return_value=("IMG", None, self._det())), \
                 patch.object(matriz_buscar.pf, "ink", return_value=200), \
                 patch.object(matriz_buscar, "ocr_text",
                              return_value="FORMULARIO") as ocr:
                ok, _ = asyncio.run(matriz_buscar.verifica_texto(1))
            self.assertTrue(ok)
            self.assertTrue(ocr.called)
        finally:
            matriz_buscar.VERBOSE = original


if __name__ == "__main__":
    unittest.main()
