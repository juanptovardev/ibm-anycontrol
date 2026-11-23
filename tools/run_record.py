"""Reconciliacion pre-corrida: evita reanudar sobre una hoja que cambio.

El ledger dice cuantas paginas se pegaron de cada direccion, pero no puede
saber si alguien edito la hoja de Google por fuera. Antes de reanudar se
compara la ultima fila que el ledger da por pegada con la ultima fila que se
lee de la hoja:

  - coincide  -> se reanuda.
  - no coincide -> se aborta: estado `requiere_revision`, no se pega nada.
  - no se puede leer -> se exige confirmacion manual; queda registrada en
    `datos/run.json` (`reconciliacion: manual`, `confirmado_por`).

`datos/run.json` tambien deja la huella de la corrida (`run_id`, `inicio`,
`sheet`, `ultima_fila_ledger`, `filas_esperadas`) para el dossier.

La lectura de la hoja es inyectable: tests pasan un `lector` falso y no tocan
Tesseract. Para una corrida real, `MATRIZ_RECONCILIA_LECTOR` puede apuntar a un
archivo de texto con la ultima fila leida; si no hay lector, se pide confirmacion
por consola. En un proceso sin consola (stdin DEVNULL) la confirmacion falla
cerrada: se aborta.
"""
import json
import os
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUN = RAIZ / "datos" / "run.json"
SHEET = "TEMP BORRADOR"


def _norm(texto) -> str:
    """Normaliza para comparar: mayusculas, sin puntos/comas, espacios simples."""
    limpio = str(texto or "").replace(".", "").replace(",", "")
    return " ".join(limpio.upper().split())


def lee(ruta: Path = RUN) -> dict:
    """run.json como dict; {} si no existe o esta roto."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _escribe(datos: dict, ruta: Path = RUN) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, ruta)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def ultima_fila_ok(hechos: dict) -> str:
    """Texto (parte1 parte2) de la ULTIMA direccion 'ok' del ledger.

    `hechos` es un dict y conserva el orden de insercion del ledger, asi que
    la ultima 'ok' recorrida es la ultima escrita. Si no hay ninguna, "".
    """
    ultima = ""
    for fila in (hechos or {}).values():
        if (fila.get("estado") or "").strip() == "ok":
            ultima = (f"{fila.get('direccion_parte1', '')} "
                      f"{fila.get('direccion_parte2', '')}").strip()
    return ultima


def filas_esperadas(hechos: dict) -> int:
    """Filas que el ledger dice haber pegado (suma de filas_copiadas en 'ok')."""
    total = 0
    for fila in (hechos or {}).values():
        if (fila.get("estado") or "").strip() != "ok":
            continue
        try:
            total += int(fila.get("filas_copiadas") or 0)
        except (TypeError, ValueError):
            pass
    return total


def _es_resumable(fila: dict) -> bool:
    """Misma regla que loop.es_resumable, sin importar pywin32 aqui."""
    estado = (fila.get("estado") or "").strip()
    if estado in ("ok", "no_encontrado", "pegado_dudoso", "requiere_revision",
                  "pegando"):
        return False
    try:
        paginas = int(fila.get("paginas_vistas") or 0)
    except (TypeError, ValueError):
        paginas = 0
    return estado == "en_curso" or (estado == "error" and paginas > 0)


def prepara(reanudables: list, hechos: dict, ruta: Path = RUN,
            ahora: str | None = None) -> dict:
    """Escribe run.json al inicio de la corrida.

    `reanudables` son las filas que el ledger da por empezadas; si no hay
    ninguna, la reconciliacion no aplica (corrida nueva).
    """
    datos = {
        "run_id": uuid.uuid4().hex,
        "inicio": ahora or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sheet": os.environ.get("HOJA_NOMBRE") or SHEET,
        "ultima_fila_ledger": ultima_fila_ok(hechos),
        "filas_esperadas": filas_esperadas(hechos),
        "reanudables": len(reanudables),
        "reconciliacion": "pendiente" if reanudables else "no_aplica",
    }
    _escribe(datos, ruta)
    return datos


def lector_hoja() -> str | None:
    """Ultima fila leida de la hoja, o None si no hay lector configurado.

    No hay API de Google Sheets ni un OCR de hoja fiable en este repo: el
    operador puede dejar la lectura en un archivo y apuntar aqui con
    `MATRIZ_RECONCILIA_LECTOR`. Sin archivo, None (se pide confirmacion).
    """
    ruta = os.environ.get("MATRIZ_RECONCILIA_LECTOR")
    if not ruta:
        return None
    try:
        texto = Path(ruta).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return texto or None


def confirmador_hoja() -> bool:
    """Confirmacion manual del operador; falla cerrado si no hay consola."""
    if os.environ.get("MATRIZ_RECONCILIA_CONFIRMA") == "1":
        return True
    try:
        resp = input("No se pudo leer la hoja. La ultima fila del ledger sigue "
                     "siendo la correcta? [s/N] ")
    except (EOFError, OSError):
        return False
    return resp.strip().lower() in ("s", "si", "sÃ­", "y", "yes")


def reconcilia(esperado: str, leido: str | None,
               confirmador=None) -> tuple[str, str]:
    """Decide si se puede reanudar.

    Devuelve `(estado, nota)`:
      - `("ok", "")` si la hoja coincide.
      - `("manual", nota)` si no se pudo leer y el operador confirmo.
      - `("abortar", nota)` si no coincide o no hay confirmacion.
    """
    if leido is None:
        confirmador = confirmador or confirmador_hoja
        if not confirmador():
            return ("abortar", "no se pudo leer la hoja y el operador no confirmo")
        return ("manual", "hoja ilegible: el operador confirmo la ultima fila del ledger")
    if _norm(leido) != _norm(esperado):
        return ("abortar",
                f"hoja '{leido}' no coincide con ledger '{esperado}'")
    return ("ok", "")


def gate(filas: list, hechos: dict, dry: bool = False, ruta: Path = RUN,
         lector=None, confirmador=None, escribir=None) -> bool:
    """Comprueba la reconciliacion antes de pegar. True = se puede seguir.

    Solo aplica si hay direcciones reanudables. `escribir` es el callback del
    ledger (para no importar `loop.py` y crear un ciclo). Si aborta, deja
    `requiere_revision` en la primera reanudable (salvo dry) y devuelve False.
    """
    reanudables = [f for f in filas
                   if _es_resumable((hechos or {}).get(f.get("id"), {}) or {})]
    if not reanudables:
        return True

    datos = lee(ruta)
    if not datos:
        datos = prepara(reanudables, hechos, ruta)
    esperado = datos.get("ultima_fila_ledger") or ""
    leido = lector() if lector else lector_hoja()
    estado, nota = reconcilia(esperado, leido,
                              confirmador or confirmador_hoja)
    datos.update({"reconciliacion": estado, "nota": nota,
                  "leido": leido if leido is not None else "",
                  "reanudables": len(reanudables)})
    _escribe(datos, ruta)

    if estado in ("ok", "manual"):
        return True

    res = {"id": reanudables[0].get("id"), "estado": "requiere_revision",
           "notas": f"reconciliacion: {nota}", "paginas_vistas": 0,
           "filas_copiadas": 0, "hora_fin": time.strftime("%H:%M:%S")}
    if not dry and escribir:
        escribir(res)
    print(json.dumps(res, ensure_ascii=False), flush=True)
    print("reconciliacion fallo: no se pega; revisar hoja", flush=True)
    return False

