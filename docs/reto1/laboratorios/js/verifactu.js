// Lab 2: Verifactu de verdad. Seis facturas de un mediodía de Burglar King, encadenadas como registros de alta
// de VERI*FACTU. La huella sigue el documento de la AEAT «Detalle de las especificaciones técnicas para generación
// de la huella o hash de los registros de facturación» (v0.1.2): SHA-256 en hexadecimal y mayúsculas de
// IDEmisorFactura=…&NumSerieFactura=…&FechaExpedicionFactura=dd-mm-aaaa&TipoFactura=…&CuotaTotal=…&ImporteTotal=…
// &Huella=<huella anterior, vacía en el primer registro>&FechaHoraHusoGenRegistro=aaaa-mm-ddThh:mm:ss+01:00,
// con los valores sin espacios al principio ni al final y la cadena en UTF-8. El QR tributario (Orden
// HAC/1177/2024, art. 21: nivel M) lleva la URL de cotejo con nif, numserie, fecha e importe (js/qr.js).
// Todo es editable: se ve qué dato rompe la huella, qué dato solo cambia el registro remitido y qué dato
// solo está en la factura impresa.
'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

// SHA-256 propio (FIPS 180-4), síncrono: por HTTP en la red local no hay contexto seguro y el navegador no
// ofrece crypto.subtle. Comprobado con los dos ejemplos de alta de la AEAT (ver PRUEBA_AEAT abajo).
function sha256(s) {
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const m = new TextEncoder().encode(s), l = m.length, n = ((l + 9 + 63) >> 6) << 6, p = new Uint8Array(n); p.set(m); p[l] = 0x80;
  const dv = new DataView(p.buffer); dv.setUint32(n - 4, l * 8 >>> 0); dv.setUint32(n - 8, Math.floor(l * 8 / 2 ** 32));
  const r = (x, k) => (x >>> k) | (x << (32 - k)), w = new Uint32Array(64);
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
    for (let i = 16; i < 64; i++) { const a = w[i - 15], b = w[i - 2]; w[i] = (w[i - 16] + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + w[i - 7] + (r(b, 17) ^ r(b, 19) ^ (b >>> 10))) >>> 0; }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0, t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    [a, b, c, d, e, f, g, h].forEach((v, i) => { H[i] = (H[i] + v) >>> 0; });
  }
  return H.map(x => x.toString(16).padStart(8, '0')).join('').toUpperCase();
}
// Ejemplos 6.1 y 6.2 del documento de la AEAT: si no cuadran, el laboratorio lo dice en pantalla.
const PRUEBA_AEAT = (() => {
  const h1 = sha256('IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00');
  const h2 = sha256(`IDEmisorFactura=89890001K&NumSerieFactura=12345679/G34&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=${h1}&FechaHoraHusoGenRegistro=2024-01-01T19:20:35+01:00`);
  return h1 === '3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60' && h2 === 'F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97';
})();

// ---------------------------------------------------------------- Datos (inventados)
const SIF = { nombre: 'ServiPass, S.L.', nif: 'B10293847', sistema: 'ServiPass TPV', id: 'SP', version: '1.0', instalacion: 'BK-BJS-01' };
const EMISOR = { emNombre: 'Burglar King Burjassot, S.L.', emNif: 'B98765432', emDir: 'C/ de la Universitat, 12 · 46100 Burjassot (València)' };
const SIN_DEST = { desNombre: '', desNif: '', desDir: '' };
const L = (d, u, p, t = '10') => ({ d, u, p, t });
const ORIGINALES = [
  { num: 'BK-2027-000127', fecha: '15/01/2027', tipo: 'F2', servicio: 'Mesa 4', registro: '2027-01-15T13:42:10+01:00',
    lineas: [L('Hamburguesa clásica con patatas', '2', '11,50'), L('Refresco', '2', '2,50')] },
  { num: 'BK-2027-000128', fecha: '15/01/2027', tipo: 'F2', servicio: 'Para llevar', registro: '2027-01-15T13:47:35+01:00',
    lineas: [L('Doble queso con patatas', '1', '13,90'), L('Nuggets (6 uds.)', '1', '5,50'), L('Agua', '1', '1,80')] },
  { num: 'BK-2027-000129', fecha: '15/01/2027', tipo: 'F1', servicio: 'Mesa 9 · comida de empresa', registro: '2027-01-15T13:55:02+01:00',
    desNombre: 'Gestoría del Turia, S.L.', desNif: 'B46112233', desDir: 'Av. de Blasco Ibáñez, 40 · 46010 València',
    lineas: [L('Menú de mediodía', '3', '12,00'), L('Café', '2', '1,50')] },
  { num: 'BK-2027-000130', fecha: '15/01/2027', tipo: 'F2', servicio: 'Mesa 2', registro: '2027-01-15T14:03:48+01:00',
    lineas: [L('Ensalada César', '1', '8,90'), L('Hamburguesa vegetal', '1', '10,50'), L('Cerveza', '2', '2,80')] },
  { num: 'BK-2027-000131', fecha: '15/01/2027', tipo: 'F2', servicio: 'Reparto', registro: '2027-01-15T14:10:15+01:00',
    lineas: [L('Menú infantil', '2', '7,50'), L('Helado', '1', '3,20')] },
  { num: 'BK-2027-000132', fecha: '15/01/2027', tipo: 'F2', servicio: 'Mesa 7', registro: '2027-01-15T14:18:40+01:00',
    lineas: [L('Menú de mediodía', '4', '12,00'), L('Café', '4', '1,50'), L('Tarta de queso', '1', '4,50')] },
].map(f => ({ ...EMISOR, ...SIN_DEST, descripcion: 'Servicio de restauración', ...f }));

// Qué afecta a qué: «h» entra en la huella (directamente o por los importes), «r» va en el registro de alta
// remitido a la AEAT pero no en la huella, «f» solo está en la factura impresa.
const CLASE = { num: 'h', fecha: 'h', tipo: 'h', emNif: 'h', registro: 'h', anterior: 'h', u: 'h', p: 'h', t: 'h',
  emNombre: 'r', desNombre: 'r', desNif: 'r', descripcion: 'r', emDir: 'f', desDir: 'f', servicio: 'f', d: 'f' };

const copia = o => JSON.parse(JSON.stringify(o));
// Importes como se escriben en España: «1.500,00», «1.500», «11,50» o «11.5».
const cent = s => {
  let t = String(s).trim().replace(/[\s€]/g, '');
  if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.'); else if (/^\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, '');
  const x = parseFloat(t); return isFinite(x) ? Math.round(x * 100) : 0;
};
const dec = c => (c / 100).toFixed(2);                       // formato del XML y de la URL: 28.00
const eur = c => { const [e, d] = (Math.abs(c) / 100).toFixed(2).split('.'); return (c < 0 ? '−' : '') + e.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + d + ' €'; };
const fechaXml = s => String(s).trim().replace(/\//g, '-');  // 15/01/2027 → 15-01-2027
const corta = h => h.slice(0, 2) + '…' + h.slice(-2);

function importes(f) {
  const grupos = {};
  for (const l of f.lineas) {
    const t = String(l.t).trim().replace(',', '.'), imp = Math.round(cent(l.p) * (parseFloat(String(l.u).replace(',', '.')) || 0));
    grupos[t] = (grupos[t] || 0) + imp;
  }
  const desglose = Object.entries(grupos).map(([t, total]) => {   // precios con IVA incluido
    const tipo = parseFloat(t) || 0, base = Math.round(total / (1 + tipo / 100));
    return { tipo, base, cuota: total - base, total };
  });
  return { desglose, cuota: desglose.reduce((a, d) => a + d.cuota, 0), total: desglose.reduce((a, d) => a + d.total, 0) };
}
// Los ocho valores de la huella, en el orden del documento de la AEAT, ya recortados.
function valores(f) {
  const { cuota, total } = importes(f);
  return [['IDEmisorFactura', f.emNif], ['NumSerieFactura', f.num], ['FechaExpedicionFactura', fechaXml(f.fecha)], ['TipoFactura', f.tipo],
    ['CuotaTotal', dec(cuota)], ['ImporteTotal', dec(total)], ['Huella', f.anterior], ['FechaHoraHusoGenRegistro', f.registro]]
    .map(([k, v]) => [k, String(v).trim()]);
}
const cadena = f => valores(f).map(([k, v]) => `${k}=${v}`).join('&');
const huella = f => sha256(cadena(f));
const urlQR = f => `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=${encodeURIComponent(f.emNif.trim())}&numserie=${encodeURIComponent(f.num.trim())}&fecha=${encodeURIComponent(fechaXml(f.fecha))}&importe=${dec(importes(f).total)}`;
// Lo que va en el registro remitido y no en la huella (para ver si difiere de lo remitido).
const fueraHuella = f => JSON.stringify([f.emNombre.trim(), f.descripcion.trim(), f.tipo === 'F1' ? [f.desNombre.trim(), f.desNif.trim()] : [], importes(f).desglose.map(d => [d.tipo, d.base])]);

// ---------------------------------------------------------------- Estado
let F = [], REG = [], sel = 0, act = [], token = 0;
function emite() {           // emite las seis en orden: cada una guarda la huella de la anterior; eso es lo remitido
  F = copia(ORIGINALES); REG = [];
  F.forEach((f, k) => { f.anterior = k ? REG[k - 1].huella : ''; REG.push({ huella: huella(f), valores: valores(f), fuera: fueraHuella(f), orig: copia(f) }); });
}
const recalcula = () => { act = F.map(huella); };
const alterada = k => act[k] !== REG[k].huella;
const enlaceRoto = k => k > 0 && F[k].anterior.trim() !== act[k - 1];   // ¿la factura k encaja con la k-1?

// ---------------------------------------------------------------- Cadena (menú horizontal)
// Cada casilla va precedida (en el mismo bloque, para que al pasar a varias filas no se separen) por la huella
// de la factura anterior tal como la guarda esta, con los caracteres que ya no coinciden en rojo.
function pintaCadena(ocultas = new Set()) {
  let h = '<div class="ini" title="PrimerRegistro = S">primer<br>registro</div>';
  F.forEach((f, k) => {
    let enl = '';
    if (k) {
      const guardada = F[k].anterior.trim().padEnd(64, ' ').slice(0, 64), roto = enlaceRoto(k);
      const lineas = []; for (let i = 0; i < 64; i += 8) lineas.push([...guardada.slice(i, i + 8)].map((c, j) => c === act[k - 1][i + j] ? esc(c) : `<i>${c === ' ' ? '&nbsp;' : esc(c)}</i>`).join(''));
      enl = `<div class="enl ${roto ? 'roto' : 'ok'}${ocultas.has('e' + k) ? ' oculta' : ''}" title="Huella de ${esc(F[k - 1].num)} guardada en ${esc(F[k].num)}"><span class="fl">${roto ? '✘ no encaja' : '✔ huella →'}</span><code class="hx">${lineas.map(x => `<span>${x}</span>`).join('')}</code></div>`;
    }
    const mal = alterada(k);
    h += `<div class="par">${enl}<button class="cas ${mal ? 'mal' : 'ok'}${k === sel ? ' sel' : ''}${ocultas.has('c' + k) ? ' oculta' : ''}" data-k="${k}"><b>${esc(f.num)}</b><span class="hc">${corta(act[k])}</span><span class="marca">${mal ? '✘ alterada' : '✔ íntegra'}</span></button></div>`;
  });
  $('#cadena').innerHTML = h;
}
$('#cadena').addEventListener('click', e => { const b = e.target.closest('.cas'); if (b) { token++; selecciona(+b.dataset.k); } });

// ---------------------------------------------------------------- Factura modelo (se construye al elegir una casilla)
const inp = (c, v, extra = '', clase = 'e') => `<input class="${clase}" data-c="${c}" value="${esc(v)}" ${extra}>`;
function selecciona(k) {
  sel = k; const f = F[k];
  $('#papel').innerHTML = `
  <div class="cab">
   <div class="qrb"><span>QR tributario:</span><div class="qr" id="qr"></div><span class="vf" title="Orden HAC/1177/2024, art. 20: «Factura verificable en la sede electrónica de la AEAT» o «VERI*FACTU»">VERI*FACTU</span></div>
   <div class="emi">${inp('emNombre', f.emNombre, '', 'e nom')}
    <div class="datos"><span>NIF</span>${inp('emNif', f.emNif)}<span>Domicilio</span>${inp('emDir', f.emDir)}
     <span>Tipo</span><select class="e" data-c="tipo"><option value="F2"${f.tipo === 'F2' ? ' selected' : ''}>F2 · simplificada</option><option value="F1"${f.tipo === 'F1' ? ' selected' : ''}>F1 · completa</option></select>
     <span>Número</span>${inp('num', f.num)}<span>Fecha de expedición</span>${inp('fecha', f.fecha)}</div></div>
  </div>
  <div class="tit"><h2 id="titulo"></h2>${inp('servicio', f.servicio, 'title="Servicio"')}</div>
  ${f.tipo === 'F1' ? `<div class="dest"><span>Destinatario</span>${inp('desNombre', f.desNombre)}<span>NIF</span>${inp('desNif', f.desNif)}<span>Domicilio</span>${inp('desDir', f.desDir)}</div>` : ''}
  <table><tr><th>Uds.</th><th>Concepto</th><th>Precio</th><th>IVA %</th><th style="text-align:right">Importe</th></tr>
  ${f.lineas.map((l, i) => `<tr><td class="n"><input class="e num" data-l="${i}" data-p="u" value="${esc(l.u)}"></td><td><input class="e" data-l="${i}" data-p="d" value="${esc(l.d)}"></td>
   <td class="p"><input class="e num" data-l="${i}" data-p="p" value="${esc(l.p)}"></td><td class="t"><input class="e num" data-l="${i}" data-p="t" value="${esc(l.t)}"></td><td class="imp" id="imp${i}"></td></tr>`).join('')}</table>
  <div class="desg" id="desg"></div>
  <div class="pie" id="pie"></div>`;
  $('#registro').innerHTML = `<h3>Registro de facturación de alta <span class="lbl" style="margin:0"># = entra en la huella</span></h3><div class="campos" id="reg"></div>`;
  $('#huella').innerHTML = `
  <h3>Huella del registro <span class="sello" id="sello"></span></h3>
  <div class="lbl" style="margin-top:0">Huella anterior (Encadenamiento${k ? ' · RegistroAnterior' : ' · PrimerRegistro = S, vacía'})</div>
  ${inp('anterior', f.anterior, k ? '' : 'placeholder="vacía: primer registro"')}
  <div class="lbl">Cadena que se calcula (SHA-256, UTF-8; en rojo, lo que difiere de lo remitido)</div>
  <div class="firma" id="firma"></div>
  <div class="lbl">Huella remitida a la AEAT al expedir la factura</div><code class="hex" id="hreg"></code>
  <div class="lbl">Huella recalculada con los datos de ahora · <span class="cuantos" id="cuantos"></span></div><code class="hex" id="hact"></code>
  <div class="lbl">URL del QR (entorno de pruebas de la AEAT)</div><div class="url" id="url"></div>
  <div class="ley"><span class="lh">rompe la huella</span><span class="lr">solo en el registro remitido</span><span class="lf">solo en la factura impresa</span></div>`;
  actualiza();
}
// Campos del registro de alta: {c: campo, val: valor (HTML ya escapado) o input, cl: 'h' si entra en la huella, 'r' si va en el registro, dif}
function filasRegistro(f, k) {
  const v = Object.fromEntries(valores(f)), rv = Object.fromEntries(REG[k].valores), o = REG[k].orig, im = importes(f), ant = k ? F[k - 1] : null;
  const fila = (c, val, cl = '', ref) => ({ c, val: esc(val), cl, dif: ref !== undefined && String(ref) !== String(val) });
  const filas = [fila('IDVersion', '1.0'),
    { g: 'IDFactura' }, fila('IDEmisorFactura', v.IDEmisorFactura, 'h', rv.IDEmisorFactura), fila('NumSerieFactura', v.NumSerieFactura, 'h', rv.NumSerieFactura),
    fila('FechaExpedicionFactura', v.FechaExpedicionFactura, 'h', rv.FechaExpedicionFactura),
    { g: 'Datos de la factura' }, fila('NombreRazonEmisor', f.emNombre.trim(), 'r', o.emNombre.trim()), fila('TipoFactura', v.TipoFactura, 'h', rv.TipoFactura),
    { c: 'DescripcionOperacion', val: inp('descripcion', f.descripcion), cl: 'r', dif: f.descripcion.trim() !== o.descripcion.trim() }];
  if (f.tipo === 'F1') filas.push({ g: 'Destinatarios · IDDestinatario' }, fila('NombreRazon', f.desNombre.trim(), 'r', o.desNombre.trim()), fila('NIF', f.desNif.trim(), 'r', o.desNif.trim()));
  im.desglose.forEach((d, i) => filas.push({ g: `Desglose · DetalleDesglose ${i + 1}` }, fila('ClaveRegimen · CalificacionOperacion', '01 · S1'),
    fila('TipoImpositivo', d.tipo.toFixed(2)), fila('BaseImponibleOimporteNoSujeto', dec(d.base), 'r'), fila('CuotaRepercutida', dec(d.cuota), 'r')));
  filas.push({ g: 'Importes' }, fila('CuotaTotal', v.CuotaTotal, 'h', rv.CuotaTotal), fila('ImporteTotal', v.ImporteTotal, 'h', rv.ImporteTotal), { g: 'Encadenamiento' });
  if (!k) filas.push(fila('PrimerRegistro', 'S'));
  else filas.push(fila('IDEmisorFactura', ant.emNif.trim()), fila('NumSerieFactura', ant.num.trim()), fila('FechaExpedicionFactura', fechaXml(ant.fecha)));
  filas.push(fila('Huella', v.Huella ? corta(v.Huella) + ' (ver la huella)' : '(vacía)', 'h', v.Huella === rv.Huella ? undefined : ''));
  filas.push({ g: 'SistemaInformatico' }, fila('NombreRazon · NIF', `${SIF.nombre} · ${SIF.nif}`), fila('NombreSistemaInformatico', SIF.sistema),
    fila('IdSistemaInformatico · Version', `${SIF.id} · ${SIF.version}`), fila('NumeroInstalacion', SIF.instalacion), fila('TipoUsoPosibleSoloVerifactu', 'S'),
    { g: 'Generación y huella' }, { c: 'FechaHoraHusoGenRegistro', val: inp('registro', f.registro), cl: 'h', dif: v.FechaHoraHusoGenRegistro !== rv.FechaHoraHusoGenRegistro },
    fila('TipoHuella', '01'), fila('Huella', corta(act[k]) + ' (ver la huella)'));
  return filas;
}
const claseFila = r => `fr ${r.cl || ''}${r.dif ? ' dif-' + r.cl : ''}`;
function actualiza() {
  recalcula();
  const k = sel, f = F[k], im = importes(f), mal = alterada(k);
  // Factura impresa
  $('#titulo').textContent = f.tipo === 'F1' ? 'FACTURA' : 'FACTURA SIMPLIFICADA';
  f.lineas.forEach((l, i) => { const c = $('#imp' + i); if (c) c.textContent = eur(Math.round(cent(l.p) * (parseFloat(String(l.u).replace(',', '.')) || 0))); });
  $('#desg').innerHTML = '<span></span><span class="h">Base imponible</span><span class="h">Cuota de IVA</span>' +
    im.desglose.map(d => `<span>IVA al ${d.tipo} %</span><b>${eur(d.base)}</b><b>${eur(d.cuota)}</b>`).join('') +
    `<span class="tot">Total</span><b class="tot" style="grid-column:2/4">${eur(im.total)}</b>`;
  $('#pie').textContent = 'Precios con IVA incluido.';
  try { $('#qr').innerHTML = QR.svg(urlQR(f)); } catch (e) { $('#qr').textContent = 'URL demasiado larga'; }
  // Registro: se rehace entero salvo mientras se escribe en uno de sus campos (entonces solo cambian los valores)
  const filas = filasRegistro(f, k), reg = $('#reg'), foco = document.activeElement && document.activeElement.closest && document.activeElement.closest('#reg');
  if (!foco || reg.children.length !== filas.length) {
    reg.innerHTML = filas.map(r => r.g ? `<div class="fr g">${esc(r.g)}</div>` : `<div class="${claseFila(r)}"><span class="c">${esc(r.c)}</span><span class="v">${r.val}</span></div>`).join('');
  } else {
    [...reg.children].forEach((d, i) => { const r = filas[i]; if (r.g) return; d.className = claseFila(r); if (!r.val.startsWith('<input')) d.lastElementChild.innerHTML = r.val; });
  }
  // Huella
  const rv = REG[k].valores;
  $('#firma').innerHTML = valores(f).map(([c, v], i) => `<u>${c}</u>=${v === rv[i][1] ? esc(v) : `<i>${esc(v) || '&nbsp;'}</i>`}`).join('&amp;');
  $('#hreg').textContent = REG[k].huella;
  $('#hact').innerHTML = [...act[k]].map((c, i) => c === REG[k].huella[i] ? c : `<i>${c}</i>`).join('');
  const iguales = [...act[k]].filter((c, i) => c === REG[k].huella[i]).length;
  $('#cuantos').textContent = mal ? `coinciden ${iguales} de 64 caracteres` : 'coincide entera';
  const s = $('#sello'); s.className = 'sello ' + (mal ? 'mal' : 'ok'); s.textContent = mal ? '✘ alterado' : '✔ íntegro';
  $('#url').textContent = urlQR(f);
  // Campos cambiados respecto de lo emitido, coloreados según lo que rompen
  const o = REG[k].orig;
  document.querySelectorAll('[data-c]').forEach(e => { const c = e.dataset.c; e.classList.remove('ch-h', 'ch-r', 'ch-f'); if (String(f[c]) !== String(o[c])) e.classList.add('ch-' + CLASE[c]); });
  document.querySelectorAll('[data-l]').forEach(e => { const i = +e.dataset.l, p = e.dataset.p; e.classList.remove('ch-h', 'ch-r', 'ch-f'); if (o.lineas[i] && String(f.lineas[i][p]) !== String(o.lineas[i][p])) e.classList.add('ch-' + CLASE[p]); });
  pintaCadena();
  explica();
}
function explica() {
  const malas = F.map((_, k) => k).filter(alterada), rotos = F.map((_, k) => k).filter(enlaceRoto), fueras = F.map((_, k) => k).filter(k => fueraHuella(F[k]) !== REG[k].fuera);
  const n = k => F[k].num.trim() || `la ${k + 1}.ª`;
  let t;
  if (!PRUEBA_AEAT) t = '<b class="ko">El cálculo de la huella no reproduce los ejemplos de la AEAT.</b>';
  else if (!malas.length && !rotos.length) t = fueras.length ? `<b class="ok">✔ Cadena íntegra.</b> ${fueras.map(n).join(', ')}: el cambio no entra en la huella, pero ya no coincide con el registro remitido a la AEAT.`
    : '<b class="ok">✔ Cadena íntegra:</b> cada huella coincide con la remitida a la AEAT y cada factura lleva la huella de la anterior. Cambia cualquier dato para romperla.';
  else if (malas.length && !rotos.length) t = `<b class="ko">✘ La cadena encaja por dentro, pero ${malas.map(n).join(', ')} ya no coincide${malas.length > 1 ? 'n' : ''} con lo remitido a la AEAT</b> al expedir: en VERI*FACTU rehacer la cadena no borra el rastro.`;
  else t = `<b class="ko">✘ Cadena rota.</b> ${malas.length ? `${malas.map(n).join(', ')}: su huella recalculada no coincide con la remitida. ` : ''}${rotos.map(k => `${n(k)} guarda una huella de ${n(k - 1)} que ya no es la suya`).join('; ')}.`;
  $('#msg').innerHTML = t;
}
// Solo «input» (también lo lanza el <select>): un «change» tardío del campo que tenía el foco, al rehacer la
// factura tras «Restaurar», volvería a meter el valor viejo.
function cambia(e) {
  const el = e.target, f = F[sel];
  if (el.dataset.c) { f[el.dataset.c] = el.value; if (el.dataset.c === 'tipo') return selecciona(sel); }
  else if (el.dataset.l !== undefined) f.lineas[+el.dataset.l][el.dataset.p] = el.value;
  else return;
  token++; actualiza();
}
['#papel', '#registro', '#huella'].forEach(s => $(s).addEventListener('input', cambia));

// ---------------------------------------------------------------- Botones
const espera = ms => new Promise(r => setTimeout(r, ms));
const suelta = () => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); };
$('#restaurar').addEventListener('click', () => { token++; suelta(); emite(); selecciona(sel); });
$('#alterar').addEventListener('click', () => {
  token++; suelta(); emite(); F[1].lineas[0].p = '3,90'; selecciona(1);
  $('#msg').innerHTML += ' <span class="lbl">(Se ha rebajado el «Doble queso» de 13,90 a 3,90 €, como haría un TPV sin Verifactu.)</span>';
});
$('#rehacer').addEventListener('click', () => {
  token++; suelta(); recalcula();
  if (!F.some((_, k) => alterada(k) || enlaceRoto(k))) { emite(); F[1].lineas[0].p = '3,90'; recalcula(); }
  for (let k = 1; k < F.length; k++) F[k].anterior = huella(F[k - 1]);
  selecciona(sel);
});
$('#simular').addEventListener('click', async () => {
  const t = ++token; suelta(); emite(); recalcula();
  const ocultas = new Set(F.flatMap((_, k) => ['c' + k, 'e' + k]));
  for (let k = 0; k < F.length; k++) {
    if (t !== token) return;
    selecciona(k);
    if (k) { ocultas.delete('e' + k); pintaCadena(ocultas); $('#msg').innerHTML = `Se expide ${esc(F[k].num)}: su registro guarda la huella de ${esc(F[k - 1].num)}…`; await espera(900); if (t !== token) return; }
    else { pintaCadena(ocultas); $('#msg').innerHTML = `Se expide ${esc(F[0].num)}, el primer registro del TPV: huella anterior vacía (PrimerRegistro = S)…`; }
    ocultas.delete('c' + k); pintaCadena(ocultas);
    const c = $(`.cas[data-k="${k}"]`); c.classList.add('calc');
    for (let i = 0; i < 6; i++) { if (t !== token) return; c.querySelector('.hc').textContent = corta(sha256(Math.random() + '')); await espera(110); }
    pintaCadena(ocultas);
    $('#msg').innerHTML = `${esc(F[k].num)}: huella ${act[k].slice(0, 8)}… calculada y registro remitido a la AEAT.`;
    await espera(800);
  }
  if (t === token) selecciona(0);
});

emite(); selecciona(0);
