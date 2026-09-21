-- Ampliación: carta en el móvil del cliente y solicitudes de pedido.
--
-- Una solicitud NO es un pedido: es lo que el cliente ha pulsado en su teléfono. Entra en una
-- bandeja y un camarero la acepta o la rechaza. Así nada llega a cocina sin que una persona lo
-- haya visto, que es la diferencia entre un sistema de sala y un formulario abierto en la red.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS solicitudes (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  mesa_id      INT NULL,                       -- de qué mesa viene (QR); NULL = para llevar
  cliente      VARCHAR(60) NULL,
  nota         VARCHAR(160) NULL,
  estado       ENUM('pendiente','aceptada','rechazada') NOT NULL DEFAULT 'pendiente',
  pedido_id    INT NULL,                       -- el pedido que se creó al aceptarla
  atendida_por INT NULL,
  creada_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resuelta_en  DATETIME NULL,
  origen_ip    VARCHAR(45) NULL,               -- solo para poder cortar abusos desde la LAN
  FOREIGN KEY (mesa_id)      REFERENCES mesas(id),
  FOREIGN KEY (pedido_id)    REFERENCES pedidos(id),
  FOREIGN KEY (atendida_por) REFERENCES empleados(id),
  KEY ix_pendientes (estado, creada_en)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS solicitud_lineas (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  solicitud_id  INT NOT NULL,
  producto_id   INT NOT NULL,
  cantidad      TINYINT NOT NULL DEFAULT 1 CHECK (cantidad > 0 AND cantidad <= 20),
  notas         VARCHAR(120) NULL,
  FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE CASCADE,
  FOREIGN KEY (producto_id)  REFERENCES productos(id)
) ENGINE=InnoDB;

-- Se puede apagar desde Ajustes si un día no interesa que el cliente pida desde la mesa.
INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('cliente_pedidos', 'si'),
 ('cliente_mensaje', 'Pide desde tu mesa. Un miembro de la tripulación confirmará tu comanda.');
