/* Serve the packaged app locally with explicit module/WASM MIME types. */
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const root = path.resolve(__dirname, '..', 'www');
require('./verify-runtime').verifyRuntime(root);
const port = Number(process.env.PORT || 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid PORT');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.wasm': 'application/wasm', '.onnx': 'application/octet-stream', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2' };

function inside(file) {
  const relative = path.relative(root, file);
  return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
}

http.createServer(async (request, response) => {
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }); response.end(); return;
  }
  let filename;
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    filename = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  } catch {
    response.writeHead(400); response.end('Invalid path'); return;
  }
  if (!inside(filename)) { response.writeHead(403); response.end(); return; }
  try {
    filename = await fs.realpath(filename);
    if (!inside(filename)) { response.writeHead(403); response.end(); return; }
    const data = await fs.readFile(filename);
    response.writeHead(200, { 'Content-Type': types[path.extname(filename)] || 'application/octet-stream',
      'Content-Length': data.length });
    response.end(request.method === 'HEAD' ? undefined : data);
  } catch {
    response.writeHead(404); response.end('Not found');
  }
}).listen(port, '127.0.0.1', () => console.log(`PitayaGrade: http://127.0.0.1:${port}`));
