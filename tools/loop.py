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
import sys
import time
from pathlib import Path

import ciclo
import pagina
import preflight_auto as pf
import nav_prefill
import native_shot
import recepcion
import rows as rowdet
import traza
import vigia
from _mcp import connect, need_hwnd
from estado import captura, clasificar

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos" / "datos.csv"
LEDGER = RAIZ / "datos" / "ledger.csv"
# Contrato congelado del repo (ver datos/ledger.csv y PROMPT_OBRERO_T-IBM-01.md).
CAMPOS_LEDGER = ["id", "direccion_parte1", "direccion_parte2", "comuna",
                  "cuenta_matriz_esperada", "estado", "paginas_vistas",
                  "filas_copiadas", "hora_inicio", "hora_fin", "evidencia",
                  "notas", "reintentos"]
REINTENTOS = 1
INK_MIN = pf.INK_MIN
# Indices de fila del formulario CONSULTA EDIFICIO (rows.detect devuelve 8).
NOMBRE = 0
CALLE = 1
CASA = 2
# El bloque del operador son 15 filas (7 abajo + 14 de alto).
FILAS_POR_BLOQUE = 15
MAX_PAGINAS = 40
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



def lee_direcciones(ruta: Path = None) -> list[dict]:
    """Entrada del operador: direcciones.csv con parte1;parte2;ficha.

    Excel en espanol guarda con ';'. La columna ficha la llena el agente.
    El id se deriva del numero de fila: D01, D02...
    """
    ruta = ruta or (RAIZ / "datos" / "direcciones.csv")
    if not ruta.exists():
        raise SystemExit(f"falta {ruta}")
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    salida = []
    for i, f in enumerate(filas, 1):
        p1 = (f.get("parte1") or "").strip()
        p2 = (f.get("parte2") or "").strip()
        if not p1 and not p2:
            continue
        salida.append({
            "id": f"D{i:02d}",
            "direccion_parte1": p1,
            "direccion_parte2": p2,
            "comuna": "BOG",
            "cuenta_matriz_esperada": "",
            "ficha": (f.get("ficha") or "").strip(),
        })
    return salida


def escribe_ficha(id_, ficha: str, ruta: Path = None) -> None:
    """Devuelve la ficha del edificio a la columna C (una celda multilinea)."""
    ruta = ruta or (RAIZ / "datos" / "direcciones.csv")
    if not ruta.exists() or not ficha:
        return
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    try:
        n = int(id_[1:]) - 1
    except (ValueError, IndexError):
        return
    if not 0 <= n < len(filas):
        return
    filas[n]["ficha"] = ficha
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["parte1", "parte2", "ficha"],
                           delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for f in filas:
            w.writerow({"parte1": f.get("parte1") or "",
                        "parte2": f.get("parte2") or "",
                        "ficha": f.get("ficha") or ""})


async def volver_formulario(s, hwnd: int, intentos: int = 3) -> bool:
    """Sale del listado/ficha hasta quedar de nuevo en el formulario.

    En CONSULTA UNIDADES la barra solo tiene F12=Anterior y al pasar de la
    ultima pagina el 5250 queda con el teclado inhibido ('A X II'), estado en
    el que F3 se ignora. Primero se limpia con Escape y se sale con F12
    (listado -> ficha -> formulario); F3 queda como ultimo recurso.
    """
    for intento in range(intentos):
        img, _ = captura(hwnd)
        if clasificar(img, usar_jev=False).get("estado") == "formulario":
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


def ledger_leido(ruta: Path = LEDGER) -> dict:
    """id -> ULTIMA fila del ledger (bitacora append-only)."""
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    return {f["id"]: f for f in filas}


def ledger_escribe(fila: dict, ruta: Path = LEDGER) -> None:
    """Anade (o reemplaza) una fila del ledger. Append-only por item."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with open(ruta, "a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CAMPOS_LEDGER)
        if nuevo:
            writer.writeheader()
        writer.writerow({c: fila.get(c, "") for c in CAMPOS_LEDGER})


async def espera_estado(hwnd: int, objetivos: set[str], intentos: int = 8,
                        delay: float = 0.7) -> dict:
    """Espera a que la pantalla llegue a uno de los estados. B3/B4."""
    for _ in range(intentos):
        img, _vp = captura(hwnd)
        st = clasificar(img, usar_jev=False)
        if st["estado"] in objetivos:
            return st
        await asyncio.sleep(delay)
    img, _vp = captura(hwnd)
    return clasificar(img, usar_jev=True)


async def buscar(s, hwnd: int, det: list, parte1: str, parte2: str) -> None:
    """Macro de busqueda validada: clic, flechas, step1, +, step2, +, F10."""
    calle = det[CALLE]
    # En este emulador no existe borrado: 'delete' no borra y 'home' salta al
    # primer campo. La unica forma de vaciar un campo es sobrescribirlo con
    # espacios. Se limpian Nombre y Calle antes de escribir para que no quede
    # basura que luego desvie la busqueda.
    for idx in (NOMBRE, CALLE):
        fila = det[idx]
        await pf.step(s, f"limpiar_{idx}", "click_point",
                      {"x": fila["field_x"] + 2, "y": fila["cy"]})
        await pf.step(s, f"blancos_{idx}", "write_to_anydesk",
                      {"command": " " * 24})
        await asyncio.sleep(0.2)
    # UN solo clic pegado al borde izquierdo del subrayado (= celda 1). Dos clics
    # al mismo punto se leen como DOBLE CLIC, seleccionan el campo entero y dejan
    # el teclado inhibido (bug medido el 27/10). No reintroducir el segundo clic.
    await pf.step(s, "clic_celda1", "click_point",
                  {"x": calle["field_x"] + 2, "y": calle["cy"]})
    await asyncio.sleep(0.2)
    await pf.step(s, "derecha", "press_keys", {"keys": ["right"]})
    await pf.step(s, "izquierda", "press_keys", {"keys": ["left"]})
    await pf.step(s, "step1", "write_to_anydesk", {"command": parte1})
    await pf.step(s, "plus1", "press_keys", {"keys": ["add"]})
    await pf.step(s, "step2", "write_to_anydesk", {"command": parte2})
    await pf.step(s, "plus2", "press_keys", {"keys": ["add"]})
    # Prellenado del bloque, validado en vivo el 27/10: tras el "+" el cursor
    # cae en Comunidad (BOG) y su "+" hace el ultimo salto a Division (TVC).
    # Sin esto F10 busca con Comunidad/Division vacias y no encuentra nada.
    await pf.step(s, "bog", "write_to_anydesk", {"command": "BOG"})
    await pf.step(s, "plus3", "press_keys", {"keys": ["add"]})
    await pf.step(s, "tvc", "write_to_anydesk", {"command": "TVC"})


async def verifica_texto(hwnd: int) -> tuple[bool, str]:
    """B2: el texto quedo en Calle.

    No se exige Nombre vacio: el formulario conserva texto de busquedas
    anteriores y este emulador no borra (delete no borra, home salta al primer
    campo). Si Calle tiene tinta, la escritura llego donde tenia que llegar.
    """
    img, _vp, det = rowdet.detect(hwnd)
    if len(det) < 3:
        return False, "no se detectaron filas del formulario"
    tinta_calle = pf.ink(img, det[CALLE])
    if tinta_calle < INK_MIN:
        return False, f"Calle vacio (tinta {tinta_calle})"
    return True, f"Calle ok (tinta {tinta_calle})"


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


async def entrar_formulario(s, hwnd: int) -> bool:
    """Desde el Menu Principal SCABLE al formulario.

    Secuencia del operador (validada en vivo): 1, ENTER, ESC, 1, ENTER, 1, ENTER.
    Solo navega cuando la pantalla no se reconoce (menu principal). Si ya hay un
    estado claro (formulario, listado, ficha) no toca nada.
    """
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


async def procesa(fila: dict, hwnd: int, s, dry: bool = False) -> dict:
    """Un item completo. Nunca lanza: devuelve el resultado para el ledger."""
    inicio = time.time()
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
    for intento in range(REINTENTOS + 1):
        res["reintentos"] = intento
        try:
            # B0: si AnyDesk corto la sesion, se reconecta antes de leer nada.
            if not reconecta_si_hace_falta(hwnd):
                res["motivo"] = "B0 sin conexion AnyDesk (dialogo de licencia)"
                return res

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
            if st["estado"] != "formulario":
                res["motivo"] = f"B1 pantalla {st['estado']}"
                return res

            _img, _vp, det = rowdet.detect(hwnd)
            if len(det) < 3:
                res["motivo"] = "B1 sin filas del formulario"
                return res

            await buscar(s, hwnd, det, parte1, parte2)

            # B2: verificar antes de F10.
            ok, detalle = await verifica_texto(hwnd)
            if not ok:
                res["motivo"] = f"B2 {detalle}"
                traza.evento("buscar", "fallo", detalle=f"{id_} {detalle}")
                if intento < REINTENTOS:
                    await pf.step(s, "esc", "press_keys", {"keys": ["escape"]})
                    continue
                return res

            await pf.step(s, "f10", "press_keys", {"keys": ["f10"]})
            await asyncio.sleep(0.8)

            # B3/B4: F10 lleva a la FICHA del edificio, no al listado. El listado
            # de unidades (con la columna Suscript) entra con Shift+F4 = F16.
            # Medido en vivo: sin este paso el bucle se quedaba en 'formulario'.
            st = await espera_estado(hwnd, {"ficha", "cuenta_matriz",
                                            "sin_coincidencia", "error",
                                            "fin_libro"})
            traza.evento("estado", st["estado"] or "desconocido",
                         detalle=f"{id_} tras F10 conf {st.get('confianza')}")
            if st["estado"] == "ficha":
                await pf.step(s, "shift_f4", "press_keys",
                              {"keys": ["shift", "f4"]})
                await asyncio.sleep(0.9)
                st = await espera_estado(hwnd, {"cuenta_matriz",
                                                "sin_coincidencia", "error",
                                                "fin_libro"})
            if st["estado"] == "sin_coincidencia":
                traza.evento("buscar", "sin_coincidencia", detalle=id_)
                res.update(estado="no_encontrado", notas="sin coincidencia")
                return res
            if st["estado"] != "cuenta_matriz":
                traza.evento("buscar", "fallo", detalle=f"{id_} estado {st['estado']}")
                res["notas"] = f"B3 estado {st['estado']}"
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
                escribe_ficha(id_, ficha or "")

            # Bloque por bloque hasta el aviso de fin de archivo.
            bloques = 0
            saltadas = 0
            # La captura de la pagina recien paginada se reutiliza: no se paga
            # otra vez el OCR de una pantalla que ya se leyo (pagina.avanza la
            # deja en pagina.ULTIMA). Se limpia al empezar cada direccion.
            pagina.ULTIMA = None
            for n in range(1, MAX_PAGINAS + 1):
                if obedece() == "detener":
                    res["notas"] = f"detenido por el panel en el bloque {n}"
                    return res
                if not reconecta_si_hace_falta(hwnd):
                    raise pf.Halt(f"bloque {n}: sin conexion AnyDesk")
                # Las 7 bajadas solo en el PRIMER bloque que se extrae: si las
                # primeras paginas venian sin suscriptores y se saltaron, el
                # cursor del 5250 sigue sin moverse de su punto.
                extra = await ciclo.extrae(s, hwnd, dry, bajar=(bloques == 0),
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
                    stp = await pagina.avanza(s, hwnd)
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
                traza.evento("extraer", "ok", detalle=f"{id_} bloque {n}")
                if dry:
                    break
                await pagina.volver(s, hwnd)
                traza.evento("volver", "ok", detalle=f"{id_} bloque {n}")
                stp = await pagina.avanza(s, hwnd)
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
            res["notas"] = (f"{bloques} bloques x {FILAS_POR_BLOQUE} filas"
                            + (f"; {saltadas} paginas vacias saltadas"
                               if saltadas else ""))
            img_fin, _vp_fin = captura(hwnd)
            res["evidencia"] = str(native_shot.save(img_fin, f"{id_}-fin"))
            res["ficha"] = ficha or ""
            if not dry:
                await volver_formulario(s, hwnd)
            # En dry no se vuelve aqui: lo hace main() con entrar_formulario(),
            # que cubre tambien los caminos de halt y error.
            return res
        except pf.Halt as exc:
            res["notas"] = f"halt: {exc}"
            traza.evento("extraer", "fallo", detalle=f"{id_} {exc}")
            return res
        except Exception as exc:  # noqa: BLE001 - un item nunca tumba la tanda
            res["notas"] = f"{type(exc).__name__}: {exc}"
            return res
    res["hora_fin"] = time.strftime("%H:%M:%S")
    return res


async def main(hwnd: int, solo_id: str | None, dry: bool = False) -> int:
    filas = lee_direcciones()
    if solo_id:
        filas = [f for f in filas if f.get("id") == solo_id]
    if not filas:
        print("sin filas que procesar")
        return 0
    hechos = ledger_leido()
    pendientes = [f for f in filas if not (hechos.get(f.get("id"), {}).get("estado") == "ok")]
    if not pendientes:
        print("todo ya processed (B7)")
        return 0

    async with connect() as s:
        await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
        await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
        traza.evento("pin", "ok", detalle=f"hwnd {hwnd}")
        for f in pendientes:
            res = await procesa(f, hwnd, s, dry)
            res["hora_fin"] = time.strftime("%H:%M:%S")
            if not dry:
                ledger_escribe(res)
            traza.evento("registrar", "ok" if res["estado"] == "ok" else "fallo",
                         detalle=f"{res['id']} {res['estado']}")
            print(json.dumps(res, ensure_ascii=False), flush=True)
            # Punto unico de reencuadre: pase lo que pase con esta direccion
            # (ok, halt o error) la siguiente arranca en el formulario.
            if not await entrar_formulario(s, hwnd):
                print(f"{res['id']}: no se pudo volver al formulario", flush=True)
    return 0


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--dry"]
    solo = argv[2] if len(argv) > 2 else None
    sys.exit(asyncio.run(main(need_hwnd(argv), solo, dry="--dry" in sys.argv)))

