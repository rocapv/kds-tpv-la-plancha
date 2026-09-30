-- Registro de entradas del personal: quién intenta entrar, desde dónde y cuántas veces.
--
-- `home.pr1.es` sirve el TPV a internet y la puerta del personal es un PIN de cuatro cifras. En el
-- primer minuto de exposición ya llegaron sondas automáticas. Antes de poner un freno hay que poder
-- VER lo que pasa, y eso es esta tabla: el encargado la consulta en «Usuarios → Intentos de entrada».
--
-- Se apuntan los fallos y también los aciertos. Un acierto después de treinta fallos desde la misma
-- IP es justo lo que hay que ver, y sin los aciertos no se vería.
--
-- Lo que NO se guarda nunca: el PIN o la contraseña que se tecleó. Un PIN fallido suele estar a una
-- cifra del bueno, y guardarlo sería dejar en la base una lista de casi-aciertos.
--
-- Va aparte de `cliente_intentos` (20_clientes.sql) a propósito: las cuentas de cliente y las del
-- personal no comparten nada, tampoco el registro.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS empleado_intentos (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  cuando      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ip          VARCHAR(45)  NULL,
  via         ENUM('pin','contrasena') NOT NULL,
  ok          BOOLEAN      NOT NULL,
  -- Con contraseña se dice un número de empleado, exista o no: se guarda el que se dijo.
  -- Con PIN, en un fallo no se sabe a quién se intentaba suplantar, y queda NULL.
  empleado_id INT          NULL,
  agente      VARCHAR(120) NULL,
  KEY ix_cuando (cuando),
  KEY ix_ip (ip, cuando)
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('intentos_dias', '30');   -- días que se conserva el registro
