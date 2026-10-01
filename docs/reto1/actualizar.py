#!/usr/bin/env python3
"""Abre un .docx/.pptx con LibreOffice (UNO), actualiza índices y campos, y guarda .docx + .pdf.

Uso: python3 actualizar.py fichero.docx      (sobrescribe el .docx y genera el .pdf al lado)
"""
import subprocess, sys, time, uno
from pathlib import Path
from com.sun.star.beans import PropertyValue

def pv(n, v):
    p = PropertyValue(); p.Name, p.Value = n, v; return p

src = Path(sys.argv[1]).resolve()
proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
                         "--accept=socket,host=127.0.0.1,port=2002;urp;"])
try:
    ctx = uno.getComponentContext()
    res = ctx.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", ctx)
    for _ in range(60):
        try:
            rctx = res.resolve("uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"); break
        except Exception:
            time.sleep(1)
    desk = rctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", rctx)
    doc = desk.loadComponentFromURL(src.as_uri(), "_blank", 0, (pv("Hidden", True),))
    if src.suffix == ".docx":
        for _ in range(2):                       # dos pasadas: el índice cambia la paginación
            idx = doc.getDocumentIndexes()
            for i in range(idx.getCount()):
                idx.getByIndex(i).update()
            doc.getTextFields().refresh()
        doc.storeToURL(src.as_uri(), (pv("FilterName", "MS Word 2007 XML"),))
        filtro = "writer_pdf_Export"
    else:
        filtro = "impress_pdf_Export"
    doc.storeToURL(src.with_suffix(".pdf").as_uri(), (pv("FilterName", filtro),))
    doc.close(True)
    print("OK", src.name, "->", src.with_suffix(".pdf").name)
finally:
    try: desk.terminate()
    except Exception: pass
    time.sleep(1); proc.kill()
