"""Copia un bloque del listado 5250 y lo pega en la hoja de limpieza.

FLUJO DEL OPERADOR (congelado, no reinterpretar):
  1. En el listado CONSULTA UNIDADES, el cursor esta en su posicion inicial.
  2. 7 abajo SIN shift, luego Shift + 72 derecha + 14 abajo -> bloque de 72
     caracteres (Direccion .. Suscriptor) por 15 filas.
  3. Se suelta Shift. Ctrl+C.
  4. Alt+Tab a la hoja. Ctrl+Shift+V (pegar sin formato).
  5. Ctrl+Abajo y luego un Abajo -> celda lista para el siguiente pegado.

El bloque copiado no se puede leer desde aqui: el portapapeles vive en la
maquina REMOTA. La unica prueba de que el pegado ocurrio es la diferencia de
pixeles en la captura posterior.

PUERTAS (si una falla, se aborta; no se reintenta a ciegas):
  G0  la pantalla es el listado (estado == cuenta_matriz)
  G1  la seleccion es un rectangulo macizo (densidad y tamano plausibles)
  G2  tras Alt+Tab la pantalla NO es IBM (es la hoja)
  G3  tras Ctrl+V hubo cambio visible (un reintento y nada mas)

Uso:
  python tools/cp.py <hwnd> --dry   # solo selecciona y mide; NO copia
  python tools/cp.py <hwnd>         # copia y pega una vez
"""
import asyncio
import sys

from PIL import Image

import preflight_auto as pf
import native_shot
import perfil
import recepcion
import ventana
import hoja
from _mcp import connect, need_hwnd
from estado import (captura, clasificar, clasificar_rapido, ocr_text,
                    tipo_pixeles)

# Bloque del operador: 7 abajo, 72 derecha, 14 abajo (15 filas x 72 columnas).
BAJAR_INICIO = 7
ANCHO = 72
ALTO = 14
KEY_DELAY_MS = 35  # 93 teclas -> ~6 s; por debajo se pierden pulsaciones
                   # (este es el minimo tecnico: el perfil manda, ver perfil.py)

SEL_MIN_ANCHO = 500   # medido: el bloque de 72 columnas mide 690 px de ancho
SEL_ROW_MIN = 300     # fila de borde: 683 px medidos en captura real
SEL_COL_MIN = 100     # columna de borde: 309 px medidos en captura real
SEL_MIN_ALTO = 150    # 15 filas ~320 px; 150 px = piso de 8 filas
PASTE_MIN_DIFF = 3000  # pixeles cambiados para dar el pegado por bueno
PASTE_MIN_CAMBIO = 800  # cambio minimo para creer que SI se pego algo (bloque de 1 fila)


def _es_borde(r: int, g: int, b: int) -> bool:
    """Color medido del borde de seleccion del 5250: amarillo apagado."""
    return r > 150 and g > 150 and 60 < b < 170


def sel_box(img: Image.Image) -> tuple[tuple | None, int]:
    """Rectangulo de seleccion del 5250 medido por sus cuatro bordes.

    El emulador dibuja un marco amarillo apagado. Medido sobre captura real:
    dos filas densas (212 y 612 px de ancho) y dos columnas densas (x=244 y
    x=934). Buscar corridas contiguas falla porque el texto rompe la linea.

    El diff entre capturas tampoco sirve: el reloj de la barra inferior
    ensancha la caja a toda la pantalla (densidad medida 0.01).

    Returns:
        (bbox, alto): bbox (x0, y0, x1, y1) o None, y alto en pixeles.
    """
    rgb = img.convert("RGB")
    px = rgb.load()
    ancho, alto = rgb.size
    y_ini, y_fin = 140, min(alto, 635)

    filas: list[int] = []
    for y in range(y_ini, y_fin):
        if sum(1 for x in range(ancho) if _es_borde(*px[x, y])) >= SEL_ROW_MIN:
            filas.append(y)
    if len(filas) < 2:
        return None, 0

    columnas: list[int] = []
    for x in range(ancho):
        if sum(1 for y in range(y_ini, y_fin) if _es_borde(*px[x, y])) >= SEL_COL_MIN:
            columnas.append(x)
    if len(columnas) < 2:
        return None, 0

    caja = (min(columnas), min(filas), max(columnas) + 1, max(filas) + 1)
    return caja, caja[3] - caja[1]


def texto_superior(img: Image.Image, caja: tuple) -> str:
    """OCR de la primera banda de la seleccion: dice si arriba hay cabecera."""
    x0, y0, _x1, y1 = caja
    banda = img.crop((x0, y0, caja[2], y0 + max(12, (y1 - y0) // 15)))
    texto = ocr_text(banda).strip()
    return texto.splitlines()[0] if texto else ""


async def _seleccionar(s, hwnd: int, dry: bool) -> tuple:
    """7 abajo SIN shift, luego Shift + 72 derecha + 14 abajo.

    El shift empieza DESPUES de bajar 7: las bajadas iniciales mueven el
    cursor, no la seleccion. Si se pulsan con shift, se marca una columna
    vertical antes de tiempo y el bloque sale corrido.
    """
    await pf.step(s, "bajar_inicio", "press_keys",
                  {"keys": ["down"] * BAJAR_INICIO, "key_delay_ms": perfil.key_delay_ms()})
    teclas = ["shift"] + ["right"] * ANCHO + ["down"] * ALTO
    await pf.step(s, "seleccion", "press_keys",
                  {"keys": teclas, "key_delay_ms": perfil.key_delay_ms()})
    await asyncio.sleep(0.2)
    img = pf.shot(hwnd, "cp-sel" if not dry else "cp-sel-dry")
    caja, alto_sel = sel_box(img)
    ancho = (caja[2] - caja[0]) if caja else 0
    print(f"G1 sel caja={caja} ancho={ancho} alto={alto_sel}", flush=True)
    if not caja:
        raise pf.Halt("G1 no hay seleccion visible (amarillo)")
    if ancho < SEL_MIN_ANCHO:
        raise pf.Halt(f"G1 seleccion angosta: {ancho}px (se esperan >={SEL_MIN_ANCHO})")
    if alto_sel < SEL_MIN_ALTO:
        raise pf.Halt(f"G1 seleccion de {alto_sel}px de alto (se esperan >={SEL_MIN_ALTO})")
    print(f"G1 primera linea: {texto_superior(img, caja)!r}", flush=True)
    return img, caja


async def _copiar(s) -> int:
    """Copia el bloque y devuelve CUANTAS lineas con datos tiene.

    El portapapeles local SI recibe lo que se copia en el 5250 (medido: la
    ficha del edificio llego al portapapeles local con sus 3 lineas). Contar
    las lineas con contenido dice si el bloque pegado es de UNA fila o de
    varias, y de eso depende como se deja el cursor para el pegado siguiente.

    Si la lectura falla se devuelve 0 y el llamador usa el comportamiento
    historico (Ctrl+Abajo), que es el que nunca ha roto nada.
    """
    # El portapapeles local es instantaneo: 0.25 s aqui era espera muerta.
    await pf.step(s, "ctrl_c", "copy_clipboard", {})
    await asyncio.sleep(0.1)
    try:
        texto = recepcion._portapapeles() or ""
    except Exception:  # noqa: BLE001 - si no se puede leer, se sigue igual
        return 0
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n") if l.strip()]
    print(f"A2 lineas copiadas con datos: {len(lineas)}", flush=True)
    return len(lineas)


async def _espera_pegado(hwnd: int, antes, intentos: int = 10,
                         espera: float = 0.2) -> tuple:
    """Espera ACTIVA a que el pegado se vea: captura y compara cada 200 ms.

    Antes se dormia 0,6 s fijos y luego se comparaba; el pegado se ve a los
    ~150 ms, asi que se perdian ~450 ms por bloque. Se capturan sin guardar
    (solo la ultima se guarda como evidencia).

    Son 2 s de margen (10 x 200 ms) a proposito: un pegado que el remoto pinta
    tarde NO se puede confundir con un pegado que no ocurrio, porque el
    reintento automatico (que existia aqui) duplicaba el bloque en la hoja.
    Medido el 27/10: D03 quedo pegada dos veces (filas 36-50 y 51-65) porque
    el primer Ctrl+Shift+V si habia funcionado y el render tardo mas que la
    espera. Un bloque perdido se reanuda; uno duplicado hay que borrarlo a
    mano y contamina el dato.
    """
    mejor = 0
    img = antes
    for i in range(intentos):
        await asyncio.sleep(espera)
        img, _vp = captura(hwnd)
        diff = pf.changed_px(antes, img)
        if diff >= PASTE_MIN_DIFF:
            return diff, img
        mejor = max(mejor, diff)
    return mejor, img


async def _pegar(s, hwnd: int) -> None:
    """Ir a la hoja (por el icono de la taskbar) -> esperar -> pegar.

    El 03/11 el Alt+Tab dejo de cambiar de ventana: la tecla de sistema no
    llega al escritorio remoto con el 5250 y Chrome ambos maximizados
    (medido con la sonda de teclas: la pantalla no cambiaba ni desde el
    5250 ni desde Chrome). La via que si funciona es hacer clic en el icono
    de la taskbar del escritorio remoto, localizado por imagen para no
    depender de una coordenada fija. El Alt+Tab queda como recurso.
    """
    async def _espera_destino(sondeos: int) -> tuple:
        """Sondea el destino del Alt+Tab hasta que sea el navegador.

        El clasificador por pixeles (20 ms) decide el caso normal: la hoja es
        casi toda blanca y el 5250 casi todo negro (medido sobre 228 capturas
        reales, margen de 4x). Solo si los pixeles no son concluyentes se
        recurre al OCR (~405 ms).
        """
        st: dict = {}
        img = None
        for _ in range(sondeos):
            await asyncio.sleep(0.35)
            img, _vp = captura(hwnd)
            tipo = tipo_pixeles(img)
            if tipo == "navegador":
                return {"estado": None, "senales": {"no_ibm": True}}, img
            if tipo == "ibm":
                # Seguimos en el 5250: el Alt+Tab no llego al remoto.
                return {"estado": None, "senales": {"no_ibm": False}}, img
            st = clasificar_rapido(img)
            if (st.get("senales") or {}).get("no_ibm"):
                return st, img
        return st, img

    # El 03/11 el Alt+Tab dejo de cambiar de ventana (la tecla de sistema no
    # llega al escritorio remoto con el 5250 y Chrome maximizados). La via que
    # si funciona es hacer clic en el icono de la taskbar del escritorio
    # remoto; el icono se localiza por imagen para no depender de una
    # coordenada fija. `ventana.ir_a` cae al Alt+Tab si no lo encuentra.
    print("G2 se busca el navegador por su icono de la taskbar", flush=True)
    await ventana.ir_a(s, hwnd, ventana.DESTINO_NAVEGADOR, intentos=2,
                       espera=0.5)
    st, antes = await _espera_destino(3)
    if not (st.get("senales") or {}).get("no_ibm"):
        print("G2 el icono no trajo el navegador: Alt+Tab", flush=True)
        await pf.step(s, "alt_tab", "press_keys", {"keys": ["alt", "tab"]})
        st, antes = await _espera_destino(5)
    no_ibm = bool((st.get("senales") or {}).get("no_ibm"))
    print(f"G2 pantalla destino: estado={st.get('estado')} no_ibm={no_ibm} "
          f"error={st.get('error')}", flush=True)
    if not no_ibm:
        raise pf.Halt("G2 no se pudo llegar a la hoja: no se pega")
    # Contrato de columnas (T3): antes de pegar se comprueba que la pantalla
    # es la hoja esperada (DIRECCION / EDIFICIO / SUSCRIPTOR). La captura
    # "antes" es la del sondeo de G2: no hace falta otra.
    ok_hoja, nota_hoja = hoja.verifica(antes)
    print(f"G2b contrato de columnas: {nota_hoja}", flush=True)
    if not ok_hoja:
        raise pf.Halt(f"G2b {nota_hoja}: no se pega")
    await pf.step(s, "ctrl_shift_v", "paste_clipboard", {"shift": True})
    diff, img_post = await _espera_pegado(hwnd, antes)
    print(f"G3 diff={diff}px", flush=True)
    if diff < PASTE_MIN_CAMBIO:
        # No se reintenta el Ctrl+Shift+V: si el primer pegado si funciono y
        # el remoto solo tardo en pintarlo, reintentar DUPLICA el bloque.
        raise pf.Halt("G3 el pegado no se ve: Ctrl+C no llego al portapapeles remoto")
    if diff < PASTE_MIN_DIFF:
        # Algo se pego (bloque de una sola fila cambio menos pixeles de lo
        # normal). Se acepta y se deja constancia; no se reintenta.
        print(f"G3 cambio pequeno ({diff}px): se acepta, no se reintenta", flush=True)
    native_shot.save(img_post, "cp-post-paste")


async def _posicionar(s, hwnd: int, filas: int = 0) -> None:
    """Deja la celda lista para el siguiente pegado.

    Bloque de VARIAS filas (el normal): Ctrl+Abajo lleva al final del bloque
    pegado y un Abajo deja la celda siguiente. Comportamiento historico,
    validado en vivo.

    Bloque de UNA sola fila: en Google Sheets Ctrl+Abajo salta al siguiente
    bloque de datos de la columna, o al FINAL de la hoja si ya no hay mas.
    Medido el 03/11: la direccion CR 14 119-33, cuya segunda pagina tenia
    una sola direccion con suscriptor, dejo el cursor al final de la hoja y
    los pegados siguientes se fueron para alla. Con una sola fila basta un
    Abajo.
    """
    if filas == 1:
        await pf.step(s, "abajo", "press_keys", {"keys": ["down"]})
    else:
        await pf.step(s, "ctrl_down", "press_keys", {"keys": ["ctrl", "down"]})
        await pf.step(s, "abajo", "press_keys", {"keys": ["down"]})
    pf.shot(hwnd, "cp-listo")


async def _secuencia(hwnd: int, dry: bool) -> bool:
    async with connect() as s:
        try:
            await pf.step(s, "focus_click_off", "set_focus_click_mode", {"enabled": False})
            await pf.step(s, "pin", "select_anydesk_window", {"hwnd": hwnd})
            st = clasificar(captura(hwnd)[0], usar_jev=False)
            print(f"G0 pantalla: estado={st['estado']} conf={st.get('confianza')}", flush=True)
            if st["estado"] != "cuenta_matriz":
                raise pf.Halt(f"G0 se esperaba el listado, hay {st['estado']}")
            pf.shot(hwnd, "cp-antes")
            await _seleccionar(s, hwnd, dry)
            if dry:
                await pf.step(s, "limpiar", "press_keys", {"keys": ["escape"]})
                print("DRY: seleccion medida, no se copio nada", flush=True)
                return True
            filas = await _copiar(s)
            await _pegar(s, hwnd)
            await _posicionar(s, hwnd, filas)
        except pf.Halt as exc:
            # Se captura DENTRO del context manager: si sale de el, anyio lo
            # envuelve en ExceptionGroup y se pierde el motivo.
            print(f"ABORTADO: {exc}", flush=True)
            return False
    return True


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    args = [a for a in argv if a != "--dry"]
    hwnd = need_hwnd(args)
    ok = asyncio.run(_secuencia(hwnd, dry))
    if not ok:
        return 1
    print("OK" + (" (dry)" if dry else ": copiado y pegado"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
