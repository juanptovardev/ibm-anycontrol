"""Anade direcciones al final de la lista de produccion.

El operador pega direcciones nuevas (en un .txt, un CSV o el portapapeles) y
este script las separa con las MISMAS reglas de tools/separar.py y las anade al
final de datos/direcciones.csv, sin tocar las que ya estan (ni sus fichas).

Por que no se usa `separar.py` para esto: ese script SOBRESCRIBE el destino.
Apuntar al CSV de produccion con el separador habria tirado las 121
direcciones anteriores (solo se salvo por el bloqueo de Excel).

Formato de salida: BOM + CRLF + `;` + cabecera `parte1;parte2;ficha`
(el mismo contrato que lee tools/loop.py).

    python tools/anexar_direcciones.py lista.txt
    python tools/anexar_direcciones.py hoja.csv --columna=1
    python tools/anexar_direcciones.py --portapapeles
    python tools/anexar_direcciones.py lista.txt --dry
    python tools/anexar_direcciones.py --portapapeles --reemplazar
"""
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import separar as sep  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "direcciones.csv"
CABECERA = ["parte1", "parte2", "ficha"]


def clave(parte1, parte2) -> str:
    """Clave de deduplicacion: sin espacios, sin guiones, en mayusculas."""
    return (f"{parte1 or ''}{parte2 or ''}").upper().replace(" ", "").replace("-", "")


def lee(ruta: Path = RUTA) -> list[dict]:
    """Filas del CSV de produccion (ficha multilinea incluida)."""
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def escribe(filas: list[dict], ruta: Path = RUTA) -> Path:
    """Escribe atomico (temporal + replace) con el contrato del repo."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CABECERA, delimiter=";",
                           quoting=csv.QUOTE_MINIMAL, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    tmp.replace(ruta)
    return ruta


def anexar(lineas: list[str], ruta: Path = RUTA, dry: bool = False,
           reemplazar: bool = False) -> int:
    """Separa `lineas` y las anade al final. Devuelve cuantas se anadieron.

    Con reemplazar=True la lista nueva SUSTITUYE a la anterior (se hace copia
    de seguridad antes). El dedup pasa a ser solo dentro del lote nuevo: lo
    que hay en el archivo viejo se descarta entero.
    """
    actuales = [] if reemplazar else lee(ruta)
    ya = {clave(f.get("parte1"), f.get("parte2")) for f in actuales}
    nuevas, repetidas, problemas = [], [], []
    for n, linea in enumerate(lineas, 1):
        if not sep.normaliza(linea):
            continue
        r = sep.parse(linea)
        if r["estado"] != "parsed":
            problemas.append((n, str(linea).strip(), r["motivo"]))
            continue
        k = clave(r["parte1"], r["parte2"])
        if k in ya:
            repetidas.append((n, str(linea).strip()))
            continue
        ya.add(k)
        nuevas.append({"parte1": r["parte1"], "parte2": r["parte2"], "ficha": ""})
    print(f"en el CSV: {len(actuales)} | nuevas: {len(nuevas)} | "
          f"repetidas: {len(repetidas)} | sin separar: {len(problemas)}")
    for n, orig in repetidas[:5]:
        print(f"  repetida linea {n}: {orig!r}")
    for n, orig, mot in problemas[:5]:
        print(f"  NO separada linea {n}: {orig!r} -> {mot}")
    if not nuevas:
        print("nada que anadir")
        return 0
    if dry:
        print("DRY: no se escribio nada")
        return len(nuevas)
    # Copia de seguridad antes de tocar la lista del operador.
    if ruta.exists():
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        copia = ruta.parent / f"direcciones_backup_{marca}.csv"
        shutil.copy2(ruta, copia)
        print(f"respaldo: {copia.name}")
    escribe(actuales + nuevas, ruta)
    if reemplazar:
        print(f"sustituidas {len(nuevas)} direcciones por las nuevas "
              f"(antes {len(lee(ruta))} lineas, ahora {len(nuevas)})")
    else:
        print(f"anadidas {len(nuevas)} direcciones "
              f"(total {len(actuales) + len(nuevas)})")
    return len(nuevas)


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    dry = "--dry" in argv
    portapapeles = "--portapapeles" in argv
    reemplazar = "--reemplazar" in argv
    columna = 0
    for a in argv[1:]:
        if a.startswith("--columna="):
            columna = int(a.split("=", 1)[1])
    try:
        if portapapeles:
            lineas = sep.lee_portapapeles()
        elif args:
            lineas = sep.lee_archivo(args[0], columna)
        else:
            print("ERROR: falta el archivo de direcciones (o usa --portapapeles)",
                  file=sys.stderr)
            return 2
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    n = anexar(lineas, dry=dry, reemplazar=reemplazar)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
