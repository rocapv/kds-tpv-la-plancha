// Plano del local en 2D, visto desde arriba.
//
// Dos modos: mirar (cualquiera con sesión) y editar (encargado para arriba). En modo editar se
// arrastra, se estira por la esquina y se borra con Supr. Las coordenadas van en milésimas del
// plano, así que el dibujo es el mismo en la pantalla de barra y en el portátil del despacho.
//
// La regla de oro la aplica el servidor, no el navegador: lo que ocupa sitio (mesas, equipos,
// barra) no se puede soltar dentro de un muro. Aquí solo se avisa y se devuelve la pieza.
let PLANO = { elementos: [], mesas_sin_colocar: [] };
let PERSONAL = [];
let EDITANDO = false, SELECCIONADO = null, PUEDE_EDITAR = false;

const ETIQUETAS = {
  muro: 'Muro', zona: 'Zona', mesa: 'Mesa', equipo: 'Equipo', puerta: 'Puerta', barra: 'Barra',
};

async function cargarPlano() {
  [PLANO, PERSONAL] = await Promise.all([
    api('/plano'),
    PUEDE_EDITAR ? api('/plantilla').catch(() => []) : Promise.resolve([]),
  ]);
  pintarPlano();
}

function pintarPlano() {
  const lienzo = $('#lienzo');
  lienzo.innerHTML = PLANO.elementos.map(e => {
    const ocupada = e.mesa?.pedido_id;
    const clases = ['pieza', e.tipo, e.forma === 'circ' ? 'redonda' : '',
                    ocupada ? 'ocupada' : '', e.id === SELECCIONADO ? 'elegida' : ''].join(' ');
    const rotulo = e.tipo === 'mesa'
      ? `<b>${esc(e.mesa?.nombre || e.nombre)}</b><small>${e.mesa ? e.mesa.plazas + ' pax' : 'sin enlazar'}</small>`
      : `<b>${esc(e.icono)} ${esc(e.nombre)}</b>`;
    return `<div class="${clases}" data-id="${e.id}" data-tipo="${e.tipo}"
      style="left:${e.x / 10}%;top:${e.y / 10}%;width:${e.ancho / 10}%;height:${e.alto / 10}%;
             --tinte:${esc(e.color)}">
      <span class="rotulo">${rotulo}</span>
      ${EDITANDO ? '<i class="tirador"></i>' : ''}
    </div>`;
  }).join('');

  // Las fichas de personal se pintan encima del local, en el puesto donde estén.
  PERSONAL.filter(p => p.puesto).forEach(p => {
    const zona = PLANO.elementos.find(e => e.puesto === p.puesto);
    if (!zona) return;
    const ficha = document.createElement('div');
    ficha.className = 'ficha-plano';
    ficha.title = `${p.nombre} · ${p.puesto_nombre || p.puesto}`;
    ficha.textContent = p.nombre.slice(0, 2).toUpperCase();
    ficha.style.left = (zona.x + zona.ancho / 2) / 10 + '%';
    ficha.style.top = (zona.y + 26) / 10 + '%';
    lienzo.appendChild(ficha);
  });

  if (EDITANDO) lienzo.querySelectorAll('.pieza').forEach(prepararEdicion);
  else lienzo.querySelectorAll('.pieza.mesa').forEach(p => p.onclick = () => {
    const e = PLANO.elementos.find(x => x.id == p.dataset.id);
    if (e?.mesa) location.href = '/tpv.html';       // desde el plano se entra a la mesa
  });
  $('#sin-colocar').textContent = PLANO.mesas_sin_colocar.length
    ? 'Mesas sin colocar: ' + PLANO.mesas_sin_colocar.map(m => m.nombre).join(', ') : '';
}

// ── edición ────────────────────────────────────────────────────────────────
function prepararEdicion(pieza) {
  const lienzo = $('#lienzo');
  const id = +pieza.dataset.id;

  pieza.onpointerdown = ev => {
    const estirando = ev.target.classList.contains('tirador');
    ev.preventDefault();
    pieza.setPointerCapture(ev.pointerId);
    SELECCIONADO = id;
    document.querySelectorAll('.pieza').forEach(p => p.classList.toggle('elegida', +p.dataset.id === id));
    const caja = lienzo.getBoundingClientRect();
    const elem = PLANO.elementos.find(e => e.id === id);
    const inicio = { x: ev.clientX, y: ev.clientY, ...elem };

    const mil = (px, total) => Math.round((px / total) * 1000);
    pieza.onpointermove = e => {
      const dx = mil(e.clientX - inicio.x, caja.width);
      const dy = mil(e.clientY - inicio.y, caja.height);
      if (estirando) {
        elem.ancho = Math.max(20, Math.min(1000 - elem.x, inicio.ancho + dx));
        elem.alto = Math.max(20, Math.min(1000 - elem.y, inicio.alto + dy));
      } else {
        elem.x = Math.max(0, Math.min(1000 - elem.ancho, inicio.x + dx));
        elem.y = Math.max(0, Math.min(1000 - elem.alto, inicio.y + dy));
      }
      pieza.style.left = elem.x / 10 + '%';
      pieza.style.top = elem.y / 10 + '%';
      pieza.style.width = elem.ancho / 10 + '%';
      pieza.style.height = elem.alto / 10 + '%';
    };

    pieza.onpointerup = pieza.onpointercancel = async e => {
      pieza.onpointermove = null;
      pieza.releasePointerCapture(ev.pointerId);
      try {
        await api('/plano/elementos/' + id, { method: 'PATCH', body: {
          x: elem.x, y: elem.y, ancho: elem.ancho, alto: elem.alto } });
      } catch (err) {
        aviso(err.message, 'error');
        await cargarPlano();                 // el servidor manda: se vuelve a su sitio
      }
    };
  };
}

async function anadir(tipo) {
  const nombre = prompt(`Nombre del elemento (${ETIQUETAS[tipo]}):`, ETIQUETAS[tipo]);
  if (nombre === null) return;
  const plantillas = {
    muro:   { ancho: 200, alto: 14, color: '#4a5160', z: 0 },
    zona:   { ancho: 220, alto: 200, color: '#2471a3', z: 0 },
    mesa:   { ancho: 86, alto: 86, color: '#2b2f36', forma: 'circ', z: 3 },
    equipo: { ancho: 140, alto: 110, color: '#c0392b', z: 2, icono: '🍳' },
    puerta: { ancho: 90, alto: 14, color: '#f1c40f', z: 1, icono: '↔' },
    barra:  { ancho: 150, alto: 60, color: '#117864', z: 2, icono: '▤' },
  };
  try {
    const nuevo = await api('/plano/elementos', { method: 'POST',
      body: { tipo, nombre, x: 460, y: 460, ...plantillas[tipo] } });
    if (tipo === 'mesa') await enlazarMesa(nuevo);
    await cargarPlano();
    aviso('Colocado en el centro: arrástralo a su sitio', 'ok');
  } catch (e) { aviso(e.message, 'error'); }
}

async function enlazarMesa(elemento) {
  const libres = (await api('/plano')).mesas_sin_colocar;
  if (!libres.length) return aviso('No quedan mesas sin colocar en la base de datos', 'info');
  const cual = prompt('¿Qué mesa es? ' + libres.map(m => m.nombre).join(', '), libres[0].nombre);
  const mesa = libres.find(m => m.nombre.toLowerCase() === (cual || '').toLowerCase().trim());
  if (mesa) await api('/plano/elementos/' + elemento.id, { method: 'PATCH', body: { mesa_id: mesa.id } });
}

async function borrarSeleccionado() {
  if (!SELECCIONADO) return aviso('Elige antes una pieza del plano', 'info');
  if (!confirm('¿Quitar esta pieza del plano?')) return;
  await api('/plano/elementos/' + SELECCIONADO, { method: 'DELETE' });
  SELECCIONADO = null;
  cargarPlano();
}

function modoEdicion(activo) {
  EDITANDO = activo;
  $('#paleta').hidden = !activo;
  $('#b-editar').textContent = activo ? 'Terminar edición' : 'Editar plano';
  $('#b-editar').classList.toggle('primario', !activo);
  pintarPlano();
}

document.addEventListener('keydown', e => {
  if (EDITANDO && (e.key === 'Delete' || e.key === 'Supr')) borrarSeleccionado();
});
