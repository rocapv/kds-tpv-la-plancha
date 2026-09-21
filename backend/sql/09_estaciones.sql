-- Las secciones de la cocina dejan de estar clavadas en el código.
--
-- Hasta ahora `estacion` era un ENUM de cuatro valores: para abrir una sección nueva (un
-- broiler, un wok, un montaje de postres) había que tocar el esquema Y el backend. Pasa a ser
-- una tabla, y además se define QUÉ secciones ve cada pantalla de cocina, que no es lo mismo:
-- el pase las mira todas, pero la freidora no tiene por qué ver la barra.
--
-- Idempotente. El ENUM se convierte a VARCHAR conservando los valores que ya hubiera.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS estaciones (
  clave  VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(40)      NOT NULL,
  icono  VARCHAR(8)       NOT NULL DEFAULT '🍳',
  orden  TINYINT UNSIGNED NOT NULL DEFAULT 0,
  activa BOOLEAN          NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

INSERT INTO estaciones (clave, nombre, icono, orden) VALUES
 ('plancha',  'Placa térmica',    '🍔', 1),
 ('freidora', 'Fritura',          '🍟', 2),
 ('frios',    'Cámara fría',      '🥗', 3),
 ('barra',    'Barra de oxígeno', '🥤', 4)
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), icono=VALUES(icono), orden=VALUES(orden);

ALTER TABLE productos      MODIFY estacion VARCHAR(20) NOT NULL;
ALTER TABLE lineas_pedido  MODIFY estacion VARCHAR(20) NOT NULL;

-- Una pantalla de cocina = un nombre y la lista de secciones que muestra (vacío = todas).
CREATE TABLE IF NOT EXISTS kds_pantallas (
  clave       VARCHAR(20) PRIMARY KEY,
  nombre      VARCHAR(40)      NOT NULL,
  icono       VARCHAR(8)       NOT NULL DEFAULT '🔔',
  estaciones  VARCHAR(200)     NOT NULL DEFAULT '',     -- claves separadas por comas
  orden       TINYINT UNSIGNED NOT NULL DEFAULT 0,
  activa      BOOLEAN          NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

INSERT INTO kds_pantallas (clave, nombre, icono, estaciones, orden) VALUES
 ('plancha',  'Placa térmica',    '🍔', 'plancha',  1),
 ('freidora', 'Fritura',          '🍟', 'freidora', 2),
 ('frios',    'Cámara fría',      '🥗', 'frios',    3),
 ('barra',    'Barra de oxígeno', '🥤', 'barra',    4),
 ('caliente', 'Línea caliente',   '🔥', 'plancha,freidora', 5),
 ('pase',     'Pase',             '🔔', '',         9)
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), icono=VALUES(icono),
  estaciones=VALUES(estaciones), orden=VALUES(orden);
