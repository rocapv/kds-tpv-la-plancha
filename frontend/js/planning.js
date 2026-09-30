// Planning de mesas: una fila por mesa y el día en horizontal, con una barra por reserva.
// Ver docs/PROPUESTA_PLANNING_MESAS.md. Es una VISTA: los estados, los solapes y los cambios de
// mesa los sigue decidiendo el servidor. Lo que se comprueba aquí (si cabe al arrastrar) es solo
// para enseñarlo antes de soltar, con la misma regla que aplica reservas.py.
let MESAS = [];

const VIVAS = ['pendiente', 'confirmada', 'sentada'];
const MOVIBLES = ['pendiente', 'confirmada', 'sentada'];     // lo que el PATCH de mesa admite

// «13:00-16:00,20:00-23:30» → [[780, 960], [1200, 1410]] en minutos desde medianoche.
function tramos(texto) {
  const min = h => { const [a, b] = h.trim().split(':').map(Number); return a * 60 + (b || 0); };
  return String(texto || '').split(',').map(p => p.split('-')).filter(p => p.length === 2)
    .map(([a, b]) => [min(a), min(b)]).filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b) && a < b);
}

const inicioDelDia = () => new Date(dia + 'T00:00:00');
const minutoDe = f => (new Date(f) - inicioDelDia()) / 60000;
const hhmm = m => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(Math.round(m % 60)).padStart(2, '0')}`;

// Dos reservas de la misma mesa chocan si sus horas están a menos de la duración: la misma
// cuenta que `reservas.mesa_ocupada`.
function cabe(r, mesa) {
  if (!mesa || mesa.plazas < r.comensales) return false;
  const dur = DATOS.config.duracion_min, t = minutoDe(r.hora);
  return !DATOS.reservas.some(o => o.id !== r.id && o.mesa_id === mesa.id && VIVAS.includes(o.estado)
                                   && Math.abs(minutoDe(o.hora) - t) < dur);
}

function rango(cfg, reservas) {
  const t = tramos(cfg.horario);
  let desde = t.length ? Math.min(...t.map(x => x[0])) : 12 * 60;
  let hasta = t.length ? Math.max(...t.map(x => x[1])) : 24 * 60;
  for (const r of reservas) {
    const m = minutoDe(r.hora);
    desde = Math.min(desde, m);
    hasta = Math.max(hasta, m + cfg.duracion_min);
  }
  hasta = Math.max(hasta, Math.max(...t.map(x => x[1]), 0) + cfg.duracion_min);
  return { desde: Math.floor(desde / 60) * 60, hasta: Math.ceil(hasta / 60) * 60, tramos: t };
}

async function pintarPlanning() {
  if (!DATOS) return;
  MESAS = await api('/mesas');
  const cfg = DATOS.config, dur = cfg.duracion_min;
  const verAnuladas = $('#ver-anuladas').checked;
  const visibles = DATOS.reservas.filter(r => r.estado !== 'anulada' || verAnuladas);
  const R = rango(cfg, visibles);
  const total = R.hasta - R.desde;
  const pct = m => ((m - R.desde) / total * 100).toFixed(3) + '%';
  const horas = [];
  for (let h = R.desde; h < R.hasta; h += 60) horas.push(h);

  // Sombreado de lo que queda fuera del horario de reservas.
  const fuera = [];
  let cursor = R.desde;
  for (const [a, b] of [...R.tramos].sort((x, y) => x[0] - y[0])) {
    if (a > cursor) fuera.push([cursor, a]);
    cursor = Math.max(cursor, b);
  }
  if (cursor < R.hasta) fuera.push([cursor, R.hasta]);
  const sombras = fuera.map(([a, b]) => `<i class="fuera-horario" style="left:${pct(a)};width:${pct(R.desde + b - a)}"></i>`).join('');

  const hoy = dia === hoyLocal();
  const ahora = minutoDe(new Date());
  const lineaAhora = hoy && ahora >= R.desde && ahora <= R.hasta
    ? `<i class="ahora" style="left:${pct(ahora)}" title="Ahora, ${hhmm(ahora)}"></i>` : '';

  const barra = r => {
    const t = minutoDe(r.hora);
    const [texto] = ESTADOS[r.estado] || [r.estado];
    const etiqueta = `${HORA(r.hora)} · ${r.nombre} · ${r.comensales}`;
    return `<button class="barra-res ${r.estado}${r.lineas.length ? ' adelantado' : ''}"
        data-id="${r.id}" style="left:${pct(t)};width:${pct(R.desde + dur)}"
        title="${esc(etiqueta)} · ${esc(texto)}${r.lineas.length ? ' · con pedido adelantado' : ''}"
        aria-label="${esc(etiqueta)} personas, ${esc(texto)}, mesa ${esc(r.mesa || 'sin mesa')}">
        <span>${esc(etiqueta)}</span></button>`;
  };

  const porMesa = {};
  for (const r of visibles) (porMesa[r.mesa_id] ||= []).push(r);
  const fila = (m, zona) => `
    <div class="pl-mesa" role="rowheader">
      <b>${esc(m.nombre)}</b>
      <span class="tenue">${m.plazas} pax${m.pedido_id ? ` · <span class="ocupada">${m.sentados || '?'} sentados</span>` : ''}</span>
    </div>
    <div class="pl-pista" data-mesa="${m.id}" data-zona="${esc(zona)}">${sombras}${lineaAhora}
      ${(porMesa[m.id] || []).map(barra).join('')}</div>`;

  const zonas = [...new Set(MESAS.map(m => m.zona))];
  const regla = `<div class="pl-esquina">Mesa</div>
    <div class="pl-regla">${horas.map(h => `<span style="left:${pct(h)}">${hhmm(h)}</span>`).join('')}${lineaAhora}</div>`;
  const cuerpo = zonas.map(z => `<div class="pl-zona">${esc(zonaNombre(z))}</div>` +
    MESAS.filter(m => m.zona === z).map(m => fila(m, z)).join('')).join('');
  const sinMesa = visibles.filter(r => !MESAS.some(m => m.id === r.mesa_id));
  const extra = sinMesa.length
    ? `<div class="pl-zona">Sin mesa</div><div class="pl-mesa"><b>—</b></div>
       <div class="pl-pista">${sombras}${sinMesa.map(barra).join('')}</div>` : '';

  $('#planning').innerHTML = `<div class="planning" style="--hora:${(60 / total * 100).toFixed(4)}%">${regla}${cuerpo}${extra}</div>`;
  enlazarPlanning(R, total);
}

// ── Interacción: tocar, arrastrar, flechas y huecos ──
function reservaDe(id) { return DATOS.reservas.find(r => r.id === Number(id)); }
function mesaDe(id) { return MESAS.find(m => m.id === Number(id)); }

function abrirDetalle(r) {
  $('#d-reserva-cuerpo').innerHTML = tarjeta(r);
  enlazarAcciones($('#d-reserva-cuerpo'), () => $('#d-reserva').close());
  $('#d-reserva').showModal();
}
$('#d-reserva-cerrar').onclick = () => $('#d-reserva').close();
$('#d-reserva').addEventListener('click', e => { if (e.target === $('#d-reserva')) $('#d-reserva').close(); });

async function moverA(r, mesa, enfocar = false) {
  try {
    await api(`/reservas/${r.id}/mesa`, { method: 'PATCH', body: { mesa_id: mesa.id } });
    aviso(`${r.nombre}: a la ${mesa.nombre}`, 'ok');
  } catch (e) { aviso(e.message, 'error'); }
  await cargar();
  if (enfocar) document.querySelector(`#planning .barra-res[data-id="${r.id}"]`)?.focus();
}

function enlazarPlanning(R, total) {
  const pistas = [...document.querySelectorAll('#planning .pl-pista[data-mesa]')];

  document.querySelectorAll('#planning .barra-res').forEach(b => {
    const r = reservaDe(b.dataset.id);
    const movible = MOVIBLES.includes(r.estado);
    let inicio = null, arrastrando = false, destino = null;

    const limpiar = () => pistas.forEach(p => p.classList.remove('destino-ok', 'destino-no'));

    b.onpointerdown = e => {
      if (!movible || e.button > 0) return;
      inicio = { y: e.clientY, x: e.clientX };
      b.setPointerCapture(e.pointerId);
    };
    b.onpointermove = e => {
      if (!inicio) return;
      const dy = e.clientY - inicio.y;
      if (!arrastrando && Math.abs(dy) < 8) return;
      arrastrando = true;
      b.classList.add('arrastrando');
      b.style.transform = `translateY(${dy}px)`;
      b.style.pointerEvents = 'none';                 // para ver qué fila hay debajo
      const debajo = document.elementFromPoint(e.clientX, e.clientY)?.closest('.pl-pista[data-mesa]');
      b.style.pointerEvents = '';
      limpiar();
      destino = debajo && Number(debajo.dataset.mesa) !== r.mesa_id ? debajo : null;
      if (destino) destino.classList.add(cabe(r, mesaDe(destino.dataset.mesa)) ? 'destino-ok' : 'destino-no');
    };
    b.onpointerup = b.onpointercancel = e => {
      const eraArrastre = arrastrando;
      inicio = null; arrastrando = false;
      b.classList.remove('arrastrando'); b.style.transform = '';
      limpiar();
      if (eraArrastre) {
        b.dataset.recienArrastrada = '1';             // que el click que sigue no abra el detalle
        setTimeout(() => delete b.dataset.recienArrastrada, 0);
        if (destino && e.type === 'pointerup') {
          const mesa = mesaDe(destino.dataset.mesa);
          if (cabe(r, mesa)) moverA(r, mesa);
          else aviso(mesa.plazas < r.comensales ? `En la ${mesa.nombre} caben ${mesa.plazas}` :
                     `La ${mesa.nombre} ya tiene reserva a esa hora`, 'error');
        }
        destino = null;
      }
    };
    b.onclick = e => { e.stopPropagation(); if (!b.dataset.recienArrastrada) abrirDetalle(r); };

    // Con teclado: ↑/↓ la lleva a la mesa anterior/siguiente donde quepa.
    b.onkeydown = e => {
      if (!['ArrowUp', 'ArrowDown'].includes(e.key) || !movible) return;
      e.preventDefault();
      const orden = pistas.map(p => mesaDe(p.dataset.mesa));
      let i = orden.findIndex(m => m.id === r.mesa_id);
      const paso = e.key === 'ArrowUp' ? -1 : 1;
      for (i += paso; i >= 0 && i < orden.length; i += paso) {
        if (cabe(r, orden[i])) return moverA(r, orden[i], true);
      }
      aviso(`No queda mesa ${paso < 0 ? 'arriba' : 'abajo'} donde quepan ${r.comensales}`, 'error');
    };
  });

  // Un hueco vacío: reserva nueva en esa mesa, a esa hora (redondeada al paso de reservas).
  pistas.forEach(p => p.onclick = e => {
    if (e.target.closest('.barra-res')) return;
    const caja = p.getBoundingClientRect();
    const paso = DATOS.config.paso_min || 30;
    const min = Math.floor((R.desde + (e.clientX - caja.left) / caja.width * total) / paso) * paso;
    if (!tramos(DATOS.config.horario).some(([a, b]) => min >= a && min <= b)) {
      return aviso(`A las ${hhmm(min)} no se reserva (horario ${DATOS.config.horario})`, 'error');
    }
    const hora = inicioDelDia(); hora.setMinutes(min);
    abrirNueva({ hora, mesa: mesaDe(p.dataset.mesa) });
  });
}

$('#ver-anuladas').onchange = () => pintarPlanning();
// La línea de «ahora» se mueve sola: se repinta cada minuto mientras el planning está a la vista.
setInterval(() => { if (vista === 'planning' && !document.querySelector('.barra-res.arrastrando')) pintarPlanning(); }, 60000);
