-- Ampliación 3: carta editable desde la aplicación y cuentas divididas / pago mixto.
-- Aplicable sobre una BD en uso.
SET NAMES utf8mb4;

-- ── Carta ──────────────────────────────────────────────────────────────────
-- 'activo'     = el producto existe en la carta (baja lógica).
-- 'disponible' = hoy no queda (agotado); sigue en la carta pero no se puede pedir.
ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS disponible BOOLEAN NOT NULL DEFAULT TRUE AFTER activo,
  ADD COLUMN IF NOT EXISTS orden TINYINT NOT NULL DEFAULT 0 AFTER disponible,
  ADD COLUMN IF NOT EXISTS alergenos VARCHAR(120) NULL AFTER orden;

ALTER TABLE categorias
  ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT TRUE;

-- ── Pagos parciales ────────────────────────────────────────────────────────
-- Un pedido puede tener varios pagos (mitad tarjeta, mitad efectivo, o uno por comensal).
-- Cuando una línea se paga con un pago concreto, queda enganchada a él.
ALTER TABLE lineas_pedido
  ADD COLUMN IF NOT EXISTS pago_id INT NULL AFTER estado,
  ADD CONSTRAINT fk_linea_pago FOREIGN KEY IF NOT EXISTS (pago_id) REFERENCES pagos(id) ON DELETE SET NULL;

ALTER TABLE pagos
  ADD COLUMN IF NOT EXISTS concepto VARCHAR(60) NULL AFTER metodo;
