# Mejoras pendientes

De las diez propuestas el 21/09/2026 están hechas **las diez**: la **7** (carta editable), la
**4** (dividir cuenta y pago mixto), la **1** (sesiones con token y roles), la **2** (HTTPS), la
**8** (alérgenos en TPV y cocina), la **9** (pantalla de recogida), la **6** (copias
incrementales con restauración probada), la **10** (pruebas automáticas y despliegue), la **5**
(arqueo de caja y cierre Z) y la **3** (modo sin red en el TPV).

No queda ninguna pendiente de aquella lista. Lo que se vaya viendo a partir de ahora se apunta
aquí abajo.

## Apuntado al cerrar la mejora 3

- **El certificado tiene que estar confiado en la tableta.** Sin instalarlo, el navegador se
  niega a registrar `sw.js` («An SSL certificate error occurred») y el TPV pierde la mitad del
  modo sin red: aguanta un corte con la pantalla abierta, pero no una recarga. Lo comprueba
  `deploy/qa_sinred.py`, que arranca el navegador haciendo de cuenta que ya está confiado.
- **Empezar el turno exige red**: el PIN lo valida el servidor. Una sesión ya abierta aguanta el
  corte, pero quien llega con la tableta recién arrancada y sin wifi no puede entrar.
- Sin red el TPV enseña la carta y las mesas **de la última vez que hubo servidor**. Si el
  encargado cambia un precio mientras una tableta está caída, esa tableta apunta el precio viejo;
  al reenviar manda el producto, y **el precio lo pone el servidor**.
