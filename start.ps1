# local-chat-search - Windows PowerShell one-click start
# 用法（在仓库根目录）：
#   powershell -ExecutionPolicy Bypass -File .\start.ps1
#   或右键「使用 PowerShell 运行」
param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if ($Port -le 0) {
    if ($env:CHAT_SEARCH_PORT) { $Port = [int]$env:CHAT_SEARCH_PORT } else { $Port = 8777 }
}

$probe = "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"

$candidates = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += ,@("py", "-3") }
foreach ($n in @("python", "python3")) {
    if (Get-Command $n -ErrorAction SilentlyContinue) { $candidates += ,@($n) }
}

$py = $null
foreach ($c in $candidates) {
    $exe = $c[0]
    $pre = @()
    if ($c.Count -gt 1) { $pre = $c[1..($c.Count - 1)] }
    & $exe @pre -c $probe 2>$null
    if ($LASTEXITCODE -eq 0) { $py = @{ exe = $exe; pre = $pre }; break }
}

if (-not $py) {
    Write-Host ""
    Write-Host "[X] Python 3.8+ not found. 未检测到 Python 3.8 或更高版本。" -ForegroundColor Red
    Write-Host "    请到 https://www.python.org/downloads/ 下载安装，"
    Write-Host "    安装时务必勾选 `"Add python.exe to PATH`"。"
    Write-Host ""
    Read-Host "按回车退出"
    exit 1
}

Write-Host ("Using: {0} {1}   Port: {2}" -f $py.exe, ($py.pre -join " "), $Port)
$launchArgs = @($py.pre) + @("app/server.py", "--port", "$Port")
& $py.exe @launchArgs
$code = $LASTEXITCODE

Write-Host ""
Write-Host "Service stopped. 服务已停止。（退出码 $code）"
Read-Host "按回车关闭窗口"
exit $code
