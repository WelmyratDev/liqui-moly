/* Liqui Moly service worker.
 * - /static/ files have a content hash in their name -> cache-first, kept forever.
 * - product/banner images (/media/) -> stale-while-revalidate.
 * - HTML pages, AJAX and POST requests are NOT intercepted (always fresh,
 *   CSRF tokens and cart state stay correct).
 */
const VERSION = "lm-v2";
const STATIC_CACHE = VERSION + "-static";
const MEDIA_CACHE = VERSION + "-media";
const MEDIA_LIMIT = 300;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

async function trim(cacheName, max) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    for (let i = 0; i < keys.length - max; i++) {
        await cache.delete(keys[i]);
    }
}

async function cacheFirst(request) {
    const cache = await caches.open(STATIC_CACHE);
    const hit = await cache.match(request);
    if (hit) return hit;
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
}

async function staleWhileRevalidate(event) {
    const cache = await caches.open(MEDIA_CACHE);
    const hit = await cache.match(event.request);
    const network = fetch(event.request).then((response) => {
        if (response.ok) {
            cache.put(event.request, response.clone()).then(() => trim(MEDIA_CACHE, MEDIA_LIMIT));
        }
        return response;
    });
    if (hit) {
        event.waitUntil(network.catch(() => {}));
        return hit;
    }
    return network;
}

self.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") return;

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    if (url.pathname.startsWith("/static/")) {
        event.respondWith(cacheFirst(request));
    } else if (url.pathname.startsWith("/media/")) {
        event.respondWith(staleWhileRevalidate(event));
    }
    // everything else: browser default (network)
});
