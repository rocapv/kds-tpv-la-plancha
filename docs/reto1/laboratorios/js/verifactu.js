// Lab 2: tres facturas de Burglar King encadenadas al estilo Verifactu. La huella es el SHA-256 de la cadena
// con el formato del reglamento (NIF, número, fecha, tipo, cuota, total, huella anterior y hora del registro).
// Se puede cambiar cualquier dato: la huella recalculada deja de coincidir con la registrada, carácter a
// carácter, y la factura siguiente deja de encajar. SHA-256 con Web Crypto y, si no está disponible (file://
// en navegadores antiguos), una implementación propia en JavaScript puro.
'use strict';
const $ = s => document.querySelector(s);
async function sha256(texto) {
  if (globalThis.crypto && crypto.subtle) {
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(texto));
    return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
  }
  return sha256js(texto).toUpperCase();
}
function sha256js(s) { // implementación compacta de FIPS 180-4 para cadenas UTF-8
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const m = new TextEncoder().encode(s), l = m.length, n = ((l + 9 + 63) >> 6) << 6, p = new Uint8Array(n); p.set(m); p[l] = 0x80;
  new DataView(p.buffer).setUint32(n - 4, l * 8 >>> 0); new DataView(p.buffer).setUint32(n - 8, Math.floor(l * 8 / 2 ** 32));
  const r = (x, k) => (x >>> k) | (x << (32 - k)), w = new Uint32Array(64);
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = new DataView(p.buffer).getUint32(o + i * 4);
    for (let i = 16; i < 64; i++) { const a = w[i - 15], b = w[i - 2]; w[i] = (w[i - 16] + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + w[i - 7] + (r(b, 17) ^ r(b, 19) ^ (b >>> 10))) >>> 0; }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0, t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    [a, b, c, d, e, f, g, h].forEach((v, i) => H[i] = (H[i] + v) >>> 0);
  }
  return H.map(x => x.toString(16).padStart(8, '0')).join('');
}

// ---------------------------------------------------------------- Las tres facturas (datos inventados)
const EMISOR = { nombre: 'Burglar King Burjassot, S.L.', nif: 'B98765432', dir: 'C/ de la Universitat, 12 · 46100 Burjassot (València)' };
const ORIGINALES = [
  { num: 'BK-2027-000127', fecha: '15/01/2027', hora: '13:42:10', donde: 'Mesa 4',
    lineas: [['Hamburguesa clásica + patatas', '2', '11,50'], ['Refresco', '2', '2,50']] },
  { num: 'BK-2027-000128', fecha: '15/01/2027', hora: '13:47:35', donde: 'Para llevar',
    lineas: [['Doble queso + patatas', '1', '13,90'], ['Nuggets (6 uds.)', '1', '5,50'], ['Agua', '1', '1,80']] },
  { num: 'BK-2027-000129', fecha: '15/01/2027', hora: '13:55:02', donde: 'Mesa 9',
    lineas: [['Menú de mediodía', '3', '12,00'], ['Café', '2', '1,50']] },
];
const IVA = 0.10;
const num = s => { const x = parseFloat(String(s).replace(/\./g, '').replace(',', '.')); return isFinite(x) ? x : 0; };
const eur = x => x.toFixed(2).replace('.', ',') + ' €';
const dosDec = x => x.toFixed(2);
let F = [];            // estado actual de cada factura: valores de los campos
let REG = [];          // lo registrado al emitir: huella y huella anterior

function importes(f) {
  const total = Math.round(f.lineas.reduce((a, l) => a + num(l[1]) * num(l[2]), 0) * 100) / 100;
  const base = Math.round(total / (1 + IVA) * 100) / 100;
  return { total, base, cuota: Math.round((total - base) * 100) / 100 };
}
// Cadena que se firma, con los campos y el orden del reglamento (registro de alta).
function cadena(f, anterior) {
  const { total, cuota } = importes(f);
  const [d, m, a] = f.fecha.split('/');
  return `IDEmisorFactura=${EMISOR.nif}&NumSerieFactura=${f.num}&FechaExpedicionFactura=${d}-${m}-${a}&TipoFactura=F2&CuotaTotal=${dosDec(cuota)}&ImporteTotal=${dosDec(total)}&Huella=${anterior}&FechaHoraHusoGenRegistro=${a}-${m}-${d}T${f.hora}+01:00`;
}
const copia = o => JSON.parse(JSON.stringify(o));

// ---------------------------------------------------------------- Pintado
function tarjeta(k) {
  const f = F[k], o = ORIGINALES[k];
  const campo = (id, v, ancho) => `<input id="${id}" value="${v}" autocomplete="off" spellcheck="false"${ancho ? ` style="width:${ancho}"` : ''}>`;
  return `<div class="fra" id="fra${k}">
   <span class="sello" id="sello${k}"></span>
   <h3>Factura simplificada</h3>
   <div class="em">${EMISOR.nombre} · NIF ${EMISOR.nif}<br>${EMISOR.dir}</div>
   <div class="enlace" id="enlace${k}"></div>
   <div class="meta"><span>Número</span>${campo(`f${k}_num`, f.num)}<span>Fecha</span>${campo(`f${k}_fecha`, f.fecha)}<span>Hora</span>${campo(`f${k}_hora`, f.hora)}<span>Servicio</span><b>${o.donde}</b></div>
   <table><tr><th>Concepto</th><th>Uds.</th><th>Precio</th><th style="text-align:right">Importe</th></tr>
   ${f.lineas.map((l, j) => `<tr><td>${l[0]}</td><td class="n">${campo(`f${k}_c${j}`, l[1])}</td><td class="p">${campo(`f${k}_p${j}`, l[2])}</td><td class="t" id="f${k}_t${j}"></td></tr>`).join('')}
   </table>
   <div class="tot"><span>Base imponible</span><b id="f${k}_base"></b><span>IVA (10 %)</span><b id="f${k}_cuota"></b><span class="g">Total</span><b class="g" id="f${k}_total"></b></div>
   <div class="huellas">
    <span>Huella anterior (la de la factura previa)</span><span class="hex" id="f${k}_prev"></span>
    <span>Huella registrada al emitir</span><span class="hex" id="f${k}_reg"></span>
    <span>Huella recalculada ahora</span><span class="hex" id="f${k}_act"></span>
    <span class="cuantos" id="f${k}_cuantos"></span>
    <details class="cadena-txt"><summary>ver lo que se firma</summary><div class="firma" id="f${k}_firma"></div></details>
   </div></div>`;
}
function pintaTodo() {
  $('#facturas').innerHTML = F.map((_, k) => tarjeta(k)).join('');
  F.forEach((f, k) => {
    const engancha = (id, set) => $('#' + id).addEventListener('input', e => { set(e.target.value); recalcula(); });
    engancha(`f${k}_num`, v => f.num = v); engancha(`f${k}_fecha`, v => f.fecha = v); engancha(`f${k}_hora`, v => f.hora = v);
    f.lineas.forEach((l, j) => { engancha(`f${k}_c${j}`, v => l[1] = v); engancha(`f${k}_p${j}`, v => l[2] = v); });
  });
}
// Huella en grupos de 16, con en rojo los caracteres que no coinciden con la de referencia.
function hex(h, ref) {
  let out = '';
  for (let i = 0; i < h.length; i++) {
    const c = h[i]; out += ref && ref[i] !== c ? `<i>${c}</i>` : c;
    if (i % 16 === 15 && i < h.length - 1) out += ' ';
  }
  return out;
}
let turno = 0;
async function recalcula() {
  const t = ++turno;
  const actuales = [];
  for (let k = 0; k < F.length; k++) actuales.push(await sha256(cadena(F[k], REG[k].prev)));
  if (t !== turno) return;        // ha llegado otra edición mientras se calculaba
  let primera = -1;
  F.forEach((f, k) => {
    const o = ORIGINALES[k], { total, base, cuota } = importes(f), ok = actuales[k] === REG[k].huella;
    f.lineas.forEach((l, j) => { $(`#f${k}_t${j}`).textContent = eur(num(l[1]) * num(l[2])); });
    $(`#f${k}_base`).textContent = eur(base); $(`#f${k}_cuota`).textContent = eur(cuota); $(`#f${k}_total`).textContent = eur(total);
    // Campos cambiados respecto a lo emitido
    const marca = (id, v, vo) => $('#' + id).classList.toggle('cambiado', v !== vo);
    marca(`f${k}_num`, f.num, o.num); marca(`f${k}_fecha`, f.fecha, o.fecha); marca(`f${k}_hora`, f.hora, o.hora);
    f.lineas.forEach((l, j) => { marca(`f${k}_c${j}`, l[1], o.lineas[j][1]); marca(`f${k}_p${j}`, l[2], o.lineas[j][2]); });
    $(`#f${k}_prev`).innerHTML = REG[k].prev ? hex(REG[k].prev) : '(ninguna: es la primera de la cadena)';
    $(`#f${k}_reg`).innerHTML = hex(REG[k].huella);
    $(`#f${k}_act`).innerHTML = hex(actuales[k], REG[k].huella);
    const iguales = [...actuales[k]].filter((c, i) => c === REG[k].huella[i]).length;
    $(`#f${k}_cuantos`).textContent = ok ? 'Coinciden los 64 caracteres.' : `Coinciden ${iguales} de 64 caracteres: con un solo cambio, la huella es otra.`;
    $(`#f${k}_firma`).innerHTML = resalta(cadena(f, REG[k].prev), cadena(o, REG[k].prev));
    $(`#fra${k}`).classList.toggle('ok', ok); $(`#fra${k}`).classList.toggle('mal', !ok);
    const s = $(`#sello${k}`); s.className = 'sello ' + (ok ? 'ok' : 'mal'); s.textContent = ok ? '✔ cuadra' : '✘ alterada';
    // Eslabón con la anterior: la huella anterior que guardó esta factura frente a la huella real de la previa.
    const en = $(`#enlace${k}`);
    if (k === 0) { en.className = 'enlace'; en.textContent = 'Primera factura de la cadena.'; }
    else { const encaja = REG[k].prev === actuales[k - 1];
      en.className = 'enlace ' + (encaja ? 'ok' : 'mal');
      en.textContent = encaja ? `⛓ Encaja con ${F[k - 1].num}` : `⛓ Eslabón roto: apunta a la huella antigua de ${ORIGINALES[k - 1].num}`; }
    if (!ok && primera < 0) primera = k;
  });
  if (primera < 0) $('#msg').innerHTML = '<span class="ok">✔ Cadena íntegra:</span> las huellas recalculadas coinciden con las registradas y cada factura encaja con la anterior.';
  else {
    const sig = primera < F.length - 1 ? ` Además, la factura ${ORIGINALES[primera + 1].num} se encadenó con la huella antigua: <b>la cadena se rompe aquí</b>, y se nota aunque nadie toque las siguientes.` : '';
    $('#msg').innerHTML = `<span class="ko">✘ La factura ${ORIGINALES[primera].num} ya no coincide con su huella registrada.</span> Alguien ha cambiado sus datos después de emitirla.${sig} Con Verifactu, la única forma válida de corregir una factura es emitir una factura rectificativa al final de la cadena.`;
  }
}
// Marca en la cadena firmada los trozos que han cambiado (por campos separados con &).
function resalta(a, b) {
  const pa = a.split('&'), pb = b.split('&');
  return pa.map((x, i) => x === pb[i] ? x : `<i>${x}</i>`).join('&amp;').replace(/&(?!amp;)/g, '&amp;');
}

// ---------------------------------------------------------------- Acciones
async function emiteTodo() {
  F = copia(ORIGINALES); REG = [];
  let prev = '';
  for (const f of F) { const h = await sha256(cadena(f, prev)); REG.push({ prev, huella: h }); prev = h; }
}
async function restaura() { await emiteTodo(); pintaTodo(); await recalcula(); }
async function rebaja(animado) {
  const id = 'f1_p0', el = $('#' + id), destino = '3,90';
  if (!animado) { el.value = destino; F[1].lineas[0][2] = destino; return recalcula(); }
  for (const v of ['13,9', '13,', '13', '1', '', '3', '3,', '3,9', destino]) { el.value = v; F[1].lineas[0][2] = v || '0'; await recalcula(); await espera(260); }
}
const espera = ms => new Promise(r => setTimeout(r, ms));
const paso = t => { $('#paso').textContent = t; };
let simulando = false;
$('#restaurar').addEventListener('click', async () => { if (simulando) return; await restaura(); paso(''); });
$('#alterar').addEventListener('click', async () => { if (simulando) return; await restaura(); await rebaja(false); paso('Factura 2 rebajada: la doble queso pasa de 13,90 € a 3,90 €.'); });
$('#simular').addEventListener('click', async () => {
  if (simulando) return; simulando = true; ['#simular', '#alterar', '#restaurar'].forEach(s => $(s).disabled = true);
  await restaura();
  document.querySelectorAll('.fra').forEach(c => c.classList.add('oculta'));
  paso('1/4 · Se emiten tres facturas en un servicio de mediodía; cada una se encadena con la huella de la anterior.');
  for (let k = 0; k < F.length; k++) { await espera(1100); const c = $('#fra' + k); c.classList.remove('oculta'); c.classList.add('entra'); }
  await espera(1600);
  paso('2/4 · Las tres huellas recalculadas coinciden con las registradas: la cadena está íntegra.'); await espera(3200);
  paso('3/4 · Alguien rebaja la factura 2 para pagar menos IVA: la doble queso pasa de 13,90 € a 3,90 €.');
  document.getElementById('fra1').scrollIntoView({ behavior: 'smooth', block: 'center' }); await espera(900);
  await rebaja(true); await espera(1500);
  paso('4/4 · La huella de la factura 2 ya no es la registrada (casi todos los caracteres cambian) y la factura 3 apuntaba a la huella antigua: la alteración se ve. Prueba a cambiar tú cualquier otro dato.');
  simulando = false; ['#simular', '#alterar', '#restaurar'].forEach(s => $(s).disabled = false);
});

restaura();
