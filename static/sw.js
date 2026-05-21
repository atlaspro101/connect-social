// Service Worker для Push-уведомлений
const CACHE_NAME = 'connect-v1';
const PUSH_ENDPOINT = '/api/push/subscribe';

self.addEventListener('install', (event) => {
    console.log('[SW] Установлен');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[SW] Активирован');
    event.waitUntil(clients.claim());
});

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Connect';
    const options = {
        body: data.body || 'Новое уведомление',
        icon: '/static/favicon.png',
        badge: '/static/favicon.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/',
            id: data.id
        }
    };
    
    event.waitUntil(self.registration.showNotification(title, options));
});

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