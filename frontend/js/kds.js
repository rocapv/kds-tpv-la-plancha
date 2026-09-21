// KDS: pantalla de cocina por estación. Clic en línea = avanzar esa línea; botón = avanzar comanda.
const estacion = new URLSearchParams(location.search).get('estacion') || '';
const NOMBRES = { plancha: 'Plancha', freidora: 'Freidora', frios: 'Fríos', barra: 'Barra', '': 'Pase (todas)' };
const AVISO_MIN = 8, CRITICO_MIN = 15;
let vistos = new Set(), primeraCarga = true, sonido = false, desfase = 0;

$('#titulo').textContent = 'KDS · ' + NOMBRES[estacion];
document.title = 'KDS ' + NOMBRES[estacion];
$('#estaciones').innerHTML = Object.entries(NOMBRES).map(([k, v]) =>
  `<a href="?estacion=${k}"><button class="${k === estacion ? 'activa' : ''}">${v}</button></a>`).join(' ');

$('#b-sonido').onclick = () => { sonido = !sonido; $('#b-sonido').textContent = sonido ? '🔔 on' : '🔔 off'; if (sonido) pitido(); };
function pitido() {
  if (!sonido) return;
  const ctx = new AudioContext(), o = ctx.createOscillator(), g = ctx.createGain();
  o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(.2, ctx.currentTime); g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + .4);
  o.start(); o.stop(ctx.currentTime + .4);
}

async function cargar() {
  const datos = await api('/kds' + (estacion ? '?estacion=' + estacion : ''));
  desfase = new Date(datos.ahora) - new Date();          // reloj del servidor manda
  const cont = $('#kds');
  if (!datos.comandas.length) { cont.innerHTML = '<div class="vacio">Sin comandas pendientes</div>'; $('#contador').textContent = ''; return; }
  let nuevas = false;
  cont.innerHTML = datos.comandas.map(c => {
    const esNueva = !vistos.has(c.pedido_id) && !primeraCarga;
    if (esNueva) nuevas = true;
    vistos.add(c.pedido_id);
    const todasListas = c.lineas.every(l => l.estado === 'lista');
    const accion = todasListas ? 'Servido ✓' : c.lineas.some(l => l.estado === 'enviada') ? 'Empezar ▶' : 'Listo ✓';
    return `<article class="comanda ${esNueva ? 'nueva' : ''}" data-desde="${c.desde}">
      <header><span>${c.tipo === 'llevar' ? '🛍 ' + esc(c.cliente || 'Llevar') : 'Mesa ' + esc(c.mesa)}</span><span class="t">0:00</span></header>
      <div class="meta">#${c.pedido_id} · ${esc(c.camarero)}</div>
      <ul>${c.lineas.map(l => `<li class="${l.estado}" data-linea="${l.id}">
          <b>${l.cantidad}×</b><span>${esc(l.producto)}${l.alergenos ? `<span class="alerg">⚠ ${esc(l.alergenos)}</span>` : ''}${l.notas ? `<span class="nota">⚠ ${esc(l.notas)}</span>` : ''}</span>
          <span class="est">${estacion ? '' : l.estacion + ' · '}${l.estado}</span></li>`).join('')}</ul>
      <button class="bump ${todasListas ? 'ok' : 'primario'}" data-pedido="${c.pedido_id}">${accion}</button>
    </article>`;
  }).join('');
  $('#contador').textContent = `${datos.comandas.length} comandas`;
  cont.querySelectorAll('[data-linea]').forEach(li => li.onclick = async () => {
    await api('/lineas/' + li.dataset.linea, { method: 'PATCH', body: { estado: 'siguiente' } }).catch(e => aviso(e.message, 'error'));
  });
  cont.querySelectorAll('[data-pedido]').forEach(b => b.onclick = async () => {
    await api(`/kds/pedido/${b.dataset.pedido}/avanzar` + (estacion ? '?estacion=' + estacion : ''), { method: 'POST' }).catch(e => aviso(e.message, 'error'));
  });
  if (nuevas) pitido();
  primeraCarga = false;
  temporizadores();
}

function temporizadores() {
  const ahora = new Date(Date.now() + desfase);
  document.querySelectorAll('.comanda').forEach(c => {
    const seg = Math.max(0, Math.floor((ahora - new Date(c.dataset.desde)) / 1000));
    c.querySelector('.t').textContent = `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, '0')}`;
    c.classList.toggle('tarde', seg >= AVISO_MIN * 60 && seg < CRITICO_MIN * 60);
    c.classList.toggle('critica', seg >= CRITICO_MIN * 60);
  });
  $('#reloj').textContent = ahora.toLocaleTimeString('es-ES');
}
setInterval(temporizadores, 1000);

exigirSesion(['cocina', 'encargado']).then(() => {
  conectarWS(ev => { if (['kds', 'listo', 'reconectado'].includes(ev.tipo)) cargar(); });
  cargar();
});
