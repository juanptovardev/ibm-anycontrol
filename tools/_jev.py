"""Cliente Jev directo (curl, sin MCP) para clasificar estado en una sola llamada.

Reutiliza la clave viva del CLI de opencode. Devuelve la opcion ganadora y sus
probabilidades; nunca lanza por un fallo de red (el bucle decide que hacer).
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

AUTH = Path(os.path.expandvars(r"%USERPROFILE%")) / ".local" / "share" / "opencode" / "auth.json"
URL = "https://opencode.ai/inference/systemone/v1/systemone"
MODEL = "jev-1.13-free"


def _key() -> str:
    try:
        data = json.loads(AUTH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    for name in ("opencode-go", "opencode"):
        entry = data.get(name) or {}
        if entry.get("key"):
            return entry["key"]
    return ""


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
    key = _key()
    if not key:
        return {"ok": False, "error": "sin clave en auth.json"}
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
