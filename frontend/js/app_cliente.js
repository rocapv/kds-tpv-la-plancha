// La carta, instalada en el móvil como una app.
//
// No es una APK: es la misma web, que el navegador guarda en la pantalla de inicio y abre sin
// barra de direcciones. Lo que se gana: **no hay nada que actualizar**. Cuando el local cambia la
// carta, el móvil ya la tiene a la siguiente vez que abre, porque el trabajador de servicio
// (`sw.js`) guarda las piezas y las refresca por detrás.
(() => {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js')
      .catch(e => console.warn('sin trabajador de servicio:', e.message)));
  }

  // Android ofrece instalar; iOS no, allí se hace desde «Compartir → Añadir a inicio».
  let invitacion = null;
  window.addEventListener('beforeinstallprompt', ev => {
    ev.preventDefault();
    invitacion = ev;
    pintarBotón();
  });

  function pintarBotón() {
    if (document.querySelector('#b-instalar')) return;
    const b = document.createElement('button');
    b.id = 'b-instalar';
    b.className = 'instalar';
    b.textContent = 'Instalar la carta';
    b.onclick = async () => {
      b.remove();
      invitacion.prompt();
      await invitacion.userChoice;
      invitacion = null;
    };
    document.querySelector('header.barra-cliente')?.appendChild(b);
  }

  window.addEventListener('appinstalled', () => document.querySelector('#b-instalar')?.remove());

  // Atajo del manifiesto: «Reservar mesa» abre la app directamente en el diálogo.
  if (new URLSearchParams(location.search).get('reservar')) {
    window.addEventListener('load', () => document.querySelector('#b-reservar')?.click());
  }
})();
