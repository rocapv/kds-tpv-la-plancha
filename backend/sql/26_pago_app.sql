-- Un método de pago más: «app». El cliente paga desde su teléfono, en la mesa.
--
-- Podría haberse apuntado como «tarjeta» y nadie se habría quejado, porque el arqueo solo cuenta
-- el efectivo para el cajón y lo demás le da igual. Pero al encargado NO le da igual: un cobro
-- con tarjeta deja un justificante en el datáfono contra el que cuadrar, y uno hecho desde el
-- móvil del cliente no deja nada físico. Meterlos en el mismo montón es pedirle que cuadre a
-- ciegas una parte de la caja. Con su propio nombre, el cierre Z los separa solo: `por_metodo` es
-- un GROUP BY y la pantalla de arqueo lo recorre tal cual, así que la fila «app» aparece sin
-- tocar ni una línea del informe.
--
-- Lo que este método NO significa: que se haya cobrado de verdad. Hoy es un simulacro (queda por
-- decidir si algún día habrá pasarela). El valor dice **de dónde salió la orden de pago**, no que
-- haya dinero en una cuenta; cuando haya pasarela, el mismo valor sirve y lo que se añade es su
-- referencia.
--
-- Y no se añade a la lista que aceptan las rutas del personal a propósito: «app» solo lo puede
-- escribir la ruta pública que atiende al teléfono del cliente. Un camarero no puede marcar un
-- cobro como hecho desde la app, porque él no es la app.
SET NAMES utf8mb4;

ALTER TABLE pagos
  MODIFY metodo ENUM('efectivo','tarjeta','bizum','app') NOT NULL;
