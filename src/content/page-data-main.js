/* Page data for owned search and channel results. YouTube's own data always
   holds a page's items, even when its grid does not stamp them. This MAIN
   bridge turns that data into public card records for the isolated renderer
   and loads further pages with the page's continuation token. */
(() => {
    'use strict';
    if(globalThis.__minimalYouTubePageData)return;
    globalThis.__minimalYouTubePageData=true;
    const channelPath=/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/;
    const shortsTitle=/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu;
    const hiddenChannelShelf=/^(?:new uploads|новые (?:видео|загрузки)|последние (?:видео|загрузки))(?=$|\s)/iu;
    const config=name=>globalThis.ytcfg?.get?.(name)??globalThis.ytcfg?.data_?.[name];
    const models=new WeakMap();
    let current=null,published='';
    const visible=node=>node&&!node.hidden&&!node.closest('[hidden]')&&node.getClientRects().length>0;
    function routeKey(){
        const url=new URL(location.href);
        if(url.pathname==='/results')return JSON.stringify(['search',url.searchParams.get('search_query')||'',url.searchParams.get('sp')||'']);
        return JSON.stringify(['channel',url.pathname.replace(/\/$/,'').replace(/\/community$/,'/posts').toLowerCase(),/\/search$/.test(url.pathname.replace(/\/$/,''))?url.searchParams.get('query')||'':'']);
    }
    function token(value){
        const stack=[value],seen=new Set();let scans=0;
        while(stack.length&&scans++<400){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            const found=item.continuationCommand?.token;if(typeof found==='string'&&found)return found;
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return '';
    }
    function isShort(entry){
        return Object.keys(entry).some(key=>/^shorts|^reel/i.test(key))||/SHORTS/.test(entry.lockupViewModel?.contentType||'')||
            Boolean(entry.videoRenderer?.navigationEndpoint?.reelWatchEndpoint);
    }
    // Only top-level item renderers become cards. Nested endpoints inside a
    // card (owner links, playlist ids of a video) never add extra records.
    function parse(list,out,group,channel){
        const data=globalThis.MinimalYouTubeSearchData;
        for(const entry of Array.isArray(list)?list:[]){
            if(!entry||typeof entry!=='object'||out.items.length>=600)continue;
            if(entry.continuationItemRenderer){const value=token(entry.continuationItemRenderer);if(value)out.continuation=value;continue;}
            if(entry.itemSectionRenderer){parse(entry.itemSectionRenderer.contents,out,group,channel);continue;}
            if(entry.richItemRenderer){parse([entry.richItemRenderer.content],out,group,channel);continue;}
            if(entry.gridRenderer){parse(entry.gridRenderer.items,out,group,channel);continue;}
            if(entry.shelfRenderer){
                const shelf=entry.shelfRenderer,title=data.label(shelf.title).trim();
                if(shortsTitle.test(title)||channel&&hiddenChannelShelf.test(title))continue;
                const content=shelf.content||{};
                const items=(content.verticalListRenderer||content.horizontalListRenderer||content.expandedShelfContentsRenderer||content.gridRenderer||{}).items;
                parse(items,out,channel?group:title||group,channel);continue;
            }
            if(entry.richSectionRenderer||entry.reelShelfRenderer||isShort(entry))continue;
            const record=data.record(entry);
            if(!record||!['video','playlist','channel'].includes(record.kind))continue;
            let path='';try{path=new URL(record.href).pathname;}catch{continue;}
            if(/^\/shorts(?:\/|$)/.test(path)||record.kind==='video'&&!/[?&]v=[-\w]{11}/.test(record.href))continue;
            if(channel&&record.kind==='channel')continue;
            out.items.push({...record,group:group||''});
        }
    }
    function source(){
        if(!document.documentElement.classList.contains('minimal-youtube')||!globalThis.MinimalYouTubeSearchData)return null;
        const path=location.pathname.replace(/\/$/,'');
        if(path==='/results'){
            const search=document.querySelector('#myt-search')?.closest('ytd-search')||[...document.querySelectorAll('ytd-search')].find(visible);
            const data=search?.data;
            const list=(data?.contents||data?.response?.contents)?.twoColumnSearchResultsRenderer?.primaryContents?.sectionListRenderer?.contents;
            return Array.isArray(list)?{type:'search',list}:null;
        }
        if(!channelPath.test(path)||/\/(?:community|posts|featured)$/.test(path)||/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)$/.test(path))return null;
        const browse=[...document.querySelectorAll('ytd-browse')].find(visible)||document.querySelector('ytd-browse');
        const tabs=(browse?.data?.contents||browse?.data?.response?.contents)?.twoColumnBrowseResultsRenderer?.tabs;
        if(!Array.isArray(tabs))return null;
        const selected=tabs.map(tab=>tab.tabRenderer||tab.expandableTabRenderer).find(tab=>tab?.selected);
        const url=selected?.endpoint?.commandMetadata?.webCommandMetadata?.url||'';
        // A selected tab for another section is a page still in transition.
        if(!url||url.split('?')[0].replace(/\/$/,'').replace(/\/community$/,'/posts').toLowerCase()!==path.replace(/\/community$/,'/posts').toLowerCase())return null;
        const content=selected.content;
        const list=content?.richGridRenderer?.contents||content?.sectionListRenderer?.contents;
        return Array.isArray(list)?{type:'channel',list}:null;
    }
    function model(){
        let found=null;try{found=source();}catch{found=null;}
        if(!found)return null;
        let value=models.get(found.list);
        if(!value){
            value={key:routeKey(),type:found.type,items:[],continuation:'',loading:false,failed:false};
            try{parse(found.list,value,'',found.type==='channel');}catch{return null;}
            models.set(found.list,value);
        }
        return value;
    }
    function publish(){
        const root=document.documentElement;
        const text=current?JSON.stringify({key:current.key,type:current.type,items:current.items,more:Boolean(current.continuation)&&!current.failed,loading:current.loading}):'';
        if(text===published)return;
        published=text;
        if(text)root.setAttribute('data-myt-page-model',text);else root.removeAttribute('data-myt-page-model');
        document.dispatchEvent(new Event('minimal-youtube:page-model-updated'));
    }
    document.addEventListener('minimal-youtube:page-model',()=>{current=model();publish();});
    document.addEventListener('minimal-youtube:page-model-more',async()=>{
        const state=current;
        if(!state||state.loading||!state.continuation||state.failed||state.key!==routeKey())return;
        const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{},version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
        if(typeof version!=='string'||!version){state.failed=true;publish();return;}
        state.loading=true;publish();
        const url=new URL(state.type==='search'?'/youtubei/v1/search':'/youtubei/v1/browse',location.origin);url.searchParams.set('prettyPrint','false');
        const key=config('INNERTUBE_API_KEY');if(typeof key==='string'&&key)url.searchParams.set('key',key);
        const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
        try{
            const response=await fetch(url.href,{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json'},
                body:JSON.stringify({continuation:state.continuation,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version}}})});
            if(!response.ok)throw new Error('Continuation failed');
            const data=await response.json();
            const next={items:[],continuation:''};
            for(const command of [...(data.onResponseReceivedCommands||[]),...(data.onResponseReceivedActions||[])]){
                const action=command.appendContinuationItemsAction||command.reloadContinuationItemsCommand;
                if(Array.isArray(action?.continuationItems))parse(action.continuationItems,next,'',state.type==='channel');
            }
            const known=new Set(state.items.map(item=>item.href+'|'+item.group));
            for(const item of next.items)if(!known.has(item.href+'|'+item.group)&&state.items.length<600)state.items.push(item);
            state.continuation=next.continuation;
        }catch{state.failed=true;}
        finally{clearTimeout(timeout);state.loading=false;}
        if(current===state)publish();
    });
})();
