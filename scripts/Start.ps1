# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::OSVersion.Version.Major -lt 10) {
    throw 'This release requires Windows 10/11 x64.'
}
foreach ($name in @('vcruntime140.dll', 'vcruntime140_1.dll')) {
    if (-not (Test-Path -LiteralPath (Join-Path $env:WINDIR ('System32\' + $name)))) {
        Write-Host 'Install the official Microsoft Visual C++ v14 x64 runtime, then launch again:'
        Write-Host 'https://aka.ms/vc14/vc_redist.x64.exe'
        Write-Host 'Microsoft terms apply. This project does not bundle or install it automatically.'
        exit 1
    }
}
Start-Process -FilePath (Join-Path $PSScriptRoot '..\app\HandsOverDGLab.exe') -WorkingDirectory (Join-Path $PSScriptRoot '..\app')
