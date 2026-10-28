"""Regenera datos/direcciones.csv respetando EXACTAMENTE su formato.

Por que existe: al editar el CSV a mano (o con Excel) se mezclan los saltos de
linea y se pierde el BOM, y luego `escribe_ficha` lo reescribe de otra forma.
Aqui el archivo se escribe con el mismo modulo `csv` y los mismos parametros
que usa el codigo de produccion:

    codificacion : utf-8-sig  (BOM, Excel en espanol lo reconoce)
    saltos       : CRLF       (csv.writer usa \r\n con newline="")
    separador    : ";"        (Excel en espanol)
    cabecera     : parte1;parte2;ficha
    ficha        : celda C, entre comillas solo si hace falta (QUOTE_MINIMAL)

Uso:
    python tools/regenerar_direcciones.py            # limpia la columna ficha
    python tools/regenerar_direcciones.py --listar    # solo muestra
"""
import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "direcciones.csv"
CAMPOS = ["parte1", "parte2", "ficha"]


def leer():
    if not RUTA.exists():
        return []
    with open(RUTA, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def escribir(filas):
    with open(RUTA, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, delimiter=";",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for f in filas:
            w.writerow({c: f.get(c, "") or "" for c in CAMPOS})


def main(argv):
    listar = "--listar" in argv
    filas = leer()
    if listar:
        for f in filas:
            print(f"{f.get('parte1', '')} | {f.get('parte2', '')} | "
                  f"ficha={'(vacia)' if not (f.get('ficha') or '').strip() else 'SI'}")
        return 0
    limpias = []
    for f in filas:
        limpias.append({"parte1": (f.get("parte1") or "").strip(),
                        "parte2": (f.get("parte2") or "").strip(),
                        "ficha": ""})
    try:
        escribir(limpias)
    except PermissionError:
        print("ERROR: el archivo esta abierto en Excel. Cierralo y vuelve a intentarlo.",
              file=sys.stderr)
        return 2
    print(f"regenerado con {len(limpias)} filas (BOM + CRLF + ';')")
    for f in limpias:
        print(f"  {f['parte1']};{f['parte2']};")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
