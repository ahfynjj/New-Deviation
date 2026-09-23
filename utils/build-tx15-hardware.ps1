[CmdletBinding()]
param(
    [string]$ArmRoot = (Join-Path $env:TEMP 'new-deviation-arm8'),
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$gcc = Join-Path $ArmRoot 'bin\arm-none-eabi-gcc.exe'
$objcopy = Join-Path $ArmRoot 'bin\arm-none-eabi-objcopy.exe'
$size = Join-Path $ArmRoot 'bin\arm-none-eabi-size.exe'
foreach ($tool in @($gcc, $objcopy, $size)) {
    if (!(Test-Path -LiteralPath $tool)) { throw "Missing Arm tool: $tool" }
}
$out = 'local/tx15-hardware/ram-probe'
$source = 'hardware/tx15/ram_probe'
Push-Location $repo
try {
    New-Item -ItemType Directory -Path $out -Force | Out-Null
    $flags = @('-mcpu=cortex-m7', '-mthumb', '-mfloat-abi=soft', '-std=c11',
               '-Os', '-g3', '-ffreestanding', '-fno-builtin', '-fno-common',
               '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror')
    & $gcc @flags -c "$source/startup.S" -o "$out/startup.o"
    if ($LASTEXITCODE -ne 0) { throw 'Startup assembly failed' }
    & $gcc @flags -c "$source/probe.c" -o "$out/probe.o"
    if ($LASTEXITCODE -ne 0) { throw 'Probe compilation failed' }
    & $gcc @flags -nostdlib '-Wl,--gc-sections' "-Wl,-Map,$out/ram-probe.map" `
        -T "$source/ram.ld" "$out/startup.o" "$out/probe.o" -o "$out/ram-probe.elf"
    if ($LASTEXITCODE -ne 0) { throw 'RAM link failed' }
    & $Python utils/hardware/check_ram_elf.py "$out/ram-probe.elf"
    if ($LASTEXITCODE -ne 0) { throw 'ELF validation failed' }
    & $objcopy -O binary "$out/ram-probe.elf" "$out/ram-probe.bin"
    if ($LASTEXITCODE -ne 0) { throw 'RAM binary generation failed' }
    & $size "$out/ram-probe.elf"
    if ($LASTEXITCODE -ne 0) { throw 'Size inspection failed' }
    Write-Output "Built RAM-only diagnostic at $out; no device accessed, no flash image generated."
} finally {
    Pop-Location
}
