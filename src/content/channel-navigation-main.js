/* Reuse YouTube's channel-tab endpoints in MAIN instead of reloading the page. */
(() => {
    'use strict';
    if(globalThis.__minimalYouTubeChannelNavigation)return;
    globalThis.__minimalYouTubeChannelNavigation=true;
    const base=path=>path.match(/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))/)?.[1]?.toLowerCase()||'';
    const section=path=>{const value=path.replace(/\/$/,'').split('/').pop();return value==='community'?'posts':value;};
    const allowed=new Set(['videos','streams','playlists','posts','search']);
    const endpointCache=new Map();
    const resolvedEndpoints=new Map();
    let active=null;
    const config=name=>globalThis.ytcfg?.get?.(name)??globalThis.ytcfg?.data_?.[name];
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
    function resolveEndpoint(browse,target){
        const current=base(location.pathname),wanted=section(target.pathname),data=responses(browse),id=channelId(data,current),stack=[];
        // Canonical response tabs precede DOM controllers, which YouTube reuses.
        for(const response of data){
            for(const tabs of [response.contents?.twoColumnBrowseResultsRenderer?.tabs,response.contents?.singleColumnBrowseResultsRenderer?.tabs,response.tabs])if(Array.isArray(tabs))for(const tab of tabs)stack.push({value:tab,hint:{}});
        }
        for(const node of browse.querySelectorAll('yt-tab-shape,tp-yt-paper-tab,ytd-tab-renderer,ytd-expandable-tab-renderer,[role="tab"]')){
            const anchor=node.matches('a[href]')?node:node.querySelector('a[href]');
            const hint={title:node.textContent.trim()||node.getAttribute('aria-label')||'',url:anchor?.href||'',native:true};
            for(const owner of [node,anchor])for(const value of [owner?.data,owner?.viewModel,owner?.__data?.data,owner?.polymerController?.data,owner?.endpoint,owner?.navigationEndpoint])if(value)stack.push({value,hint});
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
    function endpoint(browse,target){
        const current=base(location.pathname),id=channelId(responses(browse),current),key=current+'|'+id;
        let cache=endpointCache.get(key);
        if(!cache){cache=new Map();endpointCache.set(key,cache);if(endpointCache.size>8)endpointCache.delete(endpointCache.keys().next().value);}
        // Snapshot all original tab commands before the first transition can
        // replace their models. Never retain a query in a section's command.
        for(const name of allowed)if(!cache.has(name)){
            const url=new URL(current+'/'+name,location.origin),command=resolveEndpoint(browse,url);
            if(command){delete command.browseEndpoint.query;cache.set(name,command);}
        }
        const wanted=section(target.pathname),command=cache.get(wanted);if(!command)return null;
        const browseEndpoint={...command.browseEndpoint};
        if(wanted==='search')browseEndpoint.query=target.searchParams.get('query')||'';
        const route=new URL(target.href);route.searchParams.delete('hl');route.searchParams.delete('persist_hl');
        return {browseEndpoint,commandMetadata:{webCommandMetadata:{...command.commandMetadata.webCommandMetadata,url:route.pathname+route.search+route.hash}},...(command.clickTrackingParams?{clickTrackingParams:command.clickTrackingParams}:{})};
    }
    function routeURL(target){
        const route=new URL(target.href);route.searchParams.delete('hl');route.searchParams.delete('persist_hl');
        if(section(route.pathname)!=='search')route.searchParams.delete('query');
        return route;
    }
    async function resolveURL(browse,target,state){
        const route=routeURL(target),key=route.href,wanted=section(route.pathname);
        const cached=resolvedEndpoints.get(key);if(cached)return JSON.parse(cached);
        const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{};
        const version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
        const url=new URL('/youtubei/v1/navigation/resolve_url',location.origin);url.searchParams.set('prettyPrint','false');
        const apiKey=config('INNERTUBE_API_KEY');if(typeof apiKey==='string'&&apiKey)url.searchParams.set('key',apiKey);
        const timeout=setTimeout(()=>state.controller.abort(),5000);
        let result;
        try{
            const response=await fetch(url.href,{method:'POST',credentials:'same-origin',signal:state.controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({url:route.href,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version}}})});
            if(!response.ok)throw new Error('Channel URL resolution failed');
            result=await response.json();
        }finally{clearTimeout(timeout);}
        const command=result.endpoint?.innertubeCommand||result.endpoint,id=channelId(responses(browse),base(target.pathname));
        const resolved=new URL(command?.commandMetadata?.webCommandMetadata?.url||'',location.origin);
        // Never use a command for another channel, a different tab or a generic
        // channel home response in place of Live. Params come from YouTube.
        const browseId=command?.browseEndpoint?.browseId,params=command?.browseEndpoint?.params;
        const sameChannel=base(resolved.pathname)===base(target.pathname)||base(resolved.pathname)==='/channel/'+String(browseId).toLowerCase();
        // Name the failed check: it identifies a changed YouTube response.
        const problem=!/^UC[\w-]+$/.test(browseId||'')?'no channel id':typeof params!=='string'||!params?'no section params':id&&browseId!==id?'another channel':
            resolved.origin!==location.origin?'another origin':section(resolved.pathname)!==wanted?'section '+section(resolved.pathname)+' instead of '+wanted:!sameChannel?'another channel path':'';
        if(problem)throw new Error('Wrong channel section: '+problem);
        const endpoint=JSON.parse(JSON.stringify(command));
        endpoint.commandMetadata.webCommandMetadata.url=route.pathname+route.search+route.hash;
        if(wanted==='search')endpoint.browseEndpoint.query=route.searchParams.get('query')||'';
        else delete endpoint.browseEndpoint.query;
        // Keep immutable snapshots, not objects a native controller can reuse
        // or mutate. Search queries are not cached.
        if(wanted!=='search'){
            resolvedEndpoints.set(key,JSON.stringify(endpoint));
            if(resolvedEndpoints.size>32)resolvedEndpoints.delete(resolvedEndpoints.keys().next().value);
        }
        return endpoint;
    }
    function cancel(nav){if(active?.nav===nav){active.controller.abort();active=null;}}
    document.addEventListener('minimal-youtube:channel-navigation-cancel',event=>cancel(event.target));
    document.addEventListener('minimal-youtube:channel-navigate',event=>{
        const nav=event.target;
        if(!(nav instanceof Element)||nav.id!=='myt-channel-nav'||!document.documentElement.classList.contains('minimal-youtube'))return;
        const browse=nav.closest('ytd-browse');if(!browse)return;
        let request;try{request=JSON.parse(nav.getAttribute('data-myt-channel-navigation-request')||'{}');}catch{return;}
        if(!Number.isSafeInteger(request.id)||typeof request.href!=='string'||request.href.length>4096)return;
        let started=false;
        try{
            const target=new URL(request.href,location.origin);
            if(target.origin!==location.origin||base(target.pathname)!==base(location.pathname)||!allowed.has(section(target.pathname)))throw new Error('Not a channel section');
            cancel(nav);
            const context=config('INNERTUBE_CONTEXT'),version=context?.client?.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
            if(typeof version==='string'&&version){
                const state={nav,controller:new AbortController()};active=state;
                const current=()=>active===state&&nav.isConnected&&document.documentElement.classList.contains('minimal-youtube')&&base(location.pathname)===base(target.pathname);
                nav.setAttribute('data-myt-channel-navigation-result',JSON.stringify({id:request.id,started:true,resolving:true}));
                resolveURL(browse,target,state).then(command=>{
                    if(!current())return;
                    const app=document.querySelector('ytd-app');if(!app)throw new Error('Missing app');
                    app.dispatchEvent(new CustomEvent('yt-navigate',{bubbles:true,composed:true,cancelable:true,detail:{endpoint:command}}));
                }).catch(error=>{
                    if(!current())return;
                    // The channel's own tab commands are the next best route:
                    // they still avoid a document load for this section.
                    // A response that points to another section or channel is a
                    // real answer: never replace it with a possibly stale tab.
                    const message=String(error?.message||error);
                    const incomplete=!/section \S+ instead of|another (?:channel|origin)/.test(message);
                    if(incomplete)try{
                        const command=endpoint(browse,target),app=document.querySelector('ytd-app');
                        if(command&&app){
                            console.info('[Minimal YouTube] channel route:',String(error?.message||error),'- using the tab command instead');
                            app.dispatchEvent(new CustomEvent('yt-navigate',{bubbles:true,composed:true,cancelable:true,detail:{endpoint:command}}));
                            return;
                        }
                    }catch{}
                    nav.setAttribute('data-myt-channel-navigation-result',JSON.stringify({id:request.id,started:false,reason:String(error?.message||error).slice(0,200)}));
                    nav.dispatchEvent(new Event('minimal-youtube:channel-navigation-result',{bubbles:true}));
                });
                return;
            }
            // Older clients without URL resolution can still use their native
            // tab models, with the existing navigation watchdog as a fallback.
            const command=endpoint(browse,target),app=document.querySelector('ytd-app');
            if(command&&app){
                app.dispatchEvent(new CustomEvent('yt-navigate',{bubbles:true,composed:true,cancelable:true,detail:{endpoint:command}}));
                started=true;
            }
        }catch(error){console.info('[Minimal YouTube] channel route failed:',String(error?.message||error));}
        nav.setAttribute('data-myt-channel-navigation-result',JSON.stringify({id:request.id,started}));
    });
})();
