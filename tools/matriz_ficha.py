"""Modulo 2: la ficha del edificio (leerla y guardarla en el CSV).

El portapapeles del remoto se sincroniza con el local, asi que la ficha se
lee del portapapeles (texto exacto, sin OCR) y no de la pantalla. El CSV de
direcciones puede estar abierto en Excel: en ese caso la ficha no se pierde,
se apenda a datos/fichas_pendientes.csv con la direccion (el id es
posicional, asi que sin direccion no se sabe a que edificio pertenece).
"""

import csv
import hashlib
import os
import re
import time
from pathlib import Path

import csvio
import recepcion

RAIZ = Path(__file__).resolve().parent.parent
PENDIENTES = RAIZ / "datos" / "fichas_pendientes.csv"
IDS = RAIZ / "datos" / "ids.csv"
CAMPOS_IDS = ["id", "parte1", "parte2", "hash"]


def _hash(parte1, parte2) -> str:
    """Hash estable de la direccion (12 hex)."""
    base = f"{str(parte1 or '').strip()}|{str(parte2 or '').strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


def _siguiente_id(ids: list[dict]) -> str:
    nums = [int(i["id"][1:]) for i in ids
            if re.fullmatch(r"D\d+", i.get("id") or "")]
    return f"D{max(nums, default=0) + 1:02d}"


def lee_ids(ruta: Path = None) -> list[dict]:
    ruta = ruta or IDS
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return [f for f in csv.DictReader(fh, delimiter=";") if f.get("id")]


def asegura_ids(direcciones: Path = None, ids_ruta: Path = None) -> list[dict]:
    """Lee/crea el sidecar id->direccion. No toca direcciones.csv.

    Si una direccion no tiene hash en el sidecar, le asigna el siguiente Dnn.
    Si el sidecar no se puede escribir (Excel/bloqueo), sigue en memoria: la
    corrida actual usa esos ids y la siguiente los vuelve a generar igual.
    """
    direcciones = direcciones or (RAIZ / "datos" / "direcciones.csv")
    ids_ruta = ids_ruta or (direcciones.parent / "ids.csv")
    if not direcciones.exists():
        raise SystemExit(f"falta {direcciones}")
    with open(direcciones, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    ids = lee_ids(ids_ruta)
    por_hash = {i.get("hash"): i for i in ids if i.get("hash")}
    cambio = not ids_ruta.exists()
    for f in filas:
        p1 = (f.get("parte1") or "").strip()
        p2 = (f.get("parte2") or "").strip()
        if not p1 and not p2:
            continue
        h = _hash(p1, p2)
        if h in por_hash:
            continue
        nuevo = {"id": _siguiente_id(ids), "parte1": p1, "parte2": p2, "hash": h}
        ids.append(nuevo)
        por_hash[h] = nuevo
        cambio = True
    if cambio:
        try:
            csvio.write_atomic(ids_ruta, ids, CAMPOS_IDS, encoding="utf-8-sig",
                               delimiter=";")
        except PermissionError:
            # El sidecar no se pudo escribir; los ids calculados valen para
            # esta corrida. No se pierde la ficha.
            pass
    return ids


def lee_direcciones(ruta: Path = None) -> list[dict]:
    """Entrada del operador: direcciones.csv con parte1;parte2;ficha.

    Excel en espanol guarda con ';'. La columna ficha la llena el agente.
    El id es estable por hash de la direccion (datos/ids.csv), no por fila.
    """
    ruta = ruta or (RAIZ / "datos" / "direcciones.csv")
    if not ruta.exists():
        raise SystemExit(f"falta {ruta}")
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    ids = asegura_ids(direcciones=ruta, ids_ruta=ruta.parent / "ids.csv")
    por_hash = {i.get("hash"): i.get("id") for i in ids if i.get("hash")}
    salida = []
    for f in filas:
        p1 = (f.get("parte1") or "").strip()
        p2 = (f.get("parte2") or "").strip()
        if not p1 and not p2:
            continue
        salida.append({
            "id": por_hash.get(_hash(p1, p2), ""),
            "direccion_parte1": p1,
            "direccion_parte2": p2,
            "comuna": "BOG",
            "cuenta_matriz_esperada": "",
            "ficha": (f.get("ficha") or "").strip(),
        })
    return salida


def escribe_ficha(id_, ficha: str, ruta: Path = None) -> str:
    """Devuelve la ficha del edificio a la columna C (una celda multilinea).

    El CSV suele estar abierto en Excel y en Windows eso bloquea la escritura.
    La extraccion NO se tumba por eso: se reintenta y, si sigue bloqueado, la
    ficha queda en datos/fichas_pendientes.csv para volcar a mano.

    El id se resuelve por el sidecar (id -> hash) y la fila por hash, nunca por
    `int(id)-1`: reordenar o filtrar el CSV no desalinea la ficha.

    Devuelve "" si se escribio, o el motivo del bloqueo.
    """
    ruta = ruta or (RAIZ / "datos" / "direcciones.csv")
    if not ruta.exists() or not ficha:
        return ""
    ids = asegura_ids(direcciones=ruta, ids_ruta=ruta.parent / "ids.csv")
    actual = next((i for i in ids if i.get("id") == id_), None)
    if not actual or not actual.get("hash"):
        return f"id {id_} no esta en ids.csv: requiere revision"
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    n = next((i for i, f in enumerate(filas)
             if _hash(f.get("parte1"), f.get("parte2")) == actual["hash"]), None)
    if n is None:
        return f"direccion editada: {id_} no coincide: requiere revision"
    filas[n]["ficha"] = ficha
    # csvio escribe utf-8-sig (Excel en espanol reabre el CSV sin BOM como
    # ANSI y garabatea las tildes) y de forma atomica: un corte a mitad no
    # trunca el maestro. Si Excel tiene el archivo abierto, os.replace falla
    # con PermissionError y se reintenta sin tocar el original.
    for _ in range(3):
        try:
            csvio.escribe_direcciones(filas, ruta)
            return ""
        except PermissionError:
            time.sleep(0.4)
    # Sigue bloqueado: la ficha no se pierde. Se guarda CON la direccion a la
    # que pertenece: el id es posicional (D01..D0n) y si el operador cambia una
    # fila del CSV entre corridas, volcar por id pondria la ficha de un edificio
    # en la fila de otro.
    respaldo = ruta.parent / "fichas_pendientes.csv"
    try:
        with open(respaldo, "a", encoding="utf-8", newline="") as fh:
            csv.writer(fh, delimiter=";").writerow(
                [id_,
                 (filas[n].get("parte1") or "").strip(),
                 (filas[n].get("parte2") or "").strip(),
                 (ficha or "").replace("\r\n", " | ").replace("\n", " | ")])
    except OSError:
        pass
    return f"CSV bloqueado (abierto en Excel): la ficha quedo en {respaldo.name}"


def merge_fichas_pendientes() -> int:
    """Vuelca las fichas del respaldo (CSV bloqueado por Excel) al CSV.

    Upsert por id: gana la ultima. El respaldo se borra solo si el merge
    termino bien, para no perder fichas. Se llama al arrancar la corrida.

    El respaldo nuevo trae 4 campos (id; parte1; parte2; ficha): antes de
    volcarla se comprueba que la direccion siga siendo la misma que la de esa
    fila del CSV. Con el id posicional, un cambio de fila del operador pondria
    la ficha de un edificio en otro. Las de 2 campos (formato viejo) se vuelcan
    sin esa comprobacion porque no traen la direccion.
    """
    if not PENDIENTES.exists():
        return 0
    try:
        with open(PENDIENTES, encoding="utf-8-sig", newline="") as f:
            filas = [r for r in csv.reader(f, delimiter=";") if r and r[0].strip()]
    except (OSError, csv.Error, UnicodeDecodeError):
        return 0
    actuales = {f.get("id"): f for f in lee_direcciones()}
    recuperadas = 0
    fallidas = []
    for r in filas:
        if len(r) < 2:
            continue
        id_ = r[0].strip()
        if len(r) >= 4:
            cur = actuales.get(id_) or {}
            if (normaliza_dir(r[1]) != normaliza_dir(cur.get("direccion_parte1")) or
                    normaliza_dir(r[2]) != normaliza_dir(cur.get("direccion_parte2"))):
                print(f"  respaldo {id_}: la direccion cambio "
                      f"({r[1]} {r[2]}); se descarta la ficha", flush=True)
                continue
            ficha = r[3] if len(r) > 3 else ""
        else:
            ficha = r[1]
        if escribe_ficha(id_, ficha) == "":
            recuperadas += 1
        else:
            fallidas.append(r)
    # El respaldo se borra SOLO si se recuperaron todas. Si alguna fallo, se
    # reescribe con las fallidas: escribe_ficha ya las re-appendo al mismo
    # archivo, asi que reescribir evita que se dupliquen en cada corrida.
    try:
        if fallidas:
            with open(PENDIENTES, "w", encoding="utf-8", newline="") as f:
                csv.writer(f, delimiter=";").writerows(fallidas)
        else:
            PENDIENTES.unlink(missing_ok=True)
    except OSError:
        pass
    return recuperadas


def normaliza_dir(t) -> str:
    """Texto de direccion comparable: mayusculas y solo letras/digitos."""
    return re.sub(r"[^A-Z0-9]+", "", str(t or "").upper())


