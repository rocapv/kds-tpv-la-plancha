#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el informe «Análisis de la competencia y de los clientes potenciales» del KDS+TPV:

  1. Inyecta en la plantilla las dos imágenes en base64 (cabecera oficial de la guía del
     módulo y captura del mapa de mercado), para que el HTML sea un solo fichero.
  2. Imprime el HTML a PDF con FIREFOX mediante WebDriver (A4, márgenes 0, fondos).
  3. Comprueba el PDF con pypdf: número de páginas, tamaño A4 y pie con la numeración.

Uso:  python generar.py            (HTML + PDF)
      python generar.py --solo-html
"""
import base64, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLANTILLA = AQUI / "plantilla.html"
SALIDA_HTML = AQUI / "informe_competencia_clientes.html"
SALIDA_PDF = AQUI / "informe_competencia_clientes.pdf"
CABECERA = AQUI / "cabecera_guia.png"          # tira de logos extraída de la guía del módulo (.docx)
MAPA = AQUI.parent / "mercado" / "vista.png"    # captura del mapa de mercado simulado
FIREFOX = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")


def b64(p: Path) -> str:
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(p.read_bytes()).decode("ascii"))


def construir_html() -> None:
    html = PLANTILLA.read_text(encoding="utf-8")
    html = html.replace("__IMG_CABECERA__", b64(CABECERA)).replace("__IMG_MAPA__", b64(MAPA))
    SALIDA_HTML.write_text(html, encoding="utf-8")
    print("HTML:", SALIDA_HTML, "%.1f MB" % (SALIDA_HTML.stat().st_size / 1e6))


def imprimir_con_firefox(destino: Path) -> None:
    """Imprime con el motor de Firefox mediante el comando Print de WebDriver (geckodriver).

    La impresión silenciosa por preferencias (print.always_print_silent) no llega a escribir el
    fichero en Firefox 156, ni en modo headless ni con ventana; WebDriver sí.
    Requiere `pip install selenium` (Selenium Manager descarga geckodriver solo).
    """
    from selenium import webdriver
    from selenium.webdriver.common.print_page_options import PrintOptions
    opts = webdriver.FirefoxOptions()
    opts.binary_location = str(FIREFOX)
    opts.add_argument("-headless")
    drv = webdriver.Firefox(options=opts)
    try:
        drv.set_window_size(1000, 1400)
        drv.get(SALIDA_HTML.resolve().as_uri())
        t0 = time.time()
        while time.time() - t0 < 60:                   # espera a que el paginador termine
            if drv.execute_script("return document.body.dataset.paginas || ''"):
                break
            time.sleep(0.5)
        time.sleep(1.5)                                # decodificación de imágenes
        po = PrintOptions()
        po.page_width, po.page_height = 21.0, 29.7
        po.margin_top = po.margin_bottom = po.margin_left = po.margin_right = 0
        po.background = True
        po.shrink_to_fit = False
        po.orientation = "portrait"
        pdf = base64.b64decode(drv.print_page(po))
        destino.write_bytes(pdf)
        print("PDF: %s (%.1f MB), %s páginas maquetadas" % (destino, len(pdf) / 1e6,
              drv.execute_script("return document.body.dataset.paginas")))
    finally:
        drv.quit()


def comprobar_pdf(p: Path) -> None:
    from pypdf import PdfReader
    r = PdfReader(str(p))
    n = len(r.pages)
    caja = r.pages[0].mediabox
    print("Páginas: %d · tamaño: %.1f × %.1f pt (A4 = 595.3 × 841.9)" % (n, float(caja.width), float(caja.height)))
    for i in (1, n // 2, n - 1):
        texto = (r.pages[i].extract_text() or "").strip().splitlines()
        cola = " | ".join(t.strip() for t in texto[-3:])
        print("  p.%d termina en: %s" % (i + 1, cola[:120]))


if __name__ == "__main__":
    construir_html()
    if "--solo-html" not in sys.argv:
        imprimir_con_firefox(SALIDA_PDF)
        comprobar_pdf(SALIDA_PDF)
