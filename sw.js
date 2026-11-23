const CACHE_NAME='flex-zone-shell-v3-fixed-gallery';
const SHELL=['./gallery.html','./shop.html','./flex-zone-app-icon.svg?v=red-logo-1'];
self.addEventListener('install',event=>{
  event.waitUntil(
    caches.open(CACHE_NAME).then(async cache=>{
      for(const path of SHELL){
        try{
          const request=new Request(path,{cache:'reload'});
          const response=await fetch(request);
          if(response.ok) await cache.put(path,response);
        }catch(e){}
      }
    }).then(()=>self.skipWaiting())
  );
});
self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('flex-zone-shell-')&&key!==CACHE_NAME).map(key=>caches.delete(key))))
    .then(()=>self.clients.claim())
  );
});
self.addEventListener('fetch',event=>{
  if(event.request.mode!=='navigate')return;
  event.respondWith((async()=>{
    try{
      const response=await fetch(new Request(event.request,{cache:'no-store'}));
      if(response.ok){
        const cache=await caches.open(CACHE_NAME);
        cache.put(event.request,response.clone()).catch(()=>{});
      }
      return response;
    }catch(e){
      const cache=await caches.open(CACHE_NAME);
      return (await cache.match(event.request,{ignoreSearch:true}))||
             (await cache.match('./gallery.html'))||Response.error();
    }
  })());
});
