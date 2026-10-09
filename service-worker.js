const CACHE_NAME = 'pitayagrade-web-2026-10-09-3';
const BASE_URL = new URL('./', self.location.href);
const localUrl = path => new URL(path, BASE_URL).href;

const APP_SHELL = [
  './',
  'index.html',
  'manifest.webmanifest',
  'assets/logo.png',
  'css/styles.css',
  'ort.min.js',
  'ort-wasm-simd-threaded.mjs',
  'js/storage.js',
  'js/language.js',
  'js/notifications.js',
  'js/model-registry.js',
  'js/model-inference.js',
  'js/scanner.js',
  'js/live-scanner.js',
  'js/dashboard.js',
  'js/history.js',
  'js/reports.js',
  'js/app.js'
].map(localUrl);

const LARGE_RUNTIME_PATHS = [
  '/model/best.onnx',
  '/ort-wasm-simd-threaded.wasm'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(names
        .filter(name => name.startsWith('pitayagrade-web-') && name !== CACHE_NAME)
        .map(name => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (error) {
    return (await cache.match(request)) || cache.match(localUrl('index.html'));
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const network = fetch(request).then(async response => {
    if (response.ok) await cache.put(request, response.clone());
    return response;
  }).catch(() => null);
  if (cached) return cached;
  const response = await network;
  if (response) return response;
  throw new Error('Resource is unavailable offline and has not been cached.');
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE_URL.pathname)) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
    return;
  }
  if (LARGE_RUNTIME_PATHS.some(path => url.pathname.endsWith(path))) {
    event.respondWith(cacheFirst(request));
    return;
  }
  event.respondWith(staleWhileRevalidate(request));
});
