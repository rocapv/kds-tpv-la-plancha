// Pantalla de recogida: cuelga en la sala, sin PIN y sin datos de nadie. Solo números.
// Se refresca sola con el WebSocket público; el temporizador es la red de seguridad.
let desfase = 0, anteriores = new Set(), primera = true;

const tarjeta = (p, listo) =>
  `<div class="numero ${listo ? 'listo' : ''}" data-desde="${p.desde}">
     <b>${p.numero}</b><span class="t">0:00</span>
   </div>`;

async function cargar() {
  let d;
  try { d = await api('/recogida'); } catch { return; }
  desfase = new Date(d.ahora) - new Date();
  $('#local').textContent = d.local;
  document.title = d.local + ' · Pedidos para recoger';
  // El servidor manda como mucho un puñado de números (los que caben leyéndose de lejos) y
  // dice cuántos más hay. Callarlos daría a entender que la cocina va más desahogada de lo que va.
  const mas = n => n ? `<p class="mas-cola">… y ${n} más</p>` : '';
  $('#listos').innerHTML = (d.listos.length
    ? d.listos.map(p => tarjeta(p, true)).join('')
    : '<p class="vacio">Ningún pedido listo todavía</p>') + mas(d.mas_listos);
  $('#preparando').innerHTML = (d.preparando.length
    ? d.preparando.map(p => tarjeta(p, false)).join('')
    : '<p class="vacio">Nada en marcha</p>') + mas(d.mas_preparando);
  const ahora = new Set(d.listos.map(p => p.numero));
  if (!primera && d.listos.some(p => !anteriores.has(p.numero))) campana();
  anteriores = ahora;
  primera = false;
  relojes();
}

// Un aviso corto al aparecer un número nuevo en «Listos». Muchos navegadores exigen
// que alguien haya tocado la pantalla antes de dejar sonar: si no, simplemente no suena.
function campana() {
  try {
    const ctx = new AudioContext(), o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = 660; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(.25, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + .8);
    o.start(); o.stop(ctx.currentTime + .8);
  } catch {}
}

function relojes() {
  const ahora = new Date(Date.now() + desfase);
  document.querySelectorAll('.numero').forEach(n => {
    const seg = Math.max(0, Math.floor((ahora - new Date(n.dataset.desde)) / 1000));
    n.querySelector('.t').textContent = `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, '0')}`;
  });
  $('#reloj').textContent = ahora.toLocaleTimeString('es-ES');
}
setInterval(relojes, 1000);
setInterval(cargar, 30000);

// WebSocket sin token: esta pantalla no tiene sesión, así que usa el canal público.
(function conectar() {
  const marca = $('#conexion');
  const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/publico');
  ws.onopen = () => { marca.className = 'conexion ok'; marca.title = 'Conectado'; cargar(); };
  ws.onmessage = () => cargar();
  ws.onclose = () => { marca.className = 'conexion ko'; marca.title = 'Sin conexión'; setTimeout(conectar, 2000); };
  setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000);
})();
cargar();
