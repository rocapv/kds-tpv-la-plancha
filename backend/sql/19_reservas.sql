-- Reservas de mesa con pedido adelantado (bloque 4 de PROPUESTA_APP_CLIENTE.md).
--
-- El cliente reserva desde su teléfono con al menos quince minutos de antelación y, si quiere,
-- deja pedido: esas líneas se quedan esperando y entran en cocina solas un rato antes de la
-- hora, para que la comida esté hecha cuando el cliente se siente.
--
-- Aplicable sobre una base en uso: solo añade.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS reservas (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  mesa_id      INT          NULL,              -- la mesa asignada; NULL mientras no haya ninguna
  zona         ENUM('sala','terraza','barra') NULL,   -- lo que pidió el cliente, si pidió algo
  hora         DATETIME     NOT NULL,
  comensales   TINYINT UNSIGNED NOT NULL,
  nombre       VARCHAR(60)  NOT NULL,
  telefono     VARCHAR(20)  NULL,
  nota         VARCHAR(200) NULL,
  token        CHAR(32)     NOT NULL,          -- con esto el cliente consulta y anula la suya
  estado       ENUM('pendiente','confirmada','sentada','no_show','anulada')
               NOT NULL DEFAULT 'pendiente',
  pedido_id    INT          NULL,              -- el pedido de la visita, al sentarse
  soltada_en   DATETIME     NULL,              -- cuándo se mandó a cocina el pedido adelantado
  creada_en    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resuelta_en  DATETIME     NULL,
  origen_ip    VARCHAR(45)  NULL,
  creada_por   INT          NULL,              -- si la coge un camarero por teléfono, quién
  UNIQUE KEY uq_token (token),
  KEY ix_agenda (hora, estado),
  FOREIGN KEY (mesa_id)    REFERENCES mesas(id),
  FOREIGN KEY (pedido_id)  REFERENCES pedidos(id),
  FOREIGN KEY (creada_por) REFERENCES empleados(id)
) ENGINE=InnoDB;

-- Lo que el cliente deja pedido por adelantado. El precio NO se guarda aquí: se congela al
-- pasar a `lineas_pedido`, igual que en cualquier otra comanda, y manda el de ese momento.
CREATE TABLE IF NOT EXISTS reserva_lineas (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  reserva_id  INT NOT NULL,
  producto_id INT NOT NULL,
  cantidad    TINYINT UNSIGNED NOT NULL DEFAULT 1,
  notas       VARCHAR(120) NULL,
  FOREIGN KEY (reserva_id)  REFERENCES reservas(id) ON DELETE CASCADE,
  FOREIGN KEY (producto_id) REFERENCES productos(id)
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('reservas_activas',        'si'),        -- el interruptor: se cierran las reservas y ya está
 ('reserva_antelacion_min',  '15'),        -- mínimo que pide el encargo
 ('reserva_duracion_min',    '90'),        -- lo que se supone que ocupa una mesa reservada
 ('reserva_margen_cocina_min','10'),       -- cuánto antes de la hora entra el pedido adelantado
 ('reserva_max_dias',        '30'),        -- no se reserva para dentro de un año
 ('reserva_horario',         '13:00-16:00,20:00-23:30'),  -- cuándo se puede reservar
 ('reserva_paso_min',        '30');        -- cada cuánto se ofrece hueco
