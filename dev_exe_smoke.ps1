$exe = Get-ChildItem -Path (Join-Path $PSScriptRoot "dist") -Recurse -Filter "*.exe" |
       Where-Object { $_.Name -notmatch '^python' } |
       Select-Object -First 1 -ExpandProperty FullName
$tmpDir = Join-Path $env:TEMP "studydisk_exe_check"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$db = Join-Path $tmpDir "verify.db"
Remove-Item $db -ErrorAction SilentlyContinue
$env:STUDYDESK_DB = $db
$p = Start-Process -FilePath $exe -PassThru
Start-Sleep -Seconds 9
$alive = -not $p.HasExited
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
$dbCreated = Test-Path $db
Write-Output "EXE=$exe"
Write-Output "ALIVE=$alive"
Write-Output "DB_CREATED=$dbCreated"
