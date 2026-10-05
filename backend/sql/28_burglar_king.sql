-- La empresa pasa de llamarse «La Plancha» a «Burglar King». El nombre que enseña la app ya es el del
-- tema (`local_nombre` = «Cantina Vesta-9», 07_tema_asteroide.sql), así que aquí solo se cambia el
-- correo de las facturas. Condicionado al valor de fábrica: si alguien lo cambió a mano, se respeta.
UPDATE ajustes SET valor = 'facturas@burglarking.example'
 WHERE clave = 'local_email' AND valor = 'facturas@laplancha.example';
