"""Escritura atomica de CSV (contrato de direcciones.csv).

Contrato del archivo: 3 columnas (`parte1;parte2;ficha`), UTF-8 con BOM,
separador `;` y saltos CRLF. Excel en espanol reabre sin BOM como ANSI y
garabatea las tildes; el BOM evita eso.

La escritura usa un temporal en el mismo directorio, flush + fsync y
`os.replace` (atomico en Windows). Antes de reemplazar deja una copia `.bak`.
Si el destino esta abierto en Excel, `os.replace` lanza PermissionError y el
archivo original queda intacto: el llamador decide reintentar o derivar la
ficha a `fichas_pendientes.csv`.
"""

import csv
import io
import os
import tempfile
from pathlib import Path

CABECERA = ["parte1", "parte2", "ficha"]
SEP = ";"


def _texto(valor) -> str:
    # Las lineas del archivo son CRLF; los saltos internos de la ficha se
    # conservan como \n (el CSV los entrecomilla y Excel los muestra igual).
    s = str(valor or "")
    return s.replace("\r\n", "\n").replace("\r", "\n")


def write_atomic(path, rows, fieldnames=None, encoding="utf-8-sig",
                 delimiter=SEP) -> None:
    """Escribe `rows` (dicts) en `path` de forma atomica.

    - Temporal unico en el mismo directorio + flush/fsync + `os.replace`.
    - Copia `.bak` del archivo anterior antes de reemplazar.
    - Si el destino esta bloqueado, `os.replace` lanza PermissionError y el
      original queda intacto; el temporal se limpia.
    """
    path = Path(path)
    fieldnames = list(fieldnames or CABECERA)
    path.parent.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=delimiter,
                       lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
                       extrasaction="ignore", restval="")
    w.writeheader()
    for fila in rows:
        w.writerow({k: _texto(fila.get(k)) for k in fieldnames})
    data = buf.getvalue().encode(encoding)

    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.",
                                    suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists():
            bak = path.with_name(path.name + ".bak")
            bak.write_bytes(path.read_bytes())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def escribe_direcciones(filas, ruta) -> None:
    """Atajo con el contrato exacto de `datos/direcciones.csv`."""
    write_atomic(ruta, filas, CABECERA, encoding="utf-8-sig", delimiter=SEP)
