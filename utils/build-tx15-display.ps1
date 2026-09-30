[CmdletBinding()]
param(
    [string]$ArmRoot = (Join-Path $env:TEMP 'new-deviation-arm8'),
    [string]$Python = 'python',
    [switch]$InputDemo
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$gcc = Join-Path $ArmRoot 'bin\arm-none-eabi-gcc.exe'
$objcopy = Join-Path $ArmRoot 'bin\arm-none-eabi-objcopy.exe'
$size = Join-Path $ArmRoot 'bin\arm-none-eabi-size.exe'
foreach ($tool in @($gcc, $objcopy, $size)) {
    if (!(Test-Path -LiteralPath $tool)) { throw "Missing Arm tool: $tool" }
}
$name = if ($InputDemo) { 'input-demo' } else { 'display-demo' }
$out = "local/tx15-hardware/$name"
$source = 'hardware/tx15/ram_probe'
Push-Location $repo
try {
    New-Item -ItemType Directory -Path $out -Force | Out-Null
    $flags = @('-mcpu=cortex-m7', '-mthumb', '-mfloat-abi=soft', '-std=c11',
               '-Os', '-g3', '-ffreestanding', '-fno-builtin', '-fno-common',
               '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror')
    $inputObjects = @()
    if ($InputDemo) {
        $flags += '-DTX15_INPUT_DEMO'
        foreach ($unit in @('inputs', 'input_filter')) {
            & $gcc @flags -c "hardware/tx15/board/$unit.c" -o "$out/$unit.o"
            if ($LASTEXITCODE -ne 0) { throw "Input compilation failed: $unit" }
            $inputObjects += "$out/$unit.o"
        }
    }
    & $gcc @flags -c "$source/startup.S" -o "$out/startup.o"
    if ($LASTEXITCODE -ne 0) { throw 'Startup assembly failed' }
    & $gcc @flags -c "hardware/tx15/display_demo/main.c" -o "$out/probe.o"
    if ($LASTEXITCODE -ne 0) { throw 'Probe compilation failed' }
    & $gcc @flags -c 'hardware/tx15/board/power.c' -o "$out/power.o"
    if ($LASTEXITCODE -ne 0) { throw 'Power driver compilation failed' }
    & $gcc @flags -c 'hardware/tx15/board/clock.c' -o "$out/clock.o"
    if ($LASTEXITCODE -ne 0) { throw 'Clock driver compilation failed' }
    & $gcc @flags -c 'hardware/tx15/board/pll.c' -o "$out/pll.o"
    if ($LASTEXITCODE -ne 0) { throw 'PLL driver compilation failed' }
    & $gcc @flags -c 'hardware/tx15/board/sdram.c' -o "$out/sdram.o"
    if ($LASTEXITCODE -ne 0) { throw 'SDRAM driver compilation failed' }
    & $gcc @flags -c 'hardware/tx15/board/display.c' -o "$out/display.o"
    if ($LASTEXITCODE -ne 0) { throw 'Display driver compilation failed' }
    & $gcc @flags -nostdlib '-Wl,--gc-sections' "-Wl,-Map,$out/$name.map" `
        -T "hardware/tx15/display_demo/display.ld" "$out/startup.o" "$out/probe.o" "$out/power.o" "$out/clock.o" "$out/pll.o" "$out/sdram.o" "$out/display.o" @inputObjects -o "$out/$name.elf"
    if ($LASTEXITCODE -ne 0) { throw 'RAM link failed' }
    & $Python utils/hardware/check_ram_elf.py "$out/$name.elf"
    if ($LASTEXITCODE -ne 0) { throw 'ELF validation failed' }
    & $objcopy -O binary "$out/$name.elf" "$out/$name.bin"
    if ($LASTEXITCODE -ne 0) { throw 'RAM binary generation failed' }
    & $size "$out/$name.elf"
    if ($LASTEXITCODE -ne 0) { throw 'Size inspection failed' }
    Write-Output "Built RAM-only display demo at $out; no device accessed, no flash image generated."
} finally {
    Pop-Location
}
