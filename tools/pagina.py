"""Volver a IBM y avanzar de pagina en el listado.

Secuencia del operador (congelada):
  1. Despues de pegar y desplazar en la hoja, Alt+Tab regresa al 5250.
  2. Se pulsa AvPag una vez: el listado pasa a la pagina siguiente.
  3. Se mira la pantalla:
       - sale "F12=Anterior / Giro hacia arriba o hacia abajo mas alla del
         primer o ultimo registro en el archivo"  -> la matriz se acabo
       - no sale                                    -> hay otra pagina: se
         vuelve a extraer (seleccionar, copiar, tabular, pegar, desplazar)

El letrero se detecta con las reglas de `estado.py` (estado `fin_libro`); Jev
solo entra si el OCR queda dudoso. `F12=Anterior` a secas NO se usa como
senal: puede estar presente en la barra de teclas de funcion.
"""
import asyncio
import re
import sys

import preflight_auto as pf
import ventana
from _mcp import connect, need_hwnd
from estado import (captura, clasificar_rapido, clasificar_texto, ocr_completo,
                    tipo_pixeles)

ESPERA_TAB = 0.5
ESPERA_PAGINA = 0.3
ESPERA_PAGINA_LENTA = 0.7  # primer AvPag de la direccion: sin referencia previa
# Minimo de pixeles que deben cambiar entre paginas. Si la pantalla casi no
# cambia, el AvPag todavia no se ha procesado y NO se debe copiar (si no, se
# pega la pagina anterior otra vez: duplicado).
# Medido el 09/11 sobre 2865 pares de capturas reales: identicas = 0 px; solo el
# reloj = 34-36 px; avance real de pagina = 681 px o mas (tipico 2000-50000).
# Con 3000 se descartaban avances REALES de ~2209 px (D46/D53/D54/D60/D69) y la
# direccion abortaba en bucle. 400 queda entre el ruido del reloj y el cambio
# real mas pequeno.
PAGINA_MIN_DIFF = 400
# Estados que significan "seguimos dentro del listado del 5250".
IBM_OK = {"cuenta_matriz", "fin_libro"}
# Ultima captura de avanza(): el ciclo la reutiliza y no repite el OCR.
ULTIMA = None


def decide(estado: str | None, no_ibm: bool = False,
           sin_cambio: bool = False) -> str:
    """Accion pura a partir del estado de la pantalla: seguir | fin | abortar.

    `sin_cambio` avisa de que la pantalla NO cambio tras el AvPag: puede ser la
    ultima pagina repetida (copiarla seria duplicar) o una tecla perdida. En los
    dos casos se aborta: el ledger ya guardo el punto y la corrida reanuda ahi.
    """
    if no_ibm:
        return "abortar"
    if estado == "fin_libro":
        return "fin"
    if estado == "cuenta_matriz":
        return "abortar" if sin_cambio else "seguir"
    return "abortar"


# El 5250 pinta el contador de pagina abajo a la derecha: "08/031" = pagina 8
# de 31. Sirve para saber DONDE esta el listado. Sin el, reanudar tras un corte
# era pulsar AvPag a ciegas: un AvPag perdido dejaba hueco o duplicado, y el
# ledger no lo podia detectar.
RE_CONTADOR = re.compile(r"^(\d{1,3})/(\d{1,3})$")
# Tope de AvPag por reanudacion: una matriz real no pasa de ~40 paginas.
MAX_SALTOS = 60


def _limpia(texto: str) -> str:
    """Corrige las confusiones tipicas de Tesseract en un contador numerico.

    En un token que solo puede ser digitos y una barra, O->0, I/L->1 y B->8 no
    tienen ambiguedad: se vieron contadores leidos como "OB/031" o "08/03l".
    """
    return (texto or "").strip().upper().replace(" ", "").replace("O", "0") \
        .replace("I", "1").replace("L", "1").replace("B", "8")


def contador(words, ancho: int, alto: int):
    """(pagina_actual, paginas_totales) del contador NN/NNN, o (None, None).

    Solo se acepta el que cae en la franja inferior derecha: en pantalla hay
    otros numeros (cuentas, telefonos, contadores de registro) y confundirlos
    haria saltar a la pagina equivocada.
    """
    mejor = None
    for w in words or []:
        texto, x, y = w[0], w[1], w[2]
        m = RE_CONTADOR.match(_limpia(texto))
        if not m:
            continue
        if y < alto * 0.7 or x < ancho * 0.6:
            continue
        peso = x + y
        if mejor is None or peso > mejor[0]:
            mejor = (peso, int(m.group(1)), int(m.group(2)))
    if mejor is None:
        return None, None
    return mejor[1], mejor[2]


def pasos_reanudar(actual, objetivo: int):
    """AvPag que faltan para llegar a `objetivo` (None si no hay contador).

    Negativo = el listado ya esta MAS adelante de lo que dice el ledger: no se
    retrocede, porque lo que hay por delante ya se pego en la hoja.
    """
    if actual is None:
        return None
    return objetivo - actual


async def reanudar(s, hwnd: int, objetivo: int, intentos: int = 4,
                   espera: float = 0.9):
    """Deja el listado en la pagina `objetivo` mirando el contador NN/NNN.

    Devuelve (pagina_real, nota). Si no se puede leer el contador, devuelve
    None: avanzar a ciegas puede saltar o duplicar paginas.
    """
    actual = total = None
    for _ in range(intentos):
        img, _vp = captura(hwnd)
        _texto, words = ocr_completo(img)
        actual, total = contador(words, img.width, img.height)
        if actual is not None:
            break
        await asyncio.sleep(espera)

    if actual is None:
        return None, "sin contador de pagina: reanudacion abortada sin AvPag"

    saltos = pasos_reanudar(actual, objetivo)
    if saltos == 0:
        return actual, ""
    if saltos < 0:
        return actual, (f"el listado ya estaba en la pagina {actual} "
                        f"(el ledger decia {objetivo}): no se retrocede")

    dados = 0
    while saltos > 0 and dados < MAX_SALTOS:
        await pf.step(s, f"resuma_avpag_{dados}", "press_keys",
                      {"keys": ["pagedown"]})
        await asyncio.sleep(1.1)
        dados += 1
        img, _vp = captura(hwnd)
        _texto, words = ocr_completo(img)
        nuevo, _total = contador(words, img.width, img.height)
        if nuevo is not None:
            actual = nuevo
            saltos = pasos_reanudar(actual, objetivo)

    if saltos > 0:
        nota = (f"no se llego a la pagina {objetivo}: el contador quedo en "
                f"{actual} (faltan {saltos})")
    elif saltos < 0:
        nota = f"se paso de la pagina {objetivo}: el contador quedo en {actual}"
    else:
        nota = ""
    return actual, nota


async def volver(s, hwnd: int, intentos: int = 3, sondeos: int = 4) -> dict:
    """Vuelve al 5250 por el icono de su taskbar y verifica el listado.

    El 03/11 el Alt+Tab dejo de cambiar de ventana (la tecla de sistema no
    llega al escritorio remoto con el 5250 y Chrome maximizados). El clic en
    el icono de la taskbar si funciona; el icono se localiza por imagen, de
    modo que no depende de una coordenada fija. `ventana.ir_a` cae al
    Alt+Tab si no encuentra el icono.
    """
    ok = await ventana.ir_a(s, hwnd, ventana.DESTINO_IBM, intentos=2,
                            espera=0.5)
    if not ok:
        raise pf.Halt("volver: no se pudo volver al 5250 (ni por icono ni Alt+Tab)")
    for _ in range(sondeos):
        img, _vp = captura(hwnd)
        if tipo_pixeles(img) == "navegador":
            # Seguimos en el navegador: otro sondeo. El clasificador por
            # pixeles son 20 ms en vez de ~405 ms de OCR (medido: 228
            # capturas reales, margen de 4x entre los dos grupos).
            await asyncio.sleep(ESPERA_TAB)
            continue
        st = clasificar_rapido(img)
        senales = st.get("senales") or {}
        estado = st.get("estado")
        if estado in IBM_OK:
            print(f"VOLVER pantalla: estado={estado} (por icono)", flush=True)
            return st
        if not senales.get("no_ibm"):
            # Ya se esta en el 5250, pero no en el listado.
            print(f"VOLVER pantalla: estado={estado} no_ibm=False", flush=True)
            raise pf.Halt(f"volver: no se llego al listado (estado {estado})")
        await asyncio.sleep(ESPERA_TAB)
    raise pf.Halt("volver: el 5250 no llego al listado tras varios sondeos")


async def avanza(s, hwnd: int, intentos: int = 3,
                 prev=None) -> dict:
    """AvPag + clasificacion. Devuelve el estado con la senal de fin de archivo.

    La captura y el OCR quedan en `ULTIMA`: el ciclo los reutiliza para medir
    la columna Suscript sin volver a capturar ni re-ejecutar Tesseract sobre la
    misma pantalla.

    `prev` es la captura de la pagina anterior: si la pantalla casi no cambia
    tras el AvPag, el remoto todavia no lo ha procesado y se espera (copiar
    entonces seria pegar la misma pagina dos veces).

    Medido el 28/10 (run8, D03): hay frames en los que la pantalla no se puede
    leer ni con las reglas ni con Jev (estado None) y la direccion se perdia.
    Se recaptura hasta 3 veces. Solo el ultimo intento consulta a Jev, para no
    gastar cuota en frames de transicion.
    """
    global ULTIMA
    await pf.step(s, "avpag", "press_keys", {"keys": ["pagedown"]})
    await asyncio.sleep(ESPERA_PAGINA if prev is not None else ESPERA_PAGINA_LENTA)
    st = None
    img = texto = words = None
    sin_cambio = False
    for i in range(intentos):
        img = pf.shot(hwnd, "pagina")
        ultimo = i == intentos - 1
        cambio = prev is None or pf.changed_px(prev, img) >= PAGINA_MIN_DIFF
        # El guard del diff evita copiar la MISMA pagina si el AvPag aun no se
        # proceso. Pero en el ULTIMO intento se clasifica igual: al final de la
        # matriz el AvPag no redibuja y, sin clasificar, el estado quedaba None
        # y el llamador reventaba con AttributeError (medido 09/11: D46/D54/
        # D60/D69). Clasificando se ve el cartel de fin de archivo.
        if not cambio and not ultimo:
            print(f"PAGINA la pantalla casi no cambio (intento {i + 1}/{intentos}): "
                  f"se recaptura", flush=True)
            await asyncio.sleep(ESPERA_PAGINA)
            continue
        texto, words = ocr_completo(img)
        st = clasificar_texto(texto, usar_jev=ultimo)
        if st.get("estado") is not None:
            sin_cambio = not cambio
            break
        print(f"PAGINA sin lectura (intento {i + 1}/{intentos}): se recaptura",
              flush=True)
        await asyncio.sleep(ESPERA_PAGINA)
    if st is None:
        # Nunca se pudo leer: se devuelve un dict vacio (no None) para que el
        # llamador no reviente; decide() lo trata como 'abortar'.
        st = {"estado": None, "confianza": None, "senales": {},
              "error": "pagina sin lectura tras los intentos"}
    ULTIMA = {"img": img, "texto": texto, "words": words, "sin_cambio": sin_cambio}
    # El llamador decide() con este aviso: si la pantalla no cambio y sigue el
    # listado, es la misma pagina (copiarla seria duplicar).
    st["sin_cambio"] = sin_cambio
    senales = st.get("senales") or {}
    print(f"PAGINA estado={st['estado']} conf={st.get('confianza')} "
          f"senal_fin={senales.get('fin')} sin_cambio={sin_cambio} "
          f"error={st.get('error')}", flush=True)
    return st


async def _run(hwnd: int) -> bool:
    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            await volver(s, hwnd)
            st = await avanza(s, hwnd)
            decision = decide(st["estado"],
                              bool((st.get("senales") or {}).get("no_ibm")),
                              bool(st.get("sin_cambio")))
            print(f"DECISION: {decision}", flush=True)
            if decision == "abortar":
                raise pf.Halt(f"pagina: estado inesperado {st['estado']}")
        except pf.Halt as exc:
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    hwnd = need_hwnd(argv)
    if not asyncio.run(_run(hwnd)):
        return 1
    print("OK pagina", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
