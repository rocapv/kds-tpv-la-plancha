# arrancar.ps1 — levanta el estudio entero y lo abre en Firefox.
#
#   .\arrancar.ps1              ComfyUI (si hace falta) + la web del estudio
#   .\arrancar.ps1 -SinComfy    solo la web (para guiones y tutoriales de pantalla)
#
# ComfyUI tarda en cargar y se queda en su propia ventana; la web arranca aparte.
param(
    [switch]$SinComfy,
    [int]$Puerto = 8099
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
# El motor vive fuera del repo: ComfyUI con su venv y sus 8 GB de pesos.
$kinemato = if ($env:KINEMATO) { $env:KINEMATO } else { "M:\CLAUDE\Kinemato" }
$py = "M:\CLAUDE\.venv\Scripts\python.exe"      # el estudio no necesita CUDA: habla con ComfyUI por HTTP

if (-not (Test-Path "$kinemato\ComfyUI\main.py")) {
    Write-Error "No está ComfyUI en $kinemato. Instálalo con $kinemato\instalar_todo.ps1 o pon KINEMATO."
    exit 1
}

if (-not (Test-Path $py)) { Write-Error "No está $py"; exit 1 }

function Responde($url) {
    try { (Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
    catch { $false }
}

if (-not $SinComfy) {
    if (Responde "http://127.0.0.1:8188/system_stats") {
        Write-Host "==> ComfyUI ya estaba levantado"
    } else {
        Write-Host "==> arrancando ComfyUI (tarda ~40 s en cargar los modelos)"
        Start-Process -FilePath "$kinemato\.venv\Scripts\python.exe" `
            -ArgumentList @("main.py", "--listen", "127.0.0.1", "--port", "8188",
                            "--disable-auto-launch",
                            "--output-directory", "$kinemato\outputs",
                            "--input-directory", "$kinemato\references") `
            -WorkingDirectory "$kinemato\ComfyUI" -WindowStyle Minimized
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 3
            if (Responde "http://127.0.0.1:8188/system_stats") { break }
        }
    }

    # Aviso, no bloqueo: con la tarjeta ocupada el estudio sigue sirviendo para
    # guiones y para tutoriales de pantalla, que no gastan GPU.
    $libre = (& nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) -as [int]
    if ($libre -lt 5200) {
        Write-Host "==> OJO: solo $libre MiB libres en la GPU. Mira quien la tiene:" -ForegroundColor Yellow
        & "$env:USERPROFILE\.lmstudio\bin\lms.exe" ps 2>$null
    }
}

Write-Host "==> arrancando el estudio en http://127.0.0.1:$Puerto"
Start-Process -FilePath $py -ArgumentList @("estudio_cli.py", "web", "--puerto", "$Puerto") `
    -WorkingDirectory $root -WindowStyle Minimized
Start-Sleep -Seconds 2

# El HTML se abre SIEMPRE en Firefox y SIEMPRE con sello de tiempo, para no
# quedarse mirando una versión vieja de la página guardada en la caché.
$url = "http://127.0.0.1:$Puerto/?v=$([int][double]::Parse((Get-Date -UFormat %s)))"
$firefox = "C:\Program Files\Mozilla Firefox\firefox.exe"
if (Test-Path $firefox) { & $firefox $url } else { Start-Process $url }
Write-Host "==> listo: $url"
