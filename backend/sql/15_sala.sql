-- Ampliación: la sala como la ve el encargado mientras ocurre el servicio.
--
-- Hasta ahora el sistema medía la cocina (enviada → lista) y el dinero (arqueo al cerrar). Faltaba
-- lo que vive el cliente: cuánto tarda en que le tomen nota, cuánto espera la cuenta y cuántos
-- somos en la sala ahora mismo. Casi todo ya estaba fechado en la base de datos; lo único que hacía
-- falta era un dato que nadie apuntaba: cuántas personas se sientan en la mesa.
SET NAMES utf8mb4;

ALTER TABLE pedidos
  ADD COLUMN IF NOT EXISTS comensales TINYINT UNSIGNED NULL AFTER mesa_id;

-- Minutos a partir de los cuales el encargado tiene que enterarse. Son ajustables porque no es lo
-- mismo una cantina de menú que un local de sobremesa larga.
INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('sala_espera_nota',   '6'),    -- mesa abierta sin que nadie le haya tomado nota
 ('sala_espera_cuenta', '8'),    -- todo servido y la cuenta sin cobrar
 ('sala_espera_pase',   '5');    -- plato listo en el pase que nadie recoge
