"""Supervisor autonomo: relanza la corrida hasta que no queden pendientes.

El agente (tools/autonomo.py) es autonomo POR DIRECCION: reconecta AnyDesk,
hace login en el 5250 si hace falta, busca, extrae, pega, reanuda en la pagina
donde se quedo y sigue con la siguiente. Lo que no tenia era quien lo
relanzara cuando el lote se corta, el proceso muere o la sesion se cae. Eso es
este script: vueltas seguidas hasta que no quede nada que hacer.

    python tools/supervisor.py                     # las pendientes del CSV
    python tools/supervisor.py --horas=6           # tope de duracion
    python tools/supervisor.py --sin-progreso=300  # watchdog mas paciente
    python tools/supervisor.py --max-vueltas=10
    python tools/supervisor.py --dry               # solo mide, no pega

Se para cuando:

  - no quedan direcciones pendientes              -> termina OK
  - N vueltas seguidas sin avanzar (atascado)     -> STOP con informe
  - se agota --horas o --max-vueltas              -> STOP con informe
  - datos/control.json trae {"accion": "detener"} -> STOP del operador
  - una vuelta lleva --sin-progreso segundos sin escribir en su log
    -> se mata el arbol de procesos y se relanza

Deja datos/supervisor.json con el estado vivo (se puede mirar sin abrir el
log) y datos/supervisor-vuelta-N.log con el detalle de cada vuelta.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
DIRECCIONES = DATOS / "direcciones.csv"
LEDGER = DATOS / "ledger.csv"
CTRL = DATOS / "control.json"
ESTADO = DATOS / "supervisor.json"
LOCK = DATOS / "supervisor.lock"

# Estados que ya no se vuelven a tocar: 'ok' esta hecho y 'no_encontrado' es
# definitivo (el 5250 contesta 'La direccion no esta en el archivo').
TERMINALES = ("ok", "no_encontrado")


# ------------------------------------------------------------ lectura de datos
def _filas(ruta: Path) -> list[dict]:
    """Lee un CSV del repo (utf-8-sig, separador ';'). Vacio si no existe."""
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def estados(ruta: Path | None = None) -> dict:
    """id -> ultima fila del ledger (el ledger es UPSERT, una por direccion)."""
    ruta = LEDGER if ruta is None else ruta
    salida = {}
    for f in _filas(ruta):
        id_ = (f.get("id") or "").strip()
        if id_:
            salida[id_] = f
    return salida


def _con_id(filas: list) -> list[dict]:
    """Anade el id derivado por posicion (D01..D0n) si la fila no lo trae.

    direcciones.csv solo tiene parte1;parte2;ficha: el id es posicional y asi
    lo deriva tambien loop.lee_direcciones. Sin esto, pendientes y resumen
    revientan con KeyError en el CSV real del operador.
    """
    salida = []
    for i, f in enumerate(filas, 1):
        if not (f.get("id") or "").strip():
            f = dict(f)
            f["id"] = f"D{i:02d}"
        salida.append(f)
    return salida


def total(ruta: Path | None = None) -> int:
    ruta = DIRECCIONES if ruta is None else ruta
    return len(_filas(ruta))


def pendientes(est: dict, ruta: Path | None = None) -> list[dict]:
    """Direcciones del CSV que aun no estan en estado terminal."""
    ruta = DIRECCIONES if ruta is None else ruta
    return [f for f in _con_id(_filas(ruta))
            if (est.get((f.get("id") or "").strip()) or {}).get("estado")
            not in TERMINALES]


def control(ruta: Path | None = None) -> str | None:
    """Accion pedida desde el panel (PAUSAR / REANUDAR / DETENER)."""
    ruta = CTRL if ruta is None else ruta
    try:
        return (json.loads(ruta.read_text(encoding="utf-8")) or {}).get("accion")
    except (OSError, ValueError):
        return None


def resumen(est: dict, cuantas: int, ruta: Path | None = None) -> str:
    """Tabla de conteo por estado + lista de las que hay que mirar a mano."""
    ruta = DIRECCIONES if ruta is None else ruta
    cuenta = {}
    for f in _con_id(_filas(ruta)):
        e = (est.get((f.get("id") or "").strip()) or {}).get("estado") or "pendiente"
        cuenta[e] = cuenta.get(e, 0) + 1
    faltan = cuantas - sum(v for k, v in cuenta.items() if k in TERMINALES)
    lineas = [f"direcciones en el CSV: {cuantas}",
              f"  ok             : {cuenta.get('ok', 0)}",
              f"  no_encontrado  : {cuenta.get('no_encontrado', 0)}",
              f"  error          : {cuenta.get('error', 0)}",
              f"  en_curso       : {cuenta.get('en_curso', 0)}",
              f"  pendiente      : {cuenta.get('pendiente', 0)}",
              f"  SIN TERMINAR   : {faltan}"]
    rotas = [i for i, f in est.items() if (f.get("estado") == "error")]
    if rotas:
        lineas.append("requieren atencion (estado error): " + ", ".join(sorted(rotas)))
    return "\n".join(lineas)


# ------------------------------------------------------------ entorno
def excel_bloquea(ruta: Path | None = None) -> bool:
    """True si el CSV no se puede escribir (tipicamente abierto en Excel).

    No es fatal: el agente manda las fichas a datos/fichas_pendientes.csv y las
    recupera al arrancar. Pero sin Excel abierto el CSV queda completo al
    terminar, asi que conviene avisar.
    """
    ruta = DIRECCIONES if ruta is None else ruta
    if not ruta.exists():
        return False
    try:
        with open(ruta, "a", encoding="utf-8"):
            return False
    except PermissionError:
        return True


def anydesk_vivo() -> bool | None:
    """True/False si se puede mirar; None si no hay pywin32 para saberlo."""
    try:
        import win32gui
    except ImportError:
        return None

    encontrado = []

    def _cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetClassName(hwnd).startswith("ad_win"):
                encontrado.append(hwnd)
        except Exception:  # noqa: BLE001 - ventana cerrada a mitad
            pass
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:  # noqa: BLE001
        return None
    return bool(encontrado)


def hay_credenciales() -> bool:
    """Sin credenciales el re-login tras un corte de licencia no funciona."""
    try:
        import credenciales
        return bool(credenciales.carga())
    except Exception:  # noqa: BLE001 - si falta el modulo se avisa y se sigue
        return False


# ------------------------------------------------------------ lanzar y vigilar
def _tam(ruta: Path) -> int:
    try:
        return ruta.stat().st_size
    except OSError:
        return -1


def _mata(proc: subprocess.Popen) -> None:
    """Mata el ARBOL de procesos (el agente abre un server MCP hijo)."""
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


def lanza(vuelta: int, dry: bool = False, ids: str | None = None,
          perf: str | None = None, teclas: str | None = None) -> tuple:
    """Arranca tools/autonomo.py y devuelve (proceso, ruta del log)."""
    log = DATOS / f"supervisor-vuelta-{vuelta}.log"
    cmd = [sys.executable, "-u", str(RAIZ / "tools" / "autonomo.py")]
    if dry:
        cmd.append("--dry")
    if ids:
        cmd.append(f"--ids={ids}")
    env = dict(os.environ)
    if perf:
        # El perfil de velocidad lo elige el operador; viaja por el entorno
        # para que el agente hijo lo herede.
        env["MATRIZ_PERFIL"] = perf
    if teclas:
        # La cadencia de teclas es un knob aparte del perfil (ver perfil.TECLAS).
        env["MATRIZ_TECLAS"] = teclas
    fh = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(RAIZ), stdout=fh, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=env)
    proc._log_fh = fh  # se cierra en vigila()
    return proc, log


def vigila(proc: subprocess.Popen, log: Path, sin_progreso: int = 240,
           tope: int = 5400, mira_cada: float = 2.0) -> tuple:
    """Espera a la vuelta. Devuelve (codigo | None, motivo).

    Watchdog por LOG, no por estado: si el agente se cuelga (una ventana modal,
    un Alt+Tab que no llega) deja de escribir y hay que matarlo. Cuando trabaja
    escribe una linea cada pocos segundos.
    """
    inicio = time.time()
    ultimo_tam, ultimo_cambio = -1, time.time()
    try:
        while True:
            codigo = proc.poll()
            if codigo is not None:
                return codigo, "termino"
            ahora = time.time()
            if ahora - inicio > tope:
                _mata(proc)
                return None, f"la vuelta paso de {tope}s"
            tam = _tam(log)
            if tam != ultimo_tam:
                ultimo_tam, ultimo_cambio = tam, ahora
            elif ahora - ultimo_cambio > sin_progreso:
                _mata(proc)
                return None, f"sin escribir en el log {sin_progreso}s"
            time.sleep(mira_cada)
    finally:
        fh = getattr(proc, "_log_fh", None)
        if fh:
            try:
                fh.close()
            except OSError:
                pass


def escribe_estado(**datos) -> None:
    """Estado vivo para poder mirarlo sin abrir el log (el panel lo lee)."""
    try:
        ESTADO.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except OSError:
        pass


# ------------------------------------------------------------ main
def corre(dry: bool = False, ids: str | None = None, max_vueltas: int = 8,
          max_sin_avance: int = 2, horas: float = 8.0,
          sin_progreso: int = 240, tope_vuelta: int = 5400,
          perf: str | None = None, teclas: str | None = None) -> int:
    DATOS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        print(f"ya hay un supervisor corriendo (si no es asi, borra {LOCK})",
              file=sys.stderr)
        return 2
    cuantas = total()
    if not cuantas:
        print(f"no hay direcciones en {DIRECCIONES}", file=sys.stderr)
        return 2
    if excel_bloquea():
        print("AVISO: direcciones.csv esta abierto en Excel: las fichas iran a "
              "datos/fichas_pendientes.csv y se recuperaran al arrancar.", flush=True)
    if anydesk_vivo() is False:
        print("AVISO: no veo ninguna ventana de AnyDesk: el agente no podra "
              "inyectar hasta que se abra.", flush=True)
    if not hay_credenciales():
        print("AVISO: no hay credenciales del 5250 (tools/credenciales.py): "
              "tras un corte de licencia no habra re-login automatico.", flush=True)

    LOCK.write_text(str(time.time()), encoding="utf-8")
    limite = time.time() + horas * 3600
    sin_avance = 0
    anterior = None
    vuelta = 0
    try:
        while vuelta < max_vueltas and time.time() < limite:
            accion = control()
            if accion == "detener":
                print("STOP: detener pedido desde el panel", flush=True)
                break
            while control() == "pausar":
                print("PAUSA: esperando reanudar desde el panel", flush=True)
                time.sleep(5)
                if time.time() >= limite:
                    break
            vuelta += 1
            est = estados()
            faltan = pendientes(est)
            print(f"\n=== VUELTA {vuelta} | pendientes: {len(faltan)}/{cuantas} ===",
                  flush=True)
            if not faltan:
                print("nada pendiente: terminado", flush=True)
                break
            escribe_estado(vuelta=vuelta, pendientes=len(faltan), total=cuantas,
                           estado="corriendo", hora=time.strftime("%H:%M:%S"))
            proc, log = lanza(vuelta, dry, ids, perf, teclas)
            print(f"  log: {log.name}", flush=True)
            codigo, motivo = vigila(proc, log, sin_progreso, tope_vuelta)
            est = estados()
            despues = len(pendientes(est))
            print(f"  vuelta {vuelta}: {motivo} (codigo={codigo}) | "
                  f"pendientes: {despues}/{cuantas}", flush=True)
            if anterior is not None and despues >= anterior:
                sin_avance += 1
            else:
                sin_avance = 0
            anterior = despues
            escribe_estado(vuelta=vuelta, pendientes=despues, total=cuantas,
                           estado=motivo, hora=time.strftime("%H:%M:%S"))
            if despues == 0:
                break
            if sin_avance >= max_sin_avance:
                print(f"STOP: {sin_avance} vueltas seguidas sin avanzar: algo "
                      f"esta atascado (mira {log.name} y la pantalla remota)",
                      flush=True)
                break
            if motivo.startswith("sin escribir"):
                print("  el agente se colgo: se relanza", flush=True)
                time.sleep(5)
            elif motivo == "termino" and codigo not in (0, None):
                print("  la vuelta salio con error: se relanza", flush=True)
                time.sleep(5)
        else:
            print(f"STOP: tope de vueltas ({max_vueltas}) o de tiempo "
                  f"({horas}h) alcanzado", flush=True)
    finally:
        LOCK.unlink(missing_ok=True)
        est = estados()
        print("\n=== INFORME FINAL ===")
        print(resumen(est, cuantas))
        escribe_estado(vuelta=vuelta, pendientes=len(pendientes(est)),
                       total=cuantas, estado="terminado",
                       hora=time.strftime("%H:%M:%S"))
    return 0


def main(argv: list) -> int:
    dry = ids = None
    max_vueltas, max_sin, sin_prog = 8, 2, 240
    horas, tope = 8.0, 5400
    dry = False
    perf = None
    teclas = None
    for a in argv[1:]:
        if a == "--dry":
            dry = True
        elif a.startswith("--ids="):
            ids = a.split("=", 1)[1]
        elif a.startswith("--max-vueltas="):
            max_vueltas = int(a.split("=", 1)[1])
        elif a.startswith("--max-sin-avance="):
            max_sin = int(a.split("=", 1)[1])
        elif a.startswith("--sin-progreso="):
            sin_prog = int(a.split("=", 1)[1])
        elif a.startswith("--horas="):
            horas = float(a.split("=", 1)[1])
        elif a.startswith("--tope-vuelta="):
            tope = int(a.split("=", 1)[1])
        elif a.startswith("--perfil="):
            perf = a.split("=", 1)[1]
        elif a.startswith("--teclas="):
            teclas = a.split("=", 1)[1].strip().lower()
            if teclas not in ("rapido", "humano"):
                print(f"modo de teclas desconocido: {a} (usa rapido/humano)",
                      file=sys.stderr)
                return 2
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"opcion desconocida: {a}", file=sys.stderr)
            return 2
    return corre(dry, ids, max_vueltas, max_sin, horas, sin_prog, tope, perf,
                 teclas)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
