"""Modulo 2: la ficha del edificio (leerla y guardarla en el CSV).

El portapapeles del remoto se sincroniza con el local, asi que la ficha se
lee del portapapeles (texto exacto, sin OCR) y no de la pantalla. El CSV de
direcciones puede estar abierto en Excel: en ese caso la ficha no se pierde,
se apenda a datos/fichas_pendientes.csv con la direccion (el id es
posicional, asi que sin direccion no se sabe a que edificio pertenece).
"""

import csv
import os
import re
import time
from pathlib import Path

import recepcion

RAIZ = Path(__file__).resolve().parent.parent
PENDIENTES = RAIZ / "datos" / "fichas_pendientes.csv"

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


def escribe_ficha(id_, ficha: str, ruta: Path = None) -> str:
    """Devuelve la ficha del edificio a la columna C (una celda multilinea).

    El CSV suele estar abierto en Excel y en Windows eso bloquea la escritura.
    La extraccion NO se tumba por eso: se reintenta y, si sigue bloqueado, la
    ficha queda en datos/fichas_pendientes.csv para volcar a mano.

    Devuelve "" si se escribio, o el motivo del bloqueo.
    """
    ruta = ruta or (RAIZ / "datos" / "direcciones.csv")
    if not ruta.exists() or not ficha:
        return ""
    try:
        n = int(id_[1:]) - 1
    except (ValueError, IndexError):
        return ""
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    if not 0 <= n < len(filas):
        return ""
    filas[n]["ficha"] = ficha
    # utf-8-sig: Excel en espanol reabre el CSV sin BOM como ANSI y garabatea
    # las tildes de la ficha (el dato viene del portapapeles del 5250).
    for _ in range(3):
        try:
            with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["parte1", "parte2", "ficha"],
                                   delimiter=";", quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                for f in filas:
                    w.writerow({"parte1": f.get("parte1") or "",
                                "parte2": f.get("parte2") or "",
                                "ficha": f.get("ficha") or ""})
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


