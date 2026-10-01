// Maqueta el informe del Reto 1 en .docx con el formato del manual del módulo (APA 7.ª):
// Arial 11, márgenes de 2,54 cm, interlineado doble, alineado a la izquierda y sangría de 1,27 cm.
// Uso: node generar_docx.js  ->  reto1_contexto_tecnologico.docx (índice sin paginar; lo pagina actualizar.py)
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, HeadingLevel, LevelFormat, WidthType, ShadingType, BorderStyle, PageNumber,
  TableOfContents, PageBreak, TabStopType, VerticalAlign,
} = require('docx');
const { META, RESUMEN, CUERPO, REFERENCIAS, NORMATIVA, ANEXO_RA } = require('./contenido');

const AQUI = __dirname;
const FUENTE = 'Arial';
const NARANJA = 'E67E22';
const ANCHO = 9026;              // A4 (11906) menos 2 × 1440 de margen, en DXA
const SANGRIA = 720;             // 1,27 cm
const DOBLE = 480;               // interlineado doble

const lit = (t) => t.replace(/\u0001/g, '*');
// **negrita**, *cursiva*
function runs(texto, base = {}) {
  texto = texto.replace(/\\\*/g, '\u0001');   // \* = asterisco literal
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(texto))) {
    if (m.index > last) out.push(new TextRun({ text: lit(texto.slice(last, m.index)), ...base }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: lit(t.slice(2, -2)), bold: true, ...base }));
    else out.push(new TextRun({ text: lit(t.slice(1, -1)), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < texto.length) out.push(new TextRun({ text: lit(texto.slice(last)), ...base }));
  return out;
}

const P = (t) => new Paragraph({ children: runs(t) });
const H1 = (t, salto = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: salto, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const centrado = (t, o = {}) => new Paragraph({
  alignment: AlignmentType.CENTER, indent: { firstLine: 0 }, spacing: { line: DOBLE, after: o.after || 0, before: o.before || 0 },
  children: [new TextRun({ text: t, bold: !!o.bold, size: o.size, color: o.color })],
});

let nTabla = 0, nFigura = 0;
const sinBorde = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const linea = { style: BorderStyle.SINGLE, size: 6, color: '808080' };

function etiqueta(tipo, n, titulo) {      // APA: «Tabla 1» en negrita y el título en cursiva debajo
  return [
    new Paragraph({ keepNext: true, indent: { firstLine: 0 }, spacing: { before: 240, line: DOBLE }, children: [new TextRun({ text: `${tipo} ${n}`, bold: true })] }),
    new Paragraph({ keepNext: true, indent: { firstLine: 0 }, spacing: { after: 120, line: DOBLE }, children: [new TextRun({ text: titulo, italics: true })] }),
  ];
}
function nota(t) {
  const [cab, ...resto] = t.split('. ');
  return new Paragraph({
    indent: { firstLine: 0 }, spacing: { before: 80, after: 240, line: 276 },
    children: [new TextRun({ text: cab + '.', italics: true, size: 20 }), new TextRun({ text: ' ' + resto.join('. '), size: 20 })],
  });
}
function tabla(titulo, cab, filas, anchos, pie) {
  nTabla++;
  const celda = (t, i, esCab, ultima) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    verticalAlign: VerticalAlign.TOP,
    shading: esCab ? { fill: 'FDEBD9', type: ShadingType.CLEAR, color: 'auto' } : undefined,
    borders: { top: esCab ? linea : sinBorde, bottom: (esCab || ultima) ? linea : { style: BorderStyle.SINGLE, size: 2, color: 'DDDDDD' }, left: sinBorde, right: sinBorde },
    children: [new Paragraph({ indent: { firstLine: 0 }, spacing: { line: 252, before: 0, after: 0 }, children: runs(t, { size: 19, bold: esCab || undefined }) })],
  });
  const t = new Table({
    width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: cab.map((c, i) => celda(c, i, true, false)) }),
      ...filas.map((f, k) => new TableRow({ cantSplit: true, children: f.map((c, i) => celda(c, i, false, k === filas.length - 1)) })),
    ],
  });
  return [...etiqueta('Tabla', nTabla, titulo), t, nota(pie)];
}
function figura(titulo, fichero, w, h, pie) {
  nFigura++;
  const anchoPt = 450, altoPt = Math.round(anchoPt * h / w);
  return [
    ...etiqueta('Figura', nFigura, titulo),
    new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, indent: { firstLine: 0 }, spacing: { line: 240 },
      children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(AQUI, fichero)), transformation: { width: anchoPt, height: altoPt },
        altText: { title: titulo, description: titulo, name: path.basename(fichero) } })] }),
    nota(pie),
  ];
}
const lista = (items) => items.map((t) => new Paragraph({ numbering: { reference: 'vinetas', level: 0 }, indent: { left: 1080, hanging: 360, firstLine: 0 }, children: runs(t) }));

// Referencia APA: sangría francesa de 1,27 cm; el título en cursiva va marcado con *…*
const referencia = (t) => new Paragraph({ indent: { left: SANGRIA, hanging: SANGRIA }, children: runs(t) });

function cuerpo() {
  const out = [];
  for (const b of CUERPO) {
    const [tipo, ...d] = b;
    if (tipo === 'h1') out.push(H1(d[0]));
    else if (tipo === 'h2') out.push(H2(d[0]));
    else if (tipo === 'p') out.push(P(d[0]));
    else if (tipo === 'ul') out.push(...lista(d[0]));
    else if (tipo === 'table') out.push(...tabla(...d));
    else if (tipo === 'fig') out.push(...figura(...d));
  }
  return out;
}

function portada() {
  return [
    new Paragraph({ spacing: { before: 1800 }, children: [] }),
    centrado(META.titulo, { bold: true, size: 32 }),
    centrado(META.subtitulo, { size: 24, after: 480 }),
    new Paragraph({ alignment: AlignmentType.CENTER, indent: { firstLine: 0 }, spacing: { after: 960 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NARANJA, space: 1 } }, children: [] }),
    centrado(META.autores, { bold: true }),
    centrado(META.reto),
    centrado(META.ciclo),
    centrado(META.centro),
    centrado(META.fecha, { after: 960 }),
    centrado(`Resultados de aprendizaje: PAR RA1 · ISO RA4 · FH RA4 y RA5 · IPE I RA2 y RA5`, { size: 18, color: '666666' }),
  ];
}

function resumen() {
  const out = [];
  RESUMEN.forEach(([titulo, texto], i) => {
    out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: i === 0, children: [new TextRun(titulo)] }));
    out.push(new Paragraph({ indent: { firstLine: 0 }, children: runs(texto) }));
  });
  return out;
}

function indice() {
  return [
    new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, indent: { firstLine: 0 }, children: [new TextRun({ text: 'Índice', bold: true })] }),
    new TableOfContents('Índice', { hyperlink: true, headingStyleRange: '1-2' }),
  ];
}

function finales() {
  const out = [H1('Referencias')];
  out.push(...REFERENCIAS.map(referencia));
  out.push(H2('Normativa consultada'));
  out.push(...NORMATIVA.map(referencia));
  out.push(H1('Anexo I. Relación con los resultados de aprendizaje'));
  out.push(P(`El enunciado del reto vincula el trabajo a los resultados de aprendizaje de cuatro módulos, además del RA1 del propio proyecto intermodular, del que este reto supone el 50 % (IES Conselleria, 2025a). La tabla siguiente indica en qué apartados del informe se trabaja cada uno.`));
  out.push(...tabla('Resultados de aprendizaje y apartados del informe que los trabajan', ['Módulo', 'Resultado de aprendizaje', 'Apartados'],
    ANEXO_RA, [2300, 4000, 2726], 'Nota. Textos de los resultados de aprendizaje según los documentos de contenidos y criterios de cada módulo (curso 2025-2026).'));
  return out;
}

const cabecera = new Header({ children: [new Paragraph({
  indent: { firstLine: 0 }, spacing: { line: 240 },
  tabStops: [{ type: TabStopType.RIGHT, position: ANCHO }],
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NARANJA, space: 4 } },
  children: [new TextRun({ text: META.cabecera, size: 18, color: '555555' }), new TextRun({ text: '\t1.º ASIR · IES Conselleria', size: 18, color: '555555' })],
})] });
const pie = new Footer({ children: [new Paragraph({
  indent: { firstLine: 0 }, spacing: { line: 240 },
  tabStops: [{ type: TabStopType.RIGHT, position: ANCHO }],
  children: [
    new TextRun({ text: META.autores, size: 18, color: '555555' }),
    new TextRun({ children: ['\tPágina ', PageNumber.CURRENT, ' de ', PageNumber.TOTAL_PAGES], size: 18, color: '555555' }),
  ],
})] });

const pagina = { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440, header: 708, footer: 708 } };

const doc = new Document({
  creator: META.autores, title: META.titulo, description: META.subtitulo, language: 'es-ES',
  styles: {
    default: { document: { run: { font: FUENTE, size: 22, language: { value: 'es-ES' } },
      paragraph: { spacing: { line: DOBLE, before: 0, after: 0 }, indent: { firstLine: SANGRIA } } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FUENTE, size: 24, bold: true, color: '000000' },
        paragraph: { alignment: AlignmentType.CENTER, indent: { firstLine: 0 }, spacing: { before: 240, after: 240, line: DOBLE }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FUENTE, size: 22, bold: true, color: '000000' },
        paragraph: { indent: { firstLine: 0 }, spacing: { before: 240, after: 0, line: DOBLE }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: 'vinetas', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] }] },
  features: { updateFields: true },
  sections: [
    { properties: { page: pagina, titlePage: true }, headers: { default: cabecera, first: new Header({ children: [] }) },
      footers: { default: pie, first: new Footer({ children: [] }) },
      children: [...portada(), ...resumen(), ...indice(), ...cuerpo(), ...finales()] },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(AQUI, 'reto1_contexto_tecnologico.docx');
  fs.writeFileSync(out, buf);
  console.log('DOCX:', out, (buf.length / 1024).toFixed(0) + ' KB', `· ${nTabla} tablas · ${nFigura} figuras`);
});
