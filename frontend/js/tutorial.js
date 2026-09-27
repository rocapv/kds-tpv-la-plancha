// ── Modo tutorial: alguien que nunca ha visto esto se sienta y le explican la pantalla ──
//
// Burbujas de conversación que señalan un sitio concreto y dicen para qué sirve. La forma de
// la burbuja está tomada del pen «Chat Bubbles in CSS» de Founts (codepen.io/Founts/pen/AJyVOr),
// rehecha con código propio y con los colores del sistema.
//
// Tres decisiones, todas del mismo sitio: esto lo va a usar alguien con prisa el primer día.
//   1. Se carga SOLO al pulsar «?»: quien ya sabe trabajar no paga ni un byte por el tutorial.
//   2. Si el elemento de un paso no está en la pantalla (porque ese puesto no lo tiene), el
//      paso se salta en silencio. Enseñar un botón que no existe confunde más que no explicar.
//   3. Se recuerda que ya se vio, para ofrecerlo una vez y no volver a molestar.

(() => {
  const LLAVE = 'kds_tutorial_visto';

  // Un guion por pantalla. `donde` es un selector; si no encuentra nada, el paso se salta.
  const GUIONES = {
    'index.html': [
      { donde: '.menu section:first-of-type', titulo: 'Tus aplicaciones',
        texto: 'Aquí solo salen las pantallas que tu puesto puede abrir. Si echas algo en falta, no es un fallo: es que ese trabajo lo hace otro puesto.' },
      { donde: '#estado-servicio', titulo: 'Cómo va el día',
        texto: 'Tickets y caja del día, en vivo. Se actualiza solo, sin recargar.' },
      { donde: '.faccion', titulo: 'Pantalla de día o de noche',
        texto: 'La cocina trabaja con poca luz y la terraza con el sol de cara. Cada pantalla recuerda la suya.' },
      { donde: '#conexion', titulo: 'El punto verde',
        texto: 'Verde es que el servidor contesta. Si parpadea en rojo, estás sin conexión: en el TPV puedes seguir tomando nota igual.' },
    ],
    'tpv.html': [
      { donde: '#v-mesas .mesa', titulo: 'Las mesas',
        texto: 'El color no dice «ocupada», dice qué está esperando: sin pedir, en cocina, listo en el pase o esperando la cuenta. Toca una para abrirla.' },
      { donde: '#productos .producto', titulo: 'Añadir a la comanda',
        texto: 'Un toque añade el producto. Si mantienes pulsado (o haces clic derecho) puedes poner cantidad y una nota para cocina, como «sin cebolla».' },
      { donde: '#b-enviar', titulo: 'Mandarlo a cocina',
        texto: 'Hasta que no pulsas esto, la cocina no ve nada. Es el paso que convierte lo apuntado en trabajo.' },
      { donde: '#b-cobrar', titulo: 'Cobrar',
        texto: 'Se puede cobrar entero, dividido en partes iguales o por líneas, y mezclando efectivo, tarjeta y Bizum.' },
      { donde: '#comensales', titulo: 'Cuántos se sientan',
        texto: 'Marca los comensales: es lo que permite saber después cuánto gasta cada persona.' },
    ],
    'kds.html': [
      { donde: '.comanda', titulo: 'Una tarjeta, una comanda',
        texto: 'El cabecero cambia de color con el tiempo: azul recién llegada, ámbar a los 8 minutos y rojo a los 15. No hay que leer el reloj.' },
      { donde: '.comanda .bump', titulo: 'El botón grande',
        texto: 'Avanza la comanda entera: empezar, listo y servido. También puedes tocar línea a línea.' },
      { donde: '.comanda .bump-grupo .deshacer', titulo: 'Me he adelantado',
        texto: 'La franja roja devuelve un paso. En cocina se toca con las manos ocupadas y un clic de más se arregla aquí.' },
      { donde: '.estaciones', titulo: 'Tu sección',
        texto: 'Cada pantalla ve lo suyo. El pase las ve todas.' },
    ],
    'cliente.html': [
      { donde: '.cats-cliente', titulo: 'La carta',
        texto: 'Desliza para ver las secciones. Los alérgenos van marcados en cada plato.' },
      { donde: '.cesta', titulo: 'Tu cesta',
        texto: 'Cuando termines, pulsa «Pedir». Un camarero confirma la comanda antes de que entre en cocina.' },
      { donde: '#mi-comanda', titulo: 'Tu comanda, paso a paso',
        texto: 'Esta tira avanza sola: enviada, confirmada, en cocina, lista y servida.' },
    ],
    'sala.html': [
      { donde: '#avisos', titulo: 'Quién está esperando',
        texto: 'No mide el plato, mide al cliente: mesas sin atender, platos listos que nadie recoge y cuentas sin cobrar.' },
    ],
    'arqueo.html': [
      { donde: '#estado-caja', titulo: 'La caja del día',
        texto: 'El día se abre declarando el fondo y se cierra contando el cajón. El descuadre es lo contado menos lo que debería haber.' },
    ],
    'carta.html': [
      { donde: '#b-producto', titulo: 'Productos',
        texto: 'Un producto «agotado» sigue en la carta pero no se puede pedir. Uno «de baja» desaparece, y los pedidos antiguos lo conservan.' },
    ],
  };

  const $$ = s => document.querySelector(s);
  let pasos = [], i = 0, capa = null, foco = null, burbuja = null;

  function limpiar() {
    capa?.remove(); foco?.remove(); burbuja?.remove();
    capa = foco = burbuja = null;
    removeEventListener('keydown', porTeclado);
  }

  function porTeclado(e) {
    if (e.key === 'Escape') { limpiar(); }
    else if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); siguiente(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); i = Math.max(0, i - 2); siguiente(); }
  }

  function pintar(paso) {
    const el = $$(paso.donde);
    const r = el.getBoundingClientRect();
    foco.style.cssText = `position:absolute; left:${r.left - 6}px; top:${r.top - 6}px;`
                       + `width:${r.width + 12}px; height:${r.height + 12}px;`;
    // La burbuja va debajo si cabe, y si no, encima: nunca fuera de la pantalla.
    const debajo = r.bottom + 190 < innerHeight;
    burbuja.dataset.pico = debajo ? 'arriba' : 'abajo';
    burbuja.innerHTML = `
      <h4>${paso.titulo}</h4>
      <p>${paso.texto}</p>
      <div class="fila">
        <span class="pasos">${i} de ${pasos.length}</span>
        <span class="hueco" style="flex:1"></span>
        <button data-salir>Salir</button>
        <button data-siguiente class="primario">${i >= pasos.length ? 'Terminar' : 'Siguiente'}</button>
      </div>`;
    burbuja.style.visibility = 'hidden';
    burbuja.style.left = '0px'; burbuja.style.top = '0px';
    const b = burbuja.getBoundingClientRect();
    const izq = Math.min(Math.max(8, r.left - 10), innerWidth - b.width - 8);
    const arr = debajo ? r.bottom + 16 : Math.max(8, r.top - b.height - 16);
    burbuja.style.left = izq + 'px';
    burbuja.style.top = arr + 'px';
    burbuja.style.visibility = 'visible';
    burbuja.querySelector('[data-salir]').onclick = terminar;
    burbuja.querySelector('[data-siguiente]').onclick = siguiente;
  }

  function siguiente() {
    // Se salta en silencio lo que esta pantalla no tiene: cada puesto ve cosas distintas.
    while (i < pasos.length && !$$(pasos[i].donde)) i++;
    if (i >= pasos.length) return terminar();
    const paso = pasos[i];
    i++;
    $$(paso.donde).scrollIntoView({ block: 'center', behavior: 'smooth' });
    setTimeout(() => pintar(paso), 220);
  }

  function terminar() {
    try {
      const vistos = JSON.parse(localStorage.getItem(LLAVE) || '[]');
      if (!vistos.includes(pantallaActual)) localStorage.setItem(LLAVE, JSON.stringify([...vistos, pantallaActual]));
    } catch {}
    limpiar();
  }

  let pantallaActual = '';

  function empezar(pantalla) {
    pantallaActual = pantalla || (location.pathname.split('/').pop() || 'index.html');
    pasos = GUIONES[pantallaActual] || [];
    if (!pasos.length) {
      if (typeof aviso === 'function') aviso('Esta pantalla todavía no tiene explicación', 'info');
      return;
    }
    limpiar();
    capa = document.createElement('div'); capa.id = 'tutorial-capa'; capa.onclick = terminar;
    foco = document.createElement('div'); foco.id = 'tutorial-foco';
    burbuja = document.createElement('div'); burbuja.className = 'burbuja';
    document.body.append(capa, foco, burbuja);
    addEventListener('keydown', porTeclado);
    i = 0;
    siguiente();
  }

  const yaVisto = p => {
    try { return JSON.parse(localStorage.getItem(LLAVE) || '[]').includes(p); } catch { return false; }
  };

  window.tutorial = { empezar, yaVisto, guiones: Object.keys(GUIONES) };
})();
