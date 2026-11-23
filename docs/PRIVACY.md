# Privacidad y tratamiento de datos — IBM AGENT

Fecha: 2026-11-18
Estado: Jev **apagado por defecto** (D-01). Este documento describe qué datos
pueden salir de la PC si el operador decide encenderlo.

## 1. Alcance

El agente lee la pantalla del emulador 5250 con OCR y extrae direcciones,
suscriptores, cuentas y fichas de edificios. Esos datos son PII operativa.
La mayor parte del procesamiento es local. La única salida a un tercero es la
clasificación opcional con Jev.

## 2. Qué se envía a Jev

Solo cuando se cumplen **todas** estas condiciones:

- las reglas locales no pudieron decidir el estado (`estado is None`);
- la llamada se hizo con `usar_jev=True`;
- Jev está habilitado (`MATRIZ_JEV=1` o `enabled: true`) **y** hay una clave
  dedicada;
- la pantalla tiene marcadores IBM (no se envía la hoja de cálculo ni una
  pantalla sin señales del 5250).

Contenido enviado:

- los primeros **2000 caracteres** del texto OCR, sin líneas vacías;
- ese texto puede incluir direcciones, nombres de suscriptores, cuentas y
  mensajes del sistema;
- no se envían imágenes, credenciales ni el CSV completo.

## 3. Destino

- Endpoint: `https://opencode.ai/inference/systemone/v1/systemone`
- Modelo: `jev-1.13-free`
- Es un servicio de **terceros**, distinto de IBM y del operador.
- La clave se envía como `Authorization: Bearer` en un archivo temporal de
  curl que se borra en `finally`; no se escribe en logs.

## 4. Dónde quedan los datos localmente

- `datos/direcciones.csv`: maestro de direcciones y fichas. No se versiona
  (D-02). El baseline y los rollbacks van por ZIP + SHA256.
- `datos/ledger.csv`: estado por dirección. En el caso `mensajes`, las notas
  pueden guardar hasta **300 caracteres** del aviso del 5250.
- `evidencia/`: capturas de pantalla y recortes; pueden contener PII.
- `datos/traza.jsonl`: eventos de operación; no incluye el recorte enviado a
  Jev, pero sí ids, estados y detalles de error.
- El texto OCR completo (`resultado["texto"]`) se usa en memoria para paginar;
  no se persiste como tal.

## 5. Apagado y encendido

Apagado (default y recomendado):

```powershell
$env:MATRIZ_JEV = "0"
```

También queda apagado si `config/jev.json` tiene `"enabled": false` o si no
hay clave dedicada. Sin clave, `disponible()` devuelve `False` y `ask()` no
hace ninguna llamada de red.

Encendido (solo con aprobación del operador):

```powershell
$env:MATRIZ_JEV = "1"
$env:MATRIZ_JEV_KEY = "<clave-dedicada>"
```

o, en `config/jev.json` local:

```json
{"enabled": true, "key": "<clave-dedicada>"}
```

Requisitos para encender:

1. D-01 aprobada por el operador.
2. Clave **dedicada** para este agente; prohibido reutilizar la credencial
   personal de opencode.
3. DPA o base legal revisada con el proveedor.
4. Verificar retención, entrenamiento y subprocesadores del proveedor.
5. Registrar la decisión y la fecha en `FINIQUITO/DECISIONES_OPERADOR.md`.

## 6. Terceros

- **Jev**: solo recibe texto si D-01 está aprobada y `MATRIZ_JEV=1` con clave
  dedicada. Sin eso, no hay llamada de red. El proveedor y su retención se
  documentan en el DPA antes de encender.
- **Google Sheets**: destino del pegado. El agente no sube archivos; el
  operador pega en la hoja que tenga abierta. La hoja y su cuenta las controla
  el operador.
- **AnyDesk**: canal de acceso remoto a la pantalla. No recibe los CSV del
  agente; solo transporta la sesión gráfica.
- **Proveedor de opencode**: si se usa un modelo remoto para el agente, puede
  ver el prompt y las herramientas, no los CSV locales salvo que se los pases.
  Para datos reales, usar un modelo local o una cuenta con DPA.
- **Tesseract/OCR**: local; no envía imágenes a ningún servicio.

No hay telemetría propia ni analytics en el agente. Si agregas una dependencia
con telemetría, actualiza esta sección antes de mergear.

## 7. Cómo borrar

1. Detén el agente y el panel.
2. Haz un ZIP de respaldo y anota su SHA256 (D-02) por si necesitas rollback.
3. Borra solo las rutas de datos, no el código:

```powershell
$rutas = @(
  "datos\direcciones.csv",
  "datos\direcciones_segunda.csv",
  "datos\ledger.csv",
  "datos\direcciones_problema.txt",
  "datos\direcciones_orden.csv",
  "datos\direcciones_nuevas.csv",
  "datos\fichas_pendientes.csv",
  "datos\traza.jsonl",
  "datos\traza.md",
  "datos\control.json",
  "datos\ui_token.txt",
  "evidencia",
  "config\jev.json"
)
foreach ($r in $rutas) {
  if (Test-Path -LiteralPath $r) { Remove-Item -LiteralPath $r -Recurse -Force }
}
```

4. Verifica que no quedan: `Get-ChildItem datos, evidencia -Recurse -Force`.
5. Si Jev estuvo encendido, pide al proveedor el borrado del texto enviado
   según el DPA; el agente no puede borrar lo que ya salió.
6. Rota la clave dedicada y el token del panel si los archivos pudieron
   filtrarse.

No borres `direcciones.csv` sin respaldo: es la fuente de trabajo. Un borrado
sin ZIP no se puede deshacer.

## 8. Retención y derechos

El agente no controla la retención del proveedor. Antes de encender Jev, el
operador debe confirmar por escrito:

- cuánto tiempo se retiene el texto;
- si se usa para entrenamiento;
- dónde se procesa;
- cómo se ejerce un pedido de acceso o borrado.

Si no hay respuesta satisfactoria, Jev queda apagado.

## 9. Responsabilidades

- Operador: decide D-01, firma el DPA y custodia la clave.
- Encargado de finiquito: verifica que el default sea off, que no haya
  fallback a `auth.json` y que la clave no esté en el repo.
- Revisor ciego: confirma en Gate 3 que `disponible()` es `False` sin clave y
  que `MATRIZ_JEV=0` gana sobre `enabled: true`.

## 10. Cambios

- 2026-11-18: versión inicial. Se elimina el fallback a la credencial personal
  y se deja Jev apagado por defecto.
- 2026-11-18 (WP-06): se añaden terceros y procedimiento de borrado;
  `direcciones.csv` y `ledger.csv` dejan de versionarse (D-02).
