-- Factura a petición: de qué parte de la cuenta es, quién la pidió y cuándo pasó la operación.
--
-- `pago_id` es el cambio de fondo. Hasta ahora la factura era del pedido, y con una mesa que paga
-- a escote eso no se sostiene: la factura de Ana tiene que decir lo que puso Ana, no lo que cenaron
-- los cuatro. Se apunta a qué cobro corresponde, con **0 = la cuenta entera**. El 0 no es un id de
-- pago inventado: es el valor que hace que la clave única siga sirviendo de freno. Con `pago_id`
-- NULL, MariaDB no compara NULLs entre sí y dejaría meter dos facturas de la misma cuenta entera;
-- con 0 no hay manera. La regla de que no puede haber a la vez una por cabeza y otra de todos la
-- pone el código, porque eso la base de datos no lo sabe expresar.
--
-- `operacion_en` es la fecha de lo que se cobró, que deja de ser la de la factura en cuanto alguien
-- la pide al día siguiente. El Reglamento de facturación pide las dos fechas cuando no coinciden,
-- y sin guardarla no se puede imprimir ninguna de las dos con verdad.
--
-- `pedida_por` distingue la que salió del teléfono del cliente de la que hizo el camarero. No es
-- adorno: si mañana hay una reclamación sobre una factura que el local no recuerda haber emitido,
-- la respuesta está en esa columna.
--
-- `cliente_id` engancha la factura a la cuenta de cliente que la pidió, y es lo único que permite
-- la pantalla «mis facturas». Es un enlace flojo a propósito (ON DELETE SET NULL): si el cliente
-- borra su cuenta, la factura emitida **no se borra** —hay obligación de conservarla— pero deja de
-- estar atada a una persona registrada.
SET NAMES utf8mb4;

ALTER TABLE facturas
  ADD COLUMN IF NOT EXISTS pago_id      INT NOT NULL DEFAULT 0 AFTER pedido_id,
  ADD COLUMN IF NOT EXISTS pedida_por   ENUM('local','app') NOT NULL DEFAULT 'local' AFTER tipo,
  ADD COLUMN IF NOT EXISTS cliente_id   INT NULL AFTER cliente_direccion,
  ADD COLUMN IF NOT EXISTS operacion_en DATETIME NULL AFTER emitida_en;

ALTER TABLE facturas
  ADD CONSTRAINT fk_factura_cliente FOREIGN KEY IF NOT EXISTS (cliente_id)
      REFERENCES clientes(id) ON DELETE SET NULL;

-- Una por pedido pasa a ser una por (pedido, cobro). Las que ya existen se quedan con pago_id=0,
-- que es exactamente lo que eran: la factura de la cuenta entera.
--
-- El orden de estas dos líneas no es indiferente, y quitarlo cuesta un despliegue: `uq_pedido` es
-- el índice que sostiene la clave ajena a `pedidos`, así que borrarlo primero da «Cannot drop
-- index: needed in a foreign key constraint» (error 1553). Se crea antes el nuevo —que empieza
-- por `pedido_id`, y por eso vale igual para la clave ajena— y solo después se retira el viejo.
ALTER TABLE facturas ADD UNIQUE KEY IF NOT EXISTS uq_pedido_pago (pedido_id, pago_id);
ALTER TABLE facturas DROP INDEX IF EXISTS uq_pedido;

-- Las facturas viejas no guardaron la fecha de la operación; se rellena con la del pedido, que es
-- la buena, y así el documento no miente al reimprimirse.
UPDATE facturas f JOIN pedidos p ON p.id=f.pedido_id
   SET f.operacion_en = COALESCE(p.cerrado_en, f.emitida_en)
 WHERE f.operacion_en IS NULL;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('local_email',  'facturas@burglarking.example'),   -- sale en la factura y en el «cómo pedirla»
 ('factura_app',  'si');                           -- se puede apagar sin tocar el TPV
