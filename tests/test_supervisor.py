"""supervisor: lectura del ledger, pendientes y watchdog (sin tocar el remoto)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import supervisor as sup

CAB = ("id;direccion_parte1;direccion_parte2;comuna;cuenta_matriz_esperada;"
       "estado;paginas_vistas;filas_copiadas;hora_inicio;hora_fin;evidencia;"
       "notas;reintentos")


def _csv(ruta: Path, lineas: list) -> None:
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dir = Path(self.tmp) / "direcciones.csv"
        self.led = Path(self.tmp) / "ledger.csv"


class TestEstados(_Tmp):
    def test_estados_gana_la_ultima_fila(self):
        _csv(self.led, [CAB,
                        "D01;CR 18;113-47;BOG;;en_curso;2;30;;;;;0",
                        "D01;CR 18;113-47;BOG;;ok;2;30;;;;;0"])
        self.assertEqual(sup.estados(self.led)["D01"]["estado"], "ok")

    def test_ledger_ausente_no_revienta(self):
        self.assertEqual(sup.estados(self.led), {})

    def test_total_cuenta_direcciones(self):
        _csv(self.dir, ["parte1;parte2;ficha", "CR 18;113-47;", "CL 80;8-10;"])
        self.assertEqual(sup.total(self.dir), 2)

    def test_pendientes_excluye_ok_y_no_encontrado(self):
        _csv(self.dir, ["parte1;parte2;ficha",
                        "CR 18;113-47;", "CL 80;8-10;", "CR 20;118-93;"])
        _csv(self.led, [CAB,
                        "D01;CR 18;113-47;BOG;;ok;1;15;;;;;0",
                        "D02;CL 80;8-10;BOG;;no_encontrado;0;0;;;;;0"])
        faltan = sup.pendientes(sup.estados(self.led), self.dir)
        self.assertEqual([f["id"] for f in faltan], ["D03"])

    def test_un_error_sigue_pendiente(self):
        _csv(self.dir, ["parte1;parte2;ficha", "CR 18;113-47;"])
        _csv(self.led, [CAB, "D01;CR 18;113-47;BOG;;error;3;45;;;;;0"])
        self.assertEqual(len(sup.pendientes(sup.estados(self.led), self.dir)), 1)


class TestControl(_Tmp):
    def test_lee_la_accion(self):
        ctrl = Path(self.tmp) / "control.json"
        ctrl.write_text(json.dumps({"accion": "detener"}), encoding="utf-8")
        self.assertEqual(sup.control(ctrl), "detener")

    def test_json_roto_no_revienta(self):
        ctrl = Path(self.tmp) / "control.json"
        ctrl.write_text("no json", encoding="utf-8")
        self.assertIsNone(sup.control(ctrl))

    def test_sin_archivo_no_hay_accion(self):
        self.assertIsNone(sup.control(Path(self.tmp) / "nada.json"))


class TestResumen(_Tmp):
    def test_cuenta_por_estado_y_lista_las_rotas(self):
        _csv(self.dir, ["parte1;parte2;ficha",
                        "CR 18;113-47;", "CL 80;8-10;", "CR 20;118-93;"])
        est = {"D01": {"estado": "ok"}, "D02": {"estado": "error"}}
        txt = sup.resumen(est, 3, self.dir)
        self.assertIn("ok             : 1", txt)
        self.assertIn("error          : 1", txt)
        self.assertIn("pendiente      : 1", txt)
        self.assertIn("SIN TERMINAR   : 2", txt)
        self.assertIn("requieren atencion", txt)
        self.assertIn("D02", txt)


class TestEntorno(_Tmp):
    def test_excel_bloquea_detecta_permission_error(self):
        _csv(self.dir, ["parte1;parte2;ficha"])
        with patch("builtins.open", side_effect=PermissionError):
            self.assertTrue(sup.excel_bloquea(self.dir))

    def test_excel_bloquea_falso_si_se_puede_escribir(self):
        _csv(self.dir, ["parte1;parte2;ficha"])
        self.assertFalse(sup.excel_bloquea(self.dir))

    def test_sin_archivo_no_hay_bloqueo(self):
        self.assertFalse(sup.excel_bloquea(Path(self.tmp) / "nada.csv"))

    def test_corre_no_arranca_si_hay_lock(self):
        with patch.object(sup, "LOCK", Path(self.tmp) / "supervisor.lock"):
            sup.LOCK.write_text("x", encoding="utf-8")
            with patch.object(sup, "DATOS", Path(self.tmp)):
                self.assertEqual(sup.corre(), 2)

    def test_corre_no_arranca_sin_direcciones(self):
        vacio = Path(self.tmp) / "vacio.csv"
        _csv(vacio, ["parte1;parte2;ficha"])
        with patch.object(sup, "LOCK", Path(self.tmp) / "supervisor.lock"), \
                patch.object(sup, "DATOS", Path(self.tmp)), \
                patch.object(sup, "DIRECCIONES", vacio):
            self.assertEqual(sup.corre(), 2)


class _FakeProc:
    def __init__(self, codigos):
        self.codigos = list(codigos)
        self.pid = 999999
        self._log_fh = None

    def poll(self):
        return self.codigos.pop(0) if self.codigos else None


class TestVigila(unittest.TestCase):
    def test_termina_cuando_el_proceso_acaba(self):
        with patch.object(sup.time, "sleep"), \
                patch.object(sup, "_tam", return_value=10):
            codigo, motivo = sup.vigila(_FakeProc([None, 0]), Path("x.log"),
                                        sin_progreso=999, tope=999)
        self.assertEqual((codigo, motivo), (0, "termino"))

    def test_sin_progreso_mata_el_arbol(self):
        with patch.object(sup.time, "sleep"), \
                patch.object(sup, "_tam", return_value=10), \
                patch.object(sup, "_mata") as mata:
            codigo, motivo = sup.vigila(_FakeProc([None] * 20), Path("x.log"),
                                        sin_progreso=-1, tope=999)
        self.assertIsNone(codigo)
        self.assertIn("sin escribir", motivo)
        self.assertTrue(mata.called)

    def test_tope_de_vuelta(self):
        with patch.object(sup.time, "sleep"), \
                patch.object(sup, "_tam", return_value=10), \
                patch.object(sup, "_mata") as mata:
            codigo, motivo = sup.vigila(_FakeProc([None] * 20), Path("x.log"),
                                        sin_progreso=999, tope=-1)
        self.assertIsNone(codigo)
        self.assertIn("paso de", motivo)
        self.assertTrue(mata.called)


if __name__ == "__main__":
    unittest.main()
