#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paso 1 del .odt: prepara un HTML estático que LibreOffice Writer pueda importar.

- Las figuras SVG se rasterizan a PNG con Firefox (WebDriver, densidad 3x) porque la
  importación HTML de Writer no entiende SVG en línea.
- Del contenido de la plantilla se quitan el paginador, los índices hechos a mano (Writer
  los genera como campos) y los adornos de las URL; los saltos de página quedan marcados.
Requiere: selenium (venv del scratchpad o cualquiera).
"""
import base64, re, shutil, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
COMP = AQUI.parent
PLANTILLA = COMP / "plantilla.html"
INFORME = COMP / "informe_competencia_clientes.html"
TMP = AQUI / "_trabajo"
FIREFOX = r"C:\Program Files\Mozilla Firefox\firefox.exe"


def rasterizar_figuras():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    o = webdriver.FirefoxOptions()
    o.binary_location = FIREFOX
    o.add_argument("-headless")
    o.set_preference("layout.css.devPixelsPerPx", "3.0")
    d = webdriver.Firefox(options=o)
    try:
        d.set_window_size(1000, 1400)
        d.get(INFORME.resolve().as_uri())
        for _ in range(60):
            if d.execute_script("return document.body.dataset.paginas || ''"):
                break
            time.sleep(0.5)
        time.sleep(1)
        d.execute_script("document.getElementById('aviso-pantalla').style.display='none'")  # el aviso flotante salía en las capturas
        for fid in ("f1", "f2", "f4"):
            el = d.find_element(By.CSS_SELECTOR, "#documento #%s svg" % fid)
            d.execute_script("arguments[0].scrollIntoView()", el)
            (TMP / (fid + ".png")).write_bytes(base64.b64decode(el.screenshot_as_base64))
            print("figura", fid, "->", fid + ".png")
    finally:
        d.quit()


def html_estatico():
    s = PLANTILLA.read_text(encoding="utf-8")
    fuente = s[s.index('<div id="fuente">') + len('<div id="fuente">'): s.index('</div><!-- /fuente -->')]
    # figuras SVG -> PNG
    for fid, ancho in (("f1", 160), ("f2", 150), ("f4", 150)):
        fuente = re.sub(r'(<div class="figura" id="%s">.*?)<svg.*?</svg>' % fid,
                        r'\1<p class="img"><img src="%s.png" style="width:%dmm"></p>' % (fid, ancho), fuente, flags=re.S)
    shutil.copy(COMP.parent / "mercado" / "vista.png", TMP / "f3.png")
    fuente = fuente.replace('<img src="__IMG_MAPA__"', '<p class="img"><img src="f3.png" style="width:160mm"').replace(
        'alt="Captura del mapa interactivo con cien marcadores de colores sobre el plano de València y un panel de totales">',
        'alt="Mapa de mercado simulado"></p>')
    # índices: marcadores que la macro sustituye por índices automáticos
    fuente = fuente.replace('<div class="indice" id="indice-general"></div>', '<p>[[INDICE_GENERAL]]</p>')
    fuente = fuente.replace('<div class="indice" id="indice-tablas"></div>', '<p>[[INDICE_TABLAS]]</p>')
    fuente = fuente.replace('<div class="indice" id="indice-figuras"></div>', '<p>[[INDICE_FIGURAS]]</p>')
    # URL: sin envoltorios ni <wbr>, en párrafo propio (con <br> Writer estiraba la línea anterior al justificar)
    fuente = re.sub(r'\s*<span class="url"[^>]*>(.*?)</span></p>',
                    lambda m: '</p>\n<p class="refurl">' + re.sub(r'</?span[^>]*>|<wbr>', '', m.group(1)) + '</p>',
                    fuente, flags=re.S)
    fuente = fuente.replace("<wbr>", "")
    # saltos de página y portada
    fuente = fuente.replace('<div class="salto" data-tipo="portada"></div>', '')
    fuente = re.sub(r'<div class="salto"></div>\s*', '<p class="salto">[[SALTO]]</p>\n', fuente)
    fuente = re.sub(r'<div class="portada-bloque">(.*?)</div>\s*<p class="compl">',
                    r'<div class="portada">\1</div>\n<p class="compl">', fuente, flags=re.S)
    fuente = fuente.replace('<div class="filete"></div>', '<p class="filete">[[FILETE]]</p>')
    # ANCHOS_TABLA6: en Writer la fecha no cabía en su columna y se partía por la mitad
    fuente = fuente.replace('<th style="width:14%">Producto</th><th style="width:24%">Vídeo y canal</th><th style="width:11%">Fecha</th><th style="width:9%">Duración</th><th style="width:16%">Tipo de captura</th>',
                            '<th style="width:12%">Producto</th><th style="width:24%">Vídeo y canal</th><th style="width:14%">Fecha</th><th style="width:11%">Duración</th><th style="width:16%">Tipo de captura</th>')
    html = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Análisis de la competencia y de los clientes potenciales</title>
<meta name="author" content="Riches Manuel y Roca">
</head><body>
""" + fuente + "\n</body></html>"
    (TMP / "informe_odt.html").write_text(html, encoding="utf-8")
    print("HTML estático:", TMP / "informe_odt.html")


if __name__ == "__main__":
    TMP.mkdir(exist_ok=True)
    shutil.copy(COMP / "cabecera_guia.png", TMP / "cabecera.png")
    rasterizar_figuras()
    html_estatico()
