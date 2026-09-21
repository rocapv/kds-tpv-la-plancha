-- Se invierte la escala de los escalafones: 1 es el de más mando.
--
-- Con el orden anterior (1 = el más bajo) cada escalafón nuevo por abajo obligaba a renumerar
-- todo lo de arriba. Con 1 = administrador, la empresa crece por donde crece de verdad —por la
-- base— y basta con seguir contando: 6, 7, 8… sin tocar una sola fila existente. Y deja hueco
-- en medio (se puede meter un 2.5 renumerando solo un tramo, no la tabla entera).
--
-- Regla desde aquí: **a MENOR número, más mando**. `nivel <= 2` es gerencia.
SET NAMES utf8mb4;

UPDATE escalafones SET nivel = 1 WHERE clave = 'admin';
UPDATE escalafones SET nivel = 2 WHERE clave = 'gerente';
UPDATE escalafones SET nivel = 3 WHERE clave = 'encargado';
UPDATE escalafones SET nivel = 4 WHERE clave = 'base';
UPDATE escalafones SET nivel = 5 WHERE clave = 'base_junior';
