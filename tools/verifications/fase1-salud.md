# Dossier Fase 1 — Salud MCP (medido 2026-10-26, ejecución real)

## mcp-anydesk (`python test_mcp_smoke.py`)

- Servidor: AnyDesk MCP Server v3.5.1, protocolo 2025-11-25.
- Tools: 18 (bootstrap_sanitizer, capture_screenshot, check_health, export_session, get_recipe, get_session_history, get_system_status, get_version, initialize_session, list_recipes, list_sessions, log_step_result, pin_session, read_from_anydesk, select_anydesk_window, send_cancel, switch_session, write_to_anydesk).
- **NO existe herramienta de teclas especiales ni de click** (verificado en lista en vivo → gap confirmado empíricamente, no solo por lectura de código).
- Capacidades: write_capable=true, read_capable=true, ocr_capable=true (Tesseract 5.4.0, OpenCV, pywin32, mss presentes; pynput ausente).
- Recetas: 6, todas PowerShell (health_check, vm_status, network_check, service_check, ...). Ninguna sirve a IBM-Chrome.
- **BLOQUEANTE: `anydesk_windows: []` → "No AnyDesk sessions detected. Is AnyDesk running?"** — check_health=degraded, sessions=[]. Fases 2–3 requieren AnyDesk corriendo con sesión viva.

## jev-gate (`python test_mcp_smoke.py`)

- Servidor: Jev Gate Server v1.0.0, gateway apinex.bond, client curl-subprocess.
- Tools: 6 (jev_classify, jev_decide, jev_gate, jev_score, jev_status, jev_version).
- `jev_status`: endpoint https://api.apinex.bond/v1/decisions, model free/jev-1.13, key_present=true, **probe_http_status=502, ok=false**.
- `jev_gate`, `jev_classify`, `jev_score`: todos **HTTP 502** ("error code: 502").
- **BLOQUEANTE: capa Jev caída hoy.** Escala real de score sin medir (inconsistencia #1 sigue abierta). Rige modo degradado hasta `jev_status` 200.

## Sonda newline (2026-10-26, `probe_write_reject.py`)

- `write_to_anydesk("PARTE1\nPARTE2")` → status=error, char_count=0, elapsed_ms=0, note="Multi-line input rejected..." (isError MCP=false: el error va en el payload, no en el sobre).
- Verificado en código: validación en `keyboard_injector.py:142`, foco recién en `:193` → no toca ninguna ventana. Límite texto-solo confirmado en vivo.

## Umbral G1 (Fase 1, paso 5) — pendiente de medir en vivo

- Requiere primera lectura OCR real sobre la pantalla IBM (AnyDesk corriendo). Registrar aquí: confianza media + umbral fijado (media−0.05).

## Pendiente (fuera de este dossier)

- `ocr_capable` por perfil Hermes (main vs anydesk-ops vs db) — requiere sesión Hermes.
