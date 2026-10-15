// Lab 2: cadena de facturas al estilo Verifactu. SHA-256 con Web Crypto y, si no está disponible (file:// en
// navegadores antiguos), una implementación propia en JavaScript puro.
'use strict';
const $ = s => document.querySelector(s);
async function sha256(texto) {
  if (globalThis.crypto && crypto.subtle) {
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(texto));
    return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  }
  return sha256js(texto);
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

const F = []; // {n, fecha, concepto, importe, importeOriginal, prev, hash}
const eur = x => x.toFixed(2).replace('.', ',') + ' €';
const fecha = () => new Date().toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'medium' });
const texto = f => `${f.n}|${f.fecha}|${f.importe.toFixed(2)}|${f.prev}`;

async function emitir(concepto, importe) {
  const prev = F.length ? F[F.length - 1].hash : '';
  const f = { n: F.length + 1, fecha: fecha(), concepto, importe, importeOriginal: importe, prev };
  f.hash = await sha256(texto(f)); F.push(f); pinta(); $('#msg').textContent = '';
}
$('#emitir').addEventListener('click', () => emitir($('#concepto').value, +$('#importe').value || 0));
$('#rapido').addEventListener('click', async () => { const ops = [...$('#concepto').options].map(o => o.text); for (let i = 0; i < 5; i++) await emitir(ops[Math.floor(Math.random() * ops.length)], Math.round((4 + Math.random() * 30) * 20) / 20); });
$('#borrar').addEventListener('click', () => { if (!F.length) return; F.pop(); pinta(); $('#msg').innerHTML = '<span class="ko">Factura borrada.</span> En un TPV sin Verifactu no queda rastro; con la cadena, la siguiente factura que se emita no encajaría con la numeración ni con la huella registrada en la AEAT.'; });
$('#reiniciar').addEventListener('click', () => { F.length = 0; pinta(); $('#msg').textContent = ''; });
$('#verificar').addEventListener('click', verificar);

// ---- Simulación guiada (unos 25 s) ----
const espera = ms => new Promise(r => setTimeout(r, ms));
const paso = t => { $('#paso').textContent = t; };
let simulando = false;
$('#simular').addEventListener('click', async () => {
  if (simulando) return; simulando = true; $('#simular').disabled = true;
  F.length = 0; pinta(); $('#msg').textContent = '';
  const ops = [...$('#concepto').options].map(o => o.text);
  paso('1/5 · Un servicio normal: se emiten seis facturas, cada una encadenada con la huella de la anterior.');
  for (let i = 0; i < 6; i++) { await emitir(ops[i % ops.length], Math.round((6 + Math.random() * 28) * 20) / 20); await espera(650); }
  await espera(900); paso('2/5 · Se verifica la cadena: todas las huellas cuadran.'); await verificar(); await espera(2200);
  const f = F[2]; const antes = f.importe; f.importe = Math.round(antes * 0.4 * 20) / 20;
  paso(`3/5 · Alguien rebaja la factura F-0003 de ${eur(antes)} a ${eur(f.importe)} para pagar menos IVA, como permite un TPV sin Verifactu.`);
  pinta(); $('#msg').innerHTML = 'Importe alterado en F-0003.'; await espera(3200);
  paso('4/5 · Se vuelve a verificar: la huella de F-0003 ya no coincide, y desde ahí ninguna encaja. La alteración se detecta.');
  await verificar(); await espera(3600);
  paso('5/5 · La única corrección válida: dejar F-0003 como estaba y emitir una factura rectificativa encadenada al final.');
  f.importe = antes; pinta(); await espera(900);
  await emitir('Rectificativa de F-0003', -(antes - Math.round(antes * 0.4 * 20) / 20)); await espera(700); await verificar();
  $('#msg').innerHTML += ' <b>Así queda rastro de la corrección y la cadena sigue íntegra.</b> Para Burglar King, S.L., obligatorio desde el 1 de enero de 2027.';
  simulando = false; $('#simular').disabled = false;
});

async function verificar() {
  let rota = -1, prev = '';
  for (const f of F) {
    const h = await sha256(texto({ ...f, prev }));
    f.ok = h === f.hash && f.prev === prev; if (!f.ok && rota < 0) rota = f.n; prev = f.hash;
  }
  pinta(true);
  $('#msg').innerHTML = !F.length ? 'No hay facturas.' : rota < 0 ? `<span class="ok">✔ Cadena íntegra:</span> las ${F.length} facturas encajan con sus huellas.`
    : `<span class="ko">✘ Cadena rota desde la factura ${rota}.</span> La huella guardada no coincide con los datos: alguien ha alterado una venta. Todas las posteriores dependen de ella, así que tampoco cuadran.`;
}
function pinta(verificada) {
  const c = $('#cadena'); if (!F.length) { c.innerHTML = '<p class="msg">Todavía no hay facturas.</p>'; $('#estado').textContent = ''; return; }
  c.innerHTML = F.map(f => `<div class="fact ${verificada ? (f.ok ? '' : 'rota') : ''} ${f.importe !== f.importeOriginal ? 'alterada' : ''}" data-n="${f.n}">
    <b>F-${String(f.n).padStart(4, '0')}</b><span>${f.concepto}<br><small>${f.fecha}</small></span>
    <span><input type="number" step="0.05" value="${f.importe.toFixed(2)}" title="Pulsa para alterar el importe"></span>
    <span>${f.importe !== f.importeOriginal ? '<span class="ko">alterada (era ' + eur(f.importeOriginal) + ')</span>' : verificada ? (f.ok ? '<span class="ok">huella correcta</span>' : '<span class="ko">huella no coincide</span>') : ''}</span>
    <div class="h ${verificada && !f.ok ? 'ko' : ''}">huella: <b>${f.hash.slice(0, 16)}…${f.hash.slice(-8)}</b> · anterior: ${f.prev ? f.prev.slice(0, 12) + '…' : '(ninguna)'}</div></div>`).join('');
  c.querySelectorAll('input').forEach(i => i.addEventListener('change', () => { const f = F[+i.closest('.fact').dataset.n - 1]; f.importe = +i.value || 0; pinta(); $('#msg').innerHTML = 'Importe alterado. Pulsa <b>Verificar la cadena</b>.'; }));
  $('#estado').textContent = `${F.length} factura(s) · total ${eur(F.reduce((a, f) => a + f.importe, 0))}`;
}
