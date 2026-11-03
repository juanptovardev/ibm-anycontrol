"""Deja el ledger en cero: solo la cabecera.

Uso cuando el operador limpia la hoja de Google Sheets: si el ledger dijera
'ok', el agente se saltaria esas direcciones y no volveria a pegarlas.

Antes de tocar nada guarda una copia con fecha (datos/ledger_backup_*.csv).
El formato se respeta: separador ';', BOM y CRLF (asi lo abre Excel en
espanol por columnas). La escritura es atomica: si algo falla, el ledger
original queda intacto.

    python tools/reset_ledger.py            # resetea
    python tools/reset_ledger.py --dry      # solo dice que haria
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
LEDGER = DATOS / "ledger.csv"

CABECERA = [
    "id", "direccion_parte1", "direccion_parte2", "comuna",
    "cuenta_matriz_esperada", "estado", "paginas_vistas", "filas_copiadas",
    "hora_inicio", "hora_fin", "evidencia", "notas", "reintentos",
]


def _cabecera(ruta: Path) -> list[str]:
    """La cabecera que ya tiene el archivo (o la de por defecto)."""
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            primera = next(csv.reader(fh, delimiter=";"), None)
    except (OSError, csv.Error):
        return list(CABECERA)
    if primera and "id" in [c.strip().lower() for c in primera]:
        return [c.strip() for c in primera]
    return list(CABECERA)


def _filas(ruta: Path) -> int:
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh, delimiter=";"))


def escribe(filas_cab: list[str], ruta: Path = LEDGER) -> None:
    """Escribe solo la cabecera, atomico y respetando el formato."""
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            w.writerow(filas_cab)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, ruta)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    if not LEDGER.exists():
        print(f"falta {LEDGER}", file=sys.stderr)
        return 1

    cab = _cabecera(LEDGER)
    antes = _filas(LEDGER)
    print(f"ledger: {LEDGER}")
    print(f"cabecera: {';'.join(cab)}")
    print(f"filas antes: {antes}")

    if dry:
        print("DRY: no se toca nada")
        return 0

    respaldo = DATOS / f"ledger_backup_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    try:
        shutil.copy2(LEDGER, respaldo)
    except OSError as exc:
        print(f"no se pudo guardar el respaldo: {exc}", file=sys.stderr)
        return 1
    print(f"respaldo: {respaldo}")

    try:
        escribe(cab, LEDGER)
    except PermissionError:
        print("el ledger esta abierto en Excel: cierralo y reintenta",
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"no se pudo escribir: {exc}", file=sys.stderr)
        return 1

    print(f"filas despues: {_filas(LEDGER)} (las direcciones vuelven a empezar)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
