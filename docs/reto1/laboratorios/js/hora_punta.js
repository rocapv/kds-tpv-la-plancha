// Lab 3: minijuego de servicio. Mismo flujo de pedidos en los dos modos (misma semilla), para que la
// comparación sea justa; solo cambia lo que tiene que hacer el jugador para que un pedido llegue a cocina.
'use strict';
const $ = s => document.querySelector(s);
const PLATOS = [['Clásica + patatas', 11.5], ['Doble queso', 13.9], ['Menú de mediodía', 12.0], ['Pollo crujiente', 12.5], ['Vegetal', 11.0], ['Bebida', 2.5]];
const DURACION = 60, COCINA_S = 6, PACIENCIA_MESA = 14, PACIENCIA_TABLETA = 9, PACIENCIA_PASE = 10;
let modo = 'papel', corre = false, t = 0, reloj, semilla, pedidos, nextId, stats, res = {};
function rnd() { semilla = (semilla * 1103515245 + 12345) & 0x7fffffff; return semilla / 0x7fffffff; }
const eur = x => x.toFixed(2).replace('.', ',') + ' €';

$('#m_papel').addEventListener('click', () => cambia('papel')); $('#m_kds').addEventListener('click', () => cambia('kds'));
function cambia(m) { if (corre) return; modo = m; $('#m_papel').classList.toggle('on', m === 'papel'); $('#m_kds').classList.toggle('on', m === 'kds'); }
$('#empezar').addEventListener('click', empezar);

function empezar() {
  if (corre) return; corre = true; t = 0; semilla = 20261015; pedidos = []; nextId = 1; stats = { llegados: 0, servidos: 0, perdidos: 0, esperas: [], ingresos: 0 };
  $('#empezar').disabled = true; $('#msg').textContent = modo === 'papel' ? 'Modo papel: apunta, lleva a cocina y copia los pedidos de la tableta. Sirve lo que salga al pase.' : 'Modo KDS: toma nota en la mesa y sirve lo que salga al pase; el reparto entra solo.';
  clearInterval(reloj); reloj = setInterval(tic, 1000); tic();
}
function nuevo() {
  const rep = rnd() < 0.35, n = 1 + Math.floor(rnd() * 3), items = []; let total = 0;
  for (let i = 0; i < n; i++) { const p = PLATOS[Math.floor(rnd() * PLATOS.length)]; items.push(p[0]); total += p[1]; }
  const p = { id: nextId++, rep, mesa: rep ? 'Reparto #' + (100 + nextId) : 'Mesa ' + (1 + Math.floor(rnd() * 13)), items, total, t0: t, fase: rep ? 'tableta' : 'mesa', tf: t };
  if (modo === 'kds' && rep) { p.fase = 'cocina'; p.tf = t; }
  pedidos.push(p); stats.llegados++;
}
function tic() {
  t++;
  if (t <= DURACION) { // llegadas: más densas en la mitad de la ronda
    const lambda = t < 10 ? 0.25 : t < 45 ? 0.5 : 0.3; if (rnd() < lambda) nuevo(); if (t > 15 && t < 40 && rnd() < 0.25) nuevo();
  }
  pedidos.forEach(p => {
    const e = t - p.tf;
    if (p.fase === 'cocina' && e >= COCINA_S) { p.fase = 'pase'; p.tf = t; }
    else if (p.fase === 'mesa' && e >= PACIENCIA_MESA) pierde(p, 'La mesa se cansó de esperar a que alguien tomara nota.');
    else if (p.fase === 'apuntado' && e >= PACIENCIA_MESA) pierde(p, 'La comanda se quedó en el bolsillo del camarero.');
    else if (p.fase === 'tableta' && e >= PACIENCIA_TABLETA) pierde(p, 'Pedido olvidado en la tableta: la plataforma lo cancela.');
    else if (p.fase === 'pase' && e >= PACIENCIA_PASE) pierde(p, 'El plato se enfrió en el pase.');
  });
  pinta();
  const vivos = pedidos.some(p => !['servido', 'perdido'].includes(p.fase));
  if (t >= DURACION + 15 || (t >= DURACION && !vivos)) termina();
}
function pierde(p, por) { p.fase = 'perdido'; p.por = por; stats.perdidos++; }
function accion(id, que) {
  const p = pedidos.find(x => x.id === id); if (!p || !corre) return;
  if (que === 'apuntar') { p.fase = modo === 'kds' ? 'cocina' : 'apuntado'; p.tf = t; }
  else if (que === 'cocina') { p.fase = 'cocina'; p.tf = t; }
  else if (que === 'copiar') { p.fase = 'cocina'; p.tf = t; }
  else if (que === 'servir') { p.fase = 'servido'; stats.servidos++; stats.esperas.push(t - p.t0); stats.ingresos += p.total; }
  pinta();
}
function tarjeta(p, boton, paciencia) {
  const e = t - p.tf, pct = paciencia ? Math.max(0, 100 - 100 * e / paciencia) : Math.min(100, 100 * e / COCINA_S);
  return `<div class="ped ${p.rep ? 'rep' : 'mesa'} ${p.fase === 'pase' ? 'listo' : ''}"><b>${p.mesa}</b> · ${eur(p.total)}<small>${p.items.join(', ')}</small>
   ${boton ? `<button onclick="accion(${p.id},'${boton[0]}')">${boton[1]}</button>` : `<small>en cocina… ${Math.max(0, COCINA_S - e)} s</small>`}
   <div class="t ${paciencia && pct < 35 ? 'ya' : ''}" style="width:${pct}%"></div></div>`;
}
function pinta() {
  $('#reloj').textContent = Math.max(0, DURACION - t) + (t > DURACION ? ' (último servicio)' : '');
  $('#serv').textContent = stats.servidos; $('#perd').textContent = stats.perdidos; $('#ing').textContent = eur(stats.ingresos);
  const sala = pedidos.filter(p => ['mesa', 'apuntado', 'tableta'].includes(p.fase)), coc = pedidos.filter(p => p.fase === 'cocina'), pase = pedidos.filter(p => p.fase === 'pase');
  $('#sala').innerHTML = sala.map(p => p.fase === 'mesa' ? tarjeta(p, ['apuntar', modo === 'kds' ? 'Tomar nota (va a cocina)' : 'Apuntar en el comandero'], PACIENCIA_MESA)
    : p.fase === 'apuntado' ? tarjeta(p, ['cocina', 'Llevar el papel a cocina'], PACIENCIA_MESA) : tarjeta(p, ['copiar', 'Copiar de la tableta a papel'], PACIENCIA_TABLETA)).join('') || '<small>Nada pendiente</small>';
  $('#cocina').innerHTML = coc.map(p => tarjeta(p, null)).join('') || '<small>Cocina libre</small>';
  $('#pase').innerHTML = pase.map(p => tarjeta(p, ['servir', p.rep ? 'Entregar al repartidor' : 'Servir a la mesa'], PACIENCIA_PASE)).join('') || '<small>Nada en el pase</small>';
  $('#c1').textContent = sala.length; $('#c2').textContent = coc.length; $('#c3').textContent = pase.length;
}
function termina() {
  clearInterval(reloj); corre = false; $('#empezar').disabled = false;
  pedidos.filter(p => !['servido', 'perdido'].includes(p.fase)).forEach(p => pierde(p, 'Se acabó el servicio.'));
  const media = stats.esperas.length ? stats.esperas.reduce((a, b) => a + b, 0) / stats.esperas.length : 0;
  res[modo] = { ...stats, media }; pinta();
  const r = $('#r_' + modo); [stats.llegados, stats.servidos, stats.perdidos, media.toFixed(1) + ' s', eur(stats.ingresos)].forEach((v, k) => r.children[k + 1].textContent = v);
  $('#msg').innerHTML = `Ronda terminada en modo <b>${modo === 'papel' ? 'papel' : 'KDS'}</b>: ${stats.servidos} servidos, ${stats.perdidos} perdidos, ${eur(stats.ingresos)}.` + (res.papel && res.kds ? '' : ` Ahora juega el otro modo con el mismo flujo de pedidos.`);
  if (res.papel && res.kds) {
    const d = res.kds.ingresos - res.papel.ingresos, p = res.papel.perdidos - res.kds.perdidos;
    ['r_papel', 'r_kds'].forEach(id => $('#' + id).classList.remove('mejor')); $(d >= 0 ? '#r_kds' : '#r_papel').classList.add('mejor');
    $('#comparativa').innerHTML = `Con el mismo flujo de pedidos, el KDS ${d >= 0 ? 'ha ingresado <b>' + eur(d) + ' más</b>' : 'ha ingresado ' + eur(-d) + ' menos'} y ha perdido <b>${p}</b> pedido(s) menos en 60 segundos. En un servicio real de tres horas y 26 días al mes, cada pedido olvidado en la tableta son unos 15 € que no entran y una reseña negativa que sí. Lo que cambia no es la cocina, que tarda lo mismo: es que la información entra en el sistema en el momento en que nace.`;
  }
}
window.accion = accion;
pinta();
