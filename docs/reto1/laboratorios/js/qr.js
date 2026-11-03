// Generador de códigos QR (ISO/IEC 18004) sin dependencias, para el QR tributario de Verifactu:
// modo byte (UTF-8), nivel de corrección M (artículo 21 de la Orden HAC/1177/2024), versiones 1 a 40 y
// máscara elegida por penalización. QR.matriz(texto) devuelve la matriz de módulos (true = oscuro) y
// QR.svg(texto) un <svg> con 4 módulos de margen, que se refleja en la vista del público (un <canvas> no).
'use strict';
const QR = (() => {
  // Por versión (índice 1 a 40), nivel M: códigos de corrección por bloque y número de bloques.
  const ECC_M = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28];
  const BLQ_M = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49];
  const bit = (x, i) => ((x >>> i) & 1) !== 0;
  const modulosDatos = v => {               // módulos disponibles para datos y corrección
    let r = (16 * v + 128) * v + 64;
    if (v >= 2) { const n = Math.floor(v / 7) + 2; r -= (25 * n - 10) * n - 55; if (v >= 7) r -= 36; }
    return r;
  };
  const palabrasDatos = v => Math.floor(modulosDatos(v) / 8) - ECC_M[v] * BLQ_M[v];
  // Aritmética en GF(256) con el polinomio 0x11D y Reed-Solomon.
  const mul = (x, y) => { let z = 0; for (let i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((y >>> i) & 1) * x; } return z & 0xFF; };
  function divisor(grado) {
    const r = new Array(grado).fill(0); r[grado - 1] = 1; let raiz = 1;
    for (let i = 0; i < grado; i++) {
      for (let j = 0; j < r.length; j++) { r[j] = mul(r[j], raiz); if (j + 1 < r.length) r[j] ^= r[j + 1]; }
      raiz = mul(raiz, 0x02);
    }
    return r;
  }
  function resto(datos, div) {
    const r = div.map(() => 0);
    for (const b of datos) { const f = b ^ r.shift(); r.push(0); div.forEach((c, i) => { r[i] ^= mul(c, f); }); }
    return r;
  }

  function matriz(texto, mascaraFija) {
    const bytes = [...new TextEncoder().encode(texto)];
    let v = 1;
    for (; v <= 40; v++) if (4 + (v < 10 ? 8 : 16) + bytes.length * 8 <= palabrasDatos(v) * 8) break;
    if (v > 40) throw new Error('Texto demasiado largo para un QR');
    // Flujo de bits: modo byte (0100), longitud, datos, terminador y relleno 0xEC 0x11.
    const bits = [], pon = (val, n) => { for (let i = n - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
    pon(4, 4); pon(bytes.length, v < 10 ? 8 : 16); bytes.forEach(b => pon(b, 8));
    const cap = palabrasDatos(v) * 8;
    pon(0, Math.min(4, cap - bits.length)); pon(0, (8 - bits.length % 8) % 8);
    for (let p = 0xEC; bits.length < cap; p ^= 0xEC ^ 0x11) pon(p, 8);
    const datos = []; for (let i = 0; i < bits.length; i += 8) datos.push(bits.slice(i, i + 8).reduce((a, b) => a * 2 + b, 0));
    // Bloques con su corrección, intercalados.
    const nb = BLQ_M[v], ecc = ECC_M[v], brutas = Math.floor(modulosDatos(v) / 8);
    const cortos = nb - brutas % nb, largoCorto = Math.floor(brutas / nb), div = divisor(ecc), bloques = [];
    for (let i = 0, k = 0; i < nb; i++) {
      const d = datos.slice(k, k + largoCorto - ecc + (i < cortos ? 0 : 1)); k += d.length;
      const e = resto(d, div); if (i < cortos) d.push(0); bloques.push(d.concat(e));
    }
    const final = [];
    for (let i = 0; i < bloques[0].length; i++) bloques.forEach((b, j) => { if (i !== largoCorto - ecc || j >= cortos) final.push(b[i]); });

    // Patrones fijos.
    const n = v * 4 + 17, M = [...Array(n)].map(() => Array(n).fill(false)), F = [...Array(n)].map(() => Array(n).fill(false));
    const fija = (x, y, osc) => { M[y][x] = osc; F[y][x] = true; };
    for (let i = 0; i < n; i++) { fija(6, i, i % 2 === 0); fija(i, 6, i % 2 === 0); }
    for (const [cx, cy] of [[3, 3], [n - 4, 3], [3, n - 4]])
      for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
        const d = Math.max(Math.abs(dx), Math.abs(dy)), x = cx + dx, y = cy + dy;
        if (x >= 0 && x < n && y >= 0 && y < n) fija(x, y, d !== 2 && d !== 4);
      }
    if (v > 1) {
      const na = Math.floor(v / 7) + 2, paso = Math.floor((v * 8 + na * 3 + 5) / (na * 4 - 4)) * 2, pos = [6];
      for (let p = n - 7; pos.length < na; p -= paso) pos.splice(1, 0, p);
      pos.forEach((x, i) => pos.forEach((y, j) => {
        if ((i === 0 && j === 0) || (i === 0 && j === na - 1) || (i === na - 1 && j === 0)) return;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) fija(x + dx, y + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
      }));
    }
    const formato = mascara => {               // nivel M = 00, más la máscara
      const d = (0 << 3) | mascara; let r = d;
      for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537);
      const b = ((d << 10) | r) ^ 0x5412;
      for (let i = 0; i <= 5; i++) fija(8, i, bit(b, i));
      fija(8, 7, bit(b, 6)); fija(8, 8, bit(b, 7)); fija(7, 8, bit(b, 8));
      for (let i = 9; i < 15; i++) fija(14 - i, 8, bit(b, i));
      for (let i = 0; i < 8; i++) fija(n - 1 - i, 8, bit(b, i));
      for (let i = 8; i < 15; i++) fija(8, n - 15 + i, bit(b, i));
      fija(8, n - 8, true);
    };
    formato(0);
    if (v >= 7) {
      let r = v; for (let i = 0; i < 12; i++) r = (r << 1) ^ ((r >>> 11) * 0x1F25);
      const b = (v << 12) | r;
      for (let i = 0; i < 18; i++) { const a = n - 11 + i % 3, c = Math.floor(i / 3); fija(a, c, bit(b, i)); fija(c, a, bit(b, i)); }
    }
    // Datos en zigzag desde la esquina inferior derecha.
    let i = 0;
    for (let der = n - 1; der >= 1; der -= 2) {
      if (der === 6) der = 5;
      for (let vert = 0; vert < n; vert++) for (let j = 0; j < 2; j++) {
        const x = der - j, sube = ((der + 1) & 2) === 0, y = sube ? n - 1 - vert : vert;
        if (!F[y][x] && i < final.length * 8) { M[y][x] = bit(final[i >>> 3], 7 - (i & 7)); i++; }
      }
    }
    // Máscara: se prueban las ocho y se queda la de menor penalización.
    const invierte = (m, x, y) => [(x + y) % 2, y % 2, x % 3, (x + y) % 3, (Math.floor(x / 3) + Math.floor(y / 2)) % 2,
      x * y % 2 + x * y % 3, (x * y % 2 + x * y % 3) % 2, ((x + y) % 2 + x * y % 3) % 2][m] === 0;
    const enmascara = m => { for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (!F[y][x] && invierte(m, x, y)) M[y][x] = !M[y][x]; };
    let mejor = 0, pena = Infinity;
    for (let m = 0; m < 8; m++) {
      if (mascaraFija !== undefined && m !== mascaraFija) continue;
      enmascara(m); formato(m);
      const p = penalizacion(M, n); if (p < pena) { pena = p; mejor = m; }
      enmascara(m);
    }
    enmascara(mejor); formato(mejor);
    return M;
  }
  function penalizacion(M, n) {
    let p = 0, oscuros = 0;
    const lineas = []; for (let a = 0; a < n; a++) { lineas.push(M[a]); lineas.push(M.map(f => f[a])); }
    for (const l of lineas) {                  // reglas 1 (rachas de 5 o más) y 3 (1:1:3:1:1 con margen claro)
      let racha = 1;
      for (let k = 1; k <= n; k++) {
        if (k < n && l[k] === l[k - 1]) racha++;
        else { if (racha >= 5) p += racha - 2; racha = 1; }
      }
      const s = '0000' + l.map(b => b ? '1' : '0').join('') + '0000';   // fuera del símbolo todo es claro
      for (const pat of ['10111010000', '00001011101']) for (let k = s.indexOf(pat); k >= 0; k = s.indexOf(pat, k + 1)) p += 40;
    }
    for (let y = 0; y < n - 1; y++) for (let x = 0; x < n - 1; x++) {   // regla 2 (bloques 2×2)
      const c = M[y][x]; if (c === M[y][x + 1] && c === M[y + 1][x] && c === M[y + 1][x + 1]) p += 3;
    }
    M.forEach(f => f.forEach(b => { if (b) oscuros++; }));             // regla 4 (equilibrio de oscuros)
    return p + Math.max(0, Math.ceil(Math.abs(oscuros * 20 - n * n * 10) / (n * n)) - 1) * 10;
  }
  function svg(texto) {
    const M = matriz(texto), n = M.length, m = 4; let d = '';
    M.forEach((f, y) => f.forEach((b, x) => { if (b) d += `M${x + m} ${y + m}h1v1h-1z`; }));
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${n + 2 * m} ${n + 2 * m}" shape-rendering="crispEdges" role="img" aria-label="Código QR"><rect width="100%" height="100%" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
  }
  return { matriz, svg };
})();
if (typeof module !== 'undefined') module.exports = QR;
