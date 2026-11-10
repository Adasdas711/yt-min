/* Keep the current page on screen during navigation: own links and searches
   open through YouTube's SPA router (see navigation-main.js), with a regular
   document load only as a fallback. */
(() => {
    'use strict';
    if(globalThis.MinimalYouTubeNavigation)return;
    const channelBase=/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))(?:\/(?:featured)?)?\/?$/;
    const channelPath=/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/;
    const ownHost='[id^="myt-"],[data-myt-owned-playlist-card],[data-myt-search-channel-card]';
    let sequence=0,pending=null;
    // Channel homes open on Videos. Route there directly, so no second
    // document load replaces the channel home after it arrives.
    function landing(url){
        const match=url.pathname.match(channelBase);if(!match)return url;
        const target=new URL(url);target.pathname=match[1]+'/videos';return target;
    }
    function routable(url){
        if(url.origin!==location.origin)return false;
        if(url.pathname==='/')return true;
        if(url.pathname==='/watch')return Boolean(url.searchParams.get('v'));
        if(url.pathname==='/results')return Boolean((url.searchParams.get('search_query')||'').trim());
        if(url.pathname==='/playlist')return Boolean(url.searchParams.get('list'));
        return channelPath.test(url.pathname);
    }
    function settle(started){
        if(!pending)return;
        const {href,timer}=pending;clearTimeout(timer);pending=null;
        if(!started)location.assign(href);
    }
    function available(){
        const root=document.documentElement;
        return Boolean(root?.classList.contains('minimal-youtube')&&!root.hasAttribute('data-myt-standalone-home')&&document.querySelector('ytd-app'));
    }
    function go(href){
        let url;try{url=landing(new URL(href,location.href));}catch{return false;}
        if(!available()||!routable(url))return false;
        if(pending){clearTimeout(pending.timer);pending=null;}
        const id=++sequence,root=document.documentElement;
        // Never leave a click without a result: a silent router falls back
        // to a document load.
        pending={id,href:url.href,timer:setTimeout(()=>{if(pending?.id===id)settle(false);},6000)};
        root.setAttribute('data-myt-navigate-request',JSON.stringify({id,href:url.href}));
        document.dispatchEvent(new Event('minimal-youtube:navigate'));
        return true;
    }
    document.addEventListener('minimal-youtube:navigate-result',()=>{
        let result;try{result=JSON.parse(document.documentElement.getAttribute('data-myt-navigate-result')||'{}');}catch{return;}
        if(pending&&result.id===pending.id&&!result.started)settle(false);
    });
    document.addEventListener('yt-navigate-start',()=>settle(true));
    window.addEventListener('pagehide',()=>{if(pending){clearTimeout(pending.timer);pending=null;}});
    const plainClick=event=>!event.button&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey;
    function anchorOf(event){
        const anchor=event.composedPath().find(node=>node instanceof HTMLAnchorElement&&node.hasAttribute('href'));
        if(!anchor||anchor.hasAttribute('download')||anchor.target&&anchor.target!=='_self')return null;
        return anchor;
    }
    // Native channel links: route straight to the channel's Videos section.
    document.addEventListener('click',event=>{
        if(event.defaultPrevented||!plainClick(event)||!available())return;
        const anchor=anchorOf(event);if(!anchor)return;
        let url;try{url=new URL(anchor.href);}catch{return;}
        if(url.origin!==location.origin||!channelBase.test(url.pathname))return;
        if(go(url.href)){event.preventDefault();event.stopImmediatePropagation();}
    },true);
    // Own links that no native control handled would otherwise load a document.
    window.addEventListener('click',event=>{
        if(event.defaultPrevented||!plainClick(event))return;
        const anchor=anchorOf(event),root=anchor?.getRootNode();
        if(!(root instanceof ShadowRoot)||!root.host.closest(ownHost))return;
        let url;try{url=new URL(anchor.href);}catch{return;}
        if(url.origin===location.origin&&url.pathname===location.pathname&&url.search===location.search&&url.hash)return;
        if(go(url.href))event.preventDefault();
    });
    function search(query){
        const url=new URL('/results',location.origin);url.searchParams.set('search_query',query);
        return go(url.href);
    }
    globalThis.MinimalYouTubeNavigation={go,search};
})();
