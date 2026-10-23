param(
    [string]$GamePath = 'G:\SteamLibrary\steamapps\common\HANDS OVER Demo',
    [string]$FrameworkPath = (Join-Path $PSScriptRoot '..\framework'),
    [string]$PluginPath = (Join-Path $PSScriptRoot '..\plugin\HandsOverDGLab.dll'),
    [switch]$FrameworkOnly
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$LiteralPath) {
    $stream = [IO.File]::OpenRead($LiteralPath)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '') }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
$gameRoot = [IO.Path]::GetFullPath($GamePath).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $gameRoot 'Hands Over.exe'))) { throw '未找到 Hands Over.exe，请检查游戏目录。' }
if (Get-Process -Name 'Hands Over' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Join-Path $gameRoot 'Hands Over.exe') }) { throw '请先退出游戏再安装。' }
$manifestPath = Join-Path $gameRoot 'HandsOverDGLab.install.json'
$entries = @()
if (Test-Path -LiteralPath $manifestPath) {
    $old = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($old.owner -ne 'HandsOverDGLab/v1') { throw '安装记录来源不匹配。' }
    $entries = @($old.files)
}
if (-not (Test-Path -LiteralPath $FrameworkPath)) {
    if ($PSBoundParameters.ContainsKey('FrameworkPath')) { throw '指定的 framework 文件夹不存在。' }
    $FrameworkPath = & (Join-Path $PSScriptRoot 'Get-OfficialFramework.ps1')
}
$frameworkRoot = [IO.Path]::GetFullPath($FrameworkPath).TrimEnd('\')
$copies = @()
Get-ChildItem -LiteralPath $frameworkRoot -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($frameworkRoot.Length + 1)
    $copies += [pscustomobject]@{ source = $_.FullName; relative = $relative }
}
if (-not $FrameworkOnly) {
    if (-not (Test-Path -LiteralPath $PluginPath)) { throw '缺少游戏插件 DLL。' }
    $copies += [pscustomobject]@{ source = [IO.Path]::GetFullPath($PluginPath); relative = 'BepInEx\plugins\HandsOverDGLab\HandsOverDGLab.dll' }
}
# Validate every overwrite before changing any file.
foreach ($copy in $copies) {
    $target = [IO.Path]::GetFullPath((Join-Path $gameRoot $copy.relative))
    if (-not $target.StartsWith($gameRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '安装路径越界。' }
    if (Test-Path -LiteralPath $target) {
        $currentHash = Get-Sha256 $target
        $known = @($entries | Where-Object { $_.path -eq $copy.relative })
        $sourceHash = Get-Sha256 $copy.source
        if ($known.Count -eq 0 -and $currentHash -ne $sourceHash) { throw "已有其他文件，未覆盖：$($copy.relative)" }
        if ($known.Count -gt 0 -and $currentHash -ne $known[0].sha256 -and $currentHash -ne $sourceHash) { throw "文件已被修改，未覆盖：$($copy.relative)" }
    }
}
foreach ($copy in $copies) {
    $target = Join-Path $gameRoot $copy.relative
    $existed = Test-Path -LiteralPath $target
    $known = @($entries | Where-Object { $_.path -eq $copy.relative })
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $copy.source -Destination $target -Force
    if (-not $existed -or $known.Count -gt 0) {
        $entries = @($entries | Where-Object { $_.path -ne $copy.relative })
        $entries += [pscustomobject]@{ path = $copy.relative; sha256 = (Get-Sha256 $target) }
        @{ owner = 'HandsOverDGLab/v1'; version = '0.1.3'; files = @($entries) } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    }
}
Write-Output "安装完成：$gameRoot"
Write-Output '手机设置 A/B 上限；实际反馈强度按上限百分比计算。'

