// Plano de la cantina: el encargado arrastra la ficha de cada empleado al puesto donde
// trabaja. El puesto decide a qué pantalla entra y qué puede hacer (ver 08_puestos.sql).
//
// Se usa Pointer Events y no drag&drop de HTML5 a propósito: el mismo código vale para el
// ratón del despacho y para el dedo en la tableta de barra, que es donde se va a usar.
let PUESTOS = [], PLANTILLA = [];
// El mapa tiene dos modos y no se mezclan: o se reparte gente (arrastrar fichas) o se recoloca
// la sala (arrastrar y estirar las cajas). Con los dos a la vez, cada intento de mover a una
// persona acabaría moviendo la zona entera.
let modoEdicion = false;

async function cargarMapa() {
  [PUESTOS, PLANTILLA] = await Promise.all([api('/puestos'), api('/plantilla')]);
  pintarMapa();
}

function pintarMapa() {
  const plano = $('#plano');
  plano.classList.toggle('editando', modoEdicion);
  plano.innerHTML = PUESTOS.map(p => `
    <div class="zona" data-puesto="${p.clave}"
         style="left:${p.x}%;top:${p.y}%;width:${p.ancho}%;height:${p.alto}%;border-color:${esc(p.color)}">
      <b>${esc(p.nombre)}</b>
      <small class="tenue">${p.gui ? esc(p.gui.replace('.html', '').replace('?estacion=', ' · ')) : 'sin pantalla'}</small>
      ${modoEdicion ? '<span class="tirador" title="Estirar"></span>' : ''}
    </div>`).join('');

  if (modoEdicion) {
    plano.querySelectorAll('.zona').forEach(z => cajaEditable(z));
    pintarResumen();
    return;                       // en edición no se pintan fichas: se recoloca la sala, no la gente
  }

  PLANTILLA.forEach((e, i) => {
    const zona = PUESTOS.find(p => p.clave === e.puesto);
    const ficha = document.createElement('button');
    ficha.className = 'ficha' + (e.puesto ? '' : ' sin-puesto');
    ficha.dataset.id = e.id;
    ficha.title = `${e.nombre} · rol ${e.rol}${e.puesto_nombre ? ' · ahora en ' + e.puesto_nombre : ' · sin puesto'}`;
    ficha.innerHTML = `<span class="ini">${esc(e.nombre.slice(0, 2).toUpperCase())}</span>
                       <span class="nom">${esc(e.nombre)}</span>`;
    // sin puesto, las fichas se alinean en la bandeja de abajo
    const x = e.mapa_x ?? (zona ? zona.x + 2 : 4 + i * 11);
    const y = e.mapa_y ?? (zona ? zona.y + 8 : 93);
    ficha.style.left = x + '%';
    ficha.style.top = y + '%';
    arrastrable(ficha, e);
    plano.appendChild(ficha);
  });
  pintarResumen();
}

// Un botón para abrir el servicio: cada rol a sus puestos, repartidos y sin amontonarse.
// Lo decide el servidor, que es quien sabe qué puesto corresponde a cada rol.
$('#b-reparto').onclick = async () => {
  const hay = PLANTILLA.some(e => e.puesto);
  if (hay && !confirm('Esto recoloca a todo el mundo y pierde el reparto de ahora. ¿Seguir?')) return;
  try {
    const r = await api('/plantilla/reparto', { method: 'POST' });
    PLANTILLA = r.plantilla;
    pintarMapa();
    aviso(`${r.colocados} personas colocadas`, 'ok');
  } catch (e) { aviso(e.message, 'error'); }
};

function pintarResumen() {
  $('#resumen').innerHTML = PUESTOS.map(p => {
    const gente = PLANTILLA.filter(e => e.puesto === p.clave);
    if (!gente.length) return '';
    return `<span class="chip" style="border-color:${esc(p.color)}">${esc(p.nombre)}: ${gente.map(g => esc(g.nombre)).join(', ')}</span>`;
  }).join('') || '<span class="tenue">Nadie colocado en el plano todavía.</span>';
}

function arrastrable(ficha, empleado) {
  const plano = $('#plano');
  ficha.onpointerdown = ev => {
    ev.preventDefault();
    ficha.setPointerCapture(ev.pointerId);
    ficha.classList.add('moviendo');
    const caja = plano.getBoundingClientRect();

    const mover = e => {
      const x = Math.min(96, Math.max(0, ((e.clientX - caja.left) / caja.width) * 100));
      const y = Math.min(96, Math.max(0, ((e.clientY - caja.top) / caja.height) * 100));
      ficha.style.left = x + '%';
      ficha.style.top = y + '%';
      const z = zonaEn(x, y);
      plano.querySelectorAll('.zona').forEach(d => d.classList.toggle('encima', d.dataset.puesto === z?.clave));
    };

    const soltar = async e => {
      ficha.releasePointerCapture(ev.pointerId);
      ficha.classList.remove('moviendo');
      ficha.onpointermove = null;
      ficha.onpointerup = null;
      plano.querySelectorAll('.zona').forEach(d => d.classList.remove('encima'));
      const x = Math.round(parseFloat(ficha.style.left));
      const y = Math.round(parseFloat(ficha.style.top));
      const z = zonaEn(x, y);
      try {
        const r = await api(`/empleados/${empleado.id}/puesto`, {
          method: 'PUT', body: { puesto: z?.clave || null, x, y },
        });
        Object.assign(empleado, r);
        ficha.classList.toggle('sin-puesto', !r.puesto);
        ficha.title = `${r.nombre} · rol ${r.rol}${r.puesto_nombre ? ' · ahora en ' + r.puesto_nombre : ' · sin puesto'}`;
        aviso(z ? `${r.nombre} → ${z.nombre}` : `${r.nombre} queda fuera de servicio`, z ? 'ok' : 'info');
        pintarResumen();
      } catch (err) {
        aviso(err.message, 'error');
        cargarMapa();                    // si el servidor dice que no, manda el servidor
      }
    };

    ficha.onpointermove = mover;
    ficha.onpointerup = soltar;
    ficha.onpointercancel = soltar;
  };
}

/** Qué zona hay bajo un punto del plano (en %). La última gana: las de abajo se pintan encima. */
function zonaEn(x, y) {
  return [...PUESTOS].reverse().find(p => x >= p.x && x <= p.x + p.ancho && y >= p.y && y <= p.y + p.alto)
      || null;
}


// ── Modo edición: mover y estirar las cajas del mapa ─────────────────────────────────────
// Lo guarda el SERVIDOR (`PUT /api/puestos/{clave}`), que además comprueba que la caja no se
// salga del plano. Aquí solo se dibuja: si el servidor dice que no, se vuelve a cargar y la
// caja regresa a su sitio, sin dejar al encargado creyendo que ha guardado algo que no.
function cajaEditable(z) {
  const clave = z.dataset.puesto;
  const plano = $('#plano');
  const pct = (ev) => {
    const r = plano.getBoundingClientRect();
    return { x: ((ev.clientX - r.left) / r.width) * 100, y: ((ev.clientY - r.top) / r.height) * 100 };
  };

  const arrancar = (ev, estirando) => {
    ev.preventDefault(); ev.stopPropagation();
    const p = PUESTOS.find(x => x.clave === clave);
    const ini = pct(ev), base = { x: p.x, y: p.y, ancho: p.ancho, alto: p.alto };
    z.setPointerCapture(ev.pointerId);
    z.classList.add('moviendo');

    const mover = (e2) => {
      const ahora = pct(e2), dx = ahora.x - ini.x, dy = ahora.y - ini.y;
      if (estirando) {
        p.ancho = Math.max(6, Math.min(100 - base.x, Math.round(base.ancho + dx)));
        p.alto = Math.max(6, Math.min(100 - base.y, Math.round(base.alto + dy)));
      } else {
        p.x = Math.max(0, Math.min(100 - p.ancho, Math.round(base.x + dx)));
        p.y = Math.max(0, Math.min(100 - p.alto, Math.round(base.y + dy)));
      }
      z.style.left = p.x + '%'; z.style.top = p.y + '%';
      z.style.width = p.ancho + '%'; z.style.height = p.alto + '%';
    };

    const soltar = async () => {
      z.removeEventListener('pointermove', mover);
      z.removeEventListener('pointerup', soltar);
      z.classList.remove('moviendo');
      try {
        await api('/puestos/' + encodeURIComponent(clave),
                  { method: 'PUT', body: { x: p.x, y: p.y, ancho: p.ancho, alto: p.alto } });
      } catch (e) {
        aviso(e.message, 'error');
        await cargarMapa();                  // lo que diga el servidor, no lo que se arrastró
      }
    };
    z.addEventListener('pointermove', mover);
    z.addEventListener('pointerup', soltar);
  };

  z.style.pointerEvents = 'auto';
  z.onpointerdown = ev => { if (!ev.target.classList.contains('tirador')) arrancar(ev, false); };
  z.querySelector('.tirador')?.addEventListener('pointerdown', ev => arrancar(ev, true));

  // Doble toque para cambiarle el nombre: es lo que más cambia cuando se reordena una sala.
  z.ondblclick = async () => {
    const p = PUESTOS.find(x => x.clave === clave);
    const nombre = prompt('Nombre del puesto', p.nombre);
    if (!nombre || nombre.trim() === p.nombre) return;
    try {
      const r = await api('/puestos/' + encodeURIComponent(clave), { method: 'PUT', body: { nombre: nombre.trim() } });
      p.nombre = r.nombre; pintarMapa();
    } catch (e) { aviso(e.message, 'error'); }
  };
}

// Botón de la barra de pestañas: cambia entre repartir gente y recolocar la sala.
(function botonEditarMapa() {
  const zona = document.querySelector('#v-mapa .fila');
  if (!zona) return;
  const b = document.createElement('button');
  b.textContent = '✎ Editar el mapa';
  b.title = 'Mover y estirar las cajas de los puestos';
  b.onclick = () => {
    modoEdicion = !modoEdicion;
    b.classList.toggle('activa', modoEdicion);
    b.textContent = modoEdicion ? '✓ Terminar de editar' : '✎ Editar el mapa';
    aviso(modoEdicion ? 'Arrastra las cajas, estíralas por la esquina y toca dos veces para renombrar'
                      : 'Mapa guardado: vuelves a repartir gente', 'info');
    pintarMapa();
  };
  zona.prepend(b);
})();
