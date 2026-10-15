// Lab 3: simulación automática de un servicio, en paralelo con papel y con KDS, con el mismo flujo de
// pedidos (misma semilla). Nadie juega: un camarero simulado hace lo que haría en cada modo.
'use strict';
const $ = s => document.querySelector(s);
const PLATOS = [['Clásica + patatas', 11.5], ['Doble queso', 13.9], ['Menú de mediodía', 12.0], ['Pollo crujiente', 12.5], ['Vegetal', 11.0], ['Bebida', 2.5]];
const COCINA = [240, 420], PACIENCIA_MESA = 900, PACIENCIA_TABLETA = 240, PACIENCIA_PASE = 300; // segundos simulados
let timer = null, t = 0, dur = 180, vel = 8, semillaBase = 20261015;
const eur = x => x.toFixed(2).replace('.', ',') + ' €';
const mmss = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
function Rnd(seed) { let s = seed; return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; }; }

// Flujo de pedidos común: se genera antes de empezar con la semilla, igual para los dos lados.
function generaFlujo(seg) {
  const r = Rnd(semillaBase), lista = []; let id = 1;
  for (let s = 0; s < seg; s++) {
    const lambda = s < seg * 0.15 ? 0.08 : s < seg * 0.75 ? 0.17 : 0.08; // llegadas por segundo (pico en el centro)
    if (r() < lambda) {
      const rep = r() < 0.35, n = 1 + Math.floor(r() * 3), items = []; let total = 0;
      for (let i = 0; i < n; i++) { const p = PLATOS[Math.floor(r() * PLATOS.length)]; items.push(p[0]); total += p[1]; }
      lista.push({ id: id++, t0: s, rep, mesa: rep ? 'Reparto #' + (100 + id) : 'Mesa ' + (1 + Math.floor(r() * 13)), items, total, cocina: COCINA[0] + r() * (COCINA[1] - COCINA[0]) });
    }
  }
  return lista;
}
// Un lado de la simulación: modo 'papel' o 'kds'. Cada pedido pasa por fases con tiempos del camarero simulado.
const cargaDe = L => L.vivos.filter(p => ['mesa', 'apuntado', 'tableta'].includes(p.fase)).length;
function Lado(modo, flujo) {
  const r = Rnd(semillaBase + (modo === 'papel' ? 7 : 11));
  const L = { modo, pendientes: flujo.map(p => ({ ...p })), vivos: [], stats: { llegados: 0, servidos: 0, perdidos: 0, esperas: [], ingresos: 0, repLleg: 0, repPerd: 0 } };
  L.tic = () => {
    while (L.pendientes.length && L.pendientes[0].t0 <= t) { const p = L.pendientes.shift(); L.stats.llegados++; if (p.rep) L.stats.repLleg++;
      if (p.rep) { if (modo === 'kds') { p.fase = 'cocina'; p.tf = t; } else { p.fase = 'tableta'; p.tf = t; p.plazo = t + 40 + r() * 40 + 8 * cargaDe(L); } }
      else { p.fase = 'mesa'; p.tf = t; p.plazo = t + 20 + r() * 20 + (modo === 'papel' ? 6 * cargaDe(L) : 0); }
      L.vivos.push(p); }
    const carga = L.vivos.filter(p => ['mesa', 'apuntado', 'tableta'].includes(p.fase)).length;
    L.vivos.forEach(p => {
      const e = t - p.tf;
      if (p.fase === 'mesa' && t >= p.plazo) { // el camarero toma nota
        if (modo === 'kds') { p.fase = 'cocina'; p.tf = t; }
        else { p.fase = 'apuntado'; p.tf = t; p.plazo = t + 15 + r() * 20 + 8 * carga; if (r() < 0.15) p.plazo += 60; } // ilegible: se rehace
      } else if (p.fase === 'apuntado' && t >= p.plazo) { p.fase = 'cocina'; p.tf = t; }
      else if (p.fase === 'tableta' && t >= p.plazo) { // se acuerda de la tableta… o no
        if (carga >= 2 && r() < 0.3) { p.plazo = t + 30 + r() * 60; } else { p.fase = 'cocina'; p.tf = t; } // o se olvida un rato de la tableta
      }
      else if (p.fase === 'cocina' && e >= p.cocina) { p.fase = 'pase'; p.tf = t; p.plazo = t + 10 + r() * 30 + (modo === 'papel' ? 20 : 0); }
      else if (p.fase === 'pase' && t >= p.plazo) { p.fase = 'servido'; L.stats.servidos++; L.stats.esperas.push(t - p.t0); L.stats.ingresos += p.total; }
      if (p.fase === 'mesa' && t - p.t0 >= PACIENCIA_MESA) pierde(L, p, 'la mesa se fue');
      if (p.fase === 'apuntado' && t - p.t0 >= PACIENCIA_MESA) pierde(L, p, 'comanda perdida en el bolsillo');
      if (p.fase === 'tableta' && t - p.t0 >= PACIENCIA_TABLETA) pierde(L, p, 'caducó en la tableta');
      if (p.fase === 'pase' && t - p.tf >= PACIENCIA_PASE) pierde(L, p, 'se enfrió en el pase');
    });
    L.vivos = L.vivos.filter(p => !['servido', 'perdido'].includes(p.fase) || t - p.tfin < 6);
  };
  return L;
}
function pierde(L, p, por) { p.fase = 'perdido'; p.por = por; p.tfin = t; L.stats.perdidos++; if (p.rep) L.stats.repPerd++; }

let P, K, flujo;
function tarjeta(p, modo) {
  const txt = { mesa: 'esperando al camarero', apuntado: 'comanda en papel, camino de cocina', tableta: 'en la tableta, sin copiar', cocina: 'en cocina', pase: 'en el pase', servido: 'servido', perdido: p.por }[p.fase];
  return `<div class="ped ${p.rep ? 'rep' : 'mesa'} ${p.fase === 'pase' ? 'listo' : ''} ${p.fase === 'perdido' ? 'mal' : ''}" style="${p.fase === 'perdido' ? 'border-color:var(--rojo);background:#fdecea' : ''}"><b>${p.mesa}</b> · ${eur(p.total)}<small>${p.items.join(', ')} · ${txt}</small></div>`;
}
function pintaLado(L, pre) {
  const v = L.vivos; const g = f => v.filter(p => f.includes(p.fase));
  $(`#${pre}_sala`).innerHTML = g(['mesa', 'apuntado', 'tableta', 'perdido']).slice(-5).map(p => tarjeta(p)).join('') || '<small>—</small>';
  $(`#${pre}_cocina`).innerHTML = g(['cocina']).slice(-5).map(p => tarjeta(p)).join('') || '<small>—</small>';
  $(`#${pre}_pase`).innerHTML = g(['pase', 'servido']).slice(-5).map(p => tarjeta(p)).join('') || '<small>—</small>';
  $(`#${pre}_c1`).textContent = g(['mesa', 'apuntado', 'tableta']).length; $(`#${pre}_c2`).textContent = g(['cocina']).length; $(`#${pre}_c3`).textContent = g(['pase']).length;
  $(`#${pre}_serv`).textContent = L.stats.servidos; $(`#${pre}_perd`).textContent = L.stats.perdidos; $(`#${pre}_ing`).textContent = eur(L.stats.ingresos);
}
function paso() {
  for (let k = 0; k < vel; k++) { t++; P.tic(); K.tic(); if (t >= dur + 900) break; }
  $('#reloj').textContent = mmss(Math.min(t, dur)) + (t > dur ? ' · último servicio' : '');
  pintaLado(P, 'p'); pintaLado(K, 'k');
  const vivos = P.vivos.some(p => !['servido', 'perdido'].includes(p.fase)) || K.vivos.some(p => !['servido', 'perdido'].includes(p.fase));
  if (t >= dur + 900 || (t >= dur && !vivos)) termina();
}
$('#empezar').addEventListener('click', () => {
  if (timer) return; dur = +$('#dur').value; vel = +$('#vel').value; t = 0; flujo = generaFlujo(dur); P = Lado('papel', flujo); K = Lado('kds', flujo);
  $('#empezar').disabled = true; $('#msg').textContent = 'Simulando… mismo flujo de pedidos a los dos lados.'; $('#comparativa').textContent = '';
  ['r_papel', 'r_kds'].forEach(id => { $('#' + id).classList.remove('mejor'); [...$('#' + id).children].slice(1).forEach(c => c.textContent = '—'); });
  timer = setInterval(paso, 1000 / 8);
});
function termina() {
  clearInterval(timer); timer = null; $('#empezar').disabled = false;
  [P, K].forEach(L => L.vivos.filter(p => !['servido', 'perdido'].includes(p.fase)).forEach(p => pierde(L, p, 'se acabó el servicio')));
  const fila = (L, id) => { const m = L.stats.esperas.length ? L.stats.esperas.reduce((a, b) => a + b, 0) / L.stats.esperas.length : 0; L.media = m;
    [L.stats.llegados, L.stats.servidos, L.stats.perdidos, mmss(m) + ' min', eur(L.stats.ingresos)].forEach((v, k) => $('#' + id).children[k + 1].textContent = v); };
  fila(P, 'r_papel'); fila(K, 'r_kds'); pintaLado(P, 'p'); pintaLado(K, 'k');
  const d = K.stats.ingresos - P.stats.ingresos, pp = P.stats.perdidos - K.stats.perdidos, fr = P.stats.repLleg ? P.stats.repPerd / P.stats.repLleg : 0; // fracción de pedidos de reparto perdidos con papel
  $(d >= 0 ? '#r_kds' : '#r_papel').classList.add('mejor');
  $('#msg').textContent = 'Servicio terminado.';
  $('#comparativa').innerHTML = `Con el mismo flujo de pedidos, el KDS ha servido <b>${K.stats.servidos}</b> frente a <b>${P.stats.servidos}</b>, ha perdido <b>${pp}</b> pedido(s) menos y la espera media baja de <b>${mmss(P.media)}</b> a <b>${mmss(K.media)}</b> min. Diferencia de ingresos en el pico simulado: <b>${eur(d)}</b>. Con papel se ha perdido <b>${P.stats.repPerd} de ${P.stats.repLleg}</b> pedidos de reparto (${Math.round(fr * 100)} %); el informe estima 8.250 € al mes de reparto, así que esa proporción serían unos <b>${eur(8250 * fr)}</b> al mes que no entran, más las reseñas negativas que sí. La cocina tarda lo mismo: lo que cambia es que la información entra en el sistema en el momento en que nace.`;
}
pintaLado({ vivos: [], stats: { servidos: 0, perdidos: 0, ingresos: 0 } }, 'p'); pintaLado({ vivos: [], stats: { servidos: 0, perdidos: 0, ingresos: 0 } }, 'k');
