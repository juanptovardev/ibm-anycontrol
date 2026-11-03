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

Criterio de seguridad: se evita pegar dos veces la misma fila. El ledger se
escribe pagina a pagina, ASI QUE la ventana de duplicado es de UNA pagina (si
el corte cae entre el pegado y su registro). Si el ciclo se rompe a media
matriz, la direccion se marca como fallida y se sigue con la siguiente: un
hueco se ve en la hoja, un duplicado no.
"""
import asyncio
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _jev
import enfocar
import loop as L
import perfil
import preflight_auto as pf
import traza
import vigia
from _mcp import connect
from estado import (CRITERIOS_ESTADO, captura, clasificar_texto, ocr_text)
import native_shot

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
PELIGROSAS = ("FINALIZAR", "SALIR", "CERRAR", "TERMINAR", "ABANDONAR")


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
    # Nunca se ofrecen opciones que cierren la sesion o salgan del sistema
    # (medido: "90. Finalizar Sesion" cuelga el agente).
    seguras = {n: d for n, d in ops.items()
               if not any(p in d.upper() for p in PELIGROSAS)}
    if not seguras:
        return None, "todas las opciones del menu son peligrosas"
    criteria = {n: f"{n}. {d}" for n, d in seguras.items()}
    choice, nota = jev_elige(texto, list(seguras.keys()), INSTR_MENU, criteria)
    if not choice:
        return None, nota
    m = re.match(r"\s*(\d{1,2})", choice)
    if not m:
        return None, f"jev devolvio {choice!r}"
    return m.group(1), nota


INSTR_ESTADO = (
    "Esta es la pantalla de un sistema IBM 5250 de gestion de clientes. Di que "
    "pantalla es. Solo puede ser una de estas: formulario (CONSULTA "
    "EDIFICIO-CUENTA MATRIZ, donde se escribe calle y numero de casa), ficha "
    "(la ficha del edificio con otras direcciones, total de unidades y renta), "
    "cuenta_matriz (CONSULTA UNIDADES, la lista de suscriptores de un "
    "edificio), fin_libro (el aviso de giro mas alla del primer o ultimo "
    "registro), desconectado (dialogo de AnyDesk), sin_coincidencia (aviso de "
    "que la direccion no esta en el archivo) o error (aviso en rojo del 5250)."
)


async def jev_creen(texto: str):
    """Jev dice QUE pantalla es. Devuelve (clave_estado|None, nota).

    El criteria lleva el nombre del estado delante para poder mapear de vuelta
    la respuesta (Jev devuelve el VALOR del criterio, no la clave).
    """
    criterios = {k: f"{k}: {v}" for k, v in CRITERIOS_ESTADO.items()}
    choice, nota = jev_elige(texto, list(criterios.keys()), INSTR_ESTADO,
                             criterios)
    if not choice:
        return None, nota
    clave = choice.split(":", 1)[0].strip().lower()
    if clave not in CRITERIOS_ESTADO:
        return None, f"jev devolvio {choice!r}"
    return clave, nota


def _captura_limpia(hwnd: int, intentos: int = 3, espera: float = 0.9):
    """Captura hasta que la pantalla sea legible.

    Un frame a medio repintar produce un OCR vacio: si se tomara como verdad,
    el agente creeria que no sabe donde esta y mandaria la secuencia de
    navegacion a ciegas (medido el 28/10: la pantalla era el formulario y se
    Navig�� dos veces sin necesidad).

    `time.sleep` y no `asyncio.sleep` a proposito: esta funcion es sincrona y
    se llama desde el propio pre-vuelo; el script es de una sola tarea, asi
    que bloquear aqui no molesta a nadie.
    """
    img, texto, st = None, "", {}
    for i in range(intentos):
        img, _ = captura(hwnd)
        texto = ocr_text(img)
        st = clasificar_texto(texto, usar_jev=False)
        if st.get("estado") is not None or len(texto.strip()) >= 40:
            return img, texto, st
        print(f"  [pre] captura sucia ({len(texto.strip())} chars), reintento")
        time.sleep(espera)
    return img, texto, st


def traza_segura(etapa: str, resultado: str, detalle: str = "") -> None:
    try:
        traza.evento(etapa, resultado, detalle)
    except (OSError, ValueError, TypeError) as exc:
        print(f"  (traza {etapa}/{resultado}: {exc})")


# ------------------------------------------------------------ 2. pre-vuelo
async def pre_vuelo(s, hwnd: int, intentos: int = 8) -> bool:
    """Deja el escritorio remoto en el FORMULARIO. Jev decide si no se sabe.

    Ningun Halt tumba el lote: un fallo puntual (por ejemplo el guard de foco
    de `preflight_auto.step`) se cuenta como intento fallido y se sigue con el
    siguiente, igual que hace `por_direccion` con cada direccion.
    """
    for intento in range(intentos):
        try:
            if await _pre_vuelo_intento(s, hwnd, intento):
                return True
        except pf.Halt as exc:
            print(f"  [pre] Halt: {exc}", flush=True)
            continue
    return False


async def _pre_vuelo_intento(s, hwnd: int, intento: int) -> bool:
    """Un intento de dejar el remoto listo. Devuelve True si ya esta.

    Peor caso medido: si el remoto se queda pegado en el navegador, los 8
    intentos del pre-vuelo (cada uno con sus 4 sub-intentos de `ir_al_5250`)
    suman ~2 min de reintentos antes de rendirse. Es el precio de que un fallo
    puntual no tumbe el lote; no se anaden mas capas de reintento.
    """
    raiz = vigia.raiz(hwnd)
    dlg = vigia.dialogo(raiz)
    if dlg:
        print(f"  [pre] corte de AnyDesk: {dlg.get('titulo')!r} -> reconectando")
        r = vigia.reconecta(raiz)
        print(f"  [pre] reconexion ok={r.get('ok')} {r.get('motivo','')}")
        await asyncio.sleep(2.0)
        # Tras reconectar, el 5250 vuelve a la pantalla de login.
        if await L.login_si_hace_falta(s, hwnd):
            print("  [pre] login del 5250 hecho tras reconectar", flush=True)
        return False

    img, texto, st = _captura_limpia(hwnd)
    est = st.get("estado")
    print(f"  [pre] estado={est} conf={st.get('confianza')} "
          f"err={st.get('error')} texto={len(texto.strip())}c")

    # 'sin_coincidencia' = el formulario con el aviso de "no encontrada": se
    # puede escribir la direccion siguiente encima sin limpiar (03/11).
    if est in ("formulario", "sin_coincidencia"):
        return True
    if est == "desconectado":
        await asyncio.sleep(1.5)
        return False
    # Tras un corte, el 5250 vuelve a la pantalla de login: se entra solo.
    if est is None and await L.login_si_hace_falta(s, hwnd, img):
        print("  [pre] login del 5250 hecho", flush=True)
        return False
    # El remoto puede estar en el navegador (se queda ahi tras pegar en la
    # hoja). Las teclas del 5250 no llegan: hay que volver al 5250 con
    # Alt+Tab antes de intentar nada (medido el 28/10: el pre-vuelo ciclaba
    # en balde con la secuencia del operador sobre Chrome).
    if (st.get("senales") or {}).get("no_ibm"):
        print("  [pre] el remoto esta en el navegador: Alt+Tab de vuelta al 5250",
              flush=True)
        if await L.ir_al_5250(s, hwnd):
            return False
        print("  [pre] no se vuelve al 5250", flush=True)
        return False
    if est in ("cuenta_matriz", "ficha", "error", "mensajes"):
        if await L.entrar_formulario(s, hwnd):
            return True
        return False

    # Pantalla desconocida. Si hay un MENU NUMERADO, esa es la via no
    # ambigua: Jev elige la opcion que abre la consulta de edificios.
    # (Medido 28/10: la navegacion real tiene varios niveles y preguntar
    # primero "que pantalla es" gastaba un turno sin avanzar.)
    num, nota = jev_opcion_menu(texto)
    print(f"  [pre] jev: opcion de menu={num} ({nota})")
    if num:
        await pf.step(s, "jev_opcion", "write_to_anydesk", {"command": num})
        await asyncio.sleep(0.5)
        await pf.step(s, "jev_enter", "press_enter", {})
        await asyncio.sleep(1.3)
        return False

    # Sin menu numerado: Jev dice que pantalla es.
    estado_jev, nota2 = await jev_creen(texto)
    print(f"  [pre] jev: pantalla={estado_jev} ({nota2})")
    if estado_jev == "formulario":
        return True
    if estado_jev in ("cuenta_matriz", "ficha"):
        if await L.volver_formulario(s, hwnd):
            return True
        return False
    if estado_jev == "desconectado":
        await asyncio.sleep(1.5)
        return False

    # Ultimo recurso: la secuencia de navegacion probada por el operador.
    native_shot.save(img, f"pre-desconocido-{intento}")
    print("  [pre] sin veredicto de Jev: se intenta la secuencia del operador")
    if await L.entrar_formulario(s, hwnd):
        return True
    return False


# ------------------------------------------------------------ 3. direcciones
async def por_direccion(s, hwnd: int, filas: list, dry: bool,
                        solo_ficha: bool = False) -> list:
    """Procesa cada direccion pendiente. Devuelve la lista de resultados."""
    resultados = []
    fallos = 0
    for f in filas:
        id_ = f.get("id")
        print(f"\n=== {id_}: {f.get('direccion_parte1')} / {f.get('direccion_parte2')} ===")
        # Reanudacion validada por direccion (el id es posicional: si el
        # operador cambia una fila del CSV, el id apunta a otra direccion).
        desde = L.reanuda_desde(L.ledger_en_curso(), f)
        res = await L.procesa(f, hwnd, s, dry, desde_pagina=desde, solo_ficha=solo_ficha)
        # B6/B7: el resultado se persiste en el ledger ANTES de seguir. Sin esto
        # el resumen y el dossier releen datos viejos y una re-corrida puede
        # duplicar pegadas.
        fila_ledger = {k: res.get(k, "") for k in L.CAMPOS_LEDGER}
        fila_ledger["hora_fin"] = time.strftime("%H:%M:%S")
        if not dry:
            L.ledger_escribe(fila_ledger)
        resultados.append(res)
        print(f"  -> estado={res.get('estado')} paginas={res.get('paginas_vistas')} "
              f"filas={res.get('filas_copiadas')} | {res.get('notas','')}")
        traza_segura("registrar", "ok" if res.get("estado") == "ok" else "fallo",
                     f"{id_} {res.get('notas','')}")
        # Reencuadre al formulario. Si aqui revienta (por ejemplo el foco se
        # perdio y `step` corto con Halt) la EXCEPCION NO debe tumbar el
        # lote: se anota y se sigue con la siguiente direccion. Medido el
        # 28/10: un Halt aqui mato la corrida y D05 nunca arranco.
        # Un error puntual NO cuenta como reencuadre fallido (el entorno puede
        # estar bien y el foco haber temblado); solo cuenta si el reencuadre
        # respondio "no" de verdad.
        error_puntual = False
        try:
            ok = await L.entrar_formulario(s, hwnd)
        except pf.Halt as exc:
            ok = False
            error_puntual = True
            print(f"  aviso: el reencuadre fallo ({exc}); se sigue con la "
                  f"siguiente direccion", flush=True)
        except Exception as exc:  # noqa: BLE001 - una direccion no tumba el lote
            ok = False
            error_puntual = True
            print(f"  aviso: el reencuadre fallo ({type(exc).__name__}: {exc}); "
                  f"se sigue con la siguiente direccion", flush=True)
        if ok:
            fallos = 0
            continue
        if error_puntual:
            continue
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
async def corre(hwnd: int | None, ids: str | None, dry: bool,
                solo_ficha: bool = False) -> int:
    if not hwnd:
        hwnd = buscar_raiz_anydesk()
    if not hwnd:
        print("STOP: no se encuentra la ventana de AnyDesk", file=sys.stderr)
        return 2
    print(f"escritorio remoto: hwnd={hwnd}")
    # Modulo de foco: AnyDesk debe quedar delante antes de cada inyeccion.
    enfocar.set_objetivo(hwnd)

    # P0: recuperar las fichas que no se pudieron guardar porque Excel tenia
    # el CSV abierto, antes de leer el archivo de direcciones.
    recuperadas = L.merge_fichas_pendientes()
    if recuperadas:
        print(f"fichas recuperadas del respaldo: {recuperadas}")

    filas = L.lee_direcciones()
    if ids:
        pedidas = {i.strip().upper() for i in ids.split(",") if i.strip()}
        filas = [f for f in filas if str(f.get("id", "")).upper() in pedidas]
    if not filas:
        print("no hay direcciones que procesar")
        return 2

    hechos = L.ledger_leido()
    # 'no_encontrado' es definitivo: la direccion no existe en el 5250 (el
    # programa contesta 'La direccion no esta en el archivo'). Se salta en las
    # vueltas siguientes para no re-buscar lo mismo, igual que las 'ok'.
    pendientes = [f for f in filas
                  if hechos.get(f.get("id"), {}).get("estado")
                  not in ("ok", "no_encontrado")]
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
        resultados = await por_direccion(s, hwnd, pendientes, dry, solo_ficha)

    hechos = L.ledger_leido()
    # En dry el ledger NO se escribe (if not dry en por_direccion): sin esto el
    # resumen y el dossier releerian el ledger viejo y reportarian que no se
    # hizo nada, aunque el dry-run si haya recorrido todo.
    for r in (resultados or []):
        if r.get("id"):
            hechos[r["id"]] = r
    print("\n=== RESUMEN ===")
    print(resumen(filas, hechos))
    dossier = escribe_dossier(hwnd, filas, hechos, dry)
    print(f"dossier: {dossier}")
    return 0


def main(argv: list) -> int:
    hwnd = None
    ids = None
    dry = False
    solo_ficha = False
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
        elif a == "--solo-ficha":
            solo_ficha = True
        elif a.startswith("--perfil="):
            perfil.ACTIVO = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"opcion desconocida: {a}", file=sys.stderr)
            return 2
    return asyncio.run(corre(hwnd, ids, dry, solo_ficha))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
