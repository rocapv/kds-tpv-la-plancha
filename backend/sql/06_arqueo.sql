-- Ampliación 5: arqueo de caja y cierre Z.
-- El informe enseña lo vendido; el arqueo enseña el descuadre: cuánto debería haber en el
-- cajón y cuánto hay de verdad. Aplicable sobre una BD en uso (no borra nada).
SET NAMES utf8mb4;

-- Un arqueo por día de servicio. Se abre declarando el fondo de cambio y se cierra
-- contando el efectivo; al cerrar recibe número Z correlativo y queda firmado.
CREATE TABLE IF NOT EXISTS arqueos (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  fecha             DATE NOT NULL,
  estado            ENUM('abierto','cerrado') NOT NULL DEFAULT 'abierto',
  fondo_cent        INT  NOT NULL DEFAULT 0,        -- cambio con el que se empieza
  abierto_por       INT  NOT NULL,
  abierto_en        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Lo de abajo se rellena en el cierre
  z_ejercicio       SMALLINT NULL,
  z_numero          INT      NULL,
  contado_cent      INT  NULL,                      -- efectivo contado en el cajón
  esperado_cent     INT  NULL,                      -- fondo + ventas efectivo + entradas - salidas
  diferencia_cent   INT  NULL,                      -- contado - esperado (negativo = falta)
  ventas_efectivo_cent INT NULL,
  ventas_total_cent INT  NULL,
  tickets           INT  NULL,
  retirada_cent     INT  NULL DEFAULT 0,            -- lo que se saca al banco / caja fuerte
  recuento          VARCHAR(400) NULL,              -- desglose por billetes y monedas (JSON)
  notas             VARCHAR(200) NULL,
  cerrado_por       INT  NULL,
  cerrado_en        DATETIME NULL,
  UNIQUE KEY uq_fecha (fecha),
  UNIQUE KEY uq_z (z_ejercicio, z_numero),
  FOREIGN KEY (abierto_por) REFERENCES empleados(id),
  FOREIGN KEY (cerrado_por) REFERENCES empleados(id)
) ENGINE=InnoDB;

-- Entradas y salidas de efectivo que no son ventas: pagar al del pan, sacar para el banco,
-- reponer cambio. Sin esto el descuadre miente.
CREATE TABLE IF NOT EXISTS movimientos_caja (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  arqueo_id    INT NOT NULL,
  tipo         ENUM('entrada','salida') NOT NULL,
  importe_cent INT NOT NULL CHECK (importe_cent > 0),
  motivo       VARCHAR(80) NOT NULL,
  empleado_id  INT NOT NULL,
  creado_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (arqueo_id)   REFERENCES arqueos(id) ON DELETE CASCADE,
  FOREIGN KEY (empleado_id) REFERENCES empleados(id),
  KEY ix_arqueo (arqueo_id)
) ENGINE=InnoDB;

-- Fondo de cambio propuesto al abrir el día siguiente.
INSERT IGNORE INTO ajustes (clave, valor) VALUES ('fondo_caja_cent', '15000');
