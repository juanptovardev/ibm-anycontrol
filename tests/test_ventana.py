"""ventana: cambio de ventana del escritorio remoto por icono de la taskbar.

El 03/11 el Alt+Tab dejo de cambiar de ventana: la tecla de sistema no llega
al escritorio remoto con el 5250 y Chrome ambos maximizados. La via que si
funciona (medida en vivo) es hacer clic en el icono de la taskbar, y el icono
se localiza por imagen para no depender de una coordenada fija.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import ventana  # noqa: E402


class TestPlantillas(unittest.TestCase):
    def test_las_dos_plantillas_existen_y_no_estan_vacias(self):
        for nombre in ventana.PLANTILLAS.values():
            ruta = ventana.ICONOS / f"{nombre}.png"
            self.assertTrue(ruta.exists(), f"falta la plantilla {ruta}")
            self.assertGreater(ruta.stat().st_size, 0)

    def test_los_dos_destinos_estan_mapeados(self):
        self.assertEqual(ventana.PLANTILLAS[ventana.DESTINO_NAVEGADOR], "chrome")
        self.assertEqual(ventana.PLANTILLAS[ventana.DESTINO_IBM], "emulador5250")


class TestBuscarIcono(unittest.TestCase):
    """El detector tiene que encontrar la plantilla pegada en la banda."""

    def _img_con_icono(self, nombre, x=652, y=674):
        tpl = Image.open(ventana.ICONOS / f"{nombre}.png").convert("RGB")
        img = Image.new("RGB", (1255, 703), (0, 0, 0))
        img.paste(tpl, (x, y))
        return img, x + tpl.width // 2, y + tpl.height // 2

    def test_encuentra_el_icono_pegado(self):
        img, cx, cy = self._img_con_icono("chrome")
        pos = ventana.buscar_icono(img, "chrome")
        self.assertIsNotNone(pos)
        self.assertLessEqual(abs(pos[0] - cx), 3)
        self.assertLessEqual(abs(pos[1] - cy), 3)

    def test_no_encuentra_icono_en_una_imagen_lisa(self):
        img = Image.new("RGB", (1255, 703), (128, 128, 128))
        self.assertIsNone(ventana.buscar_icono(img, "chrome"))

    def test_plantilla_inexistente_devuelve_none(self):
        img = Image.new("RGB", (1255, 703), (0, 0, 0))
        self.assertIsNone(ventana.buscar_icono(img, "no-existe"))

    def test_el_icono_no_se_busca_fuera_de_la_banda_inferior(self):
        # El icono pegado arriba del todo no debe aparecer: la busqueda es
        # solo en la banda de la taskbar.
        img, _, _ = self._img_con_icono("chrome", x=652, y=10)
        self.assertIsNone(ventana.buscar_icono(img, "chrome"))


class TestIrA(unittest.IsolatedAsyncioTestCase):
    async def test_si_ya_esta_en_el_destino_no_hace_nada(self):
        with patch.object(ventana, "captura",
                          return_value=(Image.new("RGB", (10, 10)), {})), \
             patch.object(ventana, "tipo_pixeles", return_value="ibm"), \
             patch.object(ventana, "buscar_icono", return_value=(10, 10)) as busca, \
             patch.object(ventana.pf, "step", new=AsyncMock()) as paso:
            ok = await ventana.ir_a(None, 1, ventana.DESTINO_IBM)
        self.assertTrue(ok)
        busca.assert_not_called()
        paso.assert_not_called()

    async def test_hace_clic_en_el_icono(self):
        with patch.object(ventana, "captura",
                          return_value=(Image.new("RGB", (10, 10)), {})), \
             patch.object(ventana, "tipo_pixeles",
                          side_effect=["navegador", "ibm"]), \
             patch.object(ventana, "buscar_icono", return_value=(662, 684)), \
             patch.object(ventana.pf, "step", new=AsyncMock()) as paso, \
             patch.object(ventana.asyncio, "sleep", new=AsyncMock()):
            ok = await ventana.ir_a(None, 1, ventana.DESTINO_IBM,
                                    intentos=2, espera=0.01)
        self.assertTrue(ok)
        clics = [c for c in paso.await_args_list if c.args[2] == "click_point"]
        self.assertEqual(len(clics), 1, paso.await_args_list)
        self.assertEqual(clics[0].args[3], {"x": 662, "y": 684})

    async def test_sin_icono_cae_al_alt_tab(self):
        with patch.object(ventana, "captura",
                          return_value=(Image.new("RGB", (10, 10)), {})), \
             patch.object(ventana, "tipo_pixeles",
                          side_effect=["ibm", "ibm", "ibm", "ibm"]), \
             patch.object(ventana, "buscar_icono", return_value=None), \
             patch.object(ventana.pf, "step", new=AsyncMock()) as paso, \
             patch.object(ventana.asyncio, "sleep", new=AsyncMock()):
            ok = await ventana.ir_a(None, 1, ventana.DESTINO_NAVEGADOR,
                                    intentos=2, espera=0.01)
        self.assertFalse(ok)
        etiquetas = [c.args[1] for c in paso.await_args_list]
        self.assertTrue(any(t.startswith("alt_tab") for t in etiquetas), etiquetas)
        self.assertFalse(any(t.startswith("clic_icono") for t in etiquetas),
                         etiquetas)

    async def test_destino_desconocido_devuelve_false(self):
        ok = await ventana.ir_a(None, 1, "nada")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
