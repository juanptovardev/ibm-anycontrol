"""Recepcion de direcciones: lee datos/direcciones.csv y guarda la ficha.

El bloque de la ficha se copia en el 5250 (Ctrl+C) y AnyDesk lo sincroniza
al portapapeles LOCAL, de ahi se lee y se escribe en la columna C.

Uso:
    python tools/recepcion.py                 # lista las direcciones
    python tools/recepcion.py --clipboard     # muestra el portapapeles local
    python tools/recepcion.py --poner "CR 17B" "175-77" --clipboard
    python tools/recepcion.py --poner "CR 17B" "175-77" --texto "Cuenta: ..."

Columnas del CSV: parte1, parte2, ficha.
Acepta separador ',' o ';' al leer; siempre escribe con ',' y UTF-8 sin BOM.
"""
import csv
import ctypes
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV = REPO / "datos" / "direcciones.csv"
CABECERA = ["parte1", "parte2", "ficha"]
# Excel en espanol separa con ";": se escribe con ";" y se lee con "," o ";".
SEP = ";"
CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.GetClipboardData.restype = ctypes.c_void_p
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]


def _portapapeles() -> str:
    """Lee el portapapeles de Windows (sincronizado por AnyDesk)."""
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(ctypes.c_void_p(handle))
    finally:
        user32.CloseClipboard()


def normaliza(texto: str) -> str:
    """Quita blancos sobrantes y lineas vacias de los extremos."""
    lineas = [l.rstrip() for l in texto.replace("\r\n", "\n").split("\n")]
    while lineas and not lineas[0].strip():
        lineas.pop(0)
    while lineas and not lineas[-1].strip():
        lineas.pop()
    return "\n".join(lineas)


def bloque_de(texto: str) -> str:
    """Saca las 3 lineas de la cabecera (Cuenta / Edificio / Direccion).

    Sirve tanto si el portapapeles trae solo el bloque seleccionado como si
    trae la pantalla entera (Ctrl+C sin seleccion copia todo el 5250).
    Corta el 'Com:/Div:' sobrante de la primera linea.
    """
    lineas = [l.rstrip() for l in texto.replace("\r\n", "\n").split("\n")]
    for i, linea in enumerate(lineas):
        if linea.strip().upper().startswith("CUENTA"):
            resto = [l.strip() for l in lineas[i + 1:] if l.strip()]
            if len(resto) < 2:
                return ""
            primera = linea.strip()
            corte = primera.upper().find("COM:")
            if corte < 0:
                corte = primera.upper().find("DIV:")
            if corte > 0:
                primera = primera[:corte].rstrip()
            return "\n".join([primera, resto[0], resto[1]])
    return ""


def _separador(texto: str) -> str:
    primera = texto.splitlines()[0] if texto else ""
    return ";" if primera.count(";") > primera.count(",") else ","


def lee(ruta: Path = CSV) -> list[dict]:
    """Devuelve las filas como dicts con las claves parte1, parte2, ficha."""
    if not ruta.exists():
        return []
    texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    if not texto.strip():
        return []
    filas = list(csv.reader(io.StringIO(texto), delimiter=_separador(texto)))
    if not filas:
        return []
    out = []
    for crudo in filas[1:]:
        if not any(c.strip() for c in crudo):
            continue
        campos = (crudo + ["", "", ""])[:3]
        out.append({
            "parte1": campos[0].strip(),
            "parte2": campos[1].strip(),
            "ficha": normaliza(campos[2]),
        })
    return out


def escribe(filas, ruta: Path = CSV) -> None:
    """Escribe el CSV canonico: comas, UTF-8 sin BOM, saltos CRLF."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=SEP, lineterminator="\r\n")
    w.writerow(CABECERA)
    for f in filas:
        w.writerow([f["parte1"], f["parte2"], f["ficha"].replace("\n", "\r\n")])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(buf.getvalue().encode("utf-8"))


def pon(filas, parte1: str, parte2: str, ficha: str):
    """Pone la ficha en la fila que coincide; la crea si no existe."""
    for f in filas:
        if f["parte1"] == parte1 and f["parte2"] == parte2:
            f["ficha"] = normaliza(ficha)
            return filas, True
    filas.append({"parte1": parte1, "parte2": parte2, "ficha": normaliza(ficha)})
    return filas, False


def main(argv):
    if "--clipboard" in argv and "--poner" not in argv:
        print(_portapapeles().replace("\r\n", "\n"))
        return 0
    filas = lee()
    if "--poner" in argv:
        i = argv.index("--poner")
        parte1, parte2 = argv[i + 1], argv[i + 2]
        if "--clipboard" in argv:
            texto = bloque_de(_portapapeles())
            if not texto:
                print("el portapapeles no trae una cabecera 'Cuenta:'", file=sys.stderr)
                return 1
        elif "--texto" in argv:
            texto = argv[argv.index("--texto") + 1]
        else:
            print("falta --clipboard o --texto", file=sys.stderr)
            return 2
        if not texto.strip():
            print("texto vacio", file=sys.stderr)
            return 1
        filas, existia = pon(filas, parte1, parte2, texto)
        escribe(filas)
        print(f"{'actualizada' if existia else 'creada'}: {parte1} / {parte2}")
        print(f"ficha ({len(normaliza(texto).splitlines())} lineas):")
        print(normaliza(texto))
        return 0
    if not filas:
        print("sin direcciones en", CSV)
        return 0
    print(f"{'parte1':<12} {'parte2':<10} ficha")
    for f in filas:
        marca = f"{len(f['ficha'].splitlines())} lineas" if f["ficha"] else "-"
        print(f"{f['parte1']:<12} {f['parte2']:<10} {marca}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
