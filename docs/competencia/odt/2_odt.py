# -*- coding: utf-8 -*-
"""
Paso 2 del .odt: se ejecuta con el Python de LibreOffice («C:\\Program Files\\LibreOffice\\program\\python.exe»).

Arranca soffice sin interfaz, importa el HTML estático del paso 1 y aplica el formato de la guía
del módulo: A4, márgenes 2,5 cm, Arial 12 justificada, interlineado 1,5, títulos Arial 16,
leyendas Arial 9, cabecera con los logos oficiales, pie «autores · número de página», portada
sin cabecera ni pie, sin partición de palabras, e índices general, de tablas y de figuras como
campos de Writer (se actualizan con Herramientas > Actualizar). Guarda .odt y, para revisar, .pdf.
"""
import os, sys, time, subprocess, uno
from com.sun.star.beans import PropertyValue
from com.sun.star.style.ParagraphAdjust import BLOCK, LEFT, CENTER, RIGHT
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.style.BreakType import PAGE_BEFORE, NONE as SIN_SALTO

AQUI = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(AQUI, "_trabajo")
ENTRADA = os.path.join(TMP, "informe_odt.html")
SALIDA_ODT = os.path.join(os.path.dirname(AQUI), "informe_competencia_clientes.odt")
SALIDA_PDF = os.path.join(TMP, "revision_odt.pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
AUTORES = "Riches Manuel y Roca"
AZUL = 0x1F4E79
MM = 100  # unidades de 1/100 mm


def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p


def url(ruta):
    return uno.systemPathToFileUrl(os.path.abspath(ruta))


def conectar():
    import tempfile
    perfil = url(tempfile.mkdtemp(prefix="lo_odt_"))       # perfil nuevo en cada ejecución
    proc = subprocess.Popen([SOFFICE, "--headless", "--invisible", "--nologo", "--norestore",
                             "-env:UserInstallation=" + perfil,
                             "--accept=socket,host=127.0.0.1,port=2083;urp;"])
    local = uno.getComponentContext()
    res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            ctx = res.resolve("uno:socket,host=127.0.0.1,port=2083;urp;StarOffice.ComponentContext")
            return proc, ctx
        except Exception:
            time.sleep(1)
    raise SystemExit("no conecta con soffice")


def main():
    global CTX
    proc, ctx = conectar()
    CTX = ctx
    smgr = ctx.ServiceManager
    desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desk.loadComponentFromURL(url(ENTRADA), "_blank", 0,
                                    (pv("Hidden", True), pv("FilterName", "HTML (StarWriter)")))
    try:
        formatear(doc)
        doc.storeToURL(url(SALIDA_ODT), (pv("FilterName", "writer8"),))
        doc.storeToURL(url(SALIDA_PDF), (pv("FilterName", "writer_pdf_Export"),))
        print("ODT:", SALIDA_ODT)
        print("PDF de revisión:", SALIDA_PDF)
    finally:
        doc.close(True)
        try:
            desk.terminate()
        except Exception:
            pass
        time.sleep(2)
        proc.kill()


def formatear(doc):
    doc.getDocumentProperties().Author = AUTORES
    doc.getDocumentProperties().Title = "Análisis de la competencia y de los clientes potenciales"
    fam = doc.StyleFamilies
    pst = fam.getByName("ParagraphStyles")

    # --- estilos de párrafo ---
    def ajustar(nombre, **kw):
        if not pst.hasByName(nombre):
            return None
        st = pst.getByName(nombre)
        for k, v in kw.items():
            try:
                st.setPropertyValue(k, v)
            except Exception as e:
                print("  aviso estilo", nombre, k, e)
        return st
    ls = uno.createUnoStruct("com.sun.star.style.LineSpacing"); ls.Mode = 0; ls.Height = 150
    base = dict(CharFontName="Arial", CharFontNameAsian="Arial", CharFontNameComplex="Arial", ParaIsHyphenation=False)
    ajustar("Standard", CharHeight=12.0, ParaAdjust=BLOCK, ParaLineSpacing=ls, **base)
    for n in ("Text body", "Body Text", "Default Paragraph Style", "Table Contents", "List Bullet", "List"):
        ajustar(n, **base)
    ls1 = uno.createUnoStruct("com.sun.star.style.LineSpacing"); ls1.Mode = 0; ls1.Height = 115
    ajustar("Heading 1", CharHeight=16.0, CharWeight=150.0, CharColor=AZUL, ParaAdjust=LEFT, ParaLineSpacing=ls1,
            ParaTopMargin=6 * MM, ParaBottomMargin=3 * MM, ParaKeepTogether=True, **base)
    ajustar("Heading 2", CharHeight=13.0, CharWeight=150.0, CharColor=AZUL, CharPosture=uno.Enum("com.sun.star.awt.FontSlant", "NONE"),
            ParaAdjust=LEFT, ParaLineSpacing=ls1, ParaTopMargin=4 * MM, ParaBottomMargin=2 * MM, **base)
    ajustar("Heading 3", CharHeight=12.0, CharWeight=150.0, CharPosture=uno.Enum("com.sun.star.awt.FontSlant", "ITALIC"),
            ParaAdjust=LEFT, ParaLineSpacing=ls1, ParaTopMargin=3 * MM, ParaBottomMargin=1 * MM, **base)
    # estilos propios para leyendas (alimentan los índices de tablas y figuras)
    for nombre in ("Leyenda tabla", "Leyenda figura"):
        if not pst.hasByName(nombre):
            st = doc.createInstance("com.sun.star.style.ParagraphStyle")
            pst.insertByName(nombre, st)
        ajustar(nombre, CharHeight=9.0, ParaAdjust=BLOCK, ParaLineSpacing=ls1, ParaTopMargin=2 * MM,
                ParaBottomMargin=1 * MM, ParaKeepTogether=True, ParaSplit=False, **base)
        pst.getByName(nombre).setPropertyValue("ParaKeepTogether", True)
    if not pst.hasByName("Referencia"):
        pst.insertByName("Referencia", doc.createInstance("com.sun.star.style.ParagraphStyle"))
    ajustar("Referencia", CharHeight=11.0, ParaAdjust=BLOCK, ParaLineSpacing=ls1, ParaLeftMargin=12 * MM,
            ParaFirstLineIndent=-12 * MM, ParaBottomMargin=250, ParaTopMargin=0, **base)
    if not pst.hasByName("Referencia URL"):
        pst.insertByName("Referencia URL", doc.createInstance("com.sun.star.style.ParagraphStyle"))
    ajustar("Referencia URL", CharHeight=9.0, ParaAdjust=LEFT, ParaLineSpacing=ls1, ParaLeftMargin=12 * MM,
            ParaFirstLineIndent=0, ParaTopMargin=0, ParaBottomMargin=250, **base)

    # --- página: A4, márgenes 2,5 cm, cabecera y pie ---
    pag = fam.getByName("PageStyles")
    nombre_pag = "HTML" if pag.hasByName("HTML") else "Default Page Style"
    for n in (nombre_pag, "Default Page Style"):
        if not pag.hasByName(n):
            continue
        p = pag.getByName(n)
        p.Width, p.Height = 210 * MM, 297 * MM
        p.LeftMargin = p.RightMargin = 25 * MM
        p.TopMargin, p.BottomMargin = 12 * MM, 12 * MM
        p.HeaderIsOn = True; p.HeaderBodyDistance = 5 * MM; p.HeaderHeight = 18 * MM
        p.FooterIsOn = True; p.FooterBodyDistance = 5 * MM
        cab = p.HeaderText
        cab.setString("")
        img = doc.createInstance("com.sun.star.text.TextGraphicObject")
        cargar_imagen(doc, img, os.path.join(TMP, "cabecera.png"))
        img.Width = 160 * MM; img.Height = int(160 * MM * 154 / 1361)
        img.AnchorType = uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
        cab.insertTextContent(cab.getEnd(), img, False)
        pie = p.FooterText
        pie.setString("")
        c = pie.createTextCursor()
        c.setPropertyValue("CharFontName", "Arial"); c.setPropertyValue("CharHeight", 10.0)
        ts = uno.createUnoStruct("com.sun.star.style.TabStop"); ts.Position = 160 * MM
        ts.Alignment = uno.Enum("com.sun.star.style.TabAlign", "RIGHT")
        uno.invoke(c, "setPropertyValue", ("ParaTabStops", uno.Any("[]com.sun.star.style.TabStop", (ts,))))
        c.setPropertyValue("ParaAdjust", LEFT)
        pie.insertString(c, AUTORES + "\t", False)
        num = doc.createInstance("com.sun.star.text.TextField.PageNumber")
        num.NumberingType = 4; num.SubType = uno.Enum("com.sun.star.text.PageNumberType", "CURRENT")
        pie.insertTextContent(c, num, False)
    # portada: estilo propio sin cabecera ni pie
    if not pag.hasByName("Portada"):
        pag.insertByName("Portada", doc.createInstance("com.sun.star.style.PageStyle"))
    pp = pag.getByName("Portada")
    pp.Width, pp.Height = 210 * MM, 297 * MM
    pp.LeftMargin = pp.RightMargin = 25 * MM
    pp.TopMargin, pp.BottomMargin = 12 * MM, 20 * MM
    pp.HeaderIsOn = True; pp.HeaderHeight = 18 * MM; pp.HeaderBodyDistance = 5 * MM
    cab = pp.HeaderText; cab.setString("")
    img2 = doc.createInstance("com.sun.star.text.TextGraphicObject")
    cargar_imagen(doc, img2, os.path.join(TMP, "cabecera.png"))
    img2.Width = 160 * MM; img2.Height = int(160 * MM * 154 / 1361)
    img2.AnchorType = uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
    cab.insertTextContent(cab.getEnd(), img2, False)
    pp.FooterIsOn = False
    pp.FollowStyle = nombre_pag

    # --- recorrido de párrafos: estilos por clase, saltos, marcadores ---
    texto = doc.Text
    en = texto.createEnumeration()
    parrafos = []
    while en.hasMoreElements():
        parrafos.append(en.nextElement())
    primero = True
    marcadores = {}
    en_portada = True
    portada = []
    textos = [(p.getString() if p.supportsService("com.sun.star.text.Paragraph") else "") for p in parrafos]
    for i, par in enumerate(parrafos):
        if not par.supportsService("com.sun.star.text.Paragraph"):
            continue
        t = par.getString()
        siguiente = textos[i + 1] if i + 1 < len(textos) else ""
        if not en_portada and t.startswith("http"):
            par.ParaStyleName = "Referencia URL"; continue
        if not en_portada and siguiente.startswith("http") and "(" in t[:90]:
            par.ParaStyleName = "Referencia"; par.ParaBottomMargin = 0; continue
        estilo = par.ParaStyleName
        if primero:
            par.PageDescName = "Portada"; primero = False
        if en_portada and t.strip() != "[[SALTO]]":
            portada.append(par); continue
        if t.strip() == "[[SALTO]]":
            en_portada = False
        if t.strip() == "[[SALTO]]":
            marcadores.setdefault("SALTO", []).append(par); continue
        if t.strip() in ("[[INDICE_GENERAL]]", "[[INDICE_TABLAS]]", "[[INDICE_FIGURAS]]"):
            marcadores[t.strip()] = par; continue
        if t.strip() == "[[FILETE]]":
            par.setString(""); par.ParaAdjust = CENTER
            continue
        if t.startswith("Tabla ") and len(t) < 200 and ("." in t[:10]):
            par.ParaStyleName = "Leyenda tabla"; par.ParaKeepTogether = True; par.ParaAdjust = LEFT; continue
        if t.startswith("Figura ") and len(t) < 200 and ("." in t[:11]):
            par.ParaStyleName = "Leyenda figura"; par.ParaKeepTogether = True; par.ParaAdjust = LEFT; continue
        if estilo.startswith("Heading"):
            continue
        if "(20" in t[:80] and (t.count("http") or "BOE" in t or "DOUE" in t or "YouTube" in t or "Documento" in t) and len(t) < 700:
            par.ParaStyleName = "Referencia"; continue
        if t.startswith("Ley ") or t.startswith("Real Decreto") or t.startswith("Reglamento (UE)"):
            if "BOE" in t or "DOUE" in t:
                par.ParaStyleName = "Referencia"; continue
        par.ParaIsHyphenation = False
        if par.ParaAdjust in (LEFT, BLOCK) and estilo not in ("Table Contents", "Table Heading"):
            par.ParaAdjust = BLOCK
    formatear_portada(portada)
    # saltos de página: se borra el marcador (uniéndolo al párrafo siguiente) y ese párrafo abre página
    for par in marcadores.get("SALTO", []):
        c = texto.createTextCursorByRange(par)
        c.gotoStartOfParagraph(False)
        c.gotoEndOfParagraph(True)
        c.goRight(1, True)                 # texto del marcador + su fin de párrafo
        c.setString("")
        c.collapseToEnd()
        c.gotoStartOfParagraph(False)
        c.BreakType = PAGE_BEFORE
    # índices
    insertar_indice(doc, marcadores.get("[[INDICE_GENERAL]]"), "general")
    insertar_indice(doc, marcadores.get("[[INDICE_TABLAS]]"), "Leyenda tabla")
    insertar_indice(doc, marcadores.get("[[INDICE_FIGURAS]]"), "Leyenda figura")

    # --- tablas: letra 9,5, justificado en celdas de texto, cabecera repetida ---
    tablas = doc.TextTables
    for i in range(tablas.Count):
        tb = tablas.getByIndex(i)
        try:
            tb.RepeatHeadline = True; tb.HeaderRowCount = 1
            tb.setPropertyValue("Split", True)
        except Exception:
            pass
        linea = uno.createUnoStruct("com.sun.star.table.BorderLine2")
        linea.OuterLineWidth = 18; linea.LineWidth = 18; linea.Color = 0x9A9A9A
        filas = tb.Rows.Count
        for r in range(filas):
            try:
                tb.Rows.getByIndex(r).IsSplitAllowed = False
            except Exception:
                pass
        for nombre in tb.CellNames:
            celda = tb.getCellByName(nombre)
            for lado in ("LeftBorder", "RightBorder", "TopBorder", "BottomBorder"):
                celda.setPropertyValue(lado, linea)
            for lado in ("LeftBorderDistance", "RightBorderDistance"):
                celda.setPropertyValue(lado, 120)
            for lado in ("TopBorderDistance", "BottomBorderDistance"):
                celda.setPropertyValue(lado, 60)
            celda.VertOrient = 1                        # arriba
            fila = int("".join(ch for ch in nombre if ch.isdigit()))
            celda.BackColor = 0xE8EEF5 if fila == 1 else (0xF4F4F2 if fila % 2 == 1 else -1)
            ce = celda.Text.createEnumeration()
            while ce.hasMoreElements():
                p = ce.nextElement()
                if not p.supportsService("com.sun.star.text.Paragraph"):
                    continue
                p.CharFontName = "Arial"; p.CharHeight = 9.0; p.ParaIsHyphenation = False
                ls9 = uno.createUnoStruct("com.sun.star.style.LineSpacing"); ls9.Mode = 0; ls9.Height = 110
                p.ParaLineSpacing = ls9; p.ParaTopMargin = 0; p.ParaBottomMargin = 0
                s = p.getString().strip()
                if fila == 1:
                    p.CharWeight = 150.0
                if p.ParaAdjust != RIGHT and p.ParaAdjust != CENTER and not _es_numero(s):
                    p.ParaAdjust = LEFT                  # en columnas estrechas el justificado abre huecos
                elif _es_numero(s):
                    p.ParaAdjust = RIGHT

    # --- tabla 6: anchos de columna fijados aquí (Writer ignora los del HTML y partía las fechas) ---
    for i in range(tablas.Count):
        tb = tablas.getByIndex(i)
        try:
            cab = [tb.getCellByName(n).getString() for n in ("A1", "B1", "C1")]
        except Exception:
            continue
        if cab[2].strip() == "Fecha" and cab[0].strip() == "Producto":
            total = tb.TableColumnRelativeSum
            seps = tb.TableColumnSeparators
            acum = 0
            for k, pct in enumerate((12, 24, 15, 11, 16)):
                acum += pct
                seps[k].Position = int(total * acum / 100)
            tb.TableColumnSeparators = seps
            print("  tabla 6: anchos fijados")

    # --- URL de las referencias: en una sola línea (letra menor si hace falta), nunca partidas ---
    en = texto.createEnumeration()
    while en.hasMoreElements():
        p = en.nextElement()
        if p.supportsService("com.sun.star.text.Paragraph") and p.ParaStyleName == "Referencia URL":
            n = len(p.getString())
            p.CharHeight = max(6.0, min(9.0, round(820.0 / max(n, 1), 1)))

    # --- imágenes: centradas ---
    gr = doc.GraphicObjects
    for i in range(gr.Count):
        g = gr.getByIndex(i)
        try:
            px = g.Graphic.getPropertyValue("SizePixel")
            ancho = 160 * MM if px.Width / px.Height > 5 else (160 * MM if px.Width / px.Height > 1.6 else 150 * MM)
            sz = uno.createUnoStruct("com.sun.star.awt.Size")
            sz.Width = ancho; sz.Height = int(ancho * px.Height / px.Width)
            g.setSize(sz)
            g.HoriOrient = 2  # CENTER
        except Exception as e:
            print("  aviso imagen", e)
    doc.DocumentIndexes  # fuerza carga
    for i in range(doc.DocumentIndexes.Count):
        doc.DocumentIndexes.getByIndex(i).update()


def formatear_portada(pars):
    tamanos = []
    for par in pars:
        t = par.getString().strip()
        par.ParaIsHyphenation = False
        par.ParaAdjust = LEFT
        par.CharFontName = "Arial"
        if t.startswith("Análisis de la competencia"):
            par.CharHeight = 24.0; par.CharWeight = 150.0; par.CharColor = AZUL; par.ParaTopMargin = 45 * MM
            par.ParaBottomMargin = 8 * MM
        elif t.startswith("Sistema KDS"):
            par.CharHeight = 15.0; par.CharColor = 0x444444; par.ParaBottomMargin = 20 * MM
        elif t.startswith("Proyecto Intermodular"):
            par.CharHeight = 12.5; par.ParaTopMargin = 10 * MM; par.ParaBottomMargin = 12 * MM
        elif t.startswith("Autores"):
            par.CharHeight = 13.0
        elif t.startswith("Documento complementario"):
            par.CharHeight = 10.5; par.CharColor = 0x444444; par.ParaAdjust = BLOCK; par.ParaTopMargin = 45 * MM
        elif t == "[[FILETE]]":
            par.setString("")
            linea = uno.createUnoStruct("com.sun.star.table.BorderLine2")
            linea.OuterLineWidth = 53; linea.LineWidth = 53; linea.Color = AZUL
            par.BottomBorder = linea; par.ParaRightMargin = 120 * MM; par.CharHeight = 4.0
            par.ParaBottomMargin = 10 * MM
        elif t == "":
            par.CharHeight = 6.0


def _es_numero(s):
    import re
    return bool(re.fullmatch(r"[≈\d\.,%€ ()\-–/]+(€|%)?( \(\d[\d\.,]* ?€?\))?", s)) if s else False


def cargar_imagen(doc, obj, ruta):
    gp = CTX.ServiceManager.createInstanceWithContext("com.sun.star.graphic.GraphicProvider", CTX)
    g = gp.queryGraphic((pv("URL", url(ruta)),))
    obj.Graphic = g


def borrar_parrafo(texto, par):
    c = texto.createTextCursorByRange(par)
    c.gotoStartOfParagraph(False)
    c.gotoEndOfParagraph(True)
    c.setString("")
    try:
        c.goRight(1, True)   # se come el salto de párrafo
        c.setString("")
    except Exception:
        pass


def insertar_indice(doc, par, tipo):
    if par is None:
        print("  sin marcador para", tipo); return
    texto = doc.Text
    idx = doc.createInstance("com.sun.star.text.ContentIndex")
    idx.Title = ""
    if tipo == "general":
        idx.CreateFromOutline = True
        idx.Level = 2
    else:
        idx.CreateFromOutline = False
        idx.CreateFromLevelParagraphStyles = True
        idx.Level = 1
        lps = idx.LevelParagraphStyles
        vacio = uno.Any("[]string", ())
        for n in range(lps.Count):
            uno.invoke(lps, "replaceByIndex", (n, vacio))
        uno.invoke(lps, "replaceByIndex", (1, uno.Any("[]string", (tipo,))))
    c = texto.createTextCursorByRange(par)
    c.gotoStartOfParagraph(False); c.gotoEndOfParagraph(True)
    c.setString("")
    texto.insertTextContent(c, idx, False)


if __name__ == "__main__":
    main()
