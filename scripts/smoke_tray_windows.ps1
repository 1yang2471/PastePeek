$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$exe = (Resolve-Path '.\dist\PastePeek.exe').Path
$initialIds = @(
    Get-Process PastePeek -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $exe } |
        Select-Object -ExpandProperty Id
)
$primary = $null
$secondary = $null
$backgroundSecondary = $null

function Get-NewPastePeekProcesses {
    return @(
        Get-Process PastePeek -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Path -eq $exe -and $_.Id -notin $initialIds
            }
    )
}

function Stop-NewPastePeekProcesses {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $processes = @(Get-NewPastePeekProcesses)
        if ($processes.Count -eq 0) {
            return
        }
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 100
    }
}

try {
    $primary = Start-Process `
        -FilePath $exe `
        -ArgumentList '--background' `
        -PassThru `
        -WindowStyle Hidden
    Start-Sleep -Seconds 4
    $primaryProcesses = @(Get-NewPastePeekProcesses)
    if ($primaryProcesses.Count -eq 0) {
        throw '后台首实例未保持运行'
    }
    $primaryIds = @($primaryProcesses.Id | Sort-Object)

    $secondary = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    if (-not $secondary.WaitForExit(10000)) {
        throw '手动第二实例未在 10 秒内退出'
    }
    Start-Sleep -Milliseconds 500
    $afterManualIds = @((Get-NewPastePeekProcesses).Id | Sort-Object)
    if (Compare-Object $primaryIds $afterManualIds) {
        throw '手动第二次启动改变了主实例进程集合'
    }

    $backgroundSecondary = Start-Process `
        -FilePath $exe `
        -ArgumentList '--background' `
        -PassThru `
        -WindowStyle Hidden
    if (-not $backgroundSecondary.WaitForExit(10000)) {
        throw '后台第二实例未在 10 秒内退出'
    }
    Start-Sleep -Milliseconds 500
    $afterBackgroundIds = @((Get-NewPastePeekProcesses).Id | Sort-Object)
    if (Compare-Object $primaryIds $afterBackgroundIds) {
        throw '后台第二次启动改变了主实例进程集合'
    }

    Write-Output (
        'primary_pids={0} manual_second_exit={1} background_second_exit={2}' -f `
            ($primaryIds -join ','),
            $secondary.ExitCode,
            $backgroundSecondary.ExitCode
    )
}
finally {
    Stop-NewPastePeekProcesses
}

$remaining = @(Get-NewPastePeekProcesses)
if ($remaining.Count -ne 0) {
    throw '托盘单实例冒烟遗留了 PastePeek 进程'
}
Write-Output 'tray_single_instance_cleanup=ok'
