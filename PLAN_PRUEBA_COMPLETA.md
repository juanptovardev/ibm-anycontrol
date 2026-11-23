> **Histórico.** Plan de corrida real del 28/10. El estado vigente está en el README (v1.1).

# PLAN — Prueba completa (corrida real, sin `--dry`)

**Fecha:** 28/10/2026
**Objetivo:** una corrida real que busque cada dirección, lea la ficha, extraiga
**todos** los bloques paginando, pegue en la hoja y se desplace. Sin `--dry`.

Los tres puntos que el operador pidió cubrir:

| # | Punto | Dónde vive |
|---|---|---|
| 1 | Buscar la dirección y **dejar la ficha en el CSV** | `loop.py::procesa` — `escribe_ficha` **inmediatamente** tras leerla (ya no al final) |
| 2 | Tras **AvPág**, el OCR decide si se terminó | `pagina.py::avanza` (captura + `ocr_completo`) → `pagina.py::decide` → `fin_libro` = parar |
| 3 | Pegar en la hoja y **desplazarse** al bloque siguiente | `ciclo.py` (`_copiar`/`_pegar`/`_posicionar`) |

---

## F0 — Pre-vuelo (30 s, sin teclear nada)

```powershell
python tools\sonda.py
```

**Esperado:** `estado=formulario`, `confianza >= 0.9`, sin diálogo de AnyDesk.
Imprime el `hwnd` raíz y guarda un PNG en `evidencia/`.

Si sale `desconectado`:

```powershell
python tools\vigia.py <hwnd> --repetir
```

Si sale «remoto inaccesible» → el PC de la oficina está apagado: **STOP**.

Comprobar también:

- `datos\direcciones.csv` tiene 3 filas y la columna C vacía.
- No hay ningún `loop.py` vivo (`Get-CimInstance Win32_Process`).

---

## F1 — Una dirección, real (D01)

```powershell
python tools\loop.py <hwnd> D01
```

**Secuencia esperada en pantalla:**

1. `limpiar_0 … tvc` — 16 pasos de la macro, todos `ok`.
2. `copiar_cabecera: ok` → ficha leída del **portapapeles** (no OCR).
3. **La columna C del CSV queda escrita ya**, antes de extraer nada.
4. `A1 clic en x=917 y=522 (... suscriptores N)` con **N > 0**.
5. `shift_click` → `_copiar` → `alt_tab` → `ctrl_shift_v` → `ctrl_down` → `abajo`.
6. `A0 pagina siguiente: sin 7 bajadas` en los bloques 2..n.
7. `PAGINA estado=fin_libro senal_fin=True` en la última → cierra el bucle.

**Esperado en el ledger:** `estado=ok`, `paginas_vistas≈10`, `filas_copiadas≈150`
(baseline de ayer: 10 bloques × 15 filas en 2m51s).

**Verificación manual:** la hoja tiene 150 filas nuevas y la columna C del CSV
tiene las 3 líneas del edificio.

---

## F2 — Las tres direcciones

```powershell
python tools\loop.py <hwnd>
```

Procesa D01, D02, D03 en orden. Al terminar cada una vuelve al formulario
(`entrar_formulario` como punto único de reencuadre).

**Esperado en el ledger:** 3 filas, una por id, cada una con su `estado`
(`ok` o `no_encontrado`). Una dirección sin coincidencia deja la columna C
**vacía** a propósito.

---

## F3 — Verificación (la hago yo, con evidencia)

| Qué | Comando / archivo |
|---|---|
| Resultado por dirección | `datos\ledger.csv` (última fila por id) |
| Recorrido completo | `datos\traza.jsonl` + `datos\traza.md` («PUNTO ACTUAL») |
| Captura final de cada id | `evidencia\<id>-fin.png` |
| Filas reales en la hoja | captura 1:1 del viewport |
| Cero filas en blanco pegadas | ningún bloque con `suscriptores 0` en el log |
| Ficha en el CSV | abrir `datos\direcciones.csv` |

---

## STOP (parar y avisar, sin reintentar a ciegas)

1. `A1 no se encontro la cabecera Suscript` — la pantalla no es el listado.
2. G2 (tras Alt+Tab no es navegador) o G3 (no hubo cambio al pegar) **dos veces**.
3. Tras AvPág el estado no es `cuenta_matriz` ni `fin_libro`.
4. Dos direcciones seguidas con `B1` o `B3`.
5. El ledger dice 150 filas y la hoja tiene menos → desalineación de columnas.
6. Diálogo de licencia de AnyDesk que no se recupera con `--repetir`.

7. El agente imprime `dos reencuadres seguidos fallidos: se corta el lote` —
   la pantalla no es ni el formulario ni el listado: llevarla a mano.

---

## Presupuesto de tiempo

| Tramo | Estimado |
|---|---|
| Búsqueda + ficha (una dirección) | ~15–20 s |
| Cada página | ~6–8 s |
| D01 completo (10 páginas) | ~2 min |
| Las 3 direcciones | ~5–7 min |

---

## Comandos de emergencia

```powershell
# ¿dónde está la pantalla?
python tools\sonda.py

# ¿qué se ve ahora mismo, sin clasificar?
python tools\estado.py <hwnd>

# reconectar tras el corte de licencia
python tools\vigia.py <hwnd> --repetir

# pausar / reanudar / detener desde el panel
python tools\ui.py          # http://127.0.0.1:8765

# matar un bucle colgado (árbol completo)
taskkill /PID <pid> /T /F
```
