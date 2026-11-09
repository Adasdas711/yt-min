/* Hold only the channel surface until its owned layout is ready. */
(() => {
    'use strict';
    if(!/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/.test(location.pathname))return;
    const start=()=>{
        const root=document.documentElement;
        root.classList.add('minimal-youtube');root.dataset.mytPage='channel';root.setAttribute('data-myt-channel-boot','');
        const release=()=>root.removeAttribute('data-myt-channel-boot');
        // A failed content script must never leave the native channel hidden.
        setTimeout(release,2000);
        try{chrome.storage.local.get(['enabled'],data=>{
            if(chrome.runtime?.lastError||data?.enabled===false)release();
        });}catch{release();}
    };
    if(document.documentElement)start();
    else{const observer=new MutationObserver(()=>{if(document.documentElement){observer.disconnect();start();}});observer.observe(document,{childList:true});}
})();
