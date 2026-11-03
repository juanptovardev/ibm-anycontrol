"""Perfiles de velocidad del agente 5250.

El operador trabaja a ~18,3 s por direccion (medido: 4.500 leads en 6 h, unas
20.000 lineas pegadas). Cada perfil fija un TECHO de segundos por direccion.

El motor NO acelera por debajo del techo: si va mas rapido de lo previsto
rellena el tiempo sobrante con pausas repartidas en puntos naturales (revisar
el formulario, leer la ficha, procesar una pagina, cerrar) con variacion
aleatoria, para que el ritmo no sea una maquina de pulsos. Si no llega al
techo, lo dice en el informe: nunca se finge.

Perfiles (definidos por el operador el 03/11/2026):
    sigiloso   1,5x mas lento que el operador  -> 27,5 s/direccion
    humano     el ritmo del operador            -> 18,3 s/direccion
    rapido     1,5x mas rapido que el operador  -> 12,2 s/direccion
    psicopata  2x mas rapido que el operador    ->  9,15 s/direccion

Nota honesta: el perfil psicopata es el techo teorico del operador, no un
objetivo alcanzable con AnyDesk (medido: el suelo real esta en ~12,6 s por
direccion). Con ese perfil el motor informara del desfase.
"""
from __future__ import annotations

import os
import random
import time

PERFILES = {
    "sigiloso": {
        "s_dir": 27.5, "key_delay_ms": 120, "jitter": 0.30,
        "desc": "1,5x mas lento que el operador",
    },
    "humano": {
        "s_dir": 18.3, "key_delay_ms": 75, "jitter": 0.25,
        "desc": "el ritmo del operador",
    },
    "rapido": {
        "s_dir": 12.2, "key_delay_ms": 40, "jitter": 0.15,
        "desc": "1,5x mas rapido que el operador",
    },
    "psicopata": {
        "s_dir": 9.15, "key_delay_ms": 28, "jitter": 0.10,
        "desc": "2x mas rapido que el operador (techo real ~12,6 s)",
    },
}

DEFAULT = "humano"
ENV = "MATRIZ_PERFIL"

# Override en memoria (lo usa el CLI del proceso actual). El entorno sigue
# siendo la via normal: el supervisor lo pasa a los subprocesos.
ACTIVO = None

# Reparto del deficit de tiempo en pausas naturales. Suman 1,0.
PUNTOS = {
    "antes_f10": 0.20,
    "tras_ficha": 0.15,
    "entre_paginas": 0.25,
    "cierre": 0.40,
}

# Ninguna pausa individual puede pasar de esto (una persona no se queda 20 s
# mirando la pantalla antes de pulsar F10).
MAX_PAUSA = 6.0


def nombre(valor=None):
    """Nombre del perfil activo. El que no existe se ignora."""
    bruto = str(valor or ACTIVO or os.environ.get(ENV) or DEFAULT).strip().lower()
    return bruto if bruto in PERFILES else DEFAULT


def actual(valor=None):
    """Diccionario del perfil activo, con su nombre."""
    n = nombre(valor)
    p = dict(PERFILES[n])
    p["nombre"] = n
    return p


def objetivo_s(valor=None):
    """Techo de segundos por direccion."""
    return float(actual(valor)["s_dir"])


def key_delay_ms(valor=None):
    """Retardo entre teclas, en milisegundos."""
    return int(actual(valor)["key_delay_ms"])


def jitter(valor=None):
    """Variacion relativa de las pausas (0 = sin variacion)."""
    return float(actual(valor)["jitter"])


def deficit(t0, objetivo=None):
    """Segundos que faltan para llegar al techo (0 si ya se paso)."""
    obj = objetivo_s() if objetivo is None else float(objetivo)
    return max(0.0, obj - (time.time() - float(t0)))


def pausa(t0, punto, objetivo=None, valor=None):
    """Segundos a dormir en este punto (0 si no hay deficit).

    Devuelve 0 si el deficit es 0: en ese caso el motor va mas lento que el
    perfil y no hay nada que rellenar.
    """
    frac = PUNTOS.get(punto)
    if frac is None:
        return 0.0
    j = jitter(valor)
    seg = deficit(t0, objetivo) * frac * random.uniform(1.0 - j, 1.0 + j)
    return max(0.0, min(MAX_PAUSA, seg))


def resumen(valor=None):
    """Linea de texto con los perfiles (para el informe)."""
    p = actual(valor)
    return (f"perfil={p['nombre']} techo={p['s_dir']} s/dir "
            f"tecla={p['key_delay_ms']} ms jitter={p['jitter']}")
