-- Quién se sienta en cada sitio de la mesa, y de quién es cada plato.
--
-- Es la pieza que falta para cobrar «cada uno lo suyo» sin que el camarero tenga que acordarse de
-- memoria de quién pidió qué. Dos decisiones que la hacen inofensiva:
--
--   · `lineas_pedido.comensal_id` es **opcional**. NULL = «de la mesa» (la botella que comparten,
--     el pan). Quien no reparta sigue trabajando exactamente igual que hasta hoy.
--   · El comensal vive dentro del pedido y muere con él. El nombre es una etiqueta de servicio
--     («Ana», «el de la gorra»), no una ficha de cliente: al cerrar la mesa deja de existir.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS comensales (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id   INT NOT NULL,
  sitio       TINYINT UNSIGNED NOT NULL,          -- 1..plazas de la mesa; ordena la rejilla
  nombre      VARCHAR(40) NULL,
  dispositivo CHAR(64) NULL,                      -- el móvil que pide por él, si lo hay
  creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_sitio (pedido_id, sitio),
  KEY ix_dispositivo (dispositivo),
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
) ENGINE=InnoDB;

ALTER TABLE lineas_pedido
  ADD COLUMN IF NOT EXISTS comensal_id INT NULL AFTER pago_id;

ALTER TABLE lineas_pedido
  ADD CONSTRAINT fk_linea_comensal FOREIGN KEY IF NOT EXISTS (comensal_id)
      REFERENCES comensales(id) ON DELETE SET NULL;
