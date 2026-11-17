# 作文批改器（gsat-essay-grader）安裝程式：Windows
#
# 會做的事：
#   1. 裝 Claude Code（已經有就跳過）
#   2. 確認有 Python 3.9 以上（沒有就用 winget 裝 Python 3.12）
#   3. 下載作文批改器，裝成 Claude Code 的外掛
#   4. 在「文件」建一個「作文批改」資料夾，裡面放「開始批改」捷徑
#
# 用法：雙擊 install.bat。再跑一次就是更新。
# 這個檔要存成 UTF-8（有 BOM），Windows PowerShell 5.1 才讀得懂中文。

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ZipUrl = "https://github.com/lukevin202106-hub/gsat-essay-grader/archive/refs/heads/main.zip"
$AppDir = Join-Path $env:USERPROFILE ".gsat-essay-grader"
$Docs = [Environment]::GetFolderPath("MyDocuments")
$WorkDir = if ($env:GSAT_ESSAY_HOME) { $env:GSAT_ESSAY_HOME } else { Join-Path $Docs "作文批改" }
$Plugin = "gsat-essay-grader@gsat-essay-grader"

function Bold($t) { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Fail($t) {
  Write-Host ""; Write-Host $t -ForegroundColor Red
  Write-Host ""; Write-Host "可以把這個視窗的文字截圖，到 https://github.com/lukevin202106-hub/gsat-essay-grader/issues 回報。"
  Read-Host "按 Enter 關閉" | Out-Null
  exit 1
}
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + (Join-Path $env:USERPROFILE ".local\bin")
}

Bold "作文批改器安裝程式"
Write-Host "大約需要 1～5 分鐘。過程中可能會跳出視窗請你允許或登入，照著做就好。"
Refresh-Path

# ── 1. Claude Code ──
if (Get-Command claude -ErrorAction SilentlyContinue) {
  Bold "1/4 Claude Code 已經裝好了"
} else {
  Bold "1/4 安裝 Claude Code（Anthropic 官方安裝程式）…"
  try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression } catch { Fail "Claude Code 安裝失敗：$($_.Exception.Message)" }
  Refresh-Path
  if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { Fail "找不到 claude 指令。請關掉這個視窗，再雙擊一次 install.bat。" }
}

# ── 2. Python ──
Bold "2/4 確認 Python…"
function Find-Python {
  foreach ($c in @(@("py", "-3"), @("python"), @("python3"))) {
    $exe = $c[0]; $rest = @($c | Select-Object -Skip 1)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    try {
      & $exe @rest -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
      if ($LASTEXITCODE -eq 0) { return ,$c }
    } catch { }
  }
  return $null
}
$Py = Find-Python
if (-not $Py) {
  Write-Host "沒有找到 Python，用 winget 安裝 Python 3.12…"
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail "這台電腦沒有 winget。請到 https://www.python.org/downloads/ 下載安裝 Python（安裝時勾選「Add python.exe to PATH」），裝好後再雙擊一次 install.bat。"
  }
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  Refresh-Path
  $Py = Find-Python
  if (-not $Py) {
    $guess = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path $guess) { $Py = ,@($guess) } else { Fail "Python 裝好了但還找不到。請關掉這個視窗，再雙擊一次 install.bat。" }
  }
}
$PyExe = $Py[0]; $PyArgs = @($Py | Select-Object -Skip 1)
Write-Host ("Python：" + (& $PyExe @PyArgs --version 2>&1))

# ── 3. 下載作文批改器、裝成外掛 ──
Bold "3/4 下載作文批改器…"
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
$Tmp = Join-Path $env:TEMP ("gsat-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
try {
  Invoke-WebRequest -UseBasicParsing -Uri $ZipUrl -OutFile (Join-Path $Tmp "grader.zip")
  Expand-Archive -Force -Path (Join-Path $Tmp "grader.zip") -DestinationPath $Tmp
} catch { Fail "下載失敗：$($_.Exception.Message)" }
$Dest = Join-Path $AppDir "gsat-essay-grader"
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
Move-Item (Join-Path $Tmp "gsat-essay-grader-main") $Dest
Remove-Item -Recurse -Force $Tmp

$ErrorActionPreference = "Continue"
$markets = (claude plugin marketplace list 2>$null) -join "`n"
if ($markets -match "gsat-essay-grader") {
  claude plugin marketplace update gsat-essay-grader 2>$null | Out-Null
} else {
  claude plugin marketplace add $Dest
  if ($LASTEXITCODE -ne 0) { Fail "加入外掛市集失敗。" }
}
$plugins = (claude plugin list 2>$null) -join "`n"
if ($plugins -match "gsat-essay-grader") {
  claude plugin update $Plugin
  if ($LASTEXITCODE -ne 0) { Fail "更新外掛失敗。" }
} else {
  claude plugin install $Plugin
  if ($LASTEXITCODE -ne 0) { Fail "安裝外掛失敗。" }
}
$ErrorActionPreference = "Stop"

# ── 4. 工作資料夾 ──
Bold "4/4 建立「作文批改」資料夾…"
& $PyExe @PyArgs (Join-Path $Dest "tools\ws.py") init $WorkDir | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "建不了 $WorkDir。" }
$launcher = "@echo off`r`ncd /d `"%~dp0`"`r`nset `"PATH=%USERPROFILE%\.local\bin;%PATH%`"`r`nclaude `"/gsat-essay-grader:grade`"`r`n"
[IO.File]::WriteAllText((Join-Path $WorkDir "開始批改.bat"), $launcher, [Text.Encoding]::ASCII)
$readme = @"
作文批改器 怎麼用

1. 雙擊「開始批改」。第一次會請你選配色、用瀏覽器登入 Claude（要 Pro 以上的方案），
   再問你信不信任這個資料夾，選「Yes」。
2. 把題目和學生的作文貼進去（照片可以直接拖進視窗）。
   想要最好的品質，說「用最好的」；只是試試看，說「用測試等級」。
3. 批完會在 site 資料夾產生一個網頁檔，雙擊就能看，也可以直接傳給學生。

學生的作文只存在這個資料夾，不會上傳到別的地方（Claude 批改時會讀到）。
更新：再跑一次 install.bat。說明與問題回報：https://github.com/lukevin202106-hub/gsat-essay-grader
"@
[IO.File]::WriteAllText((Join-Path $WorkDir "讀我.txt"), $readme, (New-Object System.Text.UTF8Encoding $true))

Bold "裝好了"
Write-Host "「文件」裡多了一個「作文批改」資料夾。以後雙擊裡面的「開始批改」就能批改作文。"
Start-Process explorer.exe $WorkDir
$ans = Read-Host "要現在開始嗎？第一次會請你登入 Claude。（Y＝開始，其他鍵＝之後再說）"
if ($ans -eq "" -or $ans -match "^[Yy]") {
  Set-Location $WorkDir
  claude "/gsat-essay-grader:grade"
}
