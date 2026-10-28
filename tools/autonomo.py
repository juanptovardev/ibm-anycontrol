"""PRUEBA COMPLETA AUTONOMA: una sola orden, sin manos.

    python tools/autonomo.py                 # todas las direcciones pendientes
    python tools/autonomo.py --ids=D01,D02   # solo esas
    python tools/autonomo.py --dry           # no copia ni pega en la hoja
    python tools/autonomo.py --hwnd=3342962  # si la deteccion de AnyDesk falla

Que hace, en una sola sesion MCP:

  0. Localiza el escritorio remoto (AnyDesk) por su clase de ventana y
     reconecta solo si hay un corte por licencia.
  1. Lleva la pantalla al FORMULARIO. Primero con la secuencia probada del
     operador; si las reglas NO saben como, PREGUNTA A JEV que opcion de menu
     abre la consulta de edificios.
  2. Por cada direccion pendiente de datos/direcciones.csv:
     buscar -> copiar la ficha del edificio -> escribirla en la columna C del
     CSV -> extraer bloque a bloque -> pegar en la hoja -> paginar -> detectar
     el fin de archivo -> volver al formulario.
  3. Deja rastro en datos/ledger.csv y datos/traza.jsonl y escribe un dossier
     en tools/verifications/.

Jev decide todo lo que la logica no resuelve:
  - que pantalla es cuando las senales del OCR no casan,
  - si una pagina sin codigos esta vacia o trae suscriptores,
  - que opcion de menu hay que pulsar cuando la pantalla no es conocida.

Criterio de seguridad: nunca se pega dos veces la misma fila. Si el ciclo se
rompe a media matriz, la direccion se marca como fallida y se sigue con la
siguiente: un hueco se ve en la hoja, un duplicado no.
"""
import asyncio
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _jev
import loop as L
import preflight_auto as pf
import traza
import vigia
from _mcp import connect
from estado import captura, clasificar, ocr_text

RAIZ = Path(__file__).resolve().parent.parent
UMBRAL_JEV = 0.6
MAX_FALLOS_REENCUADRE = 2


# ---------------------------------------------------------------- 0. escritorio
def buscar_raiz_anydesk() -> int | None:
    """La ventana de AnyDesk: clase ad_win* visible y de mayor area."""
    try:
        import win32gui
    except ImportError:
        return None
    cands = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        if not win32gui.GetClassName(h).startswith("ad_win"):
            return
        try:
            x0, y0, x1, y1 = win32gui.GetWindowRect(h)
        except Exception:
            return
        area = (x1 - x0) * (y1 - y0)
        if area > 100000:
            cands.append((h, area))

    win32gui.EnumWindows(cb, None)
    if not cands:
        return None
    cands.sort(key=lambda t: -t[1])
    return cands[0][0]


# ------------------------------------------------------------ 1. arbitro Jev
def jev_elige(texto: str, opciones: list[str], instruccion: str,
              criteria: dict | None = None):
    """Jev elige una opcion. Devuelve (opcion|None, nota).

    Sincrona a proposito: _jev.ask es bloqueante (curl), asi que envolverla en
    un await solo anade ruido y la hace mas dificil de testear.
    """
    r = _jev.ask((texto or "")[:2500], instruccion, list(opciones), criteria=criteria)
    if not r.get("ok"):
        return None, f"jev fallo: {r.get('error')}"
    conf = float(r.get("confianza") or 0.0)
    if conf < UMBRAL_JEV:
        return None, f"jev conf {conf:.2f} < {UMBRAL_JEV} (no es veredicto)"
    return r.get("choice"), f"jev: {r.get('choice')} conf={conf:.2f}"


RE_OPCION = re.compile(r"^\s*(\d{1,2})\s*[.)]\s+(.+?)\s*$")


def opciones_menu(texto: str) -> dict:
    """Extrae {numero: descripcion} de las opciones numeradas de un menu 5250."""
    out = {}
    for linea in (texto or "").splitlines():
        m = RE_OPCION.match(linea)
        if not m:
            continue
        num = m.group(1)
        if num not in out:
            out[num] = m.group(2)[:90]
    return out


INSTR_MENU = (
    "Esta es la pantalla de un menu del sistema IBM 5250. Elige el numero de la "
    "opcion que permite CONSULTAR un edificio o una cuenta matriz (la pantalla "
    "CONSULTA EDIFICIO-CUENTA MATRIZ, donde se escribe una calle y un numero de "
    "casa y se pulsa F10). Si ninguna opcion sirve exactamente, elige la mas "
    "cercana a una consulta."
)


def jev_opcion_menu(texto: str):
    """Jev elige que opcion de menu abrir. Devuelve (numero|None, nota)."""
    ops = opciones_menu(texto)
    if len(ops) < 2:
        return None, "la pantalla no tiene un menu numerado legible"
    criteria = {n: f"{n}. {d}" for n, d in ops.items()}
    choice, nota = jev_elige(texto, list(ops.keys()), INSTR_MENU, criteria)
    if not choice:
        return None, nota
    m = re.match(r"\s*(\d{1,2})", choice)
    if not m:
        return None, f"jev devolvio {choice!r}"
    return m.group(1), nota


def traza_segura(etapa: str, resultado: str, detalle: str = "") -> None:
    try:
        traza.evento(etapa, resultado, detalle)
    except (ValueError, TypeError) as exc:
        print(f"  (traza {etapa}/{resultado}: {exc})")


# ------------------------------------------------------------ 2. pre-vuelo
async def pre_vuelo(s, hwnd: int, intentos: int = 5) -> bool:
    """Deja el escritorio remoto en el FORMULARIO. Jev decide si no se sabe."""
    for intento in range(intentos):
        raiz = vigia.raiz(hwnd)
        dlg = vigia.dialogo(raiz)
        if dlg:
            print(f"  [pre] corte de AnyDesk: {dlg.get('titulo')!r} -> reconectando")
            r = vigia.reconecta(raiz)
            print(f"  [pre] reconexion ok={r.get('ok')} {r.get('motivo','')}")
            await asyncio.sleep(2.0)
            continue

        img, _ = captura(hwnd)
        st = clasificar(img, usar_jev=False)
        est = st.get("estado")
        print(f"  [pre] estado={est} conf={st.get('confianza')} err={st.get('error')}")

        if est == "formulario":
            return True
        if est == "desconectado":
            await asyncio.sleep(1.5)
            continue

        # La logica sabe: listado/ficha -> volver, error -> ESC, None -> NAV.
        if await L.entrar_formulario(s, hwnd):
            return True

        # La logica NO sabe. Jev elige la opcion de menu.
        num, nota = jev_opcion_menu(ocr_text(img))
        print(f"  [pre] jev -> opcion {num} ({nota})")
        if not num:
            return False
        await pf.step(s, "jev_opcion", "write_to_anydesk", {"command": num})
        await asyncio.sleep(0.5)
        await pf.step(s, "jev_enter", "press_enter", None)
        await asyncio.sleep(1.3)
    return False


# ------------------------------------------------------------ 3. direcciones
async def por_direccion(s, hwnd: int, filas: list, dry: bool) -> list:
    """Procesa cada direccion pendiente. Devuelve la lista de resultados."""
    resultados = []
    fallos = 0
    for f in filas:
        id_ = f.get("id")
        print(f"\n=== {id_}: {f.get('direccion_parte1')} / {f.get('direccion_parte2')} ===")
        res = await L.procesa(f, hwnd, s, dry)
        resultados.append(res)
        print(f"  -> estado={res.get('estado')} paginas={res.get('paginas_vistas')} "
              f"filas={res.get('filas_copiadas')} | {res.get('notas','')}")
        traza_segura("registrar", "ok" if res.get("estado") == "ok" else "fallo",
                     f"{id_} {res.get('notas','')}")
        if await L.entrar_formulario(s, hwnd):
            fallos = 0
        else:
            fallos += 1
            print(f"  no se pudo volver al formulario ({fallos}/{MAX_FALLOS_REENCUADRE})")
            if fallos >= MAX_FALLOS_REENCUADRE:
                print("STOP: dos reencuadres seguidos fallidos", file=sys.stderr)
                break
    return resultados


# ------------------------------------------------------------ 4. resumen
def resumen(filas: list, hechos: dict) -> str:
    lineas = []
    total_filas = 0
    for f in filas:
        h = hechos.get(f.get("id"), {})
        estado = h.get("estado", "-")
        paginas = h.get("paginas_vistas", "-")
        filas_n = h.get("filas_copiadas", "-")
        try:
            total_filas += int(filas_n)
        except (TypeError, ValueError):
            pass
        lineas.append(f"  {f.get('id')}: {estado} | paginas={paginas} | "
                      f"filas={filas_n} | {h.get('notas','')}")
    return "\n".join(lineas) + f"\n  TOTAL filas pegadas: {total_filas}"


def escribe_dossier(hwnd: int, filas: list, hechos: dict, dry: bool) -> Path:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = RAIZ / "tools" / "verifications" / f"autonomo-{ts}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = [
        f"# Corrida autonoma {ts}",
        "",
        f"- hwnd AnyDesk: `{hwnd}`",
        f"- modo: {'DRY (sin copiar ni pegar)' if dry else 'REAL (copia y pega)'}",
        f"- direcciones: {len(filas)}",
        "",
        "## Resultado por direccion",
        "",
        "| id | estado | paginas | filas | notas |",
        "|---|---|---|---|---|",
    ]
    for f in filas:
        h = hechos.get(f.get("id"), {})
        cuerpo.append(f"| {f.get('id')} | {h.get('estado','-')} | "
                      f"{h.get('paginas_vistas','-')} | {h.get('filas_copiadas','-')} | "
                      f"{h.get('notas','')} |")
    cuerpo += ["", "## Evidencia", "", "- `datos/ledger.csv` (append-only)",
               "- `datos/traza.jsonl`", "- `evidencia/<id>-fin.png`", ""]
    destino.write_text("\n".join(cuerpo), encoding="utf-8")
    return destino


# ------------------------------------------------------------ 5. main
async def corre(hwnd: int | None, ids: str | None, dry: bool) -> int:
    if not hwnd:
        hwnd = buscar_raiz_anydesk()
    if not hwnd:
        print("STOP: no se encuentra la ventana de AnyDesk", file=sys.stderr)
        return 2
    print(f"escritorio remoto: hwnd={hwnd}")

    filas = L.lee_direcciones()
    if ids:
        pedidas = {i.strip().upper() for i in ids.split(",") if i.strip()}
        filas = [f for f in filas if str(f.get("id", "")).upper() in pedidas]
    if not filas:
        print("no hay direcciones que procesar")
        return 2

    hechos = L.ledger_leido()
    pendientes = [f for f in filas
                  if hechos.get(f.get("id"), {}).get("estado") != "ok"]
    print(f"direcciones: {len(filas)} | pendientes: {len(pendientes)} | "
          f"ya ok: {len(filas) - len(pendientes)}")
    if not pendientes:
        print("nada que hacer (B7: todo ya esta en el ledger como ok)")
        return 0

    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        if not await pre_vuelo(s, hwnd):
            print("STOP: no se pudo dejar la pantalla en el formulario",
                  file=sys.stderr)
            return 1
        await por_direccion(s, hwnd, pendientes, dry)

    hechos = L.ledger_leido()
    print("\n=== RESUMEN ===")
    print(resumen(filas, hechos))
    dossier = escribe_dossier(hwnd, filas, hechos, dry)
    print(f"dossier: {dossier}")
    return 0


def main(argv: list) -> int:
    hwnd = None
    ids = None
    dry = False
    for a in argv[1:]:
        if a.startswith("--hwnd="):
            try:
                hwnd = int(a.split("=", 1)[1])
            except ValueError:
                print(f"hwnd invalido: {a}", file=sys.stderr)
                return 2
        elif a.startswith("--ids="):
            ids = a.split("=", 1)[1]
        elif a == "--dry":
            dry = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"opcion desconocida: {a}", file=sys.stderr)
            return 2
    return asyncio.run(corre(hwnd, ids, dry))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
