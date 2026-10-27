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
# El bloque del operador son 15 filas (7 abajo + 14 de alto).
FILAS_POR_BLOQUE = 15
MAX_PAGINAS = 40


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


async def verifica_texto(hwnd: int) -> tuple[bool, str]:
    """B2: el texto quedo en Calle y NO en Nombre."""
    img, _vp, det = rowdet.detect(hwnd)
    if len(det) < 3:
        return False, "no se detectaron filas del formulario"
    tinta_calle = pf.ink(img, det[1])
    tinta_nombre = pf.ink(img, det[0])
    if tinta_nombre > INK_MIN:
        return False, f"el texto quedo en Nombre (tinta {tinta_nombre})"
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

    for intento in range(REINTENTOS + 1):
        res["reintentos"] = intento
        try:
            # B0: si AnyDesk corto la sesion, se reconecta antes de leer nada.
            if not reconecta_si_hace_falta(hwnd):
                res["motivo"] = "B0 sin conexion AnyDesk (dialogo de licencia)"
                return res

            # B1: verificar pantalla antes de teclear.
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

            # B3/B4: esperar el resultado de la busqueda.
            st = await espera_estado(hwnd, {"cuenta_matriz", "sin_coincidencia",
                                            "error", "fin_libro"})
            if st["estado"] == "sin_coincidencia":
                traza.evento("buscar", "sin_coincidencia", detalle=id_)
                res.update(estado="no_encontrado", notas="sin coincidencia")
                return res
            if st["estado"] != "cuenta_matriz":
                traza.evento("buscar", "fallo", detalle=f"{id_} estado {st['estado']}")
                res["notas"] = f"B3 estado {st['estado']}"
                return res
            traza.evento("buscar", "ok", detalle=f"{id_} {parte1} {parte2}")

            # Bloque por bloque hasta el aviso de fin de archivo.
            bloques = 0
            for n in range(1, MAX_PAGINAS + 1):
                if not reconecta_si_hace_falta(hwnd):
                    raise pf.Halt(f"bloque {n}: sin conexion AnyDesk")
                await ciclo.extrae(s, hwnd, dry)
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

            res["paginas_vistas"] = bloques
            res["filas_copiadas"] = bloques * FILAS_POR_BLOQUE
            res["estado"] = "ok"
            res["notas"] = f"{bloques} bloques x {FILAS_POR_BLOQUE} filas"
            res["evidencia"] = str(pf.shot(hwnd, f"{id_}-fin") or "")
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
    filas = lee_datos()
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
    return 0


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--dry"]
    solo = argv[2] if len(argv) > 2 else None
    sys.exit(asyncio.run(main(need_hwnd(argv), solo, dry="--dry" in sys.argv)))

