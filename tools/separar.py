"""Separador de direcciones: una direccion completa -> parte1 + parte2.

Portado de las reglas del scaffold `separador-direcciones-opencode` (parser.ts y
docs/REGLAS_DE_SEPARACION.md), adaptado al formato de este repo (CSV con `;`).

Reglas
------
La direccion se escribe entera, por ejemplo `CR 6SUR 22C-19`, y se parte en:

    parte1 = primer eje vial completo   -> "CR 6SUR"
    parte2 = segundo eje / generador    -> "22C-19"

- El primer eje empieza por `CL`, `CR` o `TR`.
- Tras el prefijo, el primer token es el numero del eje, con letra opcional
  (81, 6, 2A), y puede traer complementos PEGADOS: `6SUR`, `81BISSUR`,
  `2AESTESUR`.
- Complementos reconocidos: BIS, ESTE, SUR, NORTE, OESTE, ESTESUR, SURESTE,
  SURORIENTE, NOROCCIDENTE. Tambien valen separados por espacios
  (`CL 81 BIS SUR 8C-6` -> `CL 81BISSUR`).
- El primer numero que NO sea complemento abre la parte2 (se conserva tal cual,
  con guiones y letras).
- Si algo no encaja NO se inventa: la fila queda `unparsed` o `ambiguous` con su
  motivo y no se escribe en el CSV.

Uso
---
    python tools/separar.py                  lee el portapapeles y escribe datos/direcciones.csv
    python tools/separar.py lista.txt        lee una direccion por linea
    python tools/separar.py hoja.csv         lee la primera columna de un CSV
    python tools/separar.py --dry            solo muestra el resultado, no escribe
    python tools/separar.py --salida otra.csv

Las direcciones que no se pueden separar se listan con su motivo para
arreglarlas a mano; las validas se escriben con el contrato de siempre
(BOM + CRLF + `;` + cabecera `parte1;parte2;ficha`).
"""
import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "direcciones.csv"
CABECERA = ["parte1", "parte2", "ficha"]

PREFIJOS = ("CL", "CR", "TR", "DG", "TV")
# DG (diagonal) y TV (transversal) salieron en la lista real de 121 del
# operador (DG 82C 75A-21, TV 2 114A-25). El resto de vias (KR, AK, AV, AUT)
# se anaden cuando aparezcan en una lista de verdad, no por si acaso.
COMPLEMENTOS = tuple(sorted(
    ("BIS", "ESTE", "SUR", "NORTE", "OESTE", "ESTESUR", "SURESTE",
     "SURORIENTE", "NOROCCIDENTE"),
    key=len, reverse=True))          # por longitud: SURESTE antes que SUR+ESTE

RE_PREFIJO = re.compile(r"^(%s)\s+(.+)$" % "|".join(PREFIJOS))
RE_INICIO = re.compile(r"^(\d+)(.*)$")


def _complementos_de(texto):
    """Consume complementos concatenados. None si algo no encaja."""
    comps = []
    while texto:
        c = next((c for c in COMPLEMENTOS if texto.startswith(c)), None)
        if c is None:
            return None
        comps.append(c)
        texto = texto[len(c):]
    return comps


def normaliza(texto) -> str:
    """Mayusculas y espacios simples."""
    return re.sub(r"\s+", " ", str(texto or "").strip().upper())


def parse(texto) -> dict:
    """Separa una direccion. Devuelve estado, parte1, parte2 y motivo.

    estado: "parsed" | "unparsed" (no se puede) | "ambiguous" (dudosa).
    Nunca lanza: ante la duda devuelve el motivo.
    """
    original = normaliza(texto)
    if not original:
        return {"estado": "unparsed", "parte1": None, "parte2": None,
                "motivo": "vacia"}

    m = RE_PREFIJO.match(original)
    if not m:
        return {"estado": "unparsed", "parte1": None, "parte2": None,
                "motivo": "prefijo_no_soportado (se espera %s)"
                          % "/".join(PREFIJOS)}
    prefijo, resto = m.group(1), m.group(2)
    tokens = resto.split(" ")

    m1 = RE_INICIO.match(tokens[0])
    if not m1:
        return {"estado": "unparsed", "parte1": None, "parte2": None,
                "motivo": "falta el numero del primer eje"}
    digitos, pegado = m1.group(1), m1.group(2)

    # La letra del eje (3C, 131C, 2A) se distingue del complemento por lo que
    # sigue: primero se intenta leer TODO el resto como complementos (6SUR,
    # 81BISSUR); si no encaja, la primera letra es del eje y el resto se vuelve
    # a intentar como complementos (2AESTESUR). El regex del scaffold
    # (^(\d+[A-Z]?)(.*)$) se comia la S de 6SUR y dejaba "UR" como sufijo
    # desconocido: por eso las direcciones con complemento pegado salian
    # ambiguas.
    letra, complementos = "", _complementos_de(pegado)
    if complementos is None:
        if pegado[:1].isalpha() and _complementos_de(pegado[1:]) is not None:
            letra, complementos = pegado[:1], _complementos_de(pegado[1:])
        else:
            return {"estado": "ambiguous", "parte1": None, "parte2": None,
                    "motivo": f"sufijo pegado no reconocido: {pegado}"}
    numero = f"{digitos}{letra}"

    i = 1
    while i < len(tokens) and tokens[i] in COMPLEMENTOS:
        complementos.append(tokens[i])
        i += 1

    if i >= len(tokens):
        return {"estado": "unparsed", "parte1": None, "parte2": None,
                "motivo": "falta el segundo componente"}

    segundo = " ".join(tokens[i:])
    if not segundo[0].isdigit():
        return {"estado": "ambiguous", "parte1": None, "parte2": None,
                "motivo": f"el segundo componente no empieza por numero: {segundo}"}

    return {"estado": "parsed",
            "parte1": f"{prefijo} {numero}{''.join(complementos)}",
            "parte2": segundo,
            "motivo": ""}


def separa(lineas) -> tuple[list, list]:
    """Separa una lista de direcciones. Devuelve (filas_ok, problemas)."""
    ok, mal = [], []
    for n, linea in enumerate(lineas, 1):
        if not normaliza(linea):
            continue                      # linea en blanco: no es un error
        r = parse(linea)
        if r["estado"] == "parsed":
            ok.append({"parte1": r["parte1"], "parte2": r["parte2"], "ficha": ""})
        else:
            mal.append({"linea": n, "original": str(linea).strip(),
                        "estado": r["estado"], "motivo": r["motivo"]})
    return ok, mal


def escribe(filas, ruta: Path = None) -> Path:
    """Escribe el CSV con el contrato: BOM + CRLF + `;` + cabecera fija."""
    ruta = Path(ruta or SALIDA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CABECERA, delimiter=";",
                           quoting=csv.QUOTE_MINIMAL, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    tmp.replace(ruta)
    return ruta


def lee_archivo(ruta: Path, columna: int = 0) -> list:
    """Lee direcciones de un .txt (una por linea) o de un .csv (una columna)."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(ruta)
    if ruta.suffix.lower() in (".csv", ".tsv"):
        sep = ";" if ruta.suffix.lower() == ".csv" else "\t"
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            filas = list(csv.reader(fh, delimiter=sep))
        if not filas:
            return []
        filas = [f for f in filas if len(f) > columna]
        # La cabecera se reconoce porque NO empieza por un prefijo de via.
        # No vale mirar si tiene digitos: "parte1" lleva el 1 y se colaba como
        # dato, y entonces su "parte2" hacia saltar el guard de abajo.
        primera = normaliza(filas[0][columna]) if filas else ""
        con_cabecera = bool(primera) and primera.split(" ")[0] not in PREFIJOS
        cuerpo = filas[1:] if con_cabecera else filas
        # "Ya separado" se decide por los DATOS, no por la cabecera: el CSV del
        # agente se llama siempre parte1;parte2;ficha aunque la columna 1 traiga
        # la direccion entera, que es justo lo que pega el operador desde Excel.
        if any(len(f) > 1 and f[1].strip() for f in cuerpo):
            raise ValueError("el archivo ya tiene la columna 2 con datos: "
                             "no hace falta separarlo")
        return [f[columna] for f in cuerpo]
    return ruta.read_text(encoding="utf-8-sig").splitlines()


def lee_portapapeles() -> list:
    """Direcciones copiadas al portapapeles (una por linea / una por celda)."""
    import recepcion
    return recepcion._portapapeles().splitlines()


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    dry = "--dry" in argv
    salida = SALIDA
    columna = 0
    for a in argv[1:]:
        if a.startswith("--salida="):
            salida = Path(a.split("=", 1)[1])
        elif a.startswith("--columna="):
            columna = int(a.split("=", 1)[1])

    try:
        if args:
            lineas = lee_archivo(args[0], columna)
            origen = args[0]
        else:
            lineas = lee_portapapeles()
            origen = "portapapeles"
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    ok, mal = separa(lineas)
    print(f"origen: {origen} | lineas leidas: {len(lineas)} | "
          f"separadas: {len(ok)} | con problema: {len(mal)}")
    for f in ok[:5]:
        print(f"  {f['parte1']:22s} | {f['parte2']}")
    if len(ok) > 5:
        print(f"  ... y {len(ok) - 5} mas")
    if mal:
        print("\nNO SE PUDIERON SEPARAR (no se escriben, arreglalas a mano):")
        for p in mal:
            print(f"  linea {p['linea']}: {p['original']!r} -> "
                  f"{p['estado']}: {p['motivo']}")

    if dry:
        print("\nDRY: no se escribio nada")
        return 0 if not mal else 1
    if not ok:
        print("\nNada que escribir.", file=sys.stderr)
        return 1
    ruta = escribe(ok, salida)
    print(f"\nescrito: {ruta} ({len(ok)} direcciones)")
    return 0 if not mal else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
