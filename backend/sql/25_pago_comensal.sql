-- De quién era cada pago.
--
-- Hacía falta para algo que no se ve hasta que pasa: una mesa donde **todo es compartido** (tres
-- personas y una botella). Ahí nadie tiene líneas propias, así que no había manera de saber quién
-- había pagado ya, el reparto se hacía siempre entre tres y la caja se quedaba a dos céntimos del
-- total. Con el pago apuntado a su nombre, «ya pagó» es un hecho y no una deducción.
--
-- También arregla el ticket individual, que hasta ahora se apoyaba en el concepto escrito a mano.
SET NAMES utf8mb4;

ALTER TABLE pagos
  ADD COLUMN IF NOT EXISTS comensal_id INT NULL AFTER concepto;

ALTER TABLE pagos
  ADD CONSTRAINT fk_pago_comensal FOREIGN KEY IF NOT EXISTS (comensal_id)
      REFERENCES comensales(id) ON DELETE SET NULL;
