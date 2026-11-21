const CACHE_NAME='flex-zone-shell-v2';
const SHELL=['./gallery.html','./shop.html','./flex-zone-app-icon.svg?v=red-logo-1'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('flex-zone-shell-')&&key!==CACHE_NAME).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  if(event.request.mode!=='navigate')return;
  event.respondWith(fetch(event.request).catch(async()=>{
    const cache=await caches.open(CACHE_NAME);
    return await cache.match(event.request,{ignoreSearch:true})||await cache.match('./gallery.html')||Response.error();
  }));
});
