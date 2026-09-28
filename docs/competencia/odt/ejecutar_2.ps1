# Ejecuta el paso 2 (macro de LibreOffice) con un perfil limpio y enseña su salida.
$aqui = $PSScriptRoot
$script = Join-Path $aqui "2_odt.py"
$out = Join-Path $aqui "_trabajo\salida.txt"
$err = Join-Path $aqui "_trabajo\errores.txt"
$p = Start-Process -FilePath "C:\Program Files\LibreOffice\program\python.exe" -ArgumentList @("-X", "faulthandler", "`"$script`"") -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
"exit $($p.ExitCode)"
Get-Content -LiteralPath $out
Get-Content -LiteralPath $err | Select-Object -Last 25
