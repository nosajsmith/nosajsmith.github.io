// ui/src/lib/hex.js
// Pointy-top axial hex math (q,r) <-> pixel (x,y)
// Includes backwards-compatible exports used by HexGrid and MapCanvas

// ===============================
// Axial -> Pixel
// ===============================
export function axialToPixel(q, r, size) {
  const x = size * Math.sqrt(3) * (q + r / 2);
  const y = size * (3 / 2) * r;
  return { x, y };
}

// Backwards compatibility alias
export function hexToPixel(q, r, size) {
  return axialToPixel(q, r, size);
}

// ===============================
// Pixel -> Axial (fractional)
// ===============================
export function pixelToAxial(px, py, size) {
  const q = (Math.sqrt(3) / 3 * px - 1 / 3 * py) / size;
  const r = (2 / 3 * py) / size;
  return { q, r };
}

// ===============================
// Axial rounding helpers
// ===============================
function cubeRound(x, y, z) {
  let rx = Math.round(x);
  let ry = Math.round(y);
  let rz = Math.round(z);

  const xDiff = Math.abs(rx - x);
  const yDiff = Math.abs(ry - y);
  const zDiff = Math.abs(rz - z);

  if (xDiff > yDiff && xDiff > zDiff) {
    rx = -ry - rz;
  } else if (yDiff > zDiff) {
    ry = -rx - rz;
  } else {
    rz = -rx - ry;
  }

  return { x: rx, y: ry, z: rz };
}

export function axialRound(q, r) {
  const x = q;
  const z = r;
  const y = -x - z;
  const cr = cubeRound(x, y, z);
  return { q: cr.x, r: cr.z };
}

// ===============================
// Hex polygon (USED BY HexGrid)
// ===============================
// Returns SVG points string: "x1,y1 x2,y2 ..."
export function hexPolygonPoints(cx, cy, size) {
  const points = [];

  // Pointy-top hex: start at -30°
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    const x = cx + size * Math.cos(angle);
    const y = cy + size * Math.sin(angle);
    points.push(`${x},${y}`);
  }

  return points.join(" ");
}
