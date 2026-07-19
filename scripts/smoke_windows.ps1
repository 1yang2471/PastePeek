$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$exe = (Resolve-Path '.\dist\PastePeek.exe').Path
$initialExeIds = @(
    Get-Process PastePeek -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $exe } |
        Select-Object -ExpandProperty Id
)
$sourceProcess = $null
$launcherProcess = $null

function Stop-NewPastePeekProcesses {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $processes = @(
            Get-Process PastePeek -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Path -eq $exe -and $_.Id -notin $initialExeIds
                }
        )
        if ($processes.Count -eq 0) {
            return
        }
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 100
    }
}

try {
    $python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
    $sourceArgs = @{
        FilePath = $python
        ArgumentList = @('src\main.py')
        PassThru = $true
        WindowStyle = 'Hidden'
    }
    $sourceProcess = Start-Process @sourceArgs
    Start-Sleep -Seconds 4
    if ($sourceProcess.HasExited) {
        throw ('源码入口提前退出，退出码：{0}' -f $sourceProcess.ExitCode)
    }
    Write-Output ('source_pid={0} alive_after_seconds=4' -f $sourceProcess.Id)
    Stop-Process -Id $sourceProcess.Id -Force
    $sourceProcess.WaitForExit()
    $sourceProcess = $null

    $launcherArgs = @{
        FilePath = $exe
        PassThru = $true
        WindowStyle = 'Hidden'
    }
    $launcherProcess = Start-Process @launcherArgs
    Start-Sleep -Seconds 4
    $newExeProcesses = @(
        Get-Process PastePeek -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $exe -and $_.Id -notin $initialExeIds }
    )
    if ($newExeProcesses.Count -eq 0) {
        throw '打包 EXE 未保持运行'
    }
    $ids = ($newExeProcesses.Id -join ',')
    Write-Output ('exe_pids={0} alive_after_seconds=4' -f $ids)
}
finally {
    if ($null -ne $sourceProcess -and -not $sourceProcess.HasExited) {
        Stop-Process -Id $sourceProcess.Id -Force
    }
    if ($null -ne $launcherProcess -and -not $launcherProcess.HasExited) {
        Stop-Process -Id $launcherProcess.Id -Force
    }
    Stop-NewPastePeekProcesses
}

$remaining = @(
    Get-Process PastePeek -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $exe -and $_.Id -notin $initialExeIds }
)
if ($remaining.Count -ne 0) {
    throw '冒烟测试遗留了 PastePeek 进程'
}
Write-Output 'cleanup=ok'
