-- Ampliación 4: sesiones con token. El PIN deja de circular en cada petición.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS sesiones (
  token        CHAR(43) PRIMARY KEY,          -- token aleatorio (secrets.token_urlsafe(32))
  empleado_id  INT NOT NULL,
  creada_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_uso   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  caduca_en    DATETIME NOT NULL,
  agente       VARCHAR(120) NULL,             -- navegador/pantalla desde la que se abrió
  FOREIGN KEY (empleado_id) REFERENCES empleados(id),
  KEY ix_caducidad (caduca_en)
) ENGINE=InnoDB;

-- Duración del turno: al reiniciar el servicio las sesiones siguen valiendo.
INSERT IGNORE INTO ajustes (clave, valor) VALUES ('sesion_horas', '12');
