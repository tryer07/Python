$ErrorActionPreference = "Continue"
$game = "D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版"
$pyi  = "D:\Python\Python项目存放点\.venv\Scripts\pyinstaller.exe"
$log  = Join-Path $game "_build_log.txt"

Set-Location $game
Write-Output "CWD=$(Get-Location)"
Write-Output "PYI_EXISTS=$(Test-Path $pyi)"
Write-Output "SPEC_EXISTS=$(Test-Path (Join-Path $game '鳞光纪.spec'))"

if (Test-Path $log) { Remove-Item -Force $log }

& $pyi --noconfirm "鳞光纪.spec" *> $log
$code = $LASTEXITCODE
Write-Output "PYINSTALLER_EXIT=$code"
Write-Output "----- last 22 lines of build log -----"
Get-Content $log -Tail 22
