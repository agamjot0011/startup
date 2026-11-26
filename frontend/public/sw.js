/*
 * WZDM LiveRecord service worker — zero-PHI offline policy.
 * Caches only static first-party assets. It never caches API responses,
 * patient data, session tokens, or any URL containing identifiers.
 */
const CACHE = 'wzdm-static-v1'
const STATIC_PATHS = [
  '/',
  '/index.html',
  '/favicon.svg',
  '/icons.svg',
  '/manifest.webmanifest',
  '/safe-route.html',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(STATIC_PATHS)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

function isStatic(request) {
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return false
  if (url.pathname.startsWith('/v1/') || url.pathname.startsWith('/api/')) return false
  if (url.search) return false
  return (
    url.pathname === '/' ||
    STATIC_PATHS.includes(url.pathname) ||
    /\.(?:js|css|svg|woff2?|png|ico)$/.test(url.pathname)
  )
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  if (!isStatic(event.request)) return
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached
      return fetch(event.request).then((response) => {
        if (response.ok && response.type === 'basic') {
          const copy = response.clone()
          caches.open(CACHE).then((cache) => cache.put(event.request, copy))
        }
        return response
      })
    })
  )
})
