<#
.SYNOPSIS
    Busca secretos pegados en el arbol de IBM AGENT.
.DESCRIPTION
    Escanea archivos de texto (codigo, config, datos) buscando claves y tokens
    con valor real. No imprime el valor: solo archivo, linea, patron y longitud.
    Exit 0 = sin secretos; exit 1 = hallazgos; exit 2 = error de uso.
.PARAMETER Path
    Archivo o directorio a escanear. Default: raiz del repo (padre de scripts\).
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\check_secrets.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\check_secrets.ps1 -Path "$env:TEMP\fake-secret.txt"
#>
[CmdletBinding()]
param(
    [string]$Path = ''
)

$ErrorActionPreference = 'Stop'

if (-not $Path) {
    if ($PSScriptRoot) {
        $Path = Split-Path -Parent $PSScriptRoot
    } else {
        $Path = (Get-Location).Path
    }
}

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "No existe la ruta: $Path"
    exit 2
}

$extensiones = @(
    '.py', '.ps1', '.bat', '.cmd', '.json', '.csv', '.txt',
    '.env', '.ini', '.cfg', '.yml', '.yaml', '.toml'
)

# Carpetas de auditoria/documentacion: contienen los patrones como ejemplo.
$excluirDirs = @('.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'FINIQUITO', 'evidencia', 'docs', 'backups')

$excluirArchivos = @('*.example.json', '*.zip', '*.png', '*.jpg', '*.jpeg',
    '*.gif', '*.log', '*.pyc', '*.bak')

$patrones = @(
    @{ Nombre = 'OpenCode key';        Regex = 'oc_sk_[A-Za-z0-9_-]{8,}' },
    @{ Nombre = 'api_key con valor';   Regex = 'api_key\s*[:=]\s*["''][^"'']{8,}["'']' },
    @{ Nombre = 'password con valor';  Regex = 'password\s*[:=]\s*["''][^"'']{4,}["'']' },
    @{ Nombre = 'Bearer con token';    Regex = 'Bearer\s+[A-Za-z0-9._\-]{10,}' },
    @{ Nombre = 'token en URL';        Regex = '[?&]token=[A-Za-z0-9._\-]{8,}' },
    @{ Nombre = 'token asignado';      Regex = 'token\s*=\s*["''][A-Za-z0-9._\-]{8,}["'']' }
)

function Get-Archivos {
    param([string]$Ruta)
    if (Test-Path -LiteralPath $Ruta -PathType Leaf) {
        return @(Get-Item -LiteralPath $Ruta)
    }
    $items = Get-ChildItem -LiteralPath $Ruta -Recurse -File -Force -ErrorAction SilentlyContinue
    return @($items | Where-Object {
        $rel = $_.FullName.Substring($Ruta.Length).TrimStart('\')
        $partes = $rel -split '[\\/]'
        $enExcluida = $false
        foreach ($p in $partes) {
            if ($excluirDirs -contains $p) { $enExcluida = $true; break }
        }
        if ($enExcluida) { return $false }
        if ($extensiones -notcontains $_.Extension.ToLower()) { return $false }
        foreach ($pat in $excluirArchivos) {
            if ($_.Name -like $pat) { return $false }
        }
        return $true
    })
}

$archivos = @(Get-Archivos -Ruta $Path)
$hallazgos = 0

foreach ($archivo in $archivos) {
    $lineas = @(Get-Content -LiteralPath $archivo.FullName -ErrorAction SilentlyContinue)
    for ($i = 0; $i -lt $lineas.Count; $i++) {
        $linea = $lineas[$i]
        foreach ($p in $patrones) {
            $m = [regex]::Match($linea, $p.Regex)
            if ($m.Success) {
                $valor = $m.Value
                $largo = $valor.Length
                $visible = $valor.Substring(0, [Math]::Min(6, $largo))
                Write-Output ("{0}:{1}  {2}  valor={3}... (len={4})" -f `
                    $archivo.FullName, ($i + 1), $p.Nombre, $visible, $largo)
                $hallazgos++
                break
            }
        }
    }
}

Write-Output ""
Write-Output ("Archivos escaneados: {0}" -f $archivos.Count)
if ($hallazgos -gt 0) {
    Write-Output ("SECRETOS DETECTADOS: {0}" -f $hallazgos)
    exit 1
}

Write-Output "sin secretos"
exit 0
