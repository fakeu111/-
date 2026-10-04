$root = $PSScriptRoot
$exe = Get-ChildItem -Path (Join-Path $root "dist") -Recurse -Filter "*.exe" |
       Where-Object { $_.Name -notmatch '^python' } |
       Select-Object -First 1 -ExpandProperty FullName
$py = Join-Path $root ".venv\Scripts\python.exe"
$tmpDir = Join-Path $env:TEMP "studydisk_exe_persist"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$db = Join-Path $tmpDir "persist.db"
Remove-Item $db -ErrorAction SilentlyContinue
$env:STUDYDESK_DB = $db
& $py (Join-Path $root "dev_seed_verify.py") $db seed
for ($i = 1; $i -le 2; $i++) {
    $p = Start-Process -FilePath $exe -PassThru
    Start-Sleep -Seconds 8
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Start-Sleep -Seconds 1
}
& $py (Join-Path $root "dev_seed_verify.py") $db check
