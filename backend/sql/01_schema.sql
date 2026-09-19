-- KDS + TPV · Hamburguesería "La Plancha" · esquema MariaDB
-- Importes SIEMPRE en céntimos (INT) para evitar errores de coma flotante.
SET NAMES utf8mb4;

DROP TABLE IF EXISTS pagos;
DROP TABLE IF EXISTS lineas_pedido;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS mesas;
DROP TABLE IF EXISTS empleados;

CREATE TABLE empleados (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  nombre    VARCHAR(60)  NOT NULL,
  rol       ENUM('camarero','cocina','encargado') NOT NULL,
  pin       CHAR(4)      NOT NULL,
  activo    BOOLEAN      NOT NULL DEFAULT TRUE,
  UNIQUE KEY uq_pin (pin)
) ENGINE=InnoDB;

CREATE TABLE mesas (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  nombre    VARCHAR(20) NOT NULL,
  zona      ENUM('sala','terraza','barra') NOT NULL,
  plazas    TINYINT     NOT NULL DEFAULT 4
) ENGINE=InnoDB;

CREATE TABLE categorias (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  nombre    VARCHAR(40) NOT NULL,
  orden     TINYINT     NOT NULL DEFAULT 0,
  color     CHAR(7)     NOT NULL DEFAULT '#888888'
) ENGINE=InnoDB;

-- estacion = pantalla de cocina (KDS) a la que va cada producto
CREATE TABLE productos (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  categoria_id INT          NOT NULL,
  nombre       VARCHAR(60)  NOT NULL,
  precio_cent  INT          NOT NULL CHECK (precio_cent >= 0),
  iva_pct      TINYINT      NOT NULL DEFAULT 10,
  estacion     ENUM('plancha','freidora','frios','barra') NOT NULL,
  activo       BOOLEAN      NOT NULL DEFAULT TRUE,
  FOREIGN KEY (categoria_id) REFERENCES categorias(id)
) ENGINE=InnoDB;

CREATE TABLE pedidos (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  tipo         ENUM('sala','llevar') NOT NULL DEFAULT 'sala',
  mesa_id      INT NULL,
  empleado_id  INT NOT NULL,
  cliente      VARCHAR(60) NULL,          -- nombre para "para llevar"
  estado       ENUM('abierto','cobrado','anulado') NOT NULL DEFAULT 'abierto',
  abierto_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cerrado_en   DATETIME NULL,
  FOREIGN KEY (mesa_id)     REFERENCES mesas(id),
  FOREIGN KEY (empleado_id) REFERENCES empleados(id),
  KEY ix_estado (estado)
) ENGINE=InnoDB;

-- Cada línea viaja sola por cocina: pendiente → enviada → preparando → lista → servida
CREATE TABLE lineas_pedido (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id     INT NOT NULL,
  producto_id   INT NOT NULL,
  cantidad      TINYINT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
  precio_cent   INT NOT NULL,             -- precio congelado en el momento de la venta
  notas         VARCHAR(120) NULL,
  estacion      ENUM('plancha','freidora','frios','barra') NOT NULL,
  estado        ENUM('pendiente','enviada','preparando','lista','servida','anulada')
                NOT NULL DEFAULT 'pendiente',
  creada_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  enviada_en    DATETIME NULL,
  lista_en      DATETIME NULL,
  FOREIGN KEY (pedido_id)   REFERENCES pedidos(id) ON DELETE CASCADE,
  FOREIGN KEY (producto_id) REFERENCES productos(id),
  KEY ix_kds (estacion, estado)
) ENGINE=InnoDB;

CREATE TABLE pagos (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id       INT NOT NULL,
  metodo          ENUM('efectivo','tarjeta','bizum') NOT NULL,
  importe_cent    INT NOT NULL,
  entregado_cent  INT NULL,
  cambio_cent     INT NULL,
  pagado_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
) ENGINE=InnoDB;

-- Vista usada por informes: total de cada pedido
CREATE OR REPLACE VIEW v_totales_pedido AS
SELECT p.id AS pedido_id, p.estado, p.tipo, p.abierto_en, p.cerrado_en,
       COALESCE(SUM(CASE WHEN l.estado <> 'anulada' THEN l.cantidad * l.precio_cent END), 0) AS total_cent
FROM pedidos p LEFT JOIN lineas_pedido l ON l.pedido_id = p.id
GROUP BY p.id;
