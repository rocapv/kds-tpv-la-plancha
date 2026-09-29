-- Cuentas de cliente: entrar en la app con correo y contraseña.
--
-- Es una cuenta de **cliente**, no de empleado: no tiene nada que ver con `empleados` ni con los
-- escalafones, y su token no abre ninguna pantalla de trabajo. Están aparte a propósito, para que
-- no haya manera de que una cuenta creada desde internet acabe teniendo permisos dentro.
--
-- La sesión dura hasta que el cliente sale: no caduca sola. Lo pidió así RocaPV, y para una carta
-- es razonable; lo que se guarda en el móvil es un token, nunca la contraseña.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS clientes (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(120) NOT NULL,
  contrasena    VARCHAR(200) NOT NULL,        -- pbkdf2$vueltas$sal$resumen, como las de gestión
  nombre        VARCHAR(60)  NULL,
  telefono      VARCHAR(20)  NULL,
  -- Datos fiscales para la factura a petición. Se rellenan solo si el cliente quiere.
  nif           VARCHAR(20)  NULL,
  razon_social  VARCHAR(80)  NULL,
  direccion     VARCHAR(120) NULL,
  factura_auto  BOOLEAN      NOT NULL DEFAULT FALSE,
  alta_en       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_acceso DATETIME     NULL,
  activo        BOOLEAN      NOT NULL DEFAULT TRUE,
  UNIQUE KEY uq_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cliente_sesiones (
  token      CHAR(64)  PRIMARY KEY,
  cliente_id INT       NOT NULL,
  creada_en  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_uso DATETIME  NULL,
  agente     VARCHAR(120) NULL,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
  KEY ix_cliente (cliente_id)
) ENGINE=InnoDB;

-- Freno a la fuerza bruta: la puerta del cliente está abierta a internet igual que la del
-- personal, así que se cuentan los intentos fallidos por correo y por IP.
CREATE TABLE IF NOT EXISTS cliente_intentos (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  email     VARCHAR(120) NULL,
  ip        VARCHAR(45)  NULL,
  cuando    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_email (email, cuando),
  KEY ix_ip (ip, cuando)
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('clientes_registro',      'si'),   -- se puede cerrar el alta de cuentas nuevas
 ('cliente_intentos_max',   '8'),    -- fallos permitidos antes del freno
 ('cliente_intentos_min',   '15');   -- ventana en minutos que se mira
