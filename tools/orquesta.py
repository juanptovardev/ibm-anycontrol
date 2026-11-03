"""Orquesta: la API publica del agente.

Las tres piezas del trabajo estan en modulos separados:
- matriz_buscar  -> buscar la direccion en el formulario del 5250
- matriz_ficha   -> leer la ficha del edificio y guardarla en el CSV
- matriz_extraer -> extraer y pegar un bloque de suscriptores

Aqui vive la politica: que toca hacer segun el estado (el semaforo de traza)
y el ritmo (los perfiles de velocidad). El director (loop.procesa) usa las
tres piezas; esta capa es la que consumen el resto del sistema.
"""

import loop as L
import traza


def siguiente_paso(etapa: str, resultado: str) -> str:
    """Que toca hacer ahora. Delega en traza (fuente unica del semaforo)."""
    return traza.accion(etapa, resultado)


async def procesa(fila: dict, hwnd: int, s, dry: bool = False,
                  desde_pagina: int = 0, solo_ficha: bool = False) -> dict:
    """Procesa una direccion completa (búsqueda, ficha, bloques, ledger)."""
    return await L.procesa(fila, hwnd, s, dry, desde_pagina=desde_pagina,
                            solo_ficha=solo_ficha)


async def main(hwnd: int, solo_id: str | None = None, dry: bool = False,
               solo_ficha: bool = False) -> int:
    """CLI del agente (bucle de direcciones)."""
    return await L.main(hwnd, solo_id, dry, solo_ficha)
