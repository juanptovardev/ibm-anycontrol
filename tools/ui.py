"""Panel de control y observacion del sistema.

Solo lectura sobre el estado (traza, ledger, capturas) y una bandera de
control que el bucle consulta entre bloques.

Uso: python tools/ui.py            -> http://127.0.0.1:8765/?k=<token>
     python tools/ui.py --puerto 9000

Escucha en 0.0.0.0 para poder mirarlo desde el celular en la misma red.
Toda peticion exige el token (?k=...): sin el responde 403 porque el panel
muestra la pantalla del remoto y direcciones de clientes.
"""
import csv
import json
import os
import secrets
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
DATOS = REPO / "datos"
EVID = REPO / "evidencia"
CTRL = DATOS / "control.json"
PUERTO = 8765


def _token():
    """Token de acceso. Env MATRIZ_TOKEN o datos/ui_token.txt (se crea solo)."""
    tok = (os.environ.get("MATRIZ_TOKEN") or "").strip()
    if tok:
        return tok
    p = DATOS / "ui_token.txt"
    try:
        t = p.read_text(encoding="utf-8").strip()
        if t:
            return t
    except OSError:
        pass
    DATOS.mkdir(exist_ok=True)
    t = secrets.token_hex(4)
    p.write_text(t, encoding="utf-8")
    return t


TOKEN = _token()


def ip_red():
    """IP de esta maquina en la red local (la que se abre desde el celular)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def matar():
    """Mata el arbol del agente (autonomo/loop/supervisor). NO mata el panel."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'autonomo\\.py|loop\\.py|supervisor' "
        "-and $_.CommandLine -notmatch 'ui\\.py' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        return ((r.stdout or "") + (r.stderr or "")).strip()[-400:]
    except (OSError, subprocess.SubprocessError) as exc:
        return f"error al matar: {exc}"


def ultima_captura():
    if not EVID.exists():
        return None
    imgs = sorted(EVID.glob("native-*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return imgs[0] if imgs else None


def eventos(n=14):
    p = DATOS / "traza.jsonl"
    if not p.exists():
        return []
    lineas = p.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-n:]
    out = []
    for linea in lineas:
        try:
            out.append(json.loads(linea))
        except ValueError:
            continue
    return out


def ledger():
    p = DATOS / "ledger.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def control_actual():
    try:
        return json.loads(CTRL.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"accion": "libre"}


def normaliza_accion(accion):
    """Convierte el texto visible del panel al contrato del supervisor."""
    accion = "libre" if accion == "reanudar" else accion
    if accion not in ("libre", "pausar", "detener"):
        raise ValueError("accion invalida")
    return accion


def estado():
    cap = ultima_captura()
    evs = eventos()
    ultimo = evs[-1] if evs else {}
    filas = ledger()
    return {
        "captura": cap.name if cap else None,
        "captura_ts": cap.stat().st_mtime if cap else 0,
        "ultimo": ultimo,
        "eventos": evs[-8:],
        "ledger": filas[-8:],
        "total_ledger": len(filas),
        "control": control_actual(),
    }


HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>MATRIZ · control</title>
<style>
:root{--bg:#0c0f0c;--fg:#c8f7c5;--dim:#5d7a5b;--line:#1e2a1e;
--ok:#54e06a;--warn:#e0c454;--bad:#e05a5a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.45 Consolas,monospace}
header{display:flex;justify-content:space-between;align-items:center;
padding:10px 16px;border-bottom:1px solid var(--line)}
h1{font-size:13px;margin:0;letter-spacing:2px;color:var(--dim)}
#punto{color:var(--warn)}
main{display:grid;grid-template-columns:210px 1fr 340px;gap:1px;
background:var(--line);height:calc(100vh - 46px)}
section{background:var(--bg);padding:10px 12px;overflow:auto}
h2{font-size:11px;letter-spacing:1.5px;color:var(--dim);margin:0 0 8px}
.etapa{display:flex;gap:8px;padding:3px 0;color:var(--dim)}
.etapa.on{color:var(--fg)}
.etapa.on b{color:var(--ok)}
.pip{width:8px;height:8px;border-radius:50%;background:#25301f;margin-top:5px}
.etapa.on .pip{background:var(--ok);box-shadow:0 0 6px var(--ok)}
img{width:100%;border:1px solid var(--line);display:block}
.meta{margin-top:6px;color:var(--dim);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px}
td{padding:2px 4px;border-bottom:1px solid #141c14;vertical-align:top}
td.k{color:var(--dim);white-space:nowrap}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
footer{position:fixed;bottom:0;left:0;right:0;display:flex;gap:8px;
padding:8px 16px;background:#0a0d0a;border-top:1px solid var(--line)}
button{background:#131a13;color:var(--fg);border:1px solid #2a3a2a;
 padding:6px 14px;font:inherit;cursor:pointer}
button:hover{background:#1a241a}
button.stop{color:var(--bad);border-color:#4a2020}
@media (max-width:700px){
 body{font-size:12px;padding-bottom:76px}
 header{padding:10px 12px;gap:10px;align-items:flex-start}
 h1{font-size:12px;letter-spacing:1px}
 #punto{font-size:11px;text-align:right;overflow-wrap:anywhere}
 main{display:block;height:auto;background:var(--line)}
 section{padding:12px;min-height:0;border-bottom:1px solid var(--line)}
 section:first-child{padding-bottom:10px}
 section:nth-child(2){padding-top:12px}
 section:last-child{padding-bottom:14px}
 h2{font-size:11px;margin-bottom:9px}
 .etapa{padding:4px 0;min-height:24px}
 .pip{flex:0 0 8px}
 img{width:100%;height:auto;max-height:46vh;object-fit:contain;object-position:top center}
 .meta{font-size:11px;overflow-wrap:anywhere}
 table{font-size:11px;table-layout:fixed;overflow-wrap:anywhere}
 td{padding:5px 4px;word-break:break-word}
 td.k{white-space:normal;width:auto}
 footer{position:fixed;z-index:10;flex-wrap:wrap;gap:6px;
  padding:8px 10px calc(8px + env(safe-area-inset-bottom));
  background:#0a0d0a;box-shadow:0 -4px 12px rgba(0,0,0,.35)}
 button{min-height:44px;min-width:44px;flex:1 1 calc(50% - 6px);padding:8px 10px}
}
</style></head><body>
<header><h1>MATRIZ · CONTROL</h1><div id="punto">—</div></header>
<main>
<section><h2>SEMAFORO</h2><div id="etapas"></div>
<div class="meta" id="control"></div></section>
<section><h2>PANTALLA REMOTA</h2>
<img id="cap" alt="sin captura"><div class="meta" id="capmeta"></div></section>
<section><h2>LEDGER</h2><table id="ledger"></table>
<h2 style="margin-top:14px">TRAZA</h2><table id="traza"></table></section>
</main>
<footer><button type="button" onclick="ctl('pausar')">PAUSAR</button>
<button type="button" onclick="ctl('reanudar')">REANUDAR</button>
<button type="button" class="stop" onclick="ctl('detener')">DETENER</button>
<button type="button" class="stop" onclick="matar()">MATAR</button></footer>
<script>
const ETAPAS=["entorno","pin","estado","buscar","extraer","volver","pagina","reconectar","registrar","cierre"];
const K='__TOKEN__';
async function ctl(a){
 const accion=a==='reanudar'?'libre':a;
 try{
  const r=await fetch('/api/control?k='+K,{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify({accion:accion})});
  if(!r.ok)throw new Error('HTTP '+r.status);
  document.getElementById('control').textContent='control: '+(accion==='libre'?'reanudar':accion);
 }catch(e){document.getElementById('punto').textContent='control no enviado';}
}
async function matar(){if(!confirm('Matar el agente ahora? (no se puede deshacer)'))return;
await fetch('/api/matar?k='+K,{method:'POST'});}
function cls(r){if(!r)return'';if(/ok|cuenta_matriz|formulario|ficha/.test(r))return'ok';
if(/sin_coincidencia|desconocido|fin_libro/.test(r))return'warn';return'bad';}
async function tick(){
try{
const s=await fetch('/api/estado?k='+K).then(r=>r.json());
const u=s.ultimo||{},cur=u.etapa||'';
document.getElementById('etapas').innerHTML=ETAPAS.map(e=>
`<div class="etapa ${e===cur?'on':''}"><div class="pip"></div><span>${e}</span>`+
`<b>${e===cur?(u.resultado||''):''}</b></div>`).join('');
document.getElementById('punto').textContent=cur?
`${cur} · ${u.resultado||''} · ${u.accion||''}`:'sin actividad';
document.getElementById('control').textContent='control: '+(s.control||{}).accion;
if(s.captura){const img=document.getElementById('cap');
const url='/img?k='+K+'&t='+s.captura_ts;if(img.dataset.u!==url){img.dataset.u=url;img.src=url;}
document.getElementById('capmeta').textContent=s.captura;}
  document.getElementById('ledger').innerHTML='<tr><td class="k">id / estado</td><td class="k">paginas</td>'+
  '<td class="k">filas</td></tr>'+(s.ledger||[]).map(r=>
 `<tr><td>${r.id||''} / ${r.estado||''}</td><td>${r.paginas_vistas||0}</td>`+
 `<td>${r.filas_copiadas||0}</td></tr>`).join('');
document.getElementById('traza').innerHTML=(s.eventos||[]).slice().reverse().map(e=>
`<tr><td class="k">${(e.ts||'').slice(11,19)}</td><td>${e.etapa||''}</td>`+
`<td class="${cls(e.resultado)}">${e.resultado||''}</td></tr>`).join('');
}catch(e){document.getElementById('punto').textContent='panel sin conexion';}}
tick();setInterval(tick,1000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _enviar(self, code, body, tipo="application/json"):
        datos = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _autorizado(self):
        q = parse_qs(urlparse(self.path).query)
        return q.get("k", [""])[0] == TOKEN or self.headers.get("X-Token") == TOKEN

    def do_GET(self):
        if not self._autorizado():
            return self._enviar(403, b"no autorizado", "text/plain")
        if urlparse(self.path).path == "/":
            return self._enviar(200, HTML.replace("__TOKEN__", TOKEN),
                                "text/html; charset=utf-8")
        if self.path.startswith("/api/estado"):
            return self._enviar(200, json.dumps(estado(), ensure_ascii=False))
        if self.path.startswith("/img"):
            cap = ultima_captura()
            if not cap:
                return self._enviar(404, b"sin captura", "text/plain")
            return self._enviar(200, cap.read_bytes(), "image/png")
        return self._enviar(404, b"no existe", "text/plain")

    def do_POST(self):
        if not self._autorizado():
            return self._enviar(403, b"no autorizado", "text/plain")
        if self.path.startswith("/api/matar"):
            DATOS.mkdir(exist_ok=True)
            CTRL.write_text(json.dumps({"accion": "detener"}), encoding="utf-8")
            return self._enviar(200, json.dumps({"matar": matar()}))
        if not self.path.startswith("/api/control"):
            return self._enviar(404, b"no existe", "text/plain")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._enviar(400, b"json invalido", "text/plain")
        try:
            accion = normaliza_accion(cuerpo.get("accion", "libre"))
        except ValueError:
            return self._enviar(400, b"accion invalida", "text/plain")
        DATOS.mkdir(exist_ok=True)
        CTRL.write_text(json.dumps({"accion": accion}), encoding="utf-8")
        return self._enviar(200, json.dumps({"accion": accion}))


def main(argv):
    puerto = PUERTO
    if "--puerto" in argv:
        puerto = int(argv[argv.index("--puerto") + 1])
    srv = ThreadingHTTPServer(("0.0.0.0", puerto), Handler)
    print(f"panel local:   http://127.0.0.1:{puerto}/?k={TOKEN}")
    print(f"panel celular: http://{ip_red()}:{puerto}/?k={TOKEN}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
