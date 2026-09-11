// Preview the earlier SVG trace without overwriting the user-edited app icon.
// Requires Node.js and sharp. NODE_PATH may point at a bundled installation.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'assets', 'shinka.svg');
const destination = process.argv[2] || path.join(root, 'output', 'icon-touchup', 'shinka-vector-preview.png');

(async () => {
  fs.mkdirSync(path.dirname(path.resolve(destination)), { recursive: true });
  await sharp(source, { density: 192 }).resize(1024, 1024).png().toFile(destination);
  const meta = await sharp(destination).metadata();
  if (!meta.hasAlpha || meta.width !== 1024 || meta.height !== 1024)
    throw new Error('Icon must be a square RGBA image');
  console.log(`Rendered ${destination} (${meta.width} x ${meta.height}, alpha)`);
})().catch(error => { console.error(error); process.exitCode = 1; });
