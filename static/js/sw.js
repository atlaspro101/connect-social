// Service Worker для PWA
const CACHE_NAME = 'connect-v2';
const STATIC_CACHE = 'connect-static-v2';
const DYNAMIC_CACHE = 'connect-dynamic-v2';

// Файлы для кэширования
const STATIC_FILES = [
    '/',
    '/static/css/style.css',
    '/static/css/mobile.css',
    '/static/js/main.js',
    '/static/favicon.png',
    '/static/icons/icon-72.png',
    '/static/icons/icon-96.png',
    '/static/icons/icon-128.png',
    '/static/icons/icon-144.png',
    '/static/icons/icon-152.png',
    '/static/icons/icon-192.png',
    '/static/icons/icon-384.png',
    '/static/icons/icon-512.png',
    '/offline.html'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
    console.log('[SW] Установка...');
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            console.log('[SW] Кэширование статики');
            return cache.addAll(STATIC_FILES);
        })
    );
    self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
    console.log('[SW] Активация...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                        console.log('[SW] Удаление старого кэша:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Обработка fetch запросов
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // API запросы не кэшируем
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }
    
    // Статические файлы
    if (STATIC_FILES.includes(url.pathname)) {
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request);
            })
        );
        return;
    }
    
    // Страницы и другие запросы - стратегия "сначала сеть"
    event.respondWith(
        fetch(event.request).then((response) => {
            // Кэшируем успешные ответы
            if (response && response.status === 200) {
                const responseClone = response.clone();
                caches.open(DYNAMIC_CACHE).then((cache) => {
                    cache.put(event.request, responseClone);
                });
            }
            return response;
        }).catch(() => {
            // Если сеть недоступна, возвращаем офлайн страницу
            return caches.match('/offline.html');
        })
    );
});

// Push уведомления
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Connect';
    const options = {
        body: data.body || 'Новое уведомление',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-96.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/',
            id: data.id
        }
    };
    
    event.waitUntil(self.registration.showNotification(title, options));
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const urlToOpen = event.notification.data?.url || '/';
    event.waitUntil(
        clients.matchAll({type: 'window', includeUncontrolled: true})
            .then(windowClients => {
                for (let client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});