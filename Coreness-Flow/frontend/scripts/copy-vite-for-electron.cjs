/**
 * Копирует build/vite в frontend/dist перед electron-builder (упаковщик берёт только пути внутри frontend).
 * Запускается из npm run electron:build. Единственная папка сборки фронта — build/vite.
 */

const fs = require('fs');
const path = require('path');

const frontendRoot = path.resolve(__dirname, '..');
const src = path.join(frontendRoot, '..', 'build', 'vite');
const dst = path.join(frontendRoot, 'dist');

if (!fs.existsSync(src)) {
  console.error('Нет папки build/vite. Сначала выполните npm run build.');
  process.exit(1);
}
fs.mkdirSync(dst, { recursive: true });
fs.cpSync(src, dst, { recursive: true });
