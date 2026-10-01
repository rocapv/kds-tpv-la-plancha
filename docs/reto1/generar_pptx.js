// Presentación del Reto 1 (12-15 min). Uso: node generar_pptx.js -> reto1_presentacion.pptx
const path = require('path');
const pptxgen = require('pptxgenjs');

const C = { osc: '23272B', osc2: '33383D', nar: 'E67E22', narClaro: 'FDEBD9', txt: '2B2B2B', gris: '6B6B6B', claro: 'F4F4F4', blanco: 'FFFFFF', rojo: 'C0392B' };
const F = 'Arial';
const fig = (f) => path.join(__dirname, 'fig', f);

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';            // 13.33 × 7.5 in
pres.author = 'Riches Manuel y Roca';
pres.title = 'Análisis del contexto tecnológico de La Plancha';
const W = 13.333, M = 0.6;

const T = (s, text, o) => s.addText(text, { isTextBox: true, fontFace: F, color: C.txt, margin: 0, valign: 'top', ...o });
let n = 0;
function base(titulo, oscuro = false) {
  const s = pres.addSlide();
  s.background = { color: oscuro ? C.osc : C.blanco };
  n++;
  if (titulo) T(s, titulo, { x: M, y: 0.45, w: W - 2 * M, h: 0.8, fontSize: 32, bold: true, color: oscuro ? C.blanco : C.txt, valign: 'middle' });
  if (n > 1) T(s, `${n}`, { x: W - 1.1, y: 6.95, w: 0.5, h: 0.3, fontSize: 11, color: oscuro ? 'AAAAAA' : C.gris, align: 'right' });
  return s;
}
function circulo(s, x, y, d, txt, o = {}) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: o.fill || C.nar }, line: { color: o.fill || C.nar } });
  T(s, txt, { x, y, w: d, h: d, align: 'center', valign: 'middle', fontSize: o.size || 18, bold: true, color: o.color || C.blanco });
}
function tarjeta(s, x, y, w, h, fill = C.claro) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12 });
}

// 1 · Portada
{
  const s = base(null, true);
  circulo(s, M, 1.2, 0.9, 'R1', { size: 20 });
  T(s, 'Lo que hay detrás de la barra', { x: M, y: 2.4, w: 11, h: 1.1, fontSize: 48, bold: true, color: C.blanco });
  T(s, 'Análisis del contexto tecnológico de La Plancha', { x: M, y: 3.5, w: 11, h: 0.6, fontSize: 24, color: C.nar });
  T(s, 'Reto 1 · Proyecto Intermodular I · 1.º CFGS ASIR · IES Conselleria', { x: M, y: 5.6, w: 11, h: 0.4, fontSize: 16, color: 'CCCCCC' });
  T(s, 'Riches Manuel y Roca · octubre de 2026', { x: M, y: 6.05, w: 11, h: 0.4, fontSize: 16, color: 'CCCCCC' });
  s.addNotes('Presentamos el análisis del contexto tecnológico de La Plancha, la empresa para la que estamos desarrollando el TPV con pantallas de cocina. El objetivo del reto es entender qué tecnología tiene hoy la empresa, en qué entorno se mueve y qué necesita, antes de proponer nada. El título lo resume: vamos a mirar lo que hay detrás de la barra.');
}

// 2 · La empresa
{
  const s = base('La Plancha: una hamburguesería de barrio');
  const datos = [['13', 'mesas en sala,\nterraza y barra'], ['4', 'personas en\nplantilla'], ['15-25 €', 'ticket medio\npor comensal'], ['4', 'canales: sala, barra,\nllevar y reparto']];
  datos.forEach(([num, lab], i) => {
    const x = M + i * 3.05;
    tarjeta(s, x, 1.7, 2.8, 2.6);
    T(s, num, { x: x + 0.25, y: 1.95, w: 2.4, h: 1.1, fontSize: num.length > 3 ? 38 : 54, bold: true, color: C.nar, valign: 'middle' });
    T(s, lab, { x: x + 0.25, y: 3.15, w: 2.3, h: 0.9, fontSize: 16, color: C.txt });
  });
  T(s, [
    { text: 'Burjassot (València), junto al campus universitario. ', options: { bold: true } },
    { text: 'Servicio concentrado en franjas cortas y mucho pedido para llevar: el peor escenario para el papel.' },
  ], { x: M, y: 4.8, w: 11.5, h: 0.9, fontSize: 18 });
  T(s, 'Empresa ficticia (La Plancha Burjassot, S.L.), construida con datos reales del sector. Restauración independiente, CNAE 56.10.', { x: M, y: 6.3, w: 11, h: 0.4, fontSize: 12, color: C.gris });
  s.addNotes('La Plancha es una hamburguesería de barrio en Burjassot, al lado del campus de la Universitat de València. Tiene trece mesas y cuatro personas: el encargado, dos camareros y una cocinera. Es una empresa ficticia, como permite el enunciado, pero la hemos construido con datos reales del sector. Pertenece al grupo más numeroso de la hostelería: el local independiente, que es el 93 por ciento de los establecimientos. Lo importante es que el servicio se concentra en franjas cortas, y ahí es donde la tecnología no puede fallar.');
}

// 3 · Organización
{
  const s = base('Una persona lo concentra todo');
  s.addImage({ path: fig('organigrama.png'), x: M, y: 1.45, w: 7.6, h: 7.6 * 760 / 1600 });
  tarjeta(s, 8.7, 1.6, 4.0, 3.6, C.narClaro);
  T(s, 'El encargado es…', { x: 9.0, y: 1.85, w: 3.5, h: 0.5, fontSize: 18, bold: true });
  T(s, [
    { text: 'dirección y compras', options: { bullet: true, breakLine: true } },
    { text: 'caja y cierre del día', options: { bullet: true, breakLine: true } },
    { text: 'relación con la gestoría', options: { bullet: true, breakLine: true } },
    { text: 'y, sin quererlo, el informático', options: { bullet: true, bold: true } },
  ], { x: 9.0, y: 2.45, w: 3.5, h: 2.4, fontSize: 16, paraSpaceAfter: 8 });
  T(s, 'Si él falta, nadie sabe reiniciar el router ni recuperar la contraseña del TPV: un punto único de fallo humano.', { x: M, y: 5.6, w: 12, h: 0.8, fontSize: 18, italic: true, color: C.txt });
  s.addNotes('La estructura es plana: sala, cocina y una persona que lo concentra todo. Ese es el primer hallazgo: el encargado es dirección, compras, caja, administración y, en la práctica, el único responsable de informática. Si él falta un día, nadie sabe reiniciar el router ni recuperar la contraseña del TPV. Igual que hay puntos únicos de fallo técnicos, aquí hay uno humano.');
}

// 4 · Flujo de la comanda
{
  const s = base('El dato llega cuando el cliente ya se va');
  s.addImage({ path: fig('flujo_comanda.png'), x: M, y: 1.5, w: 12.1, h: 12.1 * 560 / 1600 });
  tarjeta(s, M, 5.85, 12.1, 0.9, C.osc);
  T(s, 'Durante el servicio, el local trabaja a ciegas: no sabe qué mesa espera ni cuánto tarda la cocina.', { x: M + 0.3, y: 5.85, w: 11.5, h: 0.9, fontSize: 18, bold: true, color: C.blanco, valign: 'middle' });
  s.addNotes('Seguimos la información del proceso central, la comanda. Nace en un comandero de papel, viaja a la cocina pinchada y a voz, se prepara de memoria, sale al pase con un grito y solo entra en un sistema informático en el último paso, cuando el camarero la teclea en el TPV para cobrar. Es decir, el dato llega cuando el cliente ya se va. En cada paso hay un problema: letra ilegible, sin hora, nadie ve el retraso, platos fríos, y el doble tecleo que acaba en descuadres.');
}

// 5 · Inventario
{
  const s = base('Inventario: lo que hay, sin diseño');
  const items = [
    ['PC del TPV', '2015 · Celeron · 4 GB · disco mecánico con sectores dañados'],
    ['Sin SAI', 'un corte de luz apaga la caja de golpe'],
    ['Router de la operadora', 'en una balda del almacén, junto a la cámara frigorífica'],
    ['Grabador de vídeo', 'firmware de 2019 y contraseña de fábrica'],
    ['Tableta de reparto', 'Android 9, siempre enchufada'],
    ['Portátil y móviles', 'personales: el negocio vive en cuentas privadas'],
  ];
  items.forEach(([t, d], i) => {
    const col = i % 3, fila = Math.floor(i / 3);
    const x = M + col * 4.1, y = 1.6 + fila * 2.45;
    tarjeta(s, x, y, 3.8, 2.15);
    circulo(s, x + 0.3, y + 0.3, 0.6, `${i + 1}`, { size: 16 });
    T(s, t, { x: x + 1.05, y: y + 0.32, w: 2.6, h: 0.6, fontSize: 18, bold: true, valign: 'middle' });
    T(s, d, { x: x + 0.3, y: y + 1.1, w: 3.3, h: 0.9, fontSize: 15, color: C.gris });
  });
  T(s, 'Equipos y estados del escenario ficticio.', { x: M, y: 6.6, w: 8, h: 0.3, fontSize: 12, color: C.gris });
  s.addNotes('Este es el inventario. El único equipo que guarda datos del negocio, el PC del TPV, es el más viejo y el que tiene el disco en peor estado. No hay SAI. El router y el grabador están en una balda del almacén, con calor y grasa: no hace falta un CPD, pero sí cuidar las condiciones del equipamiento. El grabador tiene la contraseña de fábrica. Y lo más delicado: los datos del negocio están en el portátil y en el móvil personales del encargado. Además hay cableado cruzando la barra y equipos viejos que deben ir al punto limpio como RAEE.');
}

// 6 · La red
{
  const s = base('Una sola red para todo y para todos');
  s.addImage({ path: fig('red_actual.png'), x: M, y: 1.35, w: 7.4, h: 7.4 * 1040 / 1600 });
  const pts = [['1', 'Los móviles de los clientes están en la misma red que la caja, el datáfono y las cámaras.'], ['2', 'La clave del wifi está en la pizarra y la del router, en su etiqueta.'], ['3', 'El grabador se ve desde internet por un puerto abierto.']];
  pts.forEach(([k, t], i) => {
    const y = 1.6 + i * 1.6;
    circulo(s, 8.5, y, 0.6, k, { fill: C.rojo, size: 16 });
    T(s, t, { x: 9.3, y: y - 0.05, w: 3.5, h: 1.3, fontSize: 16 });
  });
  s.addNotes('La red es la que dejó la operadora: un router que hace de módem, cortafuegos, DHCP y punto de acceso. Es una estrella con un único dispositivo de interconexión y una sola subred, la 192.168.1.0/24, sin VLAN. Eso significa que el móvil de cualquier cliente está en el mismo dominio de difusión que la caja, el datáfono y el grabador. La clave del wifi está escrita en la pizarra, la del router es la de fábrica y el grabador está expuesto a internet. Además, la cobertura en terraza es mala y el datáfono se desconecta.');
}

// 7 · Sistemas operativos
{
  const s = base('La caja funciona con un sistema sin soporte');
  T(s, '14/10/2025', { x: M, y: 1.7, w: 6, h: 1.3, fontSize: 66, bold: true, color: C.nar });
  T(s, 'fin del soporte de Windows 10, el sistema del PC del TPV. Su procesador no admite Windows 11: hay que sustituirlo o cambiar de sistema.', { x: M, y: 3.1, w: 5.7, h: 1.4, fontSize: 18 });
  T(s, 'Fuente: Microsoft (2025).', { x: M, y: 4.6, w: 5, h: 0.3, fontSize: 12, color: C.gris });
  const filas = [['Windows 11 Home', 'no puede unirse a un dominio ni cifrar con BitLocker'], ['Android 9', 'sin parches del fabricante'], ['Firmware del grabador', 'de 2019, sin actualizar'], ['Datos del negocio', 'repartidos: no hay ningún servidor']];
  filas.forEach(([a, b], i) => {
    const y = 1.7 + i * 1.2;
    tarjeta(s, 7.0, y, 5.7, 1.0);
    T(s, a, { x: 7.25, y, w: 2.3, h: 1.0, fontSize: 16, bold: true, valign: 'middle' });
    T(s, b, { x: 9.6, y, w: 2.95, h: 1.0, fontSize: 14, color: C.gris, valign: 'middle' });
  });
  s.addNotes('En sistemas operativos hay un dato con fecha: el 14 de octubre de 2025 terminó el soporte de Windows 10, que es el sistema del ordenador de cobro. Su procesador no está en la lista de Windows 11, así que no se puede actualizar: hay que sustituirlo o cambiar de sistema. El portátil lleva Windows 11 Home, que no se puede unir a un dominio. Y la información está dispersa: no hay ningún servidor que centralice datos, cuentas ni copias. Para cuatro personas un dominio completo no tiene sentido, pero un servidor local sí.');
}

// 8 · Riesgos
{
  const s = base('Diez riesgos; la mitad, críticos');
  const r = [['R1', 'Grabador accesible desde internet con credenciales de fábrica', 9], ['R2', 'Red única: caja, datáfono, cámaras y clientes', 9], ['R3', 'Sin copias de la base de datos del TPV', 6], ['R4', 'Sistema operativo sin soporte en la caja', 6], ['R5', 'Cuenta única compartida en el TPV', 6], ['R6', 'Disco dañado y sin SAI', 6]];
  r.forEach(([id, t, v], i) => {
    const y = 1.55 + i * 0.75;
    T(s, id, { x: M, y, w: 0.6, h: 0.55, fontSize: 15, bold: true, color: C.gris, valign: 'middle' });
    T(s, t, { x: M + 0.7, y, w: 5.6, h: 0.55, fontSize: 15, valign: 'middle' });
    s.addShape(pres.shapes.RECTANGLE, { x: 7.0, y: y + 0.1, w: v * 0.42, h: 0.38, fill: { color: v >= 9 ? C.rojo : C.nar }, line: { color: v >= 9 ? C.rojo : C.nar } });
    T(s, `${v}`, { x: 7.1 + v * 0.42, y, w: 0.5, h: 0.55, fontSize: 15, bold: true, valign: 'middle' });
  });
  T(s, 'Probabilidad × impacto (1-3 cada uno). Críticos ≥ 6. Hay además cuatro riesgos altos: router de fábrica, datos en cuentas personales, videovigilancia sin cartel y contraseñas a la vista.', { x: M, y: 6.15, w: 12, h: 0.6, fontSize: 13, color: C.gris });
  s.addNotes('Valoramos cada riesgo con probabilidad por impacto, de 1 a 3. Salen diez riesgos y seis son críticos. Los dos peores, con un 9: el grabador expuesto en internet con la contraseña de fábrica, y la red única compartida con los clientes. Les siguen la falta de copias, el sistema sin soporte, la cuenta compartida en el TPV, que impide saber quién cobra o anula, y el disco dañado sin SAI. Lo interesante es que casi ninguno exige dinero: separar redes, cambiar contraseñas y hacer copias cuesta muy poco. Falta conocimiento, no presupuesto.');
}

// 9 · Datos del sector
{
  const s = base('El sector: grande, atomizado y con poco margen');
  const d = [['280.403', 'establecimientos de hostelería en España', 'Profesional Horeca, 2025'], ['93 %', 'son locales independientes', 'Profesional Horeca, 2025'], ['−0,9 %', 'rentabilidad de la restauración en 2025', 'Hosteltur, 2026'], ['31.186', 'bares y restaurantes en la Comunitat Valenciana', 'El Periòdic, 2025']];
  d.forEach(([num, lab, src], i) => {
    const x = M + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.5;
    tarjeta(s, x, y, 5.9, 2.2);
    T(s, num, { x: x + 0.35, y: y + 0.25, w: 5.2, h: 1.0, fontSize: 48, bold: true, color: i === 2 ? C.rojo : C.nar });
    T(s, lab, { x: x + 0.35, y: y + 1.25, w: 5.2, h: 0.5, fontSize: 17 });
    T(s, src, { x: x + 0.35, y: y + 1.7, w: 5.2, h: 0.35, fontSize: 12, color: C.gris });
  });
  s.addNotes('Ahora el entorno. La hostelería española tiene más de 280.000 establecimientos y el 93 por ciento son independientes, como La Plancha. En la Comunitat Valenciana hay más de 31.000 bares y restaurantes, uno por cada 174 habitantes. Y el dato clave: el sector factura más, pero la restauración tuvo rentabilidad negativa en 2025. Conclusión para el proyecto: cualquier inversión se mide en euros ahorrados, no en funciones.');
}

// 10 · PESTEL
{
  const s = base('PESTEL: lo que no controla, pero le condiciona');
  const p = [['P', 'Político', 'Verifactu aplazado: 1/1/2027 para sociedades'], ['E', 'Económico', 'Factura más, gana menos: cada euro cuenta'], ['S', 'Social', 'Cliente joven que paga con móvil y espera wifi'], ['T', 'Tecnológico', 'Fin de Windows 10; la cocina sigue en papel'], ['E', 'Ambiental', 'Bisfenol A en el papel térmico; equipos viejos como RAEE'], ['L', 'Legal', 'Ley antifraude, RGPD, alérgenos, registro de jornada']];
  p.forEach(([k, t, d], i) => {
    const col = i % 3, fila = Math.floor(i / 3);
    const x = M + col * 4.1, y = 1.6 + fila * 2.45;
    tarjeta(s, x, y, 3.8, 2.15, i === 0 ? C.narClaro : C.claro);
    circulo(s, x + 0.3, y + 0.3, 0.7, k, { size: 22 });
    T(s, t, { x: x + 1.15, y: y + 0.3, w: 2.5, h: 0.7, fontSize: 18, bold: true, valign: 'middle' });
    T(s, d, { x: x + 0.3, y: y + 1.15, w: 3.3, h: 0.85, fontSize: 15, color: C.txt });
  });
  s.addNotes('El análisis PESTEL. En lo político y legal, lo que más pesa es Verifactu: desde el 1 de enero de 2027 una sociedad como La Plancha necesita un sistema de facturación adaptado, y su TPV de 2016 sin mantenimiento no lo estará. En lo económico, márgenes estrechos. En lo social, un cliente joven que paga con el móvil, así que el datáfono tiene que funcionar también en la terraza. En lo tecnológico, el fin de Windows 10 y una digitalización que se ha quedado en el cobro y no ha llegado a la cocina. En lo ambiental, el papel térmico y los residuos electrónicos. Y en lo legal, además, protección de datos con las cámaras, alérgenos y registro de jornada.');
}

// 11 · Microentorno
{
  const s = base('Clientes, proveedores y competencia');
  const cols = [
    ['Clientes', ['Estudiantes: rapidez y pago con móvil', 'Familias: cuenta dividida', 'Para llevar: saber cuándo está listo', 'Reparto: que no se pierda el pedido']],
    ['Proveedores TIC', ['Operadora: una sola línea', 'Banco: datáfono por wifi', 'TPV de 2016 sin mantenimiento', 'Plataformas: pedidos fuera del TPV']],
    ['Competencia', ['Cadenas con la comanda en pantalla', 'TPV de mercado: cobran por terminal', 'Cada pantalla de cocina es otra cuota', 'Hueco: pantallas sin licencia']],
  ];
  cols.forEach(([t, its], i) => {
    const x = M + i * 4.1;
    tarjeta(s, x, 1.55, 3.8, 3.9, i === 2 ? C.narClaro : C.claro);
    T(s, t, { x: x + 0.3, y: 1.8, w: 3.2, h: 0.5, fontSize: 20, bold: true, color: i === 2 ? C.txt : C.txt });
    T(s, its.map((x2, k) => ({ text: x2, options: { bullet: true, breakLine: k < its.length - 1 } })), { x: x + 0.3, y: 2.5, w: 3.25, h: 2.8, fontSize: 16, paraSpaceAfter: 12 });
  });
  T(s, 'Competencia tecnológica: estudio de mercado del proyecto (Riches Manuel y Roca, 2026).', { x: M, y: 5.75, w: 10, h: 0.3, fontSize: 12, color: C.gris });
  s.addNotes('El microentorno. Los clientes se concentran en franjas cortas: estudiantes que quieren rapidez, familias que dividen la cuenta, pedidos para llevar y reparto. Los proveedores que más importan son los tecnológicos: una operadora con una sola línea, el banco con su datáfono, el fabricante del TPV que ya no da mantenimiento y las plataformas, cuyos pedidos no llegan al TPV. En competencia hay dos planos: las cadenas, que ya llevan la comanda a la cocina en pantalla, y los TPV del mercado, que casi todos cobran por terminal. Nuestro estudio de trece productos lo confirma: añadir una pantalla de cocina es pagar otra licencia. Ahí está el hueco del proyecto.');
}

// 12 · Necesidades
{
  const s = base('Necesidades, por orden de urgencia');
  const nec = ['Separar la red: negocio, cocina, cámaras e invitados', 'Copias automáticas verificadas y un SAI', 'Caja con soporte y adaptable a Verifactu', 'Comanda en pantalla de cocina con tiempos', 'Cuentas individuales y datos fuera de lo personal', 'Wifi profesional en sala, terraza y cocina', 'Videovigilancia conforme al RGPD'];
  nec.forEach((t, i) => {
    const col = i < 4 ? 0 : 1, fila = i < 4 ? i : i - 4;
    const x = M + col * 6.2, y = 1.6 + fila * 1.15;
    circulo(s, x, y, 0.7, `${i + 1}`, { size: 18, fill: i < 3 ? C.nar : C.osc2 });
    T(s, t, { x: x + 0.95, y, w: 5.0, h: 0.7, fontSize: 17, valign: 'middle' });
  });
  tarjeta(s, M + 6.2, 5.05, 5.9, 1.4, C.narClaro);
  T(s, 'Proyecto de implantación: red segmentada, servidor local con el KDS+TPV, puestos de sala y cocina, copias y supervisión.', { x: M + 6.45, y: 5.15, w: 5.4, h: 1.2, fontSize: 15, valign: 'middle' });
  s.addNotes('Cruzando lo interno con el entorno salen siete necesidades. Las tres primeras son las urgentes: separar la red, hacer copias con un SAI y cambiar la caja por un sistema con soporte y adaptable a Verifactu. Después, llevar la comanda a la cocina en pantalla, que es el corazón del negocio; cuentas individuales; wifi profesional y adecuar las cámaras al RGPD. El tipo de proyecto que responde a esto es una implantación de infraestructura: red segmentada, un servidor local con nuestro TPV y KDS, los puestos de sala y cocina, y copias y supervisión.');
}

// 13 · Requisitos, obligaciones y ayudas
{
  const s = base('Lo que el proyecto tendrá que cumplir');
  const req = [['Sin internet', 'se sigue tomando nota y cobrando'], ['4 redes', 'desde invitados no se ve el negocio'], ['HTTPS', 'en todo el tráfico'], ['< 1 hora', 'para restaurar todo el sistema'], ['1 PIN', 'por persona: cada cobro tiene autor'], ['0 €', 'por terminal o por pantalla']];
  req.forEach(([a, b], i) => {
    const col = i % 3, fila = Math.floor(i / 3);
    const x = M + col * 2.6, y = 1.55 + fila * 2.0;
    tarjeta(s, x, y, 2.4, 1.75);
    T(s, a, { x: x + 0.2, y: y + 0.2, w: 2.0, h: 0.7, fontSize: 24, bold: true, color: C.nar });
    T(s, b, { x: x + 0.2, y: y + 0.9, w: 2.0, h: 0.75, fontSize: 13 });
  });
  tarjeta(s, 8.6, 1.55, 4.1, 3.75, C.osc);
  T(s, 'Fechas que obligan', { x: 8.85, y: 1.75, w: 3.6, h: 0.5, fontSize: 18, bold: true, color: C.blanco });
  T(s, [
    { text: '1/1/2027', options: { bold: true, color: C.nar, breakLine: true } },
    { text: 'Verifactu para sociedades', options: { color: C.blanco, breakLine: true } },
    { text: ' ', options: { breakLine: true, fontSize: 8 } },
    { text: '1/7/2027', options: { bold: true, color: C.nar, breakLine: true } },
    { text: 'Verifactu para el resto', options: { color: C.blanco } },
  ], { x: 8.85, y: 2.35, w: 3.6, h: 2.6, fontSize: 18 });
  T(s, 'Obligaciones: IVA del 10 % y facturación, registro de jornada, prevención de riesgos con pantallas y RGPD. Ayudas: Kit Digital (Red.es) y líneas del IVACE+i, según convocatoria abierta; el presupuesto se hará sin contar con ellas.', { x: M, y: 5.7, w: 12.1, h: 0.9, fontSize: 14, color: C.txt });
  s.addNotes('De las necesidades salen las características que tendrá que cumplir el proyecto, y que servirán para evaluarlo: funcionar sin internet, al menos cuatro redes separadas, todo el tráfico cifrado, restaurar el sistema en menos de una hora, un PIN por persona para que cada cobro tenga autor, y cero euros de cuota por pantalla. Hay fechas que obligan: Verifactu el 1 de enero de 2027 para sociedades. También recogemos las obligaciones fiscales, laborales y de prevención, y las ayudas posibles, como el Kit Digital; como dependen de convocatorias, el presupuesto se hará sin contar con ellas.');
}

// 14 · Conclusión
{
  const s = base(null, true);
  T(s, 'No falta dinero.', { x: M, y: 1.3, w: 12, h: 1.0, fontSize: 44, bold: true, color: C.blanco });
  T(s, 'Falta alguien que diseñe la infraestructura y la deje funcionando sola.', { x: M, y: 2.3, w: 11.5, h: 1.2, fontSize: 28, color: C.nar });
  const pasos = [['R2', 'Diseño'], ['R3', 'Viabilidad'], ['R4', 'Presupuesto'], ['R5', 'Documentación'], ['R6', 'Plan de intervención']];
  s.addShape(pres.shapes.LINE, { x: M + 0.45, y: 4.95, w: 10.4, h: 0, line: { color: '666666', width: 2 } });
  pasos.forEach(([k, t], i) => {
    const x = M + i * 2.6;
    circulo(s, x, 4.5, 0.9, k, { size: 18 });
    T(s, t, { x: x - 0.5, y: 5.55, w: 1.9, h: 0.6, fontSize: 15, color: C.blanco, align: 'center' });
  });
  s.addNotes('Para terminar. La Plancha tiene tres problemas de fondo: trabaja a ciegas durante el servicio, guarda sus datos en un equipo sin soporte y sin copias, y comparte una red plana con sus clientes. El entorno añade una fecha, Verifactu, y una oportunidad, el hardware barato y un software sin cuotas por pantalla. Y la conclusión que más nos ha sorprendido: las medidas más urgentes casi no cuestan dinero. No falta dinero; falta alguien que diseñe la infraestructura y la deje funcionando sola. Eso es lo que haremos en los próximos retos: diseño, viabilidad, presupuesto, documentación y plan de intervención.');
}

// 15 · Cierre
{
  const s = base(null, true);
  T(s, '¿Preguntas?', { x: M, y: 2.2, w: 12, h: 1.2, fontSize: 54, bold: true, color: C.blanco });
  T(s, 'Informe completo: «Análisis del contexto tecnológico de La Plancha» (Reto 1).', { x: M, y: 3.6, w: 12, h: 0.5, fontSize: 18, color: C.nar });
  T(s, 'Fuentes principales: INE (2025), Profesional Horeca (2025), Hosteltur (2026), El Periòdic (2025), Microsoft (2025), Garrigues (2025), Red.es (s.f.), normativa del BOE y del DOUE. Referencias completas en formato APA en el informe.', { x: M, y: 5.4, w: 12, h: 0.9, fontSize: 13, color: 'BBBBBB' });
  s.addNotes('Gracias. Quedamos abiertos a preguntas. Todas las fuentes están citadas en formato APA en el informe.');
}

pres.writeFile({ fileName: path.join(__dirname, 'reto1_presentacion.pptx') }).then((f) => console.log('PPTX:', f, `· ${n} diapositivas`));
