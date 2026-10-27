"""Trace leader + semaforo del sistema 5250.

Dos funciones en un solo archivo:

1. TRAZA (trace leader). Cada paso de cada herramienta deja un evento en
   `datos/traza.jsonl` (append-only, legible por maquina) y un resumen en
   `datos/traza.md` (legible por humano). Sabes en todo momento en que etapa
   esta el sistema, que resultado dio y que se decidio despues.

2. SEMAFORO (policia de transito). Un mapa declarativo resultado -> accion.
   Ninguna herramienta decide sola: reporta el resultado y el semaforo dice
   cual es el siguiente paso. Agregar un .py nuevo = agregar sus reglas aqui.

    from traza import evento, accion

    evento("estado", "formulario", detalle="conf 0.90")
    siguiente = accion("estado", "formulario")   # -> "buscar"

CLI:
    python tools/traza.py            # ultimos 20 eventos + punto actual
    python tools/traza.py --json     # el punto actual en JSON
    python tools/traza.py --jev      # resumen compacto para el prompt de Jev
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JSONL = RAIZ / "datos" / "traza.jsonl"
MD = RAIZ / "datos" / "traza.md"

# Etapas del pipeline, en orden. El "punto" del sistema es la ultima reportada.
ETAPAS = ("entorno", "pin", "estado", "buscar", "extraer", "volver",
          "pagina", "reconectar", "registrar", "cierre")

# Resultados que puede reportar cada etapa (contrato, no adorno).
RESULTADOS = {
    "entorno": ("ok", "fallo"),
    "pin": ("ok", "fallo"),
    "estado": ("formulario", "ficha", "cuenta_matriz", "fin_libro",
               "desconectado", "sin_coincidencia", "error", "desconocido"),
    "buscar": ("ok", "sin_coincidencia", "fallo"),
    "extraer": ("ok", "fallo"),
    "volver": ("ok", "fallo"),
    "pagina": ("cuenta_matriz", "fin_libro", "desconocido"),
    "reconectar": ("ok", "fallo"),
    "registrar": ("ok", "fallo"),
    "cierre": ("ok", "fallo"),
}

# SEMAFORO: (etapa, resultado) -> accion. Falta = DETENER (fallar cerrado).
POLICIA = {
    ("entorno", "ok"): "pin",
    ("pin", "ok"): "estado",
    ("estado", "formulario"): "buscar",
    ("estado", "ficha"): "unidades",
    ("estado", "cuenta_matriz"): "extraer",
    ("estado", "fin_libro"): "cierre",
    ("estado", "sin_coincidencia"): "siguiente",
    ("estado", "desconectado"): "reconectar",
    ("buscar", "ok"): "extraer",
    ("buscar", "sin_coincidencia"): "siguiente",
    ("extraer", "ok"): "volver",
    ("volver", "ok"): "pagina",
    ("pagina", "cuenta_matriz"): "extraer",
    ("pagina", "fin_libro"): "cierre",
    ("reconectar", "ok"): "estado",
    ("cierre", "ok"): "siguiente",
}
DETENER = "detener"
SIGUIENTE = "siguiente"


def accion(etapa: str, resultado: str) -> str:
    """Siguiente paso segun el semaforo. Desconocido = detener (no improvisar)."""
    if etapa not in RESULTADOS:
        return DETENER
    if resultado not in RESULTADOS[etapa]:
        return DETENER
    return POLICIA.get((etapa, resultado), DETENER)


class Traza:
    """Bitacora append-only de una corrida."""

    def __init__(self, jsonl: Path = JSONL, md: Path = MD, run: str | None = None):
        self.jsonl = jsonl
        self.md = md
        self.run = run or time.strftime("%Y%m%d-%H%M%S")
        self.punto: dict | None = None

    def evento(self, etapa: str, resultado: str, detalle: str = "",
               datos: dict | None = None, accion_siguiente: str | None = None) -> dict:
        """Registra un evento y mueve el puntero. Devuelve el evento."""
        if etapa not in RESULTADOS:
            raise ValueError(f"etapa desconocida: {etapa}")
        if resultado not in RESULTADOS[etapa]:
            raise ValueError(f"resultado '{resultado}' no vale para {etapa}")
        siguiente = accion_siguiente or accion(etapa, resultado)
        ev = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "run": self.run,
            "etapa": etapa,
            "resultado": resultado,
            "accion": siguiente,
            "detalle": detalle,
        }
        if datos:
            ev["datos"] = datos
        self.jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(self.jsonl, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self.punto = ev
        self._md(ev)
        return ev

    def _md(self, ev: dict) -> None:
        """Linea humana. Una fila por evento, sin reescribir el historial."""
        nuevo = not self.md.exists()
        with open(self.md, "a", encoding="utf-8") as fh:
            if nuevo:
                fh.write("# Traza del sistema 5250\n\n"
                         "| hora | corrida | etapa | resultado | siguiente | detalle |\n"
                         "|---|---|---|---|---|---|\n")
            fh.write(f"| {ev['ts']} | {ev['run']} | {ev['etapa']} | "
                     f"{ev['resultado']} | {ev['accion']} | {ev['detalle']} |\n")

    def leer(self, n: int | None = None) -> list[dict]:
        """Eventos del archivo (ultimos n si se pide)."""
        if not self.jsonl.exists():
            return []
        eventos = []
        with open(self.jsonl, encoding="utf-8") as fh:
            for linea in fh:
                linea = linea.strip()
                if linea:
                    try:
                        eventos.append(json.loads(linea))
                    except json.JSONDecodeError:
                        continue  # linea a medias por un corte: se ignora
        return eventos[-n:] if n else eventos

    def resumen(self, n: int = 20) -> str:
        """Texto compacto para el prompt de Jev o para el operador."""
        eventos = self.leer(n)
        if not eventos:
            return "sin eventos de traza"
        partes = []
        for ev in eventos:
            linea = f"{ev['etapa']}={ev['resultado']} -> {ev['accion']}"
            if ev.get("detalle"):
                linea += f" ({ev['detalle']})"
            partes.append(linea)
        ultimo = eventos[-1]
        partes.append(f"PUNTO ACTUAL: etapa {ultimo['etapa']}, "
                      f"resultado {ultimo['resultado']}, "
                      f"siguiente {ultimo['accion']}")
        return "\n".join(partes)


_DEFECTO: Traza | None = None


def _t() -> Traza:
    global _DEFECTO
    if _DEFECTO is None:
        _DEFECTO = Traza()
    return _DEFECTO


def evento(etapa: str, resultado: str, detalle: str = "",
           datos: dict | None = None) -> dict:
    """Atajo sobre la traza por defecto (una corrida = un proceso)."""
    return _t().evento(etapa, resultado, detalle=detalle, datos=datos)


def resumen(n: int = 20) -> str:
    return _t().resumen(n)


def main(argv: list[str]) -> int:
    t = Traza()
    if "--json" in argv:
        print(json.dumps(t.punto, ensure_ascii=False))
        return 0
    if "--jev" in argv:
        print(t.resumen(12))
        return 0
    print(t.resumen(20))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
