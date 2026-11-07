"""Los 4 perfiles de velocidad que definio el operador (03/11/2026).

El techo se define en segundos por direccion, no en "rapido" o "lento": el
operador trabaja a 18,3 s por direccion (4.500 leads en 6 h) y los perfiles son
multiplicadores de ese ritmo.
"""
import os
import sys
import time
import unittest
import unittest.mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import perfil  # noqa: E402


class TestNombres(unittest.TestCase):
    def test_los_cuatro_perfiles_existen(self):
        self.assertEqual(sorted(perfil.PERFILES),
                         ["humano", "psicopata", "rapido", "sigiloso"])

    def test_techos_definidos_por_el_operador(self):
        self.assertEqual(perfil.PERFILES["sigiloso"]["s_dir"], 27.5)
        self.assertEqual(perfil.PERFILES["humano"]["s_dir"], 18.3)
        self.assertEqual(perfil.PERFILES["rapido"]["s_dir"], 12.2)
        self.assertEqual(perfil.PERFILES["psicopata"]["s_dir"], 9.15)

    def test_un_perfil_inexistente_cae_al_por_defecto(self):
        self.assertEqual(perfil.nombre("turbo"), perfil.DEFAULT)
        self.assertEqual(perfil.nombre(""), perfil.DEFAULT)
        self.assertEqual(perfil.nombre(None), perfil.DEFAULT)

    def test_el_nombre_se_toma_del_entorno(self):
        os.environ[perfil.ENV] = "rapido"
        try:
            self.assertEqual(perfil.nombre(), "rapido")
        finally:
            os.environ.pop(perfil.ENV, None)

    def test_el_argumento_manda_sobre_el_entorno(self):
        os.environ[perfil.ENV] = "rapido"
        try:
            self.assertEqual(perfil.nombre("sigiloso"), "sigiloso")
        finally:
            os.environ.pop(perfil.ENV, None)

    def test_actual_devuelve_el_perfil_con_su_nombre(self):
        p = perfil.actual("humano")
        self.assertEqual(p["nombre"], "humano")
        self.assertEqual(p["s_dir"], 18.3)
        self.assertIn("jitter", p)


class TestValores(unittest.TestCase):
    def test_objetivo_y_delay(self):
        self.assertEqual(perfil.objetivo_s("sigiloso"), 27.5)
        # El retardo de tecla NO va atado al perfil (ver perfil.TECLAS): si
        # lo estuviera, el perfil sigiloso no podria cumplir su techo.
        self.assertEqual(perfil.key_delay_ms(), 35)

    def test_mas_lento_mas_jitter(self):
        # El perfil sigiloso es el que mas variacion lleva (ritmo humano).
        self.assertGreater(perfil.jitter("sigiloso"), perfil.jitter("rapido"))
        self.assertGreater(perfil.jitter("rapido"), perfil.jitter("psicopata"))

    def test_el_reparto_de_pausas_suma_uno(self):
        self.assertAlmostEqual(sum(perfil.PUNTOS.values()), 1.0, places=6)

    def test_resumen_nombra_el_perfil(self):
        self.assertIn("perfil=humano", perfil.resumen("humano"))


class TestTeclas(unittest.TestCase):
    """La cadencia de teclas es un knob global, no parte del perfil."""

    def test_el_delay_no_depende_del_perfil(self):
        self.assertEqual(perfil.key_delay_ms("sigiloso"),
                         perfil.key_delay_ms("psicopata"))

    def test_el_modo_humano_sube_el_delay(self):
        perfil.ACTIVO_TECLAS = "humano"
        try:
            self.assertEqual(perfil.key_delay_ms(), 110)
        finally:
            perfil.ACTIVO_TECLAS = None

    def test_un_modo_desconocido_cae_en_rapido(self):
        perfil.ACTIVO_TECLAS = "turbo"
        try:
            self.assertEqual(perfil.teclas_nombre(), "rapido")
        finally:
            perfil.ACTIVO_TECLAS = None

    def test_el_entorno_elige_el_modo_de_teclas(self):
        os.environ[perfil.ENV_TECLAS] = "humano"
        try:
            self.assertEqual(perfil.teclas_nombre(), "humano")
        finally:
            os.environ.pop(perfil.ENV_TECLAS, None)

    def test_el_argumento_manda_sobre_el_entorno_en_las_teclas(self):
        os.environ[perfil.ENV_TECLAS] = "humano"
        try:
            self.assertEqual(perfil.teclas_nombre("rapido"), "rapido")
        finally:
            os.environ.pop(perfil.ENV_TECLAS, None)


class TestDeficit(unittest.TestCase):
    def test_deficit_es_el_techo_menos_lo_que_lleva(self):
        t0 = time.time() - 10.0
        self.assertAlmostEqual(perfil.deficit(t0, 27.5), 17.5, delta=0.5)

    def test_deficit_nevera_es_cero(self):
        t0 = time.time() - 100.0
        self.assertEqual(perfil.deficit(t0, 18.3), 0.0)

    def test_pausa_cero_si_no_hay_deficit(self):
        t0 = time.time() - 100.0
        self.assertEqual(perfil.pausa(t0, "antes_f10", 18.3), 0.0)

    def test_pausa_positiva_y_acotada(self):
        t0 = time.time()
        seg = perfil.pausa(t0, "antes_f10", 27.5)
        self.assertGreater(seg, 0.0)
        self.assertLessEqual(seg, perfil.MAX_PAUSA)

    def test_pausa_de_un_punto_desconocido_es_cero(self):
        self.assertEqual(perfil.pausa(time.time(), "inventado", 27.5), 0.0)

    def test_la_pausa_crece_con_el_deficit(self):
        t0 = time.time()
        # Sin jitter para comparar el efecto del deficit y no del azar.
        # El deficit util es el techo menos lo que la direccion tardara de
        # verdad (23 s estimadas), asi que los techos tienen que estar por
        # encima de esa estimacion.
        with unittest.mock.patch.object(perfil, "jitter",
                                       lambda valor=None: 0.0):
            poca = perfil.pausa(t0, "cierre", 30.0)
            mucha = perfil.pausa(t0, "cierre", 40.0)
        self.assertGreater(mucha, poca)

    def test_si_el_motor_es_mas_lento_que_el_techo_no_se_pausa(self):
        # Perfil humano (18,3 s) con un motor de ~23 s: no hay nada que
        # rellenar y pausar en balde solo haria la direccion mas lenta.
        t0 = time.time()
        self.assertEqual(perfil.pausa(t0, "antes_f10", 18.3, paginas=1), 0.0)

    def test_el_reparto_entre_los_cuatro_puntos_cubre_el_deficit(self):
        t0 = time.time()
        with unittest.mock.patch.object(perfil, "jitter",
                                       lambda valor=None: 0.0):
            total = sum(perfil.pausa(t0, p, 30.0, paginas=1)
                        for p in perfil.PUNTOS)
        # Techo 30 - estimacion 23 = 7 s de relleno repartidos.
        self.assertAlmostEqual(total, 7.0, delta=0.01)


class TestIntegracionConElMotor(unittest.TestCase):
    """El perfil no es solo un dato: gobierna el ritmo real de las teclas."""

    def _step(self, name, args):
        """Ejecuta preflight_auto.step con la red y el foco simulados."""
        import asyncio
        import preflight_auto as pf

        enviados = {}

        async def call(s, tool, a):
            enviados["tool"] = tool
            enviados["args"] = a
            return {"isError": False, "text": "ok"}

        with unittest.mock.patch.object(pf, "call", call), \
                unittest.mock.patch.object(pf.enfocar, "asegura",
                                           lambda: True):
            asyncio.run(pf.step(None, "x", name, args))
        return enviados["args"]

    def test_press_keys_recibe_el_delay_global(self):
        perfil.ACTIVO_TECLAS = "humano"
        try:
            args = self._step("press_keys", {"keys": ["down"]})
        finally:
            perfil.ACTIVO_TECLAS = None
        self.assertEqual(args["key_delay_ms"], 110)

    def test_un_delay_propio_no_se_pisa(self):
        perfil.ACTIVO = "rapido"
        try:
            args = self._step("press_keys", {"keys": ["down"],
                                             "key_delay_ms": 33})
        finally:
            perfil.ACTIVO = None
        self.assertEqual(args["key_delay_ms"], 33)

    def test_otra_herramienta_no_toca_teclas(self):
        args = self._step("write_to_anydesk", {"command": "CR 18"})
        self.assertNotIn("key_delay_ms", args)
        self.assertEqual(args["command"], "CR 18")

    def test_la_pausa_del_motor_duerme_lo_que_dice(self):
        import asyncio
        import loop

        dormido = []

        async def fake_sleep(seg):
            dormido.append(seg)

        with unittest.mock.patch.object(loop.asyncio, "sleep", fake_sleep):
            asyncio.run(loop._pausa(2.5))
            asyncio.run(loop._pausa(0))
        self.assertEqual(dormido, [2.5])


if __name__ == "__main__":
    unittest.main()
