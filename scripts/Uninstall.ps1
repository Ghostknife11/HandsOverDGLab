param([string]$GamePath = 'G:\SteamLibrary\steamapps\common\HANDS OVER Demo')
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$LiteralPath) {
    $stream = [IO.File]::OpenRead($LiteralPath)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '') }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
$gameRoot = [IO.Path]::GetFullPath($GamePath).TrimEnd('\')
if (Get-Process -Name 'Hands Over' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Join-Path $gameRoot 'Hands Over.exe') }) { throw '请先退出游戏再卸载。' }
$manifestPath = Join-Path $gameRoot 'HandsOverDGLab.install.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw '没有本模组的安装记录，不执行删除。' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.owner -ne 'HandsOverDGLab/v1') { throw '安装记录来源不匹配。' }
$remaining = @()
foreach ($entry in $manifest.files) {
    $target = [IO.Path]::GetFullPath((Join-Path $gameRoot $entry.path))
    if (-not $target.StartsWith($gameRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '卸载路径越界。' }
    if (-not (Test-Path -LiteralPath $target)) { continue }
    if ((Get-Sha256 $target) -ne $entry.sha256) {
        Write-Warning "保留已被修改的文件：$($entry.path)"
        $remaining += $entry
        continue
    }
    Remove-Item -LiteralPath $target
}
if ($remaining.Count) {
    @{ owner = $manifest.owner; version = $manifest.version; files = $remaining } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
} else { Remove-Item -LiteralPath $manifestPath }
Write-Output '已移除安装记录中未被修改的文件。游戏原文件、配置、日志和首次运行生成的缓存予以保留。'
