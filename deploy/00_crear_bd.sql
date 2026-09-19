-- Ejecutar UNA vez como administrador de MariaDB:
--   sudo mariadb < deploy/00_crear_bd.sql
-- El usuario 'kds' entra por socket Unix (sin contraseña) solo si el usuario del sistema
-- se llama igual; aquí damos acceso al usuario del sistema 'roca' (el que corre el servicio).
CREATE DATABASE IF NOT EXISTS kds_tpv CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;
GRANT ALL PRIVILEGES ON kds_tpv.* TO 'roca'@'localhost';
FLUSH PRIVILEGES;
