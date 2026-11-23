"""Cliente Jev directo (curl, sin MCP) para clasificar estado en una sola llamada.

Jev es OPCIONAL y esta APAGADO por defecto (`MATRIZ_JEV=0`). Solo se usa si el
operador lo habilita con `MATRIZ_JEV=1` y una clave dedicada. Nunca reutiliza la
credencial personal del CLI de opencode. Devuelve la opcion ganadora y sus
probabilidades; nunca lanza por un fallo de red (el bucle decide que hacer).
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "jev.json"
URL = "https://opencode.ai/inference/systemone/v1/systemone"
MODEL = "jev-1.13-free"
ENABLED = False

# config/jev.json del repo (interno de empresa) manda sobre los defaults.
try:
    _cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    URL = _cfg.get("url") or URL
    MODEL = _cfg.get("model") or MODEL
    ENABLED = bool(_cfg.get("enabled"))
except (OSError, ValueError):
    pass


def habilitado() -> bool:
    """True solo si el operador habilito Jev explicitamente.

    `MATRIZ_JEV` manda sobre config/jev.json: si esta definido en 0/false/off,
    no se enciende aunque el JSON diga `enabled: true`.
    """
    raw = os.environ.get("MATRIZ_JEV")
    if raw is not None:
        return raw.strip().lower() not in ("", "0", "false", "off", "no")
    return ENABLED


def _key() -> str:
    # 1) Variable de entorno dedicada (recomendada en produccion).
    env = os.environ.get("MATRIZ_JEV_KEY", "").strip()
    if env:
        return env
    # 2) config/jev.json local, nunca versionado, con clave dedicada.
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        return (data.get("key") or "").strip()
    except (OSError, ValueError):
        return ""


def disponible() -> bool:
    """Jev solo esta disponible si esta habilitado Y hay clave dedicada."""
    return habilitado() and bool(_key())


def ask(state: str, instructions: str, options: list[str], model: str = MODEL,
        criteria: dict | None = None) -> dict:
    """Pregunta `choice` a Jev. Devuelve {ok, choice, confianza, probabilities}.

    `confianza` es la probabilidad de la opcion elegida (probabilities[choice]),
    que es la metrica fiable: el campo `confidence` de la API no lo es.
    `confidence` se conserva tal cual para diagnostico.

    `criteria` es el mapa opcion -> descripcion que ve el modelo. Por defecto es
    {opcion: opcion}; para preguntas con significado (que pantalla es, que
    opcion de menu) conviene pasar la descripcion real de cada opcion.
    """
    if not disponible():
        return {"ok": False, "error": "jev deshabilitado o sin clave dedicada"}
    key = _key()
    if not key:
        return {"ok": False, "error": "sin clave configurada"}
    crit = dict(criteria) if criteria else {opt: opt for opt in options}
    payload = {
        "model": model,
        "state": state,
        "questions": {"estado": {
            "type": "choice",
            "instructions": instructions,
            "criteria": crit,
        }},
    }
    cfg = f'header = "Authorization: Bearer {key}"\n'
    fd, cfg_path = tempfile.mkstemp(suffix=".curlcfg")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(cfg)
        proc = subprocess.run(
            ["curl.exe", "-s", "-K", cfg_path, "-X", "POST", URL,
             "-H", "Content-Type: application/json", "--data-binary", "@-",
             "-w", "\n__HTTP__%{http_code}", "--max-time", "20"],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            os.unlink(cfg_path)
        except OSError:
            pass

    out = proc.stdout.decode("utf-8", "replace")
    body, _, code = out.rpartition("__HTTP__")
    try:
        status = int(code.strip())
    except ValueError:
        return {"ok": False, "error": "respuesta sin codigo HTTP"}
    if status != 200:
        return {"ok": False, "http_status": status, "error": body.strip()[:200]}
    try:
        answer = json.loads(body)["answers"]["estado"]
    except (ValueError, KeyError, TypeError):
        return {"ok": False, "http_status": status, "error": "respuesta sin answers.estado"}
    probs = answer.get("probabilities") or {}
    choice = answer.get("choice")
    conf_api = answer.get("confidence")
    # El campo 'confidence' de la API NO es la probabilidad de la opcion elegida.
    # Medido el 28/10: para la misma pregunta devolvio confidence=0 con
    # probabilities {vacia: 0.5, con_datos: 0.5}. La metrica fiable es
    # probabilities[choice]; 'confidence' solo se usa si no hay probabilities.
    if isinstance(probs, dict) and choice in probs:
        confianza = float(probs.get(choice) or 0.0)
    else:
        confianza = float(conf_api or 0.0)
    return {
        "ok": True,
        "choice": choice,
        "confidence": conf_api,
        "confianza": confianza,
        "probabilities": probs,
    }
