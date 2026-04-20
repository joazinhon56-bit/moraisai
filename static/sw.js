self.addEventListener('install', (e) => {
  console.log('Morais AI: Service Worker Instalado');
});

self.addEventListener('fetch', (e) => {
  // Mantém a app a funcionar online
  e.respondWith(fetch(e.request));
});