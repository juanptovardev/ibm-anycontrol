"""Registra en el ledger las paginas que YA estan pegadas en la hoja.

Medido 28/10: las corridas de 16:04 y 16:06 pegaron un bloque cada una
(D02 y D03) pero el item termino en 'error' y el ledger se quedo con
paginas=0. Sin esta correccion una re-corrida pegaria las mismas 15 filas
OTRA VEZ en la hoja.

Uso: python tools/registrar_pegado.py D02=1 D03=1
"""
import csv
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LEDGER = RAIZ / "datos" / "ledger.csv"
CAMPOS = ["id", "direccion_parte1", "direccion_parte2", "comuna",
          "cuenta_matriz_esperada", "estado", "paginas_vistas",
          "filas_copiadas", "hora_inicio", "hora_fin", "evidencia", "notas",
          "reintentos"]
FILAS_POR_BLOQUE = 15


def main(argv):
    if len(argv) < 2:
        print("uso: registrar_pegado.py D02=1 D03=2")
        return 2
    filas = []
    for arg in argv[1:]:
        if "=" not in arg:
            print(f"argumento invalido: {arg}")
            return 2
        id_, n = arg.split("=", 1)
        filas.append((id_.strip(), int(n)))
    with open(LEDGER, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        for id_, n in filas:
            w.writerow({
                "id": id_, "estado": "en_curso", "paginas_vistas": n,
                "filas_copiadas": n * FILAS_POR_BLOQUE,
                "hora_fin": time.strftime("%H:%M:%S"),
                "notas": (f"registro manual: {n} pagina(s) ya pegadas en la hoja"
                          f" (corridas 16:04 y 16:06 del 28/10); reanudar en la {n + 1}"),
            })
            print(f"registrado {id_}: en_curso, {n} paginas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
