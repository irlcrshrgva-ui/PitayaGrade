const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const port = Number(process.env.REVIEW_PORT || 4174);
const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8',
  '.js':'text/javascript; charset=utf-8', '.json':'application/json; charset=utf-8',
  '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.webp':'image/webp' };

function allowed(relative) {
  return relative === 'review-tool/index.html' || relative.startsWith('review-tool/') ||
    relative === 'research/public-review-manifest.json' ||
    (/^dataset\/public\/prepared\//.test(relative) && /\.(jpe?g|png|webp)$/i.test(relative));
}
function isInside(file, directory) {
  return file.startsWith(directory + path.sep);
}
function resolveRequestPath(url) {
  let pathname;
  try { pathname = decodeURIComponent(new URL(url, 'http://127.0.0.1').pathname); }
  catch { return null; }
  if (pathname === '/') pathname = '/review-tool/index.html';
  const relative = pathname.replace(/^\/+/, '').replace(/\\/g, '/');
  if (!allowed(relative)) return null;
  const file = path.resolve(root, relative);
  const reviewRoot = path.join(root, 'review-tool');
  const preparedRoot = path.join(root, 'dataset', 'public', 'prepared');
  const manifest = path.join(root, 'research', 'public-review-manifest.json');
  if (relative.startsWith('review-tool/')) return isInside(file, reviewRoot) ? file : null;
  if (relative.startsWith('dataset/public/prepared/')) return isInside(file, preparedRoot) ? file : null;
  return file === manifest ? file : null;
}
function handler(request, response) {
  if (!['GET','HEAD'].includes(request.method)) { response.writeHead(405); return response.end(); }
  const file = resolveRequestPath(request.url);
  if (!file || !fs.existsSync(file) || !fs.statSync(file).isFile()) { response.writeHead(404); return response.end('Not found'); }
  response.writeHead(200, { 'Content-Type':types[path.extname(file).toLowerCase()] || 'application/octet-stream',
    'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff' });
  if (request.method === 'HEAD') return response.end();
  fs.createReadStream(file).pipe(response);
}
module.exports = { allowed, resolveRequestPath, handler };
if (require.main === module) http.createServer(handler).listen(port, '127.0.0.1', () =>
  console.log(`PitayaGrade Review Desk: http://127.0.0.1:${port}`));
