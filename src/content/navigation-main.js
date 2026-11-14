/* Open YouTube routes through the native SPA router instead of loading a new
   document, so the current page stays on screen until the next one is ready. */
(() => {
    'use strict';
    if(globalThis.__minimalYouTubeNavigation)return;
    globalThis.__minimalYouTubeNavigation=true;
    const config=name=>globalThis.ytcfg?.get?.(name)??globalThis.ytcfg?.data_?.[name];
    const channelPath=/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/;
    let active=null;
    function route(target){
        // The current WEB client already runs in English; language overrides
        // belong to real document loads only.
        const url=new URL(target.href);url.searchParams.delete('hl');url.searchParams.delete('persist_hl');
        return url;
    }
    const path=url=>url.pathname+url.search+url.hash;
    function direct(url){
        if(url.pathname==='/watch'){
            const videoId=url.searchParams.get('v');if(!/^[\w-]{6,20}$/.test(videoId||''))return null;
            const watchEndpoint={videoId};
            const list=url.searchParams.get('list');if(list&&/^[\w-]+$/.test(list))watchEndpoint.playlistId=list;
            const index=Number(url.searchParams.get('index'));if(Number.isSafeInteger(index)&&index>0)watchEndpoint.index=index-1;
            const time=url.searchParams.get('t')?.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);
            if(time){const seconds=(+time[1]||0)*3600+(+time[2]||0)*60+(+time[3]||0);if(seconds>0)watchEndpoint.startTimeSeconds=seconds;}
            return {watchEndpoint,commandMetadata:{webCommandMetadata:{url:path(url),webPageType:'WEB_PAGE_TYPE_WATCH',rootVe:3832}}};
        }
        if(url.pathname==='/results'){
            const query=url.searchParams.get('search_query')||url.searchParams.get('q')||'';if(!query.trim())return null;
            const searchEndpoint={query};const params=url.searchParams.get('sp');if(params)searchEndpoint.params=params;
            return {searchEndpoint,commandMetadata:{webCommandMetadata:{url:path(url),webPageType:'WEB_PAGE_TYPE_SEARCH',rootVe:4724}}};
        }
        return null;
    }
    async function resolve(url,state){
        const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{};
        const version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
        if(typeof version!=='string'||!version)throw new Error('Missing client');
        const api=new URL('/youtubei/v1/navigation/resolve_url',location.origin);api.searchParams.set('prettyPrint','false');
        const key=config('INNERTUBE_API_KEY');if(typeof key==='string'&&key)api.searchParams.set('key',key);
        const timeout=setTimeout(()=>state.controller.abort(),4000);
        let result;
        try{
            const response=await fetch(api.href,{method:'POST',credentials:'same-origin',signal:state.controller.signal,headers:{'Content-Type':'application/json'},
                body:JSON.stringify({url:url.href,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version}}})});
            if(!response.ok)throw new Error('Resolution failed');
            result=await response.json();
        }finally{clearTimeout(timeout);}
        const command=result?.endpoint?.innertubeCommand||result?.endpoint;
        const metadata=command?.commandMetadata?.webCommandMetadata;
        if(!command||typeof command!=='object'||!metadata)throw new Error('Missing endpoint');
        const resolved=new URL(metadata.url||'',location.origin);
        // Only accept a command for the same kind of page; never follow an
        // external URL endpoint or a generic fallback in place of the target.
        if(resolved.origin!==location.origin||command.urlEndpoint)throw new Error('Unexpected endpoint');
        if(!(command.browseEndpoint||command.watchEndpoint||command.searchEndpoint))throw new Error('Unexpected endpoint');
        if(channelPath.test(url.pathname)&&!/^UC[\w-]+$/.test(command.browseEndpoint?.browseId||''))throw new Error('Unexpected endpoint');
        const endpoint=JSON.parse(JSON.stringify(command));
        endpoint.commandMetadata.webCommandMetadata.url=path(url);
        return endpoint;
    }
    function report(id,started){
        const root=document.documentElement;
        root.setAttribute('data-myt-navigate-result',JSON.stringify({id,started}));
        root.dispatchEvent(new Event('minimal-youtube:navigate-result',{bubbles:true}));
    }
    function dispatch(endpoint){
        const app=document.querySelector('ytd-app');if(!app)throw new Error('Missing app');
        app.dispatchEvent(new CustomEvent('yt-navigate',{bubbles:true,composed:true,cancelable:true,detail:{endpoint}}));
    }
    // No miniplayer: leaving a watch page stops the video and closes
    // YouTube's miniplayer (its CSS never shows it), so nothing keeps playing.
    function closeMiniplayer(){
        if(!document.documentElement.classList.contains('minimal-youtube')||location.pathname==='/watch')return;
        const app=document.querySelector('ytd-app'),mini=document.querySelector('ytd-miniplayer');
        if(!app?.hasAttribute('miniplayer-is-active')&&!mini?.hasAttribute('active'))return;
        try{document.querySelector('#movie_player')?.stopVideo?.();}catch{}
        for(const video of mini?.querySelectorAll('video')||[])video.pause();
        mini?.querySelector('.ytp-miniplayer-close-button,#close-button button,button#close-button')?.click();
    }
    // The browser's own picture-in-picture window (macOS opens one when a
    // playing video leaves the screen) is closed the same way: off a watch
    // page nothing keeps playing, and on a watch page the player is already
    // on the page, so a second window would only duplicate it.
    function closePictureInPicture(){
        if(!document.documentElement.classList.contains('minimal-youtube'))return;
        const video=document.pictureInPictureElement;if(!(video instanceof HTMLVideoElement))return;
        if(location.pathname!=='/watch'){try{document.querySelector('#movie_player')?.stopVideo?.();}catch{}video.pause();}
        document.exitPictureInPicture?.().catch(()=>{});
    }
    // Arc opens its own picture-in-picture window (not the page's, so it
    // cannot be closed from here) when a page changes its address while a
    // video plays. Leaving a watch page therefore pauses the video before
    // the address changes and forbids picture-in-picture until a watch page
    // shows again.
    let pipBlocked=null;
    function leaveWatch(){
        if(!document.documentElement.classList.contains('minimal-youtube'))return;
        const player=document.querySelector('#movie_player'),video=player?.querySelector('video')||document.querySelector('video.html5-main-video');
        try{player?.pauseVideo?.();}catch{}
        if(video instanceof HTMLVideoElement){video.pause();if(!video.disablePictureInPicture){video.disablePictureInPicture=true;pipBlocked=video;}}
    }
    function arriveWatch(){
        if(location.pathname!=='/watch'||!pipBlocked)return;
        pipBlocked.disablePictureInPicture=false;pipBlocked=null;
    }
    globalThis.navigation?.addEventListener?.('navigate',event=>{
        let target;try{target=new URL(event.destination.url);}catch{return;}
        if(location.pathname==='/watch'&&target.origin===location.origin&&target.pathname!=='/watch')leaveWatch();
    });
    document.addEventListener('yt-navigate-start',event=>{
        let target;try{target=new URL(event.detail?.url||'',location.href);}catch{return;}
        if(location.pathname==='/watch'&&event.detail?.url&&target.pathname!=='/watch')leaveWatch();
    });
    document.addEventListener('yt-navigate-finish',arriveWatch);
    window.addEventListener('popstate',()=>setTimeout(arriveWatch,0));
    document.addEventListener('enterpictureinpicture',()=>{if(location.pathname!=='/watch')closePictureInPicture();},true);
    document.addEventListener('yt-navigate-finish',closePictureInPicture);
    window.addEventListener('popstate',()=>setTimeout(closePictureInPicture,0));
    new MutationObserver(records=>{if(records.some(record=>record.target.localName==='ytd-app'||record.target.localName==='ytd-miniplayer'))closeMiniplayer();})
        .observe(document.documentElement,{subtree:true,attributes:true,attributeFilter:['miniplayer-is-active','active']});
    document.addEventListener('yt-navigate-finish',closeMiniplayer);
    document.addEventListener('minimal-youtube:navigate',()=>{
        const root=document.documentElement;
        let request;try{request=JSON.parse(root.getAttribute('data-myt-navigate-request')||'{}');}catch{return;}
        if(!Number.isSafeInteger(request.id)||typeof request.href!=='string'||request.href.length>4096)return;
        active?.controller.abort();active=null;
        try{
            const target=new URL(request.href,location.origin);
            if(target.origin!==location.origin||!root.classList.contains('minimal-youtube')||!document.querySelector('ytd-app'))throw new Error('Not routable');
            const url=route(target),endpoint=direct(url);
            if(endpoint){dispatch(endpoint);report(request.id,true);return;}
            const state={id:request.id,controller:new AbortController()};active=state;
            resolve(url,state).then(command=>{
                if(active!==state)return;active=null;
                dispatch(command);report(request.id,true);
            }).catch(()=>{if(active===state){active=null;report(request.id,false);}});
        }catch{report(request.id,false);}
    });
})();
