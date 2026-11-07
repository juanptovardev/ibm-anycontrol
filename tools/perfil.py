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

La cadencia de teclas va aparte (TECLAS): 'rapido' 35 ms (el motor actual) o
'humano' 110 ms. No se ata al perfil porque el perfil sigiloso no podria
cumplir su techo con teclas de 120 ms. Con 'humano' el motor se pasa de todos
los techos y el informe lo dice.
"""
from __future__ import annotations

import os
import random
import time

PERFILES = {
    "sigiloso": {
        "s_dir": 27.5, "jitter": 0.30,
        "desc": "1,5x mas lento que el operador",
    },
    "humano": {
        "s_dir": 18.3, "jitter": 0.25,
        "desc": "el ritmo del operador",
    },
    "rapido": {
        "s_dir": 12.2, "jitter": 0.15,
        "desc": "1,5x mas rapido que el operador",
    },
    "psicopata": {
        "s_dir": 9.15, "jitter": 0.10,
        "desc": "2x mas rapido que el operador (techo real ~12,6 s)",
    },
}

DEFAULT = "humano"
ENV = "MATRIZ_PERFIL"

# Override en memoria (lo usa el CLI del proceso actual). El entorno sigue
# siendo la via normal: el supervisor lo pasa a los subprocesos.
ACTIVO = None

# ---------------------------------------------------------------- teclas ----
# La cadencia de teclas NO va atada al perfil: si lo estuviera, el perfil
# sigiloso (120 ms x ~105 teclas = 11,5 s) no podria cumplir su propio techo
# de 27,5 s por direccion. El perfil manda sobre el RITMO TOTAL (techo +
# pausas + jitter); la cadencia de tecleo es un knob tecnico aparte.
#
#   rapido  35 ms -> el motor actual (lo que aguanta el AnyDesk)
#   humano 110 ms -> cadencia de una persona; cuesta ~7,5 s mas por direccion
#
# Con "humano" el motor se va por encima de cualquier techo: el informe lo
# dice, no se disimula.
TECLAS = {"rapido": 35, "humano": 110}
ENV_TECLAS = "MATRIZ_TECLAS"
ACTIVO_TECLAS = None

# Reparto del deficit de tiempo en pausas naturales. Suman 1,0.
PUNTOS = {
    "antes_f10": 0.20,
    "tras_ficha": 0.15,
    "entre_paginas": 0.25,
    "cierre": 0.40,
}

# Estimacion del tiempo REAL que tarda una direccion (medido el 03/11 con el
# motor optimizado): unos 15 s fijos (busqueda, ficha, retorno, reencuadre) y
# unos 8 s por pagina (bloque + vuelta + AvPag).
#
# Sin esta estimacion el relleno de pausas se desborda: al principio de la
# direccion el deficit (techo - lo que lleva) parece enorme y se pausan 3-6 s
# que despues no se pueden recuperar. Medido: el perfil humano daba 27,6 s
# por direccion en vez de los 18,3 del techo.
FIJO_ESTIMADO = 15.0
POR_PAGINA_ESTIMADO = 8.0

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


def teclas_nombre(valor=None):
    """Modo de cadencia de teclas activo ('rapido' o 'humano')."""
    bruto = str(valor or ACTIVO_TECLAS or os.environ.get(ENV_TECLAS)
                or "rapido").strip().lower()
    return bruto if bruto in TECLAS else "rapido"


def key_delay_ms(valor=None):
    """Retardo entre teclas, en milisegundos.

    No depende del perfil: es un knob global (ver TECLAS). El argumento se
    acepta y se ignora para no romper a quien lo llame con un perfil.
    """
    return int(TECLAS[teclas_nombre()])


def jitter(valor=None):
    """Variacion relativa de las pausas (0 = sin variacion)."""
    return float(actual(valor)["jitter"])


def deficit(t0, objetivo=None):
    """Segundos que faltan para llegar al techo (0 si ya se paso)."""
    obj = objetivo_s() if objetivo is None else float(objetivo)
    return max(0.0, obj - (time.time() - float(t0)))


def estimar(paginas: int = 1) -> float:
    """Segundos que tardara de verdad una direccion con esas paginas."""
    return FIJO_ESTIMADO + POR_PAGINA_ESTIMADO * max(1, int(paginas))


def pausa(t0, punto, objetivo=None, valor=None, paginas: int = 1) -> float:
    """Segundos a dormir en este punto (0 si no hay deficit).

    El deficit util es el techo MENOS lo que la direccion va a tardar de
    verdad (estimado). Si el motor es mas rapido que el techo, ese es el
    relleno; si es mas lento, no hay nada que rellenar y no se pierde tiempo
    pausando en balde.
    """
    frac = PUNTOS.get(punto)
    if frac is None:
        return 0.0
    obj = objetivo_s() if objetivo is None else float(objetivo)
    if (time.time() - float(t0)) >= obj:
        return 0.0
    util = obj - estimar(paginas)
    if util <= 0:
        return 0.0
    j = jitter(valor)
    seg = util * frac * random.uniform(1.0 - j, 1.0 + j)
    return max(0.0, min(MAX_PAUSA, seg))


def resumen(valor=None):
    """Linea de texto con los perfiles (para el informe)."""
    p = actual(valor)
    return (f"perfil={p['nombre']} techo={p['s_dir']} s/dir "
            f"tecla={key_delay_ms()} ms ({teclas_nombre()}) "
            f"jitter={p['jitter']}")
