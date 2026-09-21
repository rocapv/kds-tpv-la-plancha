-- Ampliación 2: facturación con numeración propia y datos fiscales del local.
-- Se puede aplicar sobre una BD ya en uso (no borra nada).
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS facturas (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  serie        CHAR(1)  NOT NULL DEFAULT 'A',
  ejercicio    SMALLINT NOT NULL,
  numero       INT      NOT NULL,
  pedido_id    INT      NOT NULL,
  tipo         ENUM('simplificada','completa') NOT NULL DEFAULT 'simplificada',
  cliente_nif  VARCHAR(20)  NULL,
  cliente_nombre    VARCHAR(80)  NULL,
  cliente_direccion VARCHAR(120) NULL,
  base_cent    INT NOT NULL,
  iva_cent     INT NOT NULL,
  total_cent   INT NOT NULL,
  emitida_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_numero (serie, ejercicio, numero),
  UNIQUE KEY uq_pedido (pedido_id),
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
) ENGINE=InnoDB;

-- Datos del local y parámetros editables desde la app de ajustes
CREATE TABLE IF NOT EXISTS ajustes (
  clave  VARCHAR(40) PRIMARY KEY,
  valor  VARCHAR(200) NOT NULL
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('local_nombre',    'La Plancha'),
 ('local_nif',       'B00000000'),
 ('local_direccion', 'Av. de la Hamburguesa 42, 46100 Burjassot (València)'),
 ('local_telefono',  '960 00 00 00'),
 ('iva_pct',         '10'),
 ('aviso_min',       '8'),
 ('critico_min',     '15');
