<#
build.ps1 - Compile-check and package PhyNodes into an installable extension zip.

The zip is built with blender_manifest.toml at its root (required for Blender's
"Install from Disk"), excluding .git / __pycache__ / *.pyc / build outputs.

Usage:
  .\build.ps1                 # compile-check + build phynodes-<version>.zip
  .\build.ps1 -Sync           # also copy the addon into Blender's extensions dir
  .\build.ps1 -Sync -Blender 5.2
  .\build.ps1 -NoCompile      # skip the py_compile check
#>
param(
    [switch]$Sync,
    [switch]$NoCompile,
    [string]$Blender = "5.2"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# --- read id + version from the manifest ---
$manifest = Get-Content (Join-Path $root "blender_manifest.toml")
$id      = ($manifest | Select-String '^\s*id\s*=\s*"(.+)"').Matches.Groups[1].Value
$version = ($manifest | Select-String '^\s*version\s*=\s*"(.+)"').Matches.Groups[1].Value
Write-Host "PhyNodes  id=$id  version=$version" -ForegroundColor Cyan

# --- compile check ---
if (-not $NoCompile) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Warning "python not found on PATH - skipping compile check"
    } else {
        Write-Host "Compiling..." -NoNewline
        $files = Get-ChildItem -Recurse -Filter *.py |
            Where-Object { $_.FullName -notmatch '\\__pycache__\\' }
        & $py.Source -m py_compile @($files.FullName)
        if ($LASTEXITCODE -ne 0) { throw "compile failed" }
        Write-Host " OK" -ForegroundColor Green
    }
}

# --- build the zip (manifest at archive root) ---
$tmp = Join-Path $env:TEMP "phynodes_build"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
robocopy $root $tmp /E /XD .git __pycache__ .vscode .github tests .pytest_cache /XF *.pyc *.zip | Out-Null
# robocopy uses exit codes 0-7 for success; normalize so the script doesn't look failed.
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" } else { $global:LASTEXITCODE = 0 }
$zip = Join-Path $root "$id-$version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$tmp\*" -DestinationPath $zip
Remove-Item $tmp -Recurse -Force
$kb = [math]::Round((Get-Item $zip).Length / 1KB, 1)
Write-Host "Built $zip ($kb KB)" -ForegroundColor Green

# --- optional: sync into the Blender extensions folder ---
if ($Sync) {
    $ext = Join-Path $env:APPDATA "Blender Foundation\Blender\$Blender\extensions\user_default\$id"
    if (Test-Path $ext) { Remove-Item $ext -Recurse -Force }
    New-Item -ItemType Directory -Path $ext -Force | Out-Null
    robocopy $root $ext /E /XD .git __pycache__ .vscode .github tests .pytest_cache /XF *.pyc *.zip | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" } else { $global:LASTEXITCODE = 0 }
    Write-Host "Synced to $ext" -ForegroundColor Green
    Write-Host "Use 'Reload Scripts' in Blender (or restart) to load it."
}

exit 0
