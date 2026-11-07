"""Credenciales del 5250, FUERA del repo.

Orden de lectura:
  1. variables de entorno MATRIZ_5250_USUARIO / MATRIZ_5250_CLAVE
  2. %USERPROFILE%\\.matriz\\creds.json  -> {"usuario": "...", "clave": "..."}

El fichero nunca se commitea (esta fuera del arbol del repo) y la clave nunca
se escribe en el ledger ni en la traza.
"""
import json
import os
from pathlib import Path

ENV_USUARIO = "MATRIZ_5250_USUARIO"
ENV_CLAVE = "MATRIZ_5250_CLAVE"


def ruta() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / ".matriz" / "creds.json"


def carga() -> dict | None:
    """Devuelve {"usuario":..., "clave":...} o None si no hay."""
    u = os.environ.get(ENV_USUARIO)
    p = os.environ.get(ENV_CLAVE)
    if u and p:
        return {"usuario": u, "clave": p}
    f = ruta()
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if d.get("usuario") and d.get("clave"):
        return {"usuario": str(d["usuario"]), "clave": str(d["clave"])}
    return None


def guarda(usuario: str, clave: str) -> Path:
    f = ruta()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        json.dumps({"usuario": usuario, "clave": clave}, ensure_ascii=False),
        encoding="utf-8",
    )
    # En Windows os.chmod solo alterna el bit de solo lectura: la proteccion
    # real del fichero viene del perfil de usuario (ACL de %USERPROFILE%), no
    # de un chmod. Por eso no se finge que chmod(600) proteja nada aqui.
    return f


if __name__ == "__main__":
    c = carga()
    if not c:
        print(f"sin credenciales (ni {ENV_USUARIO}/{ENV_CLAVE} ni {ruta()})")
    else:
        print(f"usuario={c['usuario']} clave={len(c['clave'])} caracteres")
