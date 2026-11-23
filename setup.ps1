# Preflight del agente IBM. No toca datos: solo valida.
# Uso:
#   powershell -ExecutionPolicy Bypass -File setup.ps1 -Check
#   powershell -ExecutionPolicy Bypass -File setup.ps1 -Install
[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

function Fail([string]$msg) {
    Write-Host "FALLA: $msg" -ForegroundColor Red
    exit 2
}

function Warn([string]$msg) {
    Write-Host "AVISO: $msg" -ForegroundColor Yellow
}

function Ok([string]$msg) {
    Write-Host "OK: $msg" -ForegroundColor Green
}

if (-not $Check -and -not $Install) { $Check = $true }

$sibling = Join-Path (Split-Path -Parent $root) "mcp-anydesk"
$py = Join-Path $sibling ".venv\Scripts\python.exe"

if ($Install) {
    if (-not (Test-Path -LiteralPath $sibling)) {
        Fail "falta el repositorio hermano: $sibling"
    }
    if (-not (Test-Path -LiteralPath $py)) {
        Write-Host "creando venv en $sibling\.venv ..."
        $base = Get-Command python -ErrorAction SilentlyContinue
        if (-not $base) { $base = Get-Command py -ErrorAction SilentlyContinue }
        if (-not $base) { Fail "no encontre python ni py en PATH" }
        if ($base.Name -eq "py.exe" -or $base.Name -eq "py") {
            & $base.Source -3 -m venv (Join-Path $sibling ".venv")
        } else {
            & $base.Source -m venv (Join-Path $sibling ".venv")
        }
        if ($LASTEXITCODE -ne 0) { Fail "no se pudo crear el venv" }
    }
    $req = Join-Path $root "requirements.txt"
    if (Test-Path -LiteralPath $req) {
        & $py -m pip install -r $req
        if ($LASTEXITCODE -ne 0) { Fail "pip install fallo" }
    } else {
        Warn "no hay requirements.txt; se usa el venv existente"
    }
    $example = Join-Path $root "config\jev.example.json"
    $target = Join-Path $root "config\jev.json"
    if ((Test-Path -LiteralPath $example) -and -not (Test-Path -LiteralPath $target)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $example -Destination $target
        Warn "config\jev.json creado desde el example; completar la clave o dejar Jev apagado"
    }
}

# --- Checks ---
if (-not (Test-Path -LiteralPath $py)) {
    Fail "Falta ..\mcp-anydesk\.venv\Scripts\python.exe. Instala el repositorio hermano mcp-anydesk o crea el venv con -Install."
}
$ver = & $py -c "import sys; print(str(sys.version_info[0]) + '.' + str(sys.version_info[1]))" 2>&1
if ($LASTEXITCODE -ne 0) { Fail "no pude ejecutar $py : $ver" }
$ver = ($ver | Out-String).Trim()
$major, $minor = $ver.Split(".")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 11)) {
    Fail "Python $ver < 3.11"
}
Ok "Python $ver"

$csv = Join-Path $root "datos\direcciones.csv"
if (-not (Test-Path -LiteralPath $csv)) { Fail "falta datos\direcciones.csv" }
$header = (Get-Content -LiteralPath $csv -TotalCount 1) -replace "^\uFEFF", ""
if ($header -notmatch "^[^;]+;[^;]+;[^;]+$") {
    Fail "direcciones.csv no tiene 3 columnas separadas por ';': $header"
}
Ok "direcciones.csv con 3 columnas"

$pycache = Join-Path $root "tools\__pycache__"
$hadPycache = Test-Path -LiteralPath $pycache
$out = & $py -m compileall -q (Join-Path $root "tools") 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail ("compileall fallo en tools\: " + (($out | Out-String).Trim()))
}
if (-not $hadPycache -and (Test-Path -LiteralPath $pycache)) {
    Remove-Item -LiteralPath $pycache -Recurse -Force -ErrorAction SilentlyContinue
}
Ok "compileall tools\"

$mods = & $py -c "import importlib.util as u; ms=['mss','PIL','pytesseract','win32api','cv2','numpy','mcp']; print(','.join(m for m in ms if u.find_spec(m) is None))" 2>&1
if ($LASTEXITCODE -eq 0) {
    $mods = ($mods | Out-String).Trim()
    if ($mods) { Warn "faltan modulos Python en el venv: $mods" }
} else {
    Warn "no pude comprobar los modulos Python del venv"
}
$tess = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tess) { Warn "Tesseract no esta en PATH" }

$jev = Join-Path $root "config\jev.json"
if (-not (Test-Path -LiteralPath $jev)) {
    Warn "Jev sin config\jev.json: quedara apagado (recomendado)."
}

$writable = Join-Path $root "datos\.preflight-write-test"
try {
    Set-Content -LiteralPath $writable -Value "ok" -Encoding ASCII
    Remove-Item -LiteralPath $writable -Force
    Ok "datos\ es escribible"
} catch {
    Fail "datos\ no es escribible: $($_.Exception.Message)"
}

$anydesk = Get-Process -Name "AnyDesk" -ErrorAction SilentlyContinue
if (-not $anydesk) {
    Warn "no veo AnyDesk abierto: el agente no podra inyectar"
}

Write-Host "preflight OK" -ForegroundColor Green
exit 0
