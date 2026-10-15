// Lab 1: repartir los dispositivos de Burglar King en VLAN y probar el cortafuegos con pings simulados.
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
const NOM = { 0: 'sin asignar', 10: 'Negocio', 20: 'Cocina', 30: 'Cámaras', 40: 'Invitados' };
const $ = (s, r = document) => r.querySelector(s);
const vlans = [...document.querySelectorAll('.vlan')];
const donde = {}; // id -> vlan actual
let sel = null, listo = false, pistas = 0;

function pinta() {
  vlans.forEach(v => { v.querySelectorAll('.disp').forEach(d => d.remove()); });
  DISP.forEach(([id, nombre, ico]) => {
    const el = document.createElement('div'); el.className = 'disp' + (sel === id ? ' sel' : ''); el.draggable = true; el.dataset.id = id;
    el.innerHTML = `<i>${ico}</i>${nombre}`;
    el.addEventListener('dragstart', ev => { ev.dataTransfer.setData('text', id); sel = id; });
    el.addEventListener('click', ev => { ev.stopPropagation(); sel = sel === id ? null : id; pinta(); });
    vlans.find(v => +v.dataset.v === (donde[id] || 0)).append(el);
  });
  $('#n0').textContent = DISP.filter(d => !donde[d[0]]).length + ' pendientes';
}
vlans.forEach(v => {
  v.addEventListener('dragover', ev => { ev.preventDefault(); v.classList.add('sobre'); });
  v.addEventListener('dragleave', () => v.classList.remove('sobre'));
  v.addEventListener('drop', ev => { ev.preventDefault(); v.classList.remove('sobre'); mueve(ev.dataTransfer.getData('text') || sel, +v.dataset.v); });
  v.addEventListener('click', () => { if (sel) mueve(sel, +v.dataset.v); });
});
function mueve(id, vlan) { if (!id) return; donde[id] = vlan; sel = null; listo = false; $('#puntos').textContent = ''; $('#msg').textContent = ''; pinta(); }

$('#comprobar').addEventListener('click', () => {
  let ok = 0; const fallos = [];
  document.querySelectorAll('.disp').forEach(el => {
    const d = DISP.find(x => x[0] === el.dataset.id); const bien = (donde[d[0]] || 0) === d[3];
    el.classList.toggle('bien', bien); el.classList.toggle('mal', !bien); if (bien) ok++; else fallos.push(d);
  });
  $('#puntos').textContent = `${ok} / ${DISP.length}`;
  if (ok === DISP.length) { listo = true; $('#msg').innerHTML = '<span class="ok">✔ Red segmentada.</span> El cortafuegos ya está configurado: prueba los pings.'; escribe('Cortafuegos configurado con las VLAN 10, 20, 30 y 40.\n', 'g'); }
  else $('#msg').innerHTML = `<span class="ko">✘ ${fallos.length} dispositivo(s) mal colocado(s).</span> ` + fallos.slice(0, 3).map(d => `<b>${d[1]}</b>: ${d[4]}`).join(' · ');
});
$('#pista').addEventListener('click', () => {
  const d = DISP.find(x => (donde[x[0]] || 0) !== x[3]); pistas++;
  $('#msg').innerHTML = d ? `Pista ${pistas}: <b>${d[1]}</b> → ${d[4]}` : 'No hay nada que corregir.';
});
$('#reiniciar').addEventListener('click', () => { Object.keys(donde).forEach(k => delete donde[k]); listo = false; $('#puntos').textContent = ''; $('#msg').textContent = ''; pinta(); $('#term').textContent = ''; });

// ---- Pings ----
const ip = id => { const d = DISP.find(x => x[0] === id), v = d[3], n = DISP.filter(x => x[3] === v).indexOf(d) + 10; return `192.168.${v}.${n}`; };
['#origen', '#destino'].forEach(s => DISP.forEach(d => { const o = document.createElement('option'); o.value = d[0]; o.textContent = d[1]; $(s).append(o); }));
$('#destino').value = 'srv';
function permitido(o, d) { // devuelve [ok, motivo] según las reglas del proyecto, con las VLAN correctas
  const vo = DISP.find(x => x[0] === o)[3], vd = DISP.find(x => x[0] === d)[3];
  if (vo === vd) return [true, 'misma VLAN'];
  if (vo === 20 && d === 'srv') return [true, 'regla: cocina → servidor (HTTPS)'];
  if (o === 'por' && d === 'nvr') return [true, 'regla: portátil del encargado → grabador'];
  if (vo === 40) return [false, 'los invitados solo salen a internet'];
  if (vd === 40) return [false, 'nadie entra en la red de invitados'];
  if (vo === 30 || vd === 30) return [false, 'la VLAN de cámaras está aislada'];
  return [false, `no hay regla que permita ${NOM[vo]} → ${NOM[vd]}`];
}
function escribe(t, c) { const s = document.createElement('span'); if (c) s.className = c; s.textContent = t; $('#term').append(s); $('#term').scrollTop = 1e6; }
$('#ping').addEventListener('click', () => {
  const o = $('#origen').value, d = $('#destino').value;
  if (!listo) { escribe('Primero reparte los dispositivos y pulsa «Comprobar».\n', 'y'); return; }
  if (o === d) { escribe('Elige dos dispositivos distintos.\n', 'y'); return; }
  const [ok, motivo] = permitido(o, d);
  escribe(`$ ping ${ip(d)}   # desde ${DISP.find(x => x[0] === o)[1]} (${ip(o)})\n`);
  let n = 0; const t = setInterval(() => {
    n++;
    if (ok) escribe(`64 bytes from ${ip(d)}: icmp_seq=${n} ttl=64 time=${(0.4 + Math.random() * 1.2).toFixed(1)} ms\n`, 'g');
    else escribe(`Request timeout for icmp_seq ${n}\n`, 'r');
    if (n === 3) { clearInterval(t); escribe(ok ? `--- ${motivo}: permitido ---\n\n` : `--- bloqueado por el cortafuegos: ${motivo} ---\n\n`, ok ? 'g' : 'r'); }
  }, 350);
});
$('#limpiar').addEventListener('click', () => $('#term').textContent = '');
document.body.addEventListener('click', ev => { if (!ev.target.closest('.disp,.vlan')) { sel = null; pinta(); } });
pinta();
