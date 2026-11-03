"""Ciclo autonomo por direccion: buscar -> extraer -> paginar -> ledger.

Flujo real (validado en vivo, no reinterpretar):
  1. La pantalla debe ser el formulario (B1).
  2. Macro de busqueda: UN clic en Calle, derecha/izquierda, parte1, '+',
     parte2, '+', F10, Shift+F4.
  3. Si entra al listado: bloque por bloque -> `ciclo.extrae` (7 abajo,
     Shift+Clic, Ctrl+C, Alt+Tab, Ctrl+Shift+V, desplazar).
  4. `pagina.volver` (Alt+Tab de regreso) y `pagina.avanza` (AvPág).
     Si sale el aviso de fin de archivo, la matriz se acabo.
  5. Todo deja rastro en `datos/ledger.csv` (contrato congelado) y en
     `datos/traza.jsonl` (que paso y en que punto esta el sistema).

BLINDAJE (reglas duras, cada una verificable):
  B1  No se teclea a ciegas: la pantalla debe estar en 'formulario'.
  B2  No se presiona F10 sin verificar que el texto quedo en Calle (y no en Nombre).
  B3  Si el estado no es el esperado, el item se aborta (no se improvisa).
  B4  El foco lo vigila el server (focus guard): si la ventana local roba el
      foco, la llamada falla y aqui se aborta.
  B5  Maximo 1 reintento por item, y solo con la misma secuencia.
  B6  Todo item deja rastro: una fila en el ledger + evidencia en disco.
  B7  Idempotencia: lo que ya esta 'ok' en el ledger no se vuelve a procesar.

Uso: python tools/loop.py <hwnd> [id] [--dry]
"""
import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import ciclo
import matriz_extraer
import credenciales
import enfocar
import login
import pagina
import perfil
import preflight_auto as pf
import nav_prefill
import native_shot
import recepcion
import rows as rowdet
import traza
import vigia
import ventana
from _mcp import connect, need_hwnd
from estado import captura, clasificar, ocr_text
from matriz_buscar import (NOMBRE, CALLE, CASA, INK_MIN, buscar,
                            verifica_texto)
from matriz_ficha import (escribe_ficha, lee_direcciones,
                          merge_fichas_pendientes, normaliza_dir)

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos" / "datos.csv"
LEDGER = RAIZ / "datos" / "ledger.csv"
# Contrato congelado del repo (ver datos/ledger.csv y PROMPT_OBRERO_T-IBM-01.md).
CAMPOS_LEDGER = ["id", "direccion_parte1", "direccion_parte2", "comuna",
                  "cuenta_matriz_esperada", "estado", "paginas_vistas",
                  "filas_copiadas", "hora_inicio", "hora_fin", "evidencia",
                  "notas", "reintentos"]
REINTENTOS = 1
# Indices de fila del formulario CONSULTA EDIFICIO (rows.detect devuelve 8).
# El bloque del operador son 15 filas (7 abajo + 14 de alto).
FILAS_POR_BLOQUE = 15
MAX_PAGINAS = 40
# Verbosidad: con MATRIZ_VERBOSE=1 se lee el formulario entero antes del F10
# (cuesta ~1 s de OCR por direccion).
VERBOSE = os.environ.get("MATRIZ_VERBOSE") == "1"
CTRL = Path(__file__).resolve().parent.parent / "datos" / "control.json"


def control() -> str:
    """Accion pedida desde el panel (pausar / reanudar / detener)."""
    try:
        return json.loads(CTRL.read_text(encoding="utf-8")).get("accion", "libre")
    except (OSError, ValueError):
        return "libre"


def obedece() -> str:
    """Espera mientras este pausado; devuelve 'detener' si hay que cortar."""
    while control() == "pausar":
        time.sleep(1.0)
    return control()



async def volver_formulario(s, hwnd: int, intentos: int = 3) -> bool:
    """Sale del listado/ficha hasta quedar de nuevo en el formulario.

    En CONSULTA UNIDADES la barra solo tiene F12=Anterior y al pasar de la
    ultima pagina el 5250 queda con el teclado inhibido ('A X II'), estado en
    el que F3 se ignora. Primero se limpia con Escape y se sale con F12
    (listado -> ficha -> formulario); F3 queda como ultimo recurso.
    """
    for intento in range(intentos):
        img, _ = captura(hwnd)
        st0 = clasificar(img, usar_jev=False)
        # Si el remoto quedo en el navegador, ESC/F12/F3 no hacen nada: primero
        # hay que volver al 5250 (medido el 28/10).
        if not en_ibm(st0):
            if await ir_al_5250(s, hwnd):
                img, _ = captura(hwnd)
                st0 = clasificar(img, usar_jev=False)
        # 'sin_coincidencia' es el formulario con el aviso de "no encontrada":
        # ya se puede escribir la direccion siguiente encima (regla 03/11).
        if st0.get("estado") in ("formulario", "sin_coincidencia"):
            return True
        if intento == 0:
            await pf.step(s, "esc_inhibido", "press_keys", {"keys": ["escape"]})
            await asyncio.sleep(0.4)
        tecla = "f12" if intento < 2 else "f3"
        await pf.step(s, f"salir_{tecla}", "press_keys", {"keys": [tecla]})
        await asyncio.sleep(0.9)
    img, _ = captura(hwnd)
    return clasificar(img, usar_jev=False).get("estado") == "formulario"


def lee_datos(ruta: Path = DATOS) -> list[dict]:
    """Filas de entrada con el contrato de datos.csv."""
    if not ruta.exists():
        raise SystemExit(f"falta {ruta}")
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    for f in filas:
        faltan = {"id", "direccion_parte1", "direccion_parte2"} - set(f)
        if faltan:
            raise SystemExit(f"datos.csv sin columnas {faltan}")
    return filas


def _sep_ledger(ruta: Path) -> str:
    """Separador del ledger: ';' (el nuevo) o ',' (el antiguo, por migrar)."""
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            head = fh.readline()
    except OSError:
        return ";"
    return ";" if head.count(";") >= head.count(",") else ","


def ledger_leido(ruta: Path = LEDGER) -> dict:
    """id -> fila del ledger. UNA fila por direccion: el estado actual.

    Antes el ledger era append-only (una fila por pagina pegada) y se leia
    como una lista vertical de la misma direccion repetida. Ahora es una tabla:
    una fila por direccion, actualizada en el sitio. El historial completo
    sigue en datos/traza.jsonl, que si es append-only.
    """
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=_sep_ledger(ruta)))
    return {f.get("id"): f for f in filas if f.get("id")}


def es_resumable(fila: dict) -> bool:
    """True si la fila dice que esa direccion quedo a medias.

    Resumible = estado 'en_curso' o un error despues de haber pegado alguna
    pagina (paginas_vistas > 0). 'ok' y 'no_encontrado' no se reanudan.
    """
    estado = (fila.get("estado") or "").strip()
    if estado == "ok":
        return False
    try:
        paginas = int(fila.get("paginas_vistas") or 0)
    except (TypeError, ValueError):
        paginas = 0
    return estado == "en_curso" or paginas > 0


def ledger_en_curso(ruta: Path = LEDGER) -> dict:
    """id -> fila de las direcciones que quedaron a medias (reanudables)."""
    return {k: v for k, v in ledger_leido(ruta).items() if es_resumable(v)}


def ledger_escribe(fila: dict, ruta: Path = LEDGER) -> None:
    """Guarda el estado de UNA direccion. Una fila por id, escritura atomica.

    Reescribe el fichero entero con una fila por direccion (upsert por id). La
    escritura es atomica (temporal + os.replace): un corte a mitad no deja el
    ledger corrupto.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    filas = ledger_leido(ruta)
    id_ = (fila.get("id") or "").strip()
    if id_:
        nuevo = {c: fila.get(c, "") for c in CAMPOS_LEDGER}
        # El punto de reanudacion no se pierde: si la fila nueva no dice
        # cuantas paginas se pegaron y la anterior si, se hereda. Solo si es
        # la MISMA direccion (el id es posicional: si el operador cambia la
        # fila del CSV, el id pasa a apuntar a otra direccion y el valor viejo
        # no valdria).
        prev = filas.get(id_)
        if prev:
            try:
                paginas = int(nuevo.get("paginas_vistas") or 0)
            except (TypeError, ValueError):
                paginas = 0
            misma = (normaliza_dir(prev.get("direccion_parte1")) ==
                     normaliza_dir(nuevo.get("direccion_parte1")) and
                     normaliza_dir(prev.get("direccion_parte2")) ==
                     normaliza_dir(nuevo.get("direccion_parte2")))
            if paginas <= 0 and misma:
                nuevo["paginas_vistas"] = prev.get("paginas_vistas", "") or ""
                nuevo["filas_copiadas"] = prev.get("filas_copiadas", "") or ""
        filas[id_] = nuevo
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPOS_LEDGER, delimiter=";")
            w.writeheader()
            for f in filas.values():
                w.writerow({c: f.get(c, "") for c in CAMPOS_LEDGER})
        os.replace(tmp, ruta)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


UMBRAL_CAMBIO = 50


async def espera_estado(hwnd: int, objetivos: set[str], intentos: int = 12,
                        delay: float = 0.4) -> dict:
    """Espera a que la pantalla llegue a uno de los estados. B3/B4.

    Antes cada sondeo pagaba un OCR de pantalla completa (~0,93 s) y el
    primero se gastaba SIEMPRE: el F10 tarda ~1 s en pintarse, asi que ese
    sondeo no podia ver nada. Ahora se captura cada `delay` y se compara con
    la captura anterior (10 ms): solo se clasifica cuando la pantalla ha
    CAMBIADO. Los sondeos en espera cuestan 40 ms en vez de 960 ms.

    La clasificacion sigue siendo la COMPLETA a proposito: sus palabras
    (cabecera Suscript) son las que T4' reutiliza para el primer bloque, y
    un recorte por franja las perderia (0,33 s de ahorro contra 0,93 s de
    OCR recreado).
    """
    img0, _vp = captura(hwnd)
    for _ in range(intentos):
        await asyncio.sleep(delay)
        img, _vp = captura(hwnd)
        if pf.changed_px(img0, img) < UMBRAL_CAMBIO:
            img0 = img
            continue
        img0 = img
        st = clasificar(img, usar_jev=False)
        if st["estado"] in objetivos:
            return st
    img, _vp = captura(hwnd)
    return clasificar(img, usar_jev=True)


PENDIENTES = RAIZ / "datos" / "fichas_pendientes.csv"


def anydesk_vivo(hwnd: int) -> bool:
    """True si la ventana de AnyDesk sigue ahi y sin dialogo de corte.

    Un corte de licencia puede verse como pantalla negra igual que un edificio
    sin datos; antes de dar una direccion por vacia hay que descartar que se
    haya caido la sesion.
    """
    try:
        raiz = vigia.raiz(hwnd)
        if not raiz:
            return False
        import win32gui
        if not win32gui.IsWindow(raiz) or not win32gui.IsWindowVisible(raiz):
            return False
        return not vigia.dialogo(raiz)
    except Exception:  # noqa: BLE001 - sondear ventanas Win32 puede fallar
        # (ventana cerrada a mitad, pywin32 ausente): sin ventana no hay sesion
        # viva, y este guard nunca debe tumbar el item.
        return False


def hay_dialogo(hwnd: int) -> bool:
    """El corte de licencia de AnyDesk es una ventana LOCAL, no pixels remotos.

    Medido: OCR del viewport no siempre lo ve (el modal es hermano del viewport,
    no hijo), asi que la fuente fiable es la enumeracion de ventanas.
    """
    try:
        return bool(vigia.dialogo(vigia.raiz(hwnd)))
    except Exception:  # noqa: BLE001 - si falla la sonda, no se bloquea el flujo
        return False


def reconecta_si_hace_falta(hwnd: int) -> bool:
    """Pulsa Repetir si la sesion se corto. Devuelve True si hay conexion."""
    if not hay_dialogo(hwnd):
        return True
    res = vigia.reconecta(vigia.raiz(hwnd))
    traza.evento("reconectar", "ok" if res.get("ok") else "fallo",
                 detalle=str(res.get("boton") or res.get("motivo")))
    print(f"RECONECTAR {res}", flush=True)
    if not res.get("ok"):
        return False
    time.sleep(2.0)  # la sesion tarda en repintar la pantalla remota
    return True


async def login_si_hace_falta(s, hwnd: int, img=None) -> bool:
    """Si el 5250 pide usuario (tras un corte), entra solo con las credenciales.

    Medido el 28/10: la licencia gratuita de AnyDesk corta la sesion cada pocos
    minutos y al reconectar el 5250 vuelve al login. Sin esto, cada corte
    termina el trabajo.
    """
    if img is None:
        img, _ = captura(hwnd)
    try:
        pide = login.hace_falta(img)
    except Exception:  # noqa: BLE001 - una captura ilegible no es un login
        pide = False
    if not pide:
        return False
    cred = credenciales.carga()
    if not cred:
        print("  [login] el 5250 pide usuario y no hay credenciales guardadas "
              f"({credenciales.ruta()})", flush=True)
        return False
    print(f"  [login] entrando como {cred['usuario']}", flush=True)
    ok = await login.entrar(s, hwnd, cred["usuario"], cred["clave"])
    print(f"  [login] entrada {'ok' if ok else 'fallida'}", flush=True)
    return ok


# Pantallas del 5250 (o avisos suyos). "no_ibm" significa navegador/hoja.
ESTADOS_IBM = ("formulario", "ficha", "cuenta_matriz", "fin_libro",
               "desconectado", "error", "mensajes", "sin_coincidencia")


def en_ibm(st: dict) -> bool:
    """True si la pantalla remota es del 5250 (o un aviso suyo)."""
    sen = st.get("senales") or {}
    if sen.get("no_ibm"):
        return False
    if sen.get("ibm"):
        return True
    return st.get("estado") in ESTADOS_IBM


async def ir_al_5250(s, hwnd: int, intentos: int = 2) -> bool:
    """Si el remoto quedo en el navegador, vuelve al 5250.

    El 03/11 el Alt+Tab dejo de llegar al escritorio remoto: medido con la
    sonda de teclas, la pantalla no cambiaba ni desde el 5250 ni desde
    Chrome, y el pre-vuelo se rindio tras 4 intentos. La via principal es
    ahora el **icono de la taskbar** (ventana.ir_a, cambio en 0,3 s), que
    es ademas la via que usa el pegado. El Alt+Tab queda como ultimo
    recurso, por si la taskbar cambia de disposicion.

    Ademas el remoto tarda 1-3 s en procesar el Alt+Tab, asi que despues de
    enviarlo se sondea la pantalla en vez de esperar un tiempo fijo.
    """
    for i in range(intentos):
        img, _ = captura(hwnd)
        if en_ibm(clasificar(img, usar_jev=False)):
            return True
        ok = await ventana.ir_a(s, hwnd, ventana.DESTINO_IBM,
                                intentos=2, espera=0.4)
        img, _ = captura(hwnd)
        if ok and en_ibm(clasificar(img, usar_jev=False)):
            return True
        await pf.step(s, f"alt_tab_ibm_{i}", "press_keys", {"keys": ["alt", "tab"]})
        for _ in range(3):
            await asyncio.sleep(0.6)
            img, _ = captura(hwnd)
            if en_ibm(clasificar(img, usar_jev=False)):
                return True
    return False


async def entrar_formulario(s, hwnd: int) -> bool:
    """Desde el Menu Principal SCABLE al formulario.

    Secuencia del operador (validada en vivo): 1, ENTER, ESC, 1, ENTER, 1, ENTER.
    Solo navega cuando la pantalla no se reconoce (menu principal). Si ya hay un
    estado claro (formulario, listado, ficha) no toca nada.
    """
    img, _ = captura(hwnd)
    r = clasificar(img, usar_jev=False)
    # Si el remoto quedo en el navegador, las teclas del 5250 no llegan.
    if not en_ibm(r):
        if await ir_al_5250(s, hwnd):
            img, _ = captura(hwnd)
            r = clasificar(img, usar_jev=False)
    if r.get("estado") == "formulario":
        return True
    # Si quedo en el listado o en la ficha (arranque tras un corte, o el
    # operador dejo la pantalla ahi) hay que salir por la ruta que funciona:
    # F3 NO sale de CONSULTA UNIDADES (su barra solo tiene F12=Anterior) y con
    # el teclado inhibido ('A X II') se ignora. La ruta es Escape + F12 + F12
    # (listado -> ficha -> formulario). Sin esto la segunda direccion fallaba
    # con 'B1 pantalla cuenta_matriz' (medido 28/10).
    if r.get("estado") in ("cuenta_matriz", "ficha"):
        return await volver_formulario(s, hwnd)
    # Aviso duro residual (p. ej. el F10 de la direccion anterior no encontro
    # nada): el 5250 deja el mensaje abajo y el teclado inhibido, asi que el
    # item siguiente se quemaria en B1 sin intentar nada. Medido el 28/10: D02
    # termino con 'B3 estado error' y D03 aborto sin arrancar. ESC limpia el
    # aviso antes de rendirse (mismo patron que el NAV de aqui abajo).
    # REGLA DEL OPERADOR (03/11): cuando la direccion no existe, abajo sale
    # 'La direccion no esta en el archivo', pero el formulario SIGUE en
    # pantalla. No se limpia con ESC ni con F3: simplemente se empieza a
    # escribir la direccion de la fila siguiente encima. Por eso
    # 'sin_coincidencia' = formulario con aviso, y se continua.
    if r.get("estado") == "sin_coincidencia":
        return True
    if r.get("estado") == "error":
        await pf.step(s, "esc_residual", "press_keys", {"keys": ["escape"]})
        await asyncio.sleep(0.6)
        img, _ = captura(hwnd)
        r = clasificar(img, usar_jev=False)
        if r.get("estado") == "formulario":
            return True
        if r.get("estado") in ("cuenta_matriz", "ficha"):
            return await volver_formulario(s, hwnd)
        if r.get("estado") == "error":
            # Medido (operador, 28/10): cuando una direccion deja un aviso duro
            # del 5250, la UNICA tecla que sale de esa pantalla es F3. Ni ESC ni
            # F12 la cierran. F3 primero deja el aviso; si con el aviso se
            # vuelve al formulario, no se pulsa F3 (podria cerrar el formulario).
            await pf.step(s, "f3_error", "press_keys", {"keys": ["f3"]})
            await asyncio.sleep(0.9)
            img, _ = captura(hwnd)
            r = clasificar(img, usar_jev=False)
            if r.get("estado") == "formulario":
                return True
            if r.get("estado") in ("cuenta_matriz", "ficha"):
                return await volver_formulario(s, hwnd)
    # "Visualizar Mensajes de Programa" (medido 28/10 con sonda de teclas):
    # la UNICA salida es Intro. Ni ESC ni F3 cierran esa pantalla.
    if r.get("estado") == "mensajes":
        await pf.step(s, "intro_mensajes", "press_enter", {})
        await asyncio.sleep(1.0)
        img, _ = captura(hwnd)
        r = clasificar(img, usar_jev=False)
        if r.get("estado") == "formulario":
            return True
        if r.get("estado") in ("cuenta_matriz", "ficha"):
            return await volver_formulario(s, hwnd)
        if r.get("estado") == "mensajes":
            await pf.step(s, "intro_mensajes2", "press_enter", {})
            await asyncio.sleep(1.0)
            img, _ = captura(hwnd)
            if clasificar(img, usar_jev=False).get("estado") == "formulario":
                return True
    if r.get("estado") is not None:
        return False
    for _ in range(2):
        for label, tool, args in nav_prefill.NAV:
            await pf.step(s, label, tool, args)
            await asyncio.sleep(0.7)
        img, _ = captura(hwnd)
        st = clasificar(img, usar_jev=False)
        if st.get("estado") == "formulario":
            return True
        if st.get("estado") == "error":
            # Aviso residual del intento anterior: ESC lo limpia.
            await pf.step(s, "esc_aviso", "press_keys", {"keys": ["escape"]})
            await asyncio.sleep(0.6)
            img, _ = captura(hwnd)
            if clasificar(img, usar_jev=False).get("estado") == "formulario":
                return True
    return False


async def _pausa(seg: float) -> None:
    """Espera del perfil de velocidad (0 = no hay deficit que rellenar)."""
    if seg > 0:
        await asyncio.sleep(seg)


async def procesa(fila: dict, hwnd: int, s, dry: bool = False,
                  desde_pagina: int = 0, solo_ficha: bool = False) -> dict:
    """Un item completo. Nunca lanza: devuelve el resultado para el ledger.

    Con solo_ficha=True se busca el edificio, se guarda la ficha en la columna 3
    del CSV y se termina: no se entra al listado, no se copia y no se pega. Sirve
    para rellenar la ficha de una direccion que ya se extrajo en una corrida
    anterior, sin volver a pegar sus filas.
    """
    inicio = time.time()
    # Perfil de velocidad: el techo son segundos por direccion. El deficit se
    # reparte en pausas naturales (revisar el formulario, leer la ficha,
    # procesar una pagina, cerrar) con variacion aleatoria, para que el ritmo
    # no sea una maquina de pulsos. Si no se alcanza el techo, se dice.
    perf = perfil.actual()
    objetivo = perf["s_dir"]
    id_ = fila.get("id", "")
    parte1 = fila.get("direccion_parte1", "")
    parte2 = fila.get("direccion_parte2", "")
    res = {"id": id_, "direccion_parte1": parte1, "direccion_parte2": parte2,
           "comuna": fila.get("comuna", ""),
           "cuenta_matriz_esperada": fila.get("cuenta_matriz_esperada", ""),
           "estado": "error", "paginas_vistas": 0, "filas_copiadas": 0,
           "hora_inicio": time.strftime("%H:%M:%S"), "hora_fin": "",
           "evidencia": "", "notas": "", "reintentos": 0}

    ficha = ""
    aviso_ficha = ""
    for intento in range(REINTENTOS + 1):
        res["reintentos"] = intento
        try:
            # B0: si AnyDesk corto la sesion, se reconecta antes de leer nada.
            if not reconecta_si_hace_falta(hwnd):
                res["notas"] = "B0 sin conexion AnyDesk (dialogo de licencia)"
                return res

            # B0b: tras reconectar, el 5250 vuelve a pedir usuario: se entra solo.
            await login_si_hace_falta(s, hwnd)

            # B1: verificar pantalla antes de teclear.
            await entrar_formulario(s, hwnd)
            img, _vp = captura(hwnd)
            st = clasificar(img, usar_jev=False)
            traza.evento("estado", st["estado"] or "desconocido",
                         detalle=f"{id_} intento {intento} conf {st.get('confianza')}")
            if st["estado"] == "desconectado" and reconecta_si_hace_falta(hwnd):
                img, _vp = captura(hwnd)
                st = clasificar(img, usar_jev=False)
                traza.evento("estado", st["estado"] or "desconocido",
                             detalle=f"{id_} tras reconectar")
            # 'sin_coincidencia' es el MISMO formulario con el aviso de la
            # busqueda anterior ("La calle no se encuentra..."). El operador
            # manda escribir la siguiente direccion encima, sin limpiar nada,
            # asi que para B1 cuenta como formulario (medido 03/11: sin esto
            # todas las direcciones siguientes morian con 'B1 sin_coincidencia').
            if st["estado"] not in ("formulario", "sin_coincidencia"):
                res["notas"] = f"B1 pantalla {st['estado']}"
                return res

            _img, _vp, det = rowdet.detect(hwnd)
            if len(det) < 3:
                res["notas"] = "B1 sin filas del formulario"
                return res

            await buscar(s, hwnd, det, parte1, parte2)

            # B2: verificar antes de F10.
            ok, detalle = await verifica_texto(hwnd)
            if not ok:
                res["notas"] = f"B2 {detalle}"
                traza.evento("buscar", "fallo", detalle=f"{id_} {detalle}")
                if intento < REINTENTOS:
                    await pf.step(s, "esc", "press_keys", {"keys": ["escape"]})
                    continue
                return res

            await _pausa(perfil.pausa(inicio, "antes_f10", objetivo, paginas=1))
            await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
            await asyncio.sleep(0.8)

            # B3/B4: F10 lleva a la FICHA del edificio, no al listado. El listado
            # de unidades (con la columna Suscript) entra con Shift+F4 = F16.
            # Medido en vivo: sin este paso el bucle se quedaba en 'formulario'.
            st = await espera_estado(hwnd, {"ficha", "cuenta_matriz",
                                            "sin_coincidencia", "error",
                                            "fin_libro", "mensajes"})
            traza.evento("estado", st["estado"] or "desconocido",
                         detalle=f"{id_} tras F10 conf {st.get('confianza')}")
            vino_mensajes = False
            if st["estado"] == "mensajes":
                vino_mensajes = True
                # El 5250 abre 'Visualizar Mensajes de Programa' cuando un
                # programa falla o no encuentra el dato (medido el 28/10 con
                # D02). Se sale con Intro y el aviso queda escrito en pantalla:
                # se guarda en las notas para que el operador lo lea.
                aviso = (st.get("texto") or "").strip().replace("\n", " | ")[:300]
                for n in range(2):
                    await pf.step(s, f"intro_mensajes{n + 1}", "press_enter", {})
                    await asyncio.sleep(1.0)
                    st = await espera_estado(hwnd, {"ficha", "cuenta_matriz",
                                                    "sin_coincidencia", "error",
                                                    "fin_libro", "formulario",
                                                    "mensajes"})
                    if st["estado"] != "mensajes":
                        break
                res["notas"] = f"mensajes de programa: {aviso}"
            if st["estado"] == "ficha":
                await pf.step(s, "shift_f4", "press_keys",
                              {"keys": ["shift", "f4"]})
                await asyncio.sleep(0.9)
                st = await espera_estado(hwnd, {"cuenta_matriz",
                                                "sin_coincidencia", "error",
                                                "fin_libro"})
            # T4': el OCR con el que se detecto el listado ya esta pagado
            # (~930 ms). Esa misma lectura la reutiliza el primer bloque
            # (ciclo.extrae) en vez de volver a leer la MISMA pantalla.
            previo_inicial = None
            if st.get("estado") == "cuenta_matriz" and st.get("img") is not None:
                previo_inicial = {"img": st.get("img"),
                                   "texto": st.get("texto") or "",
                                   "words": st.get("words") or []}
            if st["estado"] in ("sin_coincidencia", "formulario") or (
                    vino_mensajes and st["estado"] == "error"):
                # 'formulario' aqui significa que la busqueda no arranco el
                # listado: el aviso del 5250 nos devolvio al formulario.
                traza.evento("buscar", "sin_coincidencia", detalle=id_)
                res.update(estado="no_encontrado",
                           notas=(res.get("notas", "") + "; " if res.get("notas") else "")
                           + "sin coincidencia")
                return res
            if st["estado"] is None:
                # Pantalla negra o sin contenido. La regla del operador (28/10)
                # es dejarla vacia y seguir; pero un corte de licencia tambien
                # se ve negro, asi que primero se descarta que la sesion viva.
                if not anydesk_vivo(hwnd):
                    ok_rec = reconecta_si_hace_falta(hwnd)
                    await login_si_hace_falta(s, hwnd)
                    traza.evento("reconectar", "ok" if ok_rec else "fallo",
                                 detalle=f"{id_} pantalla negra")
                    res.update(estado="revisar",
                               notas=(res.get("notas", "") + "; " if res.get("notas") else "")
                               + ("pantalla negra con AnyDesk caido: se reconecto, "
                                  "se reintenta en la proxima corrida"
                                  if ok_rec else
                                  "pantalla negra con AnyDesk caido y la "
                                  "reconexion fallo: se reintenta en la proxima corrida"))
                    return res
                traza.evento("buscar", "sin_coincidencia", detalle=f"{id_} pantalla vacia")
                res.update(estado="sin_datos",
                           notas=(res.get("notas", "") + "; " if res.get("notas") else "")
                           + "pantalla sin contenido: se deja vacia y se sigue")
                return res
            if st["estado"] != "cuenta_matriz":
                traza.evento("buscar", "fallo", detalle=f"{id_} estado {st['estado']}")
                res["notas"] = (res.get("notas", "") + "; " if res.get("notas") else "") \
                    + f"B3 estado {st['estado']}"
                return res
            traza.evento("buscar", "ok", detalle=f"{id_} {parte1} {parte2}")

            # Ficha del edificio (3 lineas: Cuenta / nombre / direccion) para la
            # columna C. Ctrl+C sin seleccion en el 5250 copia la pantalla entera
            # y bloque_de recorta las lineas utiles. Solo lectura.
            try:
                await pf.step(s, "copiar_cabecera", "copy_clipboard", {})
                await asyncio.sleep(0.6)
                ficha = recepcion.bloque_de(recepcion._portapapeles() or "")
            except Exception as exc:  # noqa: BLE001
                ficha = ""
                print(f"  aviso: sin ficha ({exc})", flush=True)

            # La ficha se guarda YA en la columna C del CSV: si la extraccion
            # falla despues (halt, corte de AnyDesk, tope de paginas) el dato
            # del edificio no se pierde. Orden del operador (28/10).
            if not dry:
                aviso_ficha = escribe_ficha(id_, ficha or "")
                if aviso_ficha:
                    print(f"  aviso: {aviso_ficha}", flush=True)
            await _pausa(perfil.pausa(inicio, "tras_ficha", objetivo, paginas=1))

            if solo_ficha:
                nota = ("solo ficha: no se extrajo (la extraccion de esta "
                        "direccion ya estaba hecha)")
                if aviso_ficha:
                    nota += f"; {aviso_ficha}"
                res.update(estado="ok", notas=nota)
                print(f"  {nota}", flush=True)
                return res

            # Reanudacion: si el ledger dice que ya se pegaron N paginas de esta
            # direccion, se avanzan N paginas con AvPag antes de extraer. La
            # licencia gratuita de AnyDesk corta la sesion a los pocos minutos
            # y sin esto cada corte obligaria a repetir (y duplicar) lo pegado.
            if desde_pagina > 0:
                print(f"reanudando en la pagina {desde_pagina + 1} "
                      f"({desde_pagina} ya pegadas)", flush=True)
                for k in range(desde_pagina):
                    await pf.step(s, f"resuma_avpag_{k}", "press_keys",
                                  {"keys": ["pagedown"]})
                    await asyncio.sleep(1.1)
                await asyncio.sleep(0.9)

            # Bloque por bloque hasta el aviso de fin de archivo.
            bloques = desde_pagina
            hechos_hoy = 0
            saltadas = 0
            # La captura de la pagina recien paginada se reutiliza: no se paga
            # otra vez el OCR de una pantalla que ya se leyo (pagina.avanza la
            # deja en pagina.ULTIMA). Se limpia al empezar cada direccion.
            # T4': el primer bloque de una direccion nueva reutiliza la lectura
            # del listado que ya hizo espera_estado (sin OCR nuevo). Con
            # reanudacion no sirve: la pagina actual es otra.
            pagina.ULTIMA = previo_inicial if desde_pagina == 0 else None
            for n in range(1, MAX_PAGINAS + 1):
                if obedece() == "detener":
                    res["notas"] = f"detenido por el panel en el bloque {n}"
                    return res
                if not reconecta_si_hace_falta(hwnd):
                    raise pf.Halt(f"bloque {n}: sin conexion AnyDesk")
                # Las 7 bajadas solo en el PRIMER bloque que se extrae: si las
                # primeras paginas venian sin suscriptores y se saltaron, el
                # cursor del 5250 sigue sin moverse de su punto.
                extra = await matriz_extraer.extrae_bloque(s, hwnd, dry, bajar=(hechos_hoy == 0),
                                           previo=pagina.ULTIMA)
                if extra == "vacia":
                    # La pagina existe pero la columna Suscript viene vacia: no
                    # se copia ni se pega nada, solo se avanza (orden del
                    # operador). No se toca la hoja de calculo.
                    saltadas += 1
                    traza.evento("extraer", "vacia",
                                 detalle=f"{id_} bloque {n} sin suscriptores")
                    if dry:
                        break
                    stp = await pagina.avanza(s, hwnd, prev=ciclo.ULTIMA_IMG)
                    decision = pagina.decide(
                        stp["estado"], bool((stp.get("senales") or {}).get("no_ibm")))
                    traza.evento("pagina", stp["estado"] or "desconocido",
                                 detalle=f"{id_} pagina {n} (vacia) decision {decision}")
                    if decision == "fin":
                        break
                    if decision != "seguir":
                        res["notas"] = f"pagina {n}: estado {stp['estado']}"
                        return res
                    continue
                bloques += 1
                hechos_hoy += 1
                await _pausa(perfil.pausa(inicio, "entre_paginas", objetivo,
                                         paginas=(bloques + saltadas)))
                # B6 por pagina: lo pegado se registra YA. Si AnyDesk corta la
                # sesion en la pagina siguiente, el ledger dice cuantas
                # quedaron pegadas y la corrida reanuda ahi en vez de repetir.
                if not dry:
                    parcial = {k: res.get(k, "") for k in CAMPOS_LEDGER}
                    parcial["estado"] = "en_curso"
                    # paginas_vistas cuenta las paginas AVANZADAS (pegadas + las
                    # saltadas por estar vacias): el cursor de pagina del 5250
                    # avanza en los dos casos, asi que si se contaran solo las
                    # pegadas, al reanudar se volveria a pegar una pagina ya
                    # pegada. filas_copiadas si cuenta solo las pegadas.
                    parcial["paginas_vistas"] = bloques + saltadas
                    parcial["filas_copiadas"] = bloques * FILAS_POR_BLOQUE
                    parcial["hora_fin"] = time.strftime("%H:%M:%S")
                    parcial["notas"] = (f"pagina {bloques + saltadas} pegada; "
                                        f"reanudar en la {bloques + saltadas + 1}")
                    ledger_escribe(parcial)
                traza.evento("extraer", "ok", detalle=f"{id_} bloque {n}")
                if dry:
                    break
                await pagina.volver(s, hwnd)
                traza.evento("volver", "ok", detalle=f"{id_} bloque {n}")
                stp = await pagina.avanza(s, hwnd, prev=ciclo.ULTIMA_IMG)
                decision = pagina.decide(
                    stp["estado"], bool((stp.get("senales") or {}).get("no_ibm")))
                traza.evento("pagina", stp["estado"] or "desconocido",
                             detalle=f"{id_} pagina {n} decision {decision}")
                if decision == "fin":
                    break
                if decision != "seguir":
                    res["notas"] = f"pagina {n}: estado {stp['estado']}"
                    return res
            else:
                res["notas"] = f"tope de {MAX_PAGINAS} paginas alcanzado"
                return res

            res["paginas_vistas"] = bloques + saltadas
            res["filas_copiadas"] = bloques * FILAS_POR_BLOQUE
            res["estado"] = "ok"
            img_fin, _vp_fin = captura(hwnd)
            res["evidencia"] = str(native_shot.save(img_fin, f"{id_}-fin"))
            res["ficha"] = ficha or ""
            if not dry:
                await volver_formulario(s, hwnd)
            # En dry no se vuelve aqui: lo hace main() con entrar_formulario(),
            # que cubre tambien los caminos de halt y error.
            await _pausa(perfil.pausa(inicio, "cierre", objetivo,
                                     paginas=(bloques + saltadas)))
            res["notas"] = (f"{bloques} bloques x {FILAS_POR_BLOQUE} filas"
                            + (f"; {saltadas} paginas vacias saltadas"
                               if saltadas else "")
                            + (f"; {aviso_ficha}" if aviso_ficha else "")
                            + f"; {perf['nombre']} {time.time() - inicio:.1f}"
                              f"/{objetivo:.1f}s")
            return res
        except pf.Halt as exc:
            res["notas"] = f"halt: {exc}"
            traza.evento("extraer", "fallo", detalle=f"{id_} {exc}")
            return res
        except Exception as exc:  # noqa: BLE001 - un item nunca tumba la tanda
            res["notas"] = f"{type(exc).__name__}: {exc}"
            return res


def reanuda_desde(hechos: dict, fila: dict) -> int:
    """Paginas ya pegadas de ESTA direccion; 0 si el ledger es de otra.

    El id es posicional (D01..D0n): si el operador cambia una fila del CSV el
    id pasa a apuntar a otra direccion, y reanudar seria saltarse la pagina 1
    del edificio nuevo. Por eso se exige que la direccion del ledger coincida.
    """
    prev = hechos.get(fila.get("id"), {}) or {}
    if not es_resumable(prev):
        return 0
    if (normaliza_dir(prev.get("direccion_parte1")) !=
            normaliza_dir(fila.get("direccion_parte1")) or
            normaliza_dir(prev.get("direccion_parte2")) !=
            normaliza_dir(fila.get("direccion_parte2"))):
        print(f"  {fila.get('id')}: el ledger en_curso es de otra direccion "
              f"({prev.get('direccion_parte1')} {prev.get('direccion_parte2')}):"
              f" se empieza de cero", flush=True)
        return 0
    try:
        return max(0, int(prev.get("paginas_vistas") or 0))
    except (TypeError, ValueError):
        return 0


async def main(hwnd: int, solo_id: str | None, dry: bool = False,
               solo_ficha: bool = False) -> int:
    # Objetivo del modulo de foco: desde aqui, AnyDesk debe quedar delante
    # antes de cada inyeccion (medido: el foco oscila y las teclas de sistema
    # y el portapapeles dejan de llegar al remoto).
    enfocar.set_objetivo(hwnd)
    filas = lee_direcciones()
    if solo_id:
        filas = [f for f in filas if f.get("id") == solo_id]
    if not filas:
        print("sin filas que procesar")
        return 0
    hechos = ledger_leido()
    pendientes = [f for f in filas if not (hechos.get(f.get("id"), {}).get("estado") == "ok")]
    if not pendientes:
        print("todo ya procesado (B7)")
        return 0

    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        traza.evento("pin", "ok", detalle=f"hwnd {hwnd}")
        fallos_reencuadre = 0
        for f in pendientes:
            # Reanudacion validada por direccion (el id es posicional).
            desde = reanuda_desde(ledger_en_curso(), f)
            res = await procesa(f, hwnd, s, dry, desde_pagina=desde, solo_ficha=solo_ficha)
            res["hora_fin"] = time.strftime("%H:%M:%S")
            if not dry:
                ledger_escribe(res)
            traza.evento("registrar", "ok" if res["estado"] == "ok" else "fallo",
                         detalle=f"{res['id']} {res['estado']}")
            print(json.dumps(res, ensure_ascii=False), flush=True)
            # Punto unico de reencuadre: pase lo que pase con esta direccion
            # (ok, halt o error) la siguiente arranca en el formulario.
            # El Halt del guard de foco (AnyDesk no se pudo poner delante) NO
            # puede tumbar el lote ni contar como reencuadre fallido: el
            # reencuadre no respondio "no", sencillamente no pudo hacerse.
            # Se sigue con la siguiente, igual que hace autonomo.por_direccion.
            try:
                ok_reencuadre = await entrar_formulario(s, hwnd)
            except pf.Halt as exc:
                print(f"{res['id']}: reencuadre con Halt ({exc}); "
                      f"se sigue con la siguiente", flush=True)
                continue
            except Exception as exc:  # noqa: BLE001 - una direccion no tumba el lote
                # Fallo de entorno Win32 (PrintWindow, captura, foco): no es un
                # Halt del guard, pero tampoco puede matar el lote entero.
                print(f"{res['id']}: reencuadre fallo "
                      f"({type(exc).__name__}: {exc}); se sigue con la siguiente",
                      flush=True)
                continue
            if ok_reencuadre:
                fallos_reencuadre = 0
            else:
                fallos_reencuadre += 1
                print(f"{res['id']}: no se pudo volver al formulario "
                      f"({fallos_reencuadre}/2)", flush=True)
                # Dos seguidos = la pantalla no es ni el formulario ni el
                # listado: seguir solo gasta reintentos y ensucia el ledger
                # con B1 en cascada. Se corta el lote y se avisa.
                if fallos_reencuadre >= 2:
                    print("dos reencuadres seguidos fallidos: se corta el lote",
                          flush=True)
                    break
    return 0


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--dry"]
    solo = argv[2] if len(argv) > 2 else None
    sys.exit(asyncio.run(main(need_hwnd(argv), solo, dry="--dry" in sys.argv)))

