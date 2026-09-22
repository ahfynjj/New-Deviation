[CmdletBinding()]
param(
    [ValidateSet('test', 'runner', 'devo8', 'emu_devo8', 'lint')]
    [string]$Target = 'test',
    [string]$ToolsRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) '..\tools'),
    [string]$NativeRoot = (Join-Path $env:TEMP 'new-deviation-ucrt64'),
    [string]$ArmRoot = (Join-Path $env:TEMP 'new-deviation-arm8'),
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'
$toolsPath = (Resolve-Path -LiteralPath $ToolsRoot).Path
$bashPath = Join-Path $toolsPath 'msys64\usr\bin\bash.exe'
if (!(Test-Path -LiteralPath $bashPath)) {
    throw "MSYS2 is missing at $bashPath. See docs/tx15/build.md."
}
if ($Target -eq 'emu_devo8' -and !(Test-Path -LiteralPath (Join-Path $NativeRoot 'bin\g++.exe'))) {
    throw "Native compiler is missing at $NativeRoot. See docs/tx15/build.md."
}
if ($Target -eq 'devo8' -and !(Test-Path -LiteralPath (Join-Path $ArmRoot 'bin\arm-none-eabi-gcc.exe'))) {
    throw "Arm compiler is missing at $ArmRoot. See docs/tx15/build.md."
}
$scriptPath = (Join-Path $PSScriptRoot 'build-msys2.sh').Replace('\', '/')
& $bashPath --noprofile --norc $scriptPath $Target $toolsPath $NativeRoot ([int]$Rebuild.IsPresent) $ArmRoot
exit $LASTEXITCODE
