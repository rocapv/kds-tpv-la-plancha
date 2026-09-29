// La pantalla de la mesa: pide un código, lo enseña y vuelve a pedir otro.
//
// El secreto de la pantalla va en la dirección (`?s=…`) y se guarda en el propio aparato la
// primera vez, para que al reiniciarse arranque solo y sin que nadie tenga que escribir nada.
// No es un secreto que proteja dinero: lo peor que se consigue con él es generar códigos de esa
// mesa, y el servidor solo se los da a quien pregunta desde la red del local.
const LLAVE_PANTALLA = 'kds_pantalla_secreto';

const parametros = new URLSearchParams(location.search);
let secreto = parametros.get('s');
if (secreto) {
  try { localStorage.setItem(LLAVE_PANTALLA, secreto); } catch {}
  history.replaceState(null, '', location.pathname);      // que no se quede a la vista
} else {
  try { secreto = localStorage.getItem(LLAVE_PANTALLA); } catch {}
}

const cuadro = $('#cuadro');
let siguiente = null;

function pintarAviso(texto, detalle = '') {
  cuadro.innerHTML = `<div class="aviso-pantalla"><b>${esc(texto)}</b>
    ${detalle ? `<p>${esc(detalle)}</p>` : ''}</div>`;
}

function pintar(d) {
  const union = d.modo === 'union';
  cuadro.innerHTML = `
    <div class="qr-mesa ${union ? 'union' : ''}">
      <h1>${esc(d.mesa)}</h1>
      <p class="pie">${union ? 'Mesa abierta · únete con este código' : 'Apunta con la cámara para pedir'}</p>
      <div class="qr">${d.svg}</div>
      <p class="codigo">${esc(d.codigo.replace(/(.{4})/g, '$1 ').trim())}</p>
      <p class="pie tenue">${union
        ? 'También vale tecleando el código en la carta'
        : 'El código cambia cada poco: si no llegas, espera al siguiente'}</p>
    </div>`;
}

async function pedirCodigo() {
  if (!secreto) {
    pintarAviso('Pantalla sin dar de alta',
                'Abre esta página con ?s=<secreto> una vez, y se acordará.');
    return;
  }
  try {
    const d = await api('/pantalla/codigo', {
      method: 'POST', headers: { 'X-Pantalla': secreto },
    });
    pintar(d);
    clearTimeout(siguiente);
    // Se pide el siguiente un pelín antes de que caduque, para que no haya un hueco en blanco.
    siguiente = setTimeout(pedirCodigo, Math.max(2, d.segundos - 1) * 1000);
  } catch (e) {
    pintarAviso('Sin conexión con la cantina', e.message);
    clearTimeout(siguiente);
    siguiente = setTimeout(pedirCodigo, 5000);
  }
}

// Si alguien canjea el código, el servidor avisa por el canal público y la pantalla pasa al
// código de unirse sin esperar a que caduque el que está enseñando.
(function escuchar() {
  const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://')
                           + location.host + '/ws/publico');
  ws.onmessage = e => { try { if (JSON.parse(e.data).tipo === 'visitas') pedirCodigo(); } catch {} };
  ws.onclose = () => setTimeout(escuchar, 4000);
  setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000);
})();

pedirCodigo();
