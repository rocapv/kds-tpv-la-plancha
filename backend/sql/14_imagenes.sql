-- Ampliación: imágenes (foto en el móvil, fichero en el PC) y albaranes leídos con visión.
--
-- La imagen se guarda en disco, no en la base de datos: en MariaDB solo va la ficha. Un albarán
-- de 3 MB dentro de una fila convierte cualquier copia de seguridad en un problema, y el volcado
-- de texto deja de poder abrirse.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS imagenes (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  sha256      CHAR(64) NOT NULL,              -- la misma foto dos veces es UNA fila
  tipo        ENUM('albaran','producto','palet','otro') NOT NULL DEFAULT 'otro',
  ruta        VARCHAR(200) NOT NULL,          -- relativa al almacén de imágenes
  mime        VARCHAR(40)  NOT NULL,
  bytes       INT NOT NULL,
  ancho       SMALLINT NULL,
  alto        SMALLINT NULL,
  origen      ENUM('camara','fichero') NOT NULL DEFAULT 'fichero',
  subida_por  INT NOT NULL,
  creada_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_sha (sha256),
  FOREIGN KEY (subida_por) REFERENCES empleados(id)
) ENGINE=InnoDB;

-- Un albarán es una imagen que el modelo ya ha leído. Se guarda la respuesta entera para poder
-- auditar después qué dijo exactamente el modelo, no solo lo que aceptó la persona.
CREATE TABLE IF NOT EXISTS albaranes (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  imagen_id    INT NOT NULL,
  proveedor    VARCHAR(80)  NULL,
  numero       VARCHAR(40)  NULL,
  fecha        DATE NULL,
  total_cent   INT NULL,                      -- lo que DICE el papel; el cuadre lo calcula el código
  estado       ENUM('analizando','revisar','aplicado','descartado') NOT NULL DEFAULT 'analizando',
  modelo       VARCHAR(80)  NULL,
  ms           INT NULL,                      -- lo que tardó el modelo, para saber qué cuesta
  respuesta    JSON NULL,                     -- la salida cruda del modelo, tal cual
  error        VARCHAR(200) NULL,
  creado_por   INT NOT NULL,
  creado_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  aplicado_por INT NULL,
  aplicado_en  DATETIME NULL,
  UNIQUE KEY uq_imagen (imagen_id),
  FOREIGN KEY (imagen_id)    REFERENCES imagenes(id),
  FOREIGN KEY (creado_por)   REFERENCES empleados(id),
  FOREIGN KEY (aplicado_por) REFERENCES empleados(id),
  KEY ix_estado (estado, creado_en)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS albaran_lineas (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  albaran_id    INT NOT NULL,
  descripcion   VARCHAR(160) NOT NULL,        -- lo que pone el papel, transcrito tal cual
  cantidad      DECIMAL(10,2) NOT NULL DEFAULT 1,
  unidad        VARCHAR(12) NULL,
  precio_cent   INT NULL,
  importe_cent  INT NULL,
  inventario_id INT NULL,                     -- con qué artículo del almacén casa
  confianza     TINYINT NULL,                 -- 0-100: cuánto se parece el nombre
  aceptada      BOOLEAN NOT NULL DEFAULT TRUE,
  FOREIGN KEY (albaran_id)    REFERENCES albaranes(id) ON DELETE CASCADE,
  FOREIGN KEY (inventario_id) REFERENCES inventario(id)
) ENGINE=InnoDB;

-- Todo lo que entra y sale del almacén deja rastro: sin esto, el stock es un número sin historia.
CREATE TABLE IF NOT EXISTS movimientos_inventario (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  inventario_id INT NOT NULL,
  cantidad      DECIMAL(10,2) NOT NULL,       -- positiva entra, negativa sale
  motivo        ENUM('albaran','merma','ajuste','consumo','recuento') NOT NULL,
  albaran_id    INT NULL,
  nota          VARCHAR(160) NULL,
  empleado_id   INT NOT NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (inventario_id) REFERENCES inventario(id),
  FOREIGN KEY (albaran_id)    REFERENCES albaranes(id),
  FOREIGN KEY (empleado_id)   REFERENCES empleados(id),
  KEY ix_articulo (inventario_id, creado_en)
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('vision_url',    'http://192.168.1.69:1234/v1'),
 ('vision_modelo', 'google/gemma-4-12b-qat'),
 ('vision_activa', 'si');
