/* Reuse YouTube's channel-tab endpoints in MAIN instead of reloading the page. */
(() => {
    'use strict';
    if(globalThis.__minimalYouTubeChannelNavigation)return;
    globalThis.__minimalYouTubeChannelNavigation=true;
    const base=path=>path.match(/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))/)?.[1]?.toLowerCase()||'';
    const section=path=>{const value=path.replace(/\/$/,'').split('/').pop();return value==='community'?'posts':value;};
    const allowed=new Set(['videos','streams','playlists','posts','search']);
    const titles=[
        ['videos',/^(videos|видео)$/iu],['streams',/^(live|streams|трансляции|livestreams)$/iu],
        ['playlists',/^(playlists|плейлисты)$/iu],['posts',/^(posts|community|посты|записи|сообщество|beiträge)$/iu],
        ['search',/^(search(?: this channel)?|поиск(?: на канале)?|suchen|kanalsuche)$/iu],
    ];
    const text=value=>typeof value==='string'?value:value?.content||value?.simpleText||value?.runs?.map(run=>run.text||'').join('')||'';
    function responses(browse){
        const app=document.querySelector('ytd-app'),result=[];
        for(const owner of [browse,app])for(const value of [owner?.data,owner?.__data?.data,owner?.polymerController?.data])result.push(value?.response,value);
        result.push(globalThis.ytInitialData);return result.filter(Boolean);
    }
    function channelId(data,current){
        for(const response of data){
            const metadata=response.metadata?.channelMetadataRenderer;if(!metadata)continue;
            const urls=[metadata.vanityChannelUrl,metadata.channelUrl,...(Array.isArray(metadata.ownerUrls)?metadata.ownerUrls:[])];
            if(urls.some(value=>{try{return typeof value==='string'&&base(new URL(value,location.origin).pathname)===current;}catch{return false;}})||current==='/channel/'+String(metadata.externalId||'').toLowerCase())return metadata.externalId||'';
        }
        return '';
    }
    function endpoint(browse,target){
        const current=base(location.pathname),wanted=section(target.pathname),data=responses(browse),id=channelId(data,current),stack=[];
        for(const node of browse.querySelectorAll('yt-tab-shape,tp-yt-paper-tab,ytd-tab-renderer,ytd-expandable-tab-renderer,[role="tab"]')){
            const anchor=node.matches('a[href]')?node:node.querySelector('a[href]');
            const hint={title:node.textContent.trim()||node.getAttribute('aria-label')||'',url:anchor?.href||'',native:true};
            for(const owner of [node,anchor])for(const value of [owner?.data,owner?.viewModel,owner?.__data?.data,owner?.polymerController?.data,owner?.endpoint,owner?.navigationEndpoint])if(value)stack.push({value,hint});
        }
        for(const response of data){
            for(const tabs of [response.contents?.twoColumnBrowseResultsRenderer?.tabs,response.contents?.singleColumnBrowseResultsRenderer?.tabs,response.tabs])if(tabs)stack.push({value:tabs,hint:{}});
        }
        const seen=new Set();let scans=0,index=0;
        while(index<stack.length&&scans++<2500){
            const {value,hint}=stack[index++];if(!value||typeof value!=='object'||seen.has(value))continue;seen.add(value);
            const tab=value.tabRenderer||value.expandableTabRenderer||value.tabViewModel||value;
            const candidate=tab.endpoint||tab.navigationEndpoint||tab.rendererContext?.commandContext?.onTap||tab.onTap||tab;
            const command=candidate.innertubeCommand||candidate;
            if(command.browseEndpoint&&/^UC[\w-]+$/.test(command.browseEndpoint.browseId||'')){
                const raw=command.commandMetadata?.webCommandMetadata?.url||hint.url;
                let url;try{if(raw)url=new URL(raw,location.origin);}catch{}
                const title=text(tab.title||tab.tabTitle||tab.label)||hint.title||'';
                const key=url?section(url.pathname):titles.find(([,pattern])=>pattern.test(title))?.[0];
                const sameId=!id||command.browseEndpoint.browseId===id;
                const sameBase=url&&url.origin===location.origin&&(base(url.pathname)===current||id&&base(url.pathname)==='/channel/'+id.toLowerCase());
                if(key===wanted&&sameId&&(sameBase||id||hint.native&&!url)){
                    const browseEndpoint={...command.browseEndpoint};
                    if(wanted==='search')browseEndpoint.query=target.searchParams.get('query')||'';
                    else delete browseEndpoint.query;
                    // The current WEB client already runs in English. Keep
                    // language overrides on real links, not on SPA commands.
                    const route=new URL(target.href);route.searchParams.delete('hl');route.searchParams.delete('persist_hl');
                    const metadata={...command.commandMetadata?.webCommandMetadata,url:route.pathname+route.search+route.hash};
                    metadata.webPageType ||= 'WEB_PAGE_TYPE_CHANNEL';
                    metadata.apiUrl ||= '/youtubei/v1/browse';
                    const endpoint={browseEndpoint,commandMetadata:{webCommandMetadata:metadata}};
                    if(typeof command.clickTrackingParams==='string')endpoint.clickTrackingParams=command.clickTrackingParams;
                    return endpoint;
                }
            }
            // Selected tabs contain the whole video feed. Only inspect tab
            // controls, never walk their content looking for another endpoint.
            if(value.tabRenderer||value.expandableTabRenderer||value.tabViewModel)continue;
            for(const key of Object.keys(value)){
                if(['content','contents','thumbnail','trackingParams'].includes(key))continue;
                const child=value[key];if(child&&typeof child==='object')stack.push({value:child,hint});
            }
        }
        return null;
    }
    document.addEventListener('minimal-youtube:channel-navigate',event=>{
        const nav=event.target;
        if(!(nav instanceof Element)||nav.id!=='myt-channel-nav'||!document.documentElement.classList.contains('minimal-youtube'))return;
        const browse=nav.closest('ytd-browse[page-subtype="channels"]');if(!browse)return;
        let request;try{request=JSON.parse(nav.getAttribute('data-myt-channel-navigation-request')||'{}');}catch{return;}
        if(!Number.isSafeInteger(request.id)||typeof request.href!=='string'||request.href.length>4096)return;
        let started=false;
        try{
            const target=new URL(request.href,location.origin);
            if(target.origin!==location.origin||base(target.pathname)!==base(location.pathname)||!allowed.has(section(target.pathname)))throw new Error('Not a channel section');
            const command=endpoint(browse,target),app=document.querySelector('ytd-app');
            if(command&&app){
                app.dispatchEvent(new CustomEvent('yt-navigate',{bubbles:true,composed:true,cancelable:true,detail:{endpoint:command}}));
                started=true;
            }
        }catch{}
        nav.setAttribute('data-myt-channel-navigation-result',JSON.stringify({id:request.id,started}));
    });
})();
