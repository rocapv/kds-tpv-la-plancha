// KDS: pantalla de cocina por estación.
//   · clic en una línea        → la avanza un paso
//   · clic derecho / mantener  → la devuelve un paso
//   · botón grande             → avanza la comanda entera
//   · ↶ de la comanda          → deshace el último paso de esa comanda
//   · ↶ de la barra            → deshace lo último que se tocó en esta pantalla
//
// El repintado es incremental: solo se toca lo que ha cambiado. Si se rehiciera la pantalla
// entera en cada aviso, las comandas ya listas parpadearían cada vez que alguien avanza otra.
const params = new URLSearchParams(location.search);
const estacion = params.get('estacion') || '';      // una o varias, separadas por comas
const pantalla = params.get('pantalla') || '';      // fila de kds_pantallas (Ajustes)
const AVISO_MIN = 8, CRITICO_MIN = 15;
let sonido = false, desfase = 0, primeraCarga = true;
const tarjetas = new Map();          // pedido_id → {art, firma}
const historial = [];                // lo que se ha tocado desde esta pantalla, para deshacer

// Qué secciones de cocina mira esta pantalla ya no está escrito aquí: lo decide el encargado
// en Ajustes → Cocina. Esta barra se pinta con lo que haya dado de alta.
async function pintarPantallas() {
  const lista = await api('/kds-pantallas').catch(() => []);
  const actual = lista.find(p => p.clave === pantalla)
              || lista.find(p => p.estaciones === estacion)
              || (!pantalla && !estacion ? lista.find(p => !p.estaciones) : null);
  const titulo = actual ? actual.nombre : (estacion ? estacion.split(',').join(' + ') : 'Pase (todas)');
  $('#titulo').textContent = 'KDS · ' + titulo;
  document.title = 'KDS ' + titulo;
  $('#estaciones').innerHTML = lista.map(p =>
    `<a href="?pantalla=${encodeURIComponent(p.clave)}" title="${esc(p.detalle)}">
       <button class="${p === actual ? 'activa' : ''}">${esc(p.icono)} ${esc(p.nombre)}</button></a>`).join(' ');
}

$('#b-sonido').onclick = () => { sonido = !sonido; $('#b-sonido').textContent = sonido ? '🔔 on' : '🔔 off'; if (sonido) pitido(); };
function pitido() {
  if (!sonido) return;
  const ctx = new AudioContext(), o = ctx.createOscillator(), g = ctx.createGain();
  o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(.2, ctx.currentTime); g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + .4);
  o.start(); o.stop(ctx.currentTime + .4);
}

// ── Acciones ──
const sufijoEstacion = pantalla ? '?pantalla=' + encodeURIComponent(pantalla)
                       : estacion ? '?estacion=' + encodeURIComponent(estacion) : '';

async function avanzarLinea(lid) {
  try {
    const r = await api('/lineas/' + lid, { method: 'PATCH', body: { estado: 'siguiente' } });
    apuntar({ que: 'linea', id: lid, estado: r.estado });
  } catch (e) { aviso(e.message, 'error'); }
}

async function retrocederLinea(lid) {
  try {
    const r = await api('/lineas/' + lid, { method: 'PATCH', body: { estado: 'anterior' } });
    aviso('Deshecho: vuelve a «' + r.estado + '»', 'info');
  } catch (e) { aviso(e.message, 'error'); }
}

async function avanzarComanda(pid) {
  try {
    const r = await api(`/kds/pedido/${pid}/avanzar` + sufijoEstacion, { method: 'POST' });
    apuntar({ que: 'comanda', id: pid, estado: r.estado });
  } catch (e) { aviso(e.message, 'error'); }
}

async function retrocederComanda(pid) {
  try {
    const r = await api(`/kds/pedido/${pid}/retroceder` + sufijoEstacion, { method: 'POST' });
    aviso(`Deshecho «${r.deshecho}»: ${r.lineas} línea(s) vuelven a «${r.estado}»`, 'info');
  } catch (e) { aviso(e.message, 'error'); }
}

function apuntar(accion) {
  historial.push(accion);
  if (historial.length > 30) historial.shift();
  pintarDeshacer();
}

async function deshacerUltimo() {
  const ultimo = historial.pop();
  pintarDeshacer();
  if (!ultimo) return aviso('No hay nada que deshacer en esta pantalla', 'info');
  if (ultimo.que === 'linea') await retrocederLinea(ultimo.id);
  else await retrocederComanda(ultimo.id);
}

function pintarDeshacer() {
  const b = $('#b-deshacer');
  if (!b) return;
  b.disabled = !historial.length;
  b.title = historial.length
    ? `Deshacer lo último (${historial.length} paso${historial.length > 1 ? 's' : ''} guardados)`
    : 'Nada que deshacer';
}

// ── Pintado incremental ──
function firmaDe(c) {
  return c.lineas.map(firmaLinea).join('|') + '#' + c.mesa + c.cliente;
}

// Una línea se repinta solo si cambia algo suyo. Antes la firma miraba nada más el estado,
// así que cambiar la cantidad o una nota no se veía hasta el siguiente cambio de estado.
function firmaLinea(l) {
  return [l.id, l.estado, l.cantidad, l.producto, l.alergenos || '', l.notas || '', l.estacion].join('');
}

function htmlLinea(l) {
  return `<b>${l.cantidad}×</b>
      <span>${esc(l.producto)}${l.alergenos ? `<span class="alerg">⚠ ${esc(l.alergenos)}</span>` : ''}${l.notas ? `<span class="nota">⚠ ${esc(l.notas)}</span>` : ''}</span>
      <span class="est">${estacion.includes(',') || !estacion ? l.estacion + ' · ' : ''}${l.estado}</span>`;
}

// Repintado POR LÍNEA. Antes se hacía `ul.innerHTML = ...`, que rehacía todas las líneas de la
// comanda: parpadeaban todas al marcar una, y el <li> que tenías debajo del dedo desaparecía a
// media pulsación (se perdía el `dataset.larga` del mantener-para-deshacer).
function actualizarLineas(ul, c) {
  const previas = new Map();
  ul.querySelectorAll('[data-linea]').forEach(li => previas.set(li.dataset.linea, li));
  let anterior = null;
  c.lineas.forEach(l => {
    const clave = String(l.id), firma = firmaLinea(l);
    let li = previas.get(clave);
    if (!li) {
      li = document.createElement('li');
      li.dataset.linea = l.id;
      li.title = 'Clic: avanzar · clic derecho o mantener: deshacer';
      li.className = l.estado;
      li.dataset.firma = firma;
      li.innerHTML = htmlLinea(l);
    } else {
      previas.delete(clave);
      if (li.dataset.firma !== firma) {        // solo ESTA línea se toca
        if (li.className !== l.estado) li.className = l.estado;
        li.innerHTML = htmlLinea(l);
        li.dataset.firma = firma;
      }
    }
    // colocarla en su sitio solo si no lo está ya: mover un nodo que ya está bien
    // lo saca y lo vuelve a meter en el DOM, y eso reinicia sus animaciones.
    const esperada = anterior ? anterior.nextElementSibling : ul.firstElementChild;
    if (esperada !== li) ul.insertBefore(li, esperada);
    anterior = li;
  });
  previas.forEach(li => li.remove());          // líneas que ya no vienen
}

function etiquetaBump(c) {
  if (c.lineas.every(l => l.estado === 'lista')) return { texto: 'Servido ✓', clase: 'ok' };
  if (c.lineas.some(l => l.estado === 'enviada')) return { texto: 'Empezar ▶', clase: 'primario' };
  return { texto: 'Listo ✓', clase: 'primario' };
}

function crearTarjeta(c, esNueva) {
  const art = document.createElement('article');
  art.className = 'comanda' + (esNueva ? ' nueva' : '');
  art.dataset.desde = c.desde;
  // La animación de entrada se corre UNA vez: si la clase se queda puesta, cualquier
  // reinserción futura la repetiría.
  if (esNueva) art.addEventListener('animationend', () => art.classList.remove('nueva'), { once: true });
  art.innerHTML = `
    <header>
      <span class="quien"></span>
      <span class="t">0:00</span>
      <button class="borrar" title="Anular este pedido entero">🗑</button>
    </header>
    <div class="meta"></div>
    <ul></ul>
    <div class="bump-grupo">
      <button class="bump"></button>
      <button class="deshacer" title="Me he adelantado: volver al paso anterior">↶</button>
    </div>`;
  // El deshacer va pegado al botón grande, en rojo: es el gesto de «le he dado sin querer».
  art.querySelector('.deshacer').onclick = e => { e.stopPropagation(); retrocederComanda(c.pedido_id); };
  art.querySelector('.borrar').onclick = async e => {
    e.stopPropagation();
    if (!confirm(`¿Anular el pedido #${c.pedido_id} entero? Desaparece de todas las pantallas.`)) return;
    try { await api('/pedidos/' + c.pedido_id + '/anular', { method: 'POST' }); aviso('Pedido anulado', 'ok'); }
    catch (err) { aviso(err.message, 'error'); }
  };
  art.querySelector('.bump').onclick = () => avanzarComanda(c.pedido_id);
  art.querySelector('ul').addEventListener('click', e => {
    const li = e.target.closest('[data-linea]');
    if (li) avanzarLinea(+li.dataset.linea);
  });
  art.querySelector('ul').addEventListener('contextmenu', e => {
    const li = e.target.closest('[data-linea]');
    if (!li) return;
    e.preventDefault();
    retrocederLinea(+li.dataset.linea);
  });
  // Pulsación larga en táctil = deshacer esa línea
  let temporizador;
  art.querySelector('ul').addEventListener('pointerdown', e => {
    const li = e.target.closest('[data-linea]');
    if (!li) return;
    temporizador = setTimeout(() => {
      li.dataset.larga = '1';
      retrocederLinea(+li.dataset.linea);
    }, 600);
  });
  const soltar = e => {
    clearTimeout(temporizador);
    const li = e.target.closest?.('[data-linea]');
    if (li?.dataset.larga) setTimeout(() => delete li.dataset.larga, 0);   // no avanzar tras deshacer
  };
  art.querySelector('ul').addEventListener('pointerup', soltar);
  art.querySelector('ul').addEventListener('pointerleave', soltar);
  return art;
}

function ponerTexto(el, texto) {         // no reescribir lo que ya pone eso
  if (el && el.textContent !== texto) el.textContent = texto;
}

function actualizarTarjeta(art, c) {
  ponerTexto(art.querySelector('.quien'),
    c.tipo === 'llevar' ? '🛍 ' + (c.cliente || 'Llevar') : 'Mesa ' + c.mesa);
  ponerTexto(art.querySelector('.meta'), `#${c.pedido_id} · ${c.camarero}`);
  actualizarLineas(art.querySelector('ul'), c);
  const bump = art.querySelector('.bump');
  const { texto, clase } = etiquetaBump(c);
  ponerTexto(bump, texto);
  if (bump.className !== 'bump ' + clase) bump.className = 'bump ' + clase;
  art.dataset.desde = c.desde;
}

async function cargar() {
  const datos = await api('/kds' + sufijoEstacion);
  desfase = new Date(datos.ahora) - new Date();          // el reloj del servidor manda
  const cont = $('#kds');
  const vacio = cont.querySelector('.vacio');

  if (!datos.comandas.length) {
    tarjetas.clear();
    cont.innerHTML = '<div class="vacio">Sin comandas pendientes</div>';
    $('#contador').textContent = '';
    primeraCarga = false;
    return;
  }
  if (vacio) { vacio.remove(); tarjetas.clear(); }

  let nuevas = false;
  const vistos = new Set();
  datos.comandas.forEach(c => {
    vistos.add(c.pedido_id);
    const firma = firmaDe(c);
    let ficha = tarjetas.get(c.pedido_id);
    if (!ficha) {                                         // comanda que no estaba
      const esNueva = !primeraCarga;
      if (esNueva) nuevas = true;
      const art = crearTarjeta(c, esNueva);
      actualizarTarjeta(art, c);
      cont.appendChild(art);
      tarjetas.set(c.pedido_id, { art, firma });
      return;
    }
    if (ficha.firma !== firma) {                          // cambió: se retoca, no se recrea
      actualizarTarjeta(ficha.art, c);
      ficha.firma = firma;
    }
    // si no ha cambiado no se toca: así las comandas listas no parpadean
  });

  tarjetas.forEach((ficha, pid) => {                      // comandas que ya no están
    if (!vistos.has(pid)) { ficha.art.remove(); tarjetas.delete(pid); }
  });

  // El orden lo decide el servidor (más antigua primero), pero se mueve SOLO lo que está fuera
  // de sitio. Antes se hacía `appendChild` de todas las tarjetas en cada aviso: reinsertar un
  // nodo reinicia sus animaciones CSS, así que la comanda crítica (que parpadea) y la recién
  // entrada (que hace zoom) se reiniciaban cada vez que alguien marcaba algo en cualquier zona.
  let anterior = null;
  datos.comandas.forEach(c => {
    const art = tarjetas.get(c.pedido_id).art;
    const esperada = anterior ? anterior.nextElementSibling : cont.firstElementChild;
    if (esperada !== art) cont.insertBefore(art, esperada);
    anterior = art;
  });

  // La pantalla enseña las más viejas (se cocina por orden de llegada). Si la cocina va con
  // retraso hay más esperando, y callarlo sería mentir sobre el trabajo que queda.
  $('#contador').textContent = datos.esperando
    ? `${datos.comandas.length} comandas · ${datos.esperando} esperando`
    : `${datos.comandas.length} comandas`;
  let cola = cont.querySelector('.mas-cola');
  if (datos.esperando) {
    if (!cola) { cola = document.createElement('div'); cola.className = 'mas-cola'; }
    cola.textContent = `… y ${datos.esperando} comandas más esperando turno`;
    cont.appendChild(cola);                       // siempre la última
  } else if (cola) cola.remove();
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

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); deshacerUltimo(); }
});

exigirSesion(['cocina', 'encargado']).then(() => {
  pintarPantallas();
  $('#b-deshacer').onclick = deshacerUltimo;
  pintarDeshacer();
  conectarWS(ev => { if (['kds', 'listo', 'reconectado'].includes(ev.tipo)) cargar(); });
  cargar();
});
