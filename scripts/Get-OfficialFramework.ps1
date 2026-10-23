# SPDX-License-Identifier: GPL-3.0-only
param(
    [string]$CacheRoot = (Join-Path $env:LOCALAPPDATA 'HandsOverDGLab\downloads'),
    [string]$ArchivePath
)
$ErrorActionPreference = 'Stop'
function Get-ArchiveHash([string]$LiteralPath) {
    $stream = [IO.File]::OpenRead($LiteralPath)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '') }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
$expected = '7e2c83e38db7744d6457839bc869b311aa29a47517938a3a7643be24d00c72ec'
$url = 'https://builds.bepinex.dev/projects/bepinex_be/790/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.790%2B4e98359.zip'
$cache = [IO.Path]::GetFullPath($CacheRoot).TrimEnd('\')
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$supplied = -not [string]::IsNullOrEmpty($ArchivePath)
if (-not $supplied) { $ArchivePath = Join-Path $cache 'BepInEx-790.zip' }
$valid = (Test-Path -LiteralPath $ArchivePath) -and ((Get-ArchiveHash $ArchivePath) -eq $expected)
if (-not $valid -and $supplied) { throw 'BepInEx archive SHA-256 mismatch; no extraction or installation performed.' }
if (-not $valid) {
    Write-Host 'Downloading fixed BepInEx build 790 from the official server (about 34 MB)...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $partial = Join-Path $cache ('BepInEx-790-' + [Guid]::NewGuid().ToString('N') + '.zip')
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $partial
    if ((Get-ArchiveHash $partial) -ne $expected) { throw 'Official download SHA-256 mismatch; installation stopped.' }
    Move-Item -LiteralPath $partial -Destination $ArchivePath -Force
}
# Always extract a verified archive afresh; do not trust an older extracted cache.
$destination = [IO.Path]::GetFullPath((Join-Path $cache ('framework-' + [Guid]::NewGuid().ToString('N'))))
if (-not $destination.StartsWith($cache + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Cache path escaped selected directory.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $destination)
if (-not (Test-Path -LiteralPath (Join-Path $destination 'BepInEx\core\BepInEx.Unity.IL2CPP.dll'))) { throw 'Unexpected official archive layout.' }
Write-Output $destination
