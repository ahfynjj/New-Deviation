[CmdletBinding()]
param(
    [string]$NativeRoot = (Join-Path $env:TEMP 'new-deviation-ucrt64')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$exe = Join-Path $repo 'src\emu_tx15.exe'
$runtime = Join-Path $repo 'local\tx15'
if (!(Test-Path -LiteralPath $exe)) {
    throw 'Build first: .\utils\build-msys2.ps1 -Target emu_tx15'
}
if (!(Test-Path -LiteralPath $runtime)) {
    New-Item -ItemType Directory -Path (Join-Path $repo 'local') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repo 'src\filesystem\tx15') -Destination $runtime -Recurse
}
$oldPath = $env:PATH
$oldFilesystem = $env:DEVIATION_EMU_FILESYSTEM
$oldCapture = $env:DEVIATION_EMU_CAPTURE
try {
    $env:PATH = "$NativeRoot\bin;$oldPath"
    $env:DEVIATION_EMU_FILESYSTEM = '../local/tx15'
    Remove-Item Env:DEVIATION_EMU_CAPTURE -ErrorAction SilentlyContinue
    # This launcher is explicitly for the user's interactive simulator window.
    Start-Process -FilePath $exe -WorkingDirectory (Join-Path $repo 'src') -Wait
} finally {
    $env:PATH = $oldPath
    $env:DEVIATION_EMU_FILESYSTEM = $oldFilesystem
    $env:DEVIATION_EMU_CAPTURE = $oldCapture
}
