# Arranque del agente — prompt inicial (antes de la iteración)

Este archivo es el **punto de entrada**. Se pega tal cual al agente (Hermes `matriz-ops`
o cualquier modelo con acceso a las tools MCP). No se modifica en caliente: si algo
cambia, se cambia aquí y se commitea.

---

## 1. Precondiciones (el humano las deja listas; el agente las VERIFICA)

| # | Condición | Verificación |
|---|---|---|
| P1 | AnyDesk conectado a la oficina | `get_system_status` → `anydesk_windows` no vacío |
| P2 | Emulador 5250 abierto en `CONSULTA EDIFICIO-CUENTA MATRIZ` | `python tools/estado.py <hwnd>` → `"estado": "formulario"` |
| P3 | Chrome abierto en la hoja destino (`LIMPIEZA RR`) | captura del viewport / ojo del humano |
| P4 | `datos/direcciones.csv` con las direcciones del día (3 columnas: `parte1;parte2;ficha`) | `python -c "import csv;print(len(list(csv.DictReader(open('datos/direcciones.csv',encoding='utf-8-sig'),delimiter=';')))))"` |
| P5 | Ventana local del humano fuera del foco | el focus guard del server lo detecta y aborta |

> ERRATA (WP-07): `PROMPT_OBRERO_T-IBM-01.md` esta congelado y dice
> `datos/datos.csv` con 6 columnas. La entrada real es `datos/direcciones.csv`
> con 3 columnas (`parte1;parte2;ficha`). El prompt no se edita; esta errata manda.
> El viejo `datos/datos.csv` se movio a `datos/legacy/datos.csv` y no es entrada.

Si P1–P4 no se cumplen, el agente **no teclea nada** y pide lo que falta.

---

## 2. Prompt inicial (copiar y pegar)

```text
Eres el operador del ciclo 5250 de matriz-ibm-agent. Trabajas sobre una máquina
remota por AnyDesk y NUNCA improvisas.

ARRANQUE (en este orden, sin saltarte pasos):
1. get_system_status y reporta: anydesk_windows, write_capable, read_capable, ocr_capable.
   Si anydesk_windows está vacío -> DETENTE y pide que se conecte AnyDesk.
2. set_focus_click_mode(enabled=false) en la MISMA sesión MCP que usarás después.
   (Si se reinicia el server, hay que repetirlo: el override es por proceso.)
3. Resuelve el hwnd raíz de AnyDesk por título; NO uses hwnd cacheados:
   cambian en cada reconexión.
4. select_anydesk_window(hwnd) para pinear.
5. python tools/estado.py <hwnd>
   - "formulario"        -> listo para iterar
   - "cuenta_matriz"      -> ya estás dentro de un listado: decide si continuar ahí o volver
   - "sin_coincidencia"   -> la búsqueda anterior falló
   - null + error         -> DETENTE (pantalla no IBM o Jev con confianza baja)
6. python tools/loop.py <hwnd>          (todas las filas pendientes)
   o python tools/loop.py <hwnd> <id>   (una sola fila)
7. Reporta el resultado por fila desde datos/ledger.csv.

REGLAS DURAS (violarlas es un fallo, no una variante):
- Nunca pulsar Enter. Nunca inyectar saltos de línea.
- Un clic, y solo uno, en la celda 1 de Calle. Dos clics = doble clic = campo
  seleccionado + teclado inhibido (bug medido).
- Después del clic: flecha derecha, flecha izquierda (asientan el cursor en celda 1).
- El avance de campo es el "+" del BLOQUE NUMÉRICO (numpad add), no el "+" normal.
- F4 SIEMPRE con shift. Un F4 suelto cierra la ventana del emulador.
- No pulsar F10 hasta que la verificación de tinta confirme que el texto está en
  Calle y NO en Nombre.
- Un reintento máximo por fila, con la misma secuencia exacta.
- Si `estado` no es el esperado: parar la fila, escribir el motivo en el ledger,
  seguir con la siguiente. Nada de "arreglarlo a mano".
- La hoja LIMPIEZA RR / Chrome NUNCA es la pantalla IBM: si aparece, es destino
  de pegado, no origen.

PROHIBIDO (necesita humano):
- Logins, 2FA, contraseñas, cambio de claves.
- Borrar o reordenar filas ya escritas en la hoja.
- Cambiar el contrato de direcciones.csv o del ledger sin aprobación.

SALIDA ESPERADA:
- Una línea JSON por fila: {"id","estado","paginas_vistas","filas_copiadas","notas"}.
- Al final: cuántas ok, cuántas no_encontrado, cuántas error, y qué quedó pendiente.
```

---

## 3. Qué hace hoy cada pieza (y qué no)

| Pieza | Estado | Evidencia |
|---|---|---|
| `estado.py` — clasifica la pantalla | ✅ vivo | `formulario conf 0.9` antes, `cuenta_matriz conf 0.95` después |
| `rows.py` — mide las 8 filas del formulario | ✅ vivo | 8 filas, `field_x=531`, `--draw` calza sobre los subrayados |
| `paso1.py` — clic + flechas + parte 1 | ✅ vivo | `tinta calle=117`, `nombre=0` |
| `paso2.py` — `+` + parte 2 + `+` + F10 + Shift+F4 | ✅ vivo | `diff_f10=78768`, entra a `CONSULTA UNIDADES` |
| `paginar.py` — AvPág con paradas | ✅ probado en tests, ⚠️ no con libro real multi-página | hoy el libro era `01/001` |
| `tabla.py` — extrae Direccion/Apto/Com/Div/Nodo/Suscript/Est | ✅ sobre OCR real | el Suscript es la **penúltima** columna |
| `loop.py` — ciclo por fila con blindaje B1–B7 | ✅ tests, ⚠️ sin corrida con >1 fila real | alineado el clic único |
| Pegado en Chrome | ❌ no existe | batch T-IBM-03 |
| Jev como segunda opinión | ⚠️ degradado | free = 429 de cuota; pago = 403 en esta cuenta |

---

## 4. Lo que falta para que sea "agente completo"

1. **Pegado (T-IBM-03)**: contrato de columnas de la hoja + cambio de ventana
   (Alt+Tab / clic) + escribir una fila + verificar leyendo la celda.
2. **Corrida real con N>1**: hoy el ledger tiene 1 fila probada de punta a punta.
3. **OCR del SUSCRIPTOR a 1:1**: en captura reducida los dígitos se confunden
   (`50867551` → `soBs7ss1`). La captura del loop es 1:1, hay que re-medir ahí.
4. **Jev**: necesita cuota o cuenta con acceso al modelo de pago. Mientras tanto
   el gate son las reglas + aprobación humana.

---

## 5. Comandos de referencia

```powershell
$PY = 'C:\Users\juanp_8h8f07l\dev\mcp-anydesk\.venv\Scripts\python.exe'
$PY -m unittest discover -s tests          # 56 tests
$PY tools\estado.py <hwnd>
$PY tools\rows.py <hwnd> --draw
$PY tools\paso1.py <hwnd> "CR 17B"
$PY tools\paso2.py <hwnd> "175-77"
$PY tools\loop.py <hwnd> [id]
```

El python global **no** tiene `mss`/`PIL`: usar siempre el venv de `mcp-anydesk`.
