param([string]$Python, [string]$Output)
$ErrorActionPreference='Stop'
$repoPath=Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python=Join-Path $repoPath 'local/tx15-usb-venv/Scripts/python.exe' }
if (-not $Output) { $Output=Join-Path $repoPath 'local/tx15-usb-release' }
$resolvedOutput=[System.IO.Path]::GetFullPath($Output)
$work=Join-Path $repoPath 'local/tx15-updater-build'
& $Python -m pip install -r (Join-Path $PSScriptRoot 'usb_update/requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Updater dependency install failed' }
& $Python -m PyInstaller --noconfirm --onedir --windowed --name NewDeviationUpdater --paths $PSScriptRoot --distpath $resolvedOutput --workpath $work --specpath $work (Join-Path $PSScriptRoot 'run-tx15-updater.py')
if ($LASTEXITCODE -ne 0) { throw 'Updater packaging failed' }
Write-Output (Join-Path $resolvedOutput 'NewDeviationUpdater/NewDeviationUpdater.exe')
