-- El cliente pide y va directo a cocina, salvo que salte el filtro (bloque 2 de la propuesta).
--
-- Hasta ahora toda comanda del cliente esperaba a que un camarero la tecleara. Con la mesa
-- vinculada por QR ya se sabe quién pide y desde dónde, así que lo normal es que entre sola. Lo
-- que se queda esperando es lo que huele raro: once botellas de agua, un carrito de treinta
-- líneas o un importe que no cuadra con una mesa de dos.
--
-- No se añade un estado nuevo: una solicitud retenida sigue siendo `pendiente`, pero con el
-- motivo escrito. Así la sala no tiene que aprender otra palabra y el flujo de siempre vale.
SET NAMES utf8mb4;

ALTER TABLE solicitudes
  ADD COLUMN IF NOT EXISTS visita_id INT NULL AFTER mesa_id,
  ADD COLUMN IF NOT EXISTS motivo_retencion VARCHAR(200) NULL AFTER estado,
  ADD COLUMN IF NOT EXISTS motivo_rechazo VARCHAR(200) NULL AFTER motivo_retencion,
  ADD COLUMN IF NOT EXISTS automatica BOOLEAN NOT NULL DEFAULT FALSE AFTER motivo_rechazo;

ALTER TABLE solicitudes
  ADD CONSTRAINT fk_solicitud_visita FOREIGN KEY IF NOT EXISTS (visita_id)
      REFERENCES visitas(id) ON DELETE SET NULL;

-- La cantidad de una línea la limitaba la propia tabla a 20, y eso estorba: para PARAR las
-- once botellas de agua hay que poder guardarlas primero y que el camarero las corrija. El tope
-- de la base pasa a ser una barrera contra lo absurdo (999), y quien decide cuánto admite una
-- comanda es el filtro de `pedido_cliente`, que además explica por qué la para.
ALTER TABLE solicitud_lineas MODIFY COLUMN cantidad SMALLINT UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE solicitud_lineas DROP CONSTRAINT IF EXISTS `solicitud_lineas.cantidad`;
ALTER TABLE solicitud_lineas ADD CONSTRAINT chk_solicitud_cantidad
  CHECK (cantidad > 0 AND cantidad <= 999);

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('cliente_pedido_directo',      'si'),   -- el interruptor: si se apaga, todo pasa por camarero
 ('cliente_max_unidades_linea',  '10'),   -- aquí se paran las 1111 botellas de agua
 ('cliente_max_lineas_pedido',   '25'),   -- el carrito absurdo
 ('cliente_max_importe_cent',    '15000'),-- por encima, lo confirma alguien
 ('cliente_max_pedidos_hora',    '12'),   -- el que se aburre pulsando
 ('cliente_confirmar_categorias', '');    -- ids de categoría que SIEMPRE pasan por camarero
