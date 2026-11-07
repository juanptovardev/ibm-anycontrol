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

La escritura es ATOMICA: se escribe en un temporal y se reemplaza con
`os.replace`. Si el write se corta a mitad (disco lleno, Ctrl+C), la lista de
direcciones del operador no queda corrupta.

Uso:
    python tools/regenerar_direcciones.py            # limpia la columna ficha
    python tools/regenerar_direcciones.py --listar    # solo muestra

Ojo: este archivo limpia SOLO la columna 3 del CSV de direcciones. NO toca
`datos/fichas_pendientes.csv` (el respaldo donde caen las fichas cuando Excel
tiene el CSV abierto): `autonomo.corre` hace merge de ese respaldo al empezar,
asi que si quieres un arranque de verdad limpio, borra tambien el respaldo.
"""
import csv
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "direcciones.csv"
CAMPOS = ["parte1", "parte2", "ficha"]


def _ruta(ruta: Path | None) -> Path:
    """Resuelve la ruta en el momento de la llamada.

    NO se usa `ruta: Path = RUTA` como default: el default se evalua al
    importar el modulo, asi que `patch.object(reg, "RUTA", ...)` en los tests
    no surte efecto y se acabaria leyendo o escribiendo el CSV real del
    proyecto (perdida silenciosa de los datos del operador).
    """
    return RUTA if ruta is None else ruta


def leer(ruta: Path | None = None):
    ruta = _ruta(ruta)
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def cabecera(ruta: Path | None = None) -> list[str]:
    """Columnas de la primera fila del CSV."""
    ruta = _ruta(ruta)
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        for fila in csv.reader(fh, delimiter=";"):
            return [c.strip() for c in fila]
    return []


def escribir(filas, ruta: Path | None = None):
    """Escribe atomico: temporal + os.replace (atomico en Windows)."""
    ruta = _ruta(ruta)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPOS, delimiter=";",
                               quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for f in filas:
                w.writerow({c: f.get(c, "") or "" for c in CAMPOS})
        os.replace(tmp, ruta)
    except BaseException:
        # Si algo falla, el temporal no se queda tirado y el original queda
        # intacto: el `replace` nunca llego a ocurrir.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def main(argv):
    listar = "--listar" in argv
    if not RUTA.exists():
        # Sin archivo de entrada no se inventa uno: un CSV fantasma con solo
        # cabecera seria leido por `lee_direcciones` como "0 direcciones".
        print(f"falta {RUTA}", file=sys.stderr)
        return 1
    cols = cabecera(RUTA)
    normalizadas = {c.strip().lower() for c in cols}
    if not {"parte1", "parte2"} <= normalizadas:
        # Sin este guard, un CSV con otra cabecera (p. ej. importado de Excel)
        # daria f.get("parte1") == None -> "" y se escribirian filas VACIAS:
        # el operador perderia su lista sin ningun aviso.
        print(f"ERROR: cabecera inesperada: {cols}. Se esperaba parte1;parte2;ficha",
              file=sys.stderr)
        return 1
    filas = leer(RUTA)
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
        escribir(limpias, RUTA)
    except PermissionError:
        # Cubre tanto el open del temporal como el os.replace: con Excel
        # abierto, Windows deniega el reemplazo (WinError 5).
        print("ERROR: el archivo esta abierto en Excel. Cierralo y vuelve a intentarlo.",
              file=sys.stderr)
        return 2
    print(f"regenerado con {len(limpias)} filas (BOM + CRLF + ';')")
    for f in limpias:
        print(f"  {f['parte1']};{f['parte2']};")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
