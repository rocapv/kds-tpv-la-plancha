// Lab 1: simulación de la red actual (una sola red) frente a la red segmentada en VLAN, con la misma
// batería de pings. Debajo, un modo manual para quien quiera repartir los dispositivos y probar.
'use strict';
const DISP = [ // [id, nombre, icono, VLAN correcta, por qué]
  ['tpv', 'PC del TPV (caja)', '🧾', 10, 'Cobra y guarda las ventas: va en la red del negocio.'],
  ['srv', 'Servidor del local', '🖥', 10, 'Guarda los datos y sirve el TPV y el KDS: red del negocio.'],
  ['imp', 'Impresora de tickets', '🖨', 10, 'La usa el TPV: misma red que la caja.'],
  ['dat', 'Datáfono (wifi)', '💳', 10, 'Cobra en la mesa: red del negocio, nunca la de invitados.'],
  ['tab', 'Tableta de reparto', '📱', 10, 'Recibe los pedidos de las plataformas: red del negocio.'],
  ['por', 'Portátil del encargado', '💻', 10, 'Administra todo: red del negocio (y único con acceso al grabador).'],
  ['kds1', 'Pantalla KDS plancha', '📺', 20, 'Las pantallas de cocina van en su propia VLAN y solo hablan con el servidor.'],
  ['kds2', 'Pantalla KDS pase', '📺', 20, 'Igual que la otra pantalla: VLAN de cocina.'],
  ['nvr', 'Grabador de vídeo (NVR)', '🎞', 30, 'Imágenes de personas (RGPD): red aislada y sin salida a internet.'],
  ['cam1', 'Cámara IP sala', '📷', 30, 'Las cámaras solo hablan con el grabador.'],
  ['cam2', 'Cámara IP almacén', '📷', 30, 'Las cámaras solo hablan con el grabador.'],
  ['mov', 'Móviles de los clientes', '📶', 40, 'Son desconocidos: solo internet, sin ver ningún equipo del local.'],
  ['tv', 'Smart TV de la sala', '📡', 40, 'Solo necesita internet: con los invitados, no con la caja.'],
];
// Batería de pruebas: [origen, destino, qué se demuestra, es un riesgo si pasa]
const PRUEBAS = [
  ['mov', 'tpv', 'Un móvil de cliente alcanza la caja', true],
  ['mov', 'nvr', 'Un móvil de cliente alcanza el grabador de las cámaras', true],
  ['cam1', 'internet', 'Una cámara sale a internet (P2P del fabricante)', true],
  ['tv', 'srv', 'La Smart TV alcanza el servidor', true],
  ['kds1', 'srv', 'La pantalla de cocina llega al servidor (necesario)', false],
  ['por', 'nvr', 'El encargado consulta el grabador (necesario)', false],
  ['tpv', 'imp', 'La caja imprime el ticket (necesario)', false],
  ['dat', 'internet', 'El datáfono sale a internet (necesario)', false],
];
const NOM = { 0: 'sin asignar', 1: 'red actual', 10: 'Negocio', 20: 'Cocina', 30: 'Cámaras', 40: 'Invitados' };
const $ = (s, r = document) => r.querySelector(s);
const vlans = [...document.querySelectorAll('.vlan')];
const donde = {}; let sel = null, pistas = 0, ocupado = false;
const espera = ms => new Promise(r => setTimeout(r, ms));
const nombre = id => id === 'internet' ? 'internet' : DISP.find(x => x[0] === id)[1];
const ip = (id, modo) => { if (id === 'internet') return '8.8.8.8'; const d = DISP.find(x => x[0] === id), v = modo === 'actual' ? 1 : d[3]; return `192.168.${v}.${DISP.filter(x => modo === 'actual' || x[3] === v).indexOf(d) + 10}`; };

function pinta() {
  vlans.forEach(v => v.querySelectorAll('.disp').forEach(d => d.remove()));
  DISP.forEach(([id, n, ico]) => {
    const el = document.createElement('div'); el.className = 'disp' + (sel === id ? ' sel' : ''); el.draggable = !ocupado; el.dataset.id = id;
    el.innerHTML = `<i>${ico}</i>${n}`;
    el.addEventListener('dragstart', ev => { ev.dataTransfer.setData('text', id); sel = id; });
    el.addEventListener('click', ev => { ev.stopPropagation(); if (ocupado) return; sel = sel === id ? null : id; pinta(); });
    vlans.find(v => +v.dataset.v === (donde[id] || 0)).append(el);
  });
  $('#n0').textContent = DISP.filter(d => !donde[d[0]]).length ? DISP.filter(d => !donde[d[0]]).length + ' equipos' : '';
}
vlans.forEach(v => {
  v.addEventListener('dragover', ev => { ev.preventDefault(); v.classList.add('sobre'); });
  v.addEventListener('dragleave', () => v.classList.remove('sobre'));
  v.addEventListener('drop', ev => { ev.preventDefault(); v.classList.remove('sobre'); if (!ocupado) mueve(ev.dataTransfer.getData('text') || sel, +v.dataset.v); });
  v.addEventListener('click', () => { if (sel && !ocupado) mueve(sel, +v.dataset.v); });
});
function mueve(id, vlan) { if (!id) return; donde[id] = vlan; sel = null; pinta(); }
function escribe(t, c) { const s = document.createElement('span'); if (c) s.className = c; s.textContent = t; $('#term').append(s); $('#term').scrollTop = 1e6; }

// Reglas del cortafuegos de la red propuesta (con cada dispositivo en su VLAN correcta)
function permitido(o, d) {
  const vo = DISP.find(x => x[0] === o)[3], vd = d === 'internet' ? 'inet' : DISP.find(x => x[0] === d)[3];
  if (vd === 'inet') return vo === 30 ? [false, 'las cámaras no salen a internet'] : [true, 'salida a internet permitida'];
  if (vo === vd) return [true, 'misma VLAN'];
  if (vo === 20 && d === 'srv') return [true, 'regla: cocina → servidor (HTTPS)'];
  if (o === 'por' && d === 'nvr') return [true, 'regla: portátil del encargado → grabador'];
  if (vo === 40) return [false, 'los invitados solo salen a internet'];
  if (vd === 40) return [false, 'nadie entra en la red de invitados'];
  if (vo === 30 || vd === 30) return [false, 'la VLAN de cámaras está aislada'];
  return [false, `no hay regla que permita ${NOM[vo]} → ${NOM[vd]}`];
}
async function ping(o, d, modo, rapido) {
  const [ok, motivo] = modo === 'actual' ? [true, 'una sola red: todo llega a todo'] : permitido(o, d);
  escribe(`$ ping ${ip(d, modo)}   # ${nombre(o)} → ${nombre(d)}\n`);
  for (let n = 1; n <= (rapido ? 2 : 3); n++) {
    await espera(rapido ? 120 : 300);
    escribe(ok ? `64 bytes from ${ip(d, modo)}: icmp_seq=${n} ttl=64 time=${(0.4 + Math.random() * 1.2).toFixed(1)} ms\n` : `Request timeout for icmp_seq ${n}\n`, ok ? 'g' : 'r');
  }
  escribe(ok ? `--- responde (${motivo}) ---\n\n` : `--- bloqueado por el cortafuegos: ${motivo} ---\n\n`, ok ? 'g' : 'r');
  return ok;
}

// ---- Simulación ----
const resultados = { actual: {}, prop: {} };
function tabla() {
  $('#res').innerHTML = '<tr><th>Prueba</th><th>Red actual</th><th>Red segmentada</th></tr>' + PRUEBAS.map(([o, d, t, riesgo], k) => {
    const c = m => { const r = resultados[m][k]; if (r === undefined) return '<td>—</td>'; const bien = riesgo ? !r : r; return `<td class="${bien ? 'ok' : 'ko'}">${r ? 'responde' : 'bloqueado'} ${bien ? '✔' : '✘'}</td>`; };
    return `<tr><td>${t}</td>${c('actual')}${c('prop')}</tr>`; }).join('');
  const na = Object.keys(resultados.actual).length, np = Object.keys(resultados.prop).length;
  const malas = m => PRUEBAS.filter(([o, d, t, r], k) => resultados[m][k] !== undefined && (r ? resultados[m][k] : !resultados[m][k])).length;
  $('#msg').innerHTML = (na ? `Red actual: <b class="ko">${malas('actual')} de ${na}</b> pruebas con resultado peligroso. ` : '') + (np ? `Red segmentada: <b class="${malas('prop') ? 'ko' : 'ok'}">${malas('prop')} de ${np}</b>.` : '');
}
async function simular(modo) {
  if (ocupado) return; ocupado = true; sel = null;
  document.querySelectorAll('#sim_actual,#sim_prop,#sim_ambas').forEach(b => b.disabled = true);
  resultados[modo] = {}; $('#term').textContent = ''; $('#puntos').textContent = '';
  escribe(modo === 'actual' ? '== RED ACTUAL: un solo router, 192.168.1.0/24, un solo SSID ==\n\n' : '== RED SEGMENTADA: VLAN 10/20/30/40 y cortafuegos entre ellas ==\n\n', 'y');
  $('#t0').textContent = modo === 'actual' ? 'Red actual · 192.168.1.0/24 (todo junto)' : 'Sin asignar';
  Object.keys(donde).forEach(k => delete donde[k]); pinta();
  if (modo === 'prop') for (const d of DISP) { await espera(160); donde[d[0]] = d[3]; pinta(); }
  await espera(400);
  for (let k = 0; k < PRUEBAS.length; k++) { const [o, d] = PRUEBAS[k]; resultados[modo][k] = await ping(o, d, modo, true); tabla(); }
  escribe(modo === 'actual' ? 'Conclusión: cualquier cliente del wifi ve la caja y las cámaras. Riesgos R1 y R2 del informe.\n' : 'Conclusión: lo necesario funciona y lo peligroso está bloqueado. Coste: un conmutador gestionable y un punto de acceso con varios SSID.\n', 'y');
  ocupado = false; document.querySelectorAll('#sim_actual,#sim_prop,#sim_ambas').forEach(b => b.disabled = false); pinta();
}
$('#sim_actual').addEventListener('click', () => simular('actual'));
$('#sim_prop').addEventListener('click', () => simular('prop'));
$('#sim_ambas').addEventListener('click', async () => { await simular('actual'); await espera(900); await simular('prop'); });
$('#reiniciar').addEventListener('click', () => { if (ocupado) return; Object.keys(donde).forEach(k => delete donde[k]); resultados.actual = {}; resultados.prop = {}; $('#t0').textContent = 'Sin asignar'; $('#term').textContent = 'Pulsa «Simular».'; $('#puntos').textContent = ''; $('#msg2').textContent = ''; tabla(); $('#msg').textContent = ''; pinta(); });

// ---- Modo manual ----
$('#comprobar').addEventListener('click', () => {
  let ok = 0; const fallos = [];
  document.querySelectorAll('.disp').forEach(el => { const d = DISP.find(x => x[0] === el.dataset.id); const bien = (donde[d[0]] || 0) === d[3]; el.classList.toggle('bien', bien); el.classList.toggle('mal', !bien); if (bien) ok++; else fallos.push(d); });
  $('#puntos').textContent = `${ok} / ${DISP.length}`;
  $('#msg2').innerHTML = ok === DISP.length ? '<span class="ok">✔ Red segmentada correctamente.</span>' : `<span class="ko">✘ ${fallos.length} mal colocado(s).</span> ` + fallos.slice(0, 3).map(d => `<b>${d[1]}</b>: ${d[4]}`).join(' · ');
});
$('#pista').addEventListener('click', () => { const d = DISP.find(x => (donde[x[0]] || 0) !== x[3]); pistas++; $('#msg2').innerHTML = d ? `Pista ${pistas}: <b>${d[1]}</b> → ${d[4]}` : 'No hay nada que corregir.'; });
['#origen', '#destino'].forEach(s => DISP.forEach(d => { const o = document.createElement('option'); o.value = d[0]; o.textContent = d[1]; $(s).append(o); }));
$('#destino').value = 'srv';
$('#ping').addEventListener('click', async () => {
  if (ocupado) return; const o = $('#origen').value, d = $('#destino').value; if (o === d) return;
  const todoBien = DISP.every(x => (donde[x[0]] || 0) === x[3]);
  if (!todoBien) { escribe('El modo manual usa el cortafuegos del proyecto: coloca antes todos los dispositivos en su VLAN y pulsa «Comprobar».\n', 'y'); return; }
  ocupado = true; await ping(o, d, 'prop', false); ocupado = false;
});
document.body.addEventListener('click', ev => { if (!ev.target.closest('.disp,.vlan,button,select')) { sel = null; pinta(); } });
pinta(); tabla();
