/* Read public channel/about data in MAIN; only the selected channel is queried. */
(() => {
    'use strict';
    const channelBase=path=>path.match(/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))/)?.[1]?.toLowerCase()||'';
    const label=value=>typeof value==='string'?value:typeof value?.content==='string'?value.content:typeof value?.simpleText==='string'?value.simpleText:Array.isArray(value?.runs)?value.runs.map(run=>run.text||'').join(''):'';
    const cache=new Map();
    function webURL(value){
        if(typeof value!=='string'||!value.trim())return '';
        try{
            if(/^(?:[\w-]+\.)+[\w-]+(?::\d+)?(?:[/?#]|$)/.test(value))value='https://'+value;
            let url=new URL(value,location.origin);
            if(/(^|\.)youtube\.com$/.test(url.hostname)&&url.pathname==='/redirect')url=new URL(url.searchParams.get('q')||url.searchParams.get('url'));
            return /^https?:$/.test(url.protocol)?url.href:'';
        }catch{return '';}
    }
    function links(items){
        const result=new Map();
        for(const item of Array.isArray(items)?items:[]){
            if(!item||typeof item!=='object')continue;
            const model=item.channelExternalLinkViewModel||item;
            const commands=model.link?.commandRuns||[],runs=model.link?.runs||[];
            const display=label(model.link);
            const href=model.navigationEndpoint?.urlEndpoint?.url||commands.map(run=>run.onTap?.innertubeCommand?.urlEndpoint?.url||run.onTap?.urlEndpoint?.url).find(Boolean)||runs.map(run=>run.navigationEndpoint?.urlEndpoint?.url).find(Boolean)||model.url||(/^(?:https?:\/\/|\/\/|(?:[\w-]+\.)+[\w-]+(?:[/?#]|$))/.test(display)?display:'');
            const url=webURL(href);if(!url||result.has(url))continue;
            result.set(url,{title:(label(model.title)||new URL(url).hostname).slice(0,256),url});
            if(result.size===40)break;
        }
        return [...result.values()];
    }
    function normalize(model){
        if(!model)return null;
        const info={};
        for(const [key,field]of [['country','country'],['joined','joinedDateText'],['subscribers','subscriberCountText'],['videos','videoCountText'],['views','viewCountText']]){
            const value=label(model[field]).trim();if(value)info[key]=value.slice(0,500);
        }
        const url=webURL(model.canonicalChannelUrl||model.channelUrl);if(url)info.channelUrl=url;
        return {fullDescription:label(model.description),links:links(model.links||model.primaryLinks),info};
    }
    function models(roots){
        const seen=new Set(),stack=[...roots].reverse();let model=null,endpoint=null,scans=0;
        while(stack.length&&scans++<12000){
            const value=stack.pop();if(!value||typeof value!=='object'||seen.has(value))continue;seen.add(value);
            model ||= value.aboutChannelViewModel||value.channelAboutFullMetadataRenderer||null;
            endpoint ||= value.continuationItemRenderer?.continuationEndpoint||value.channelTaglineRenderer?.moreEndpoint||null;
            const children=Array.isArray(value)?value:Object.values(value);
            for(let i=children.length-1;i>=0;i--)if(children[i]&&typeof children[i]==='object')stack.push(children[i]);
        }
        return {model,endpoint};
    }
    function merge(snapshot,data){
        if(!data)return;
        if(data.fullDescription)snapshot.fullDescription=data.fullDescription;
        if(data.links.length)snapshot.links=data.links;
        Object.assign(snapshot.info,data.info);
    }
    function inspect(source){
        const base=channelBase(location.pathname),browse=source.closest('ytd-browse[page-subtype="channels"]');
        if(!base||!browse)return null;
        const snapshot={base,description:'',fullDescription:'',links:[],info:{channelUrl:location.origin+base},aboutStatus:''};
        const roots=[],app=document.querySelector('ytd-app');let channelId='';
        for(let owner=source;owner&&owner!==browse;owner=owner.parentElement){
            const values=[owner.data,owner.viewModel,owner.__data?.data,owner.polymerController?.data];
            roots.push(...values);
            if(owner===source)for(const data of values){
                snapshot.description ||= label(data?.descriptionPreviewViewModel?.description)||label(data?.description)||label(data?.descriptionText);
            }
        }
        const responses=[];
        for(const owner of [browse,app])for(const data of [owner?.data,owner?.__data?.data,owner?.polymerController?.data])responses.push(data?.response,data);
        responses.push(globalThis.ytInitialData);
        for(const response of responses){
            for(const metadata of [response?.metadata?.channelMetadataRenderer,response?.microformat?.microformatDataRenderer]){
                if(!metadata)continue;
                const urls=[metadata.vanityChannelUrl,metadata.channelUrl,metadata.urlCanonical,...(Array.isArray(metadata.ownerUrls)?metadata.ownerUrls:[])];
                const matches=urls.some(value=>{const url=webURL(value);return url&&channelBase(new URL(url).pathname)===base;})||base==='/channel/'+String(metadata.externalId||'').toLowerCase();
                if(!matches)continue;
                snapshot.fullDescription ||= label(metadata.description);
                channelId ||= metadata.externalId||'';
                const url=urls.map(webURL).find(value=>value&&channelBase(new URL(value).pathname)===base);
                if(url)snapshot.info.channelUrl=url;
                roots.push(response.header,response.engagementPanels);
            }
        }
        // SPA navigation leaves ytInitialData on the previous page.
        roots.push(browse.data?.header,browse.data?.response?.header,browse.__data?.data?.header);
        const header=browse.querySelector(':scope > #header,:scope > #page-header')||source.parentElement;
        const anchors=header?.querySelectorAll('yt-channel-external-link-view-model a[href],yt-attribution-view-model a[href],#primary-links a[href]')||[];
        snapshot.links=links([...anchors].map(anchor=>({title:anchor.textContent.trim(),url:anchor.href})));
        const found=models(roots);
        if(found.model){merge(snapshot,normalize(found.model));snapshot.aboutStatus='ready';}
        const state=cache.get(base);
        if(state&&!found.model){merge(snapshot,state.data);snapshot.aboutStatus=state.status;}
        return {snapshot,endpoint:found.endpoint,channelId};
    }
    function publish(source){
        const current=inspect(source);if(!current)return null;
        const value=JSON.stringify(current.snapshot);
        if(source.getAttribute('data-myt-channel-description-data')!==value)source.setAttribute('data-myt-channel-description-data',value);
        return current;
    }
    function notify(source){
        publish(source);
        source.dispatchEvent(new Event('minimal-youtube:channel-about-updated',{bubbles:true}));
    }
    function payload(endpoint){
        const command=endpoint?.innertubeCommand||endpoint;
        const api=command?.commandMetadata?.webCommandMetadata?.apiUrl;
        if(api&&new URL(api,location.origin).pathname!=='/youtubei/v1/browse')return null;
        if(typeof command?.continuationCommand?.token==='string')return {continuation:command.continuationCommand.token};
        const browse=command?.browseEndpoint;
        if(typeof browse?.browseId==='string'&&/^UC[\w-]+$/.test(browse.browseId)&&typeof browse.params==='string')return {browseId:browse.browseId,params:browse.params};
        return null;
    }
    document.addEventListener('minimal-youtube:channel-description',event=>{
        if(event.target instanceof Element)publish(event.target);
    });
    document.addEventListener('minimal-youtube:channel-about',async event=>{
        if(!document.documentElement.classList.contains('minimal-youtube'))return;
        const source=event.target;if(!(source instanceof Element))return;
        const current=publish(source);if(!current)return;
        const base=current.snapshot.base,previous=cache.get(base);
        if(current.snapshot.aboutStatus==='ready'||previous?.status==='loading'){notify(source);return;}
        const state={status:'loading',data:null};cache.set(base,state);
        while(cache.size>8)cache.delete(cache.keys().next().value);
        notify(source);
        let timeout;
        try{
            const request=payload(current.endpoint);
            const config=name=>globalThis.ytcfg?.get?.(name)??globalThis.ytcfg?.data_?.[name];
            const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{};
            const version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
            if(!request||typeof version!=='string'||!version)throw new Error('No public about endpoint');
            const url=new URL('/youtubei/v1/browse',location.origin);url.searchParams.set('prettyPrint','false');
            const key=config('INNERTUBE_API_KEY');if(typeof key==='string'&&key)url.searchParams.set('key',key);
            const controller=new AbortController();timeout=setTimeout(()=>controller.abort(),10000);
            const response=await fetch(url.href,{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({...request,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version,hl:'en'}}})});
            if(!response.ok)throw new Error('About request failed');
            const found=models([await response.json()]);
            if(!found.model||current.channelId&&found.model.channelId&&current.channelId!==found.model.channelId)throw new Error('No matching channel details');
            state.data=normalize(found.model);state.status='ready';
        }catch{state.status='error';}
        finally{clearTimeout(timeout);}
        if(source.isConnected&&channelBase(location.pathname)===base&&cache.get(base)===state)notify(source);
    });
})();
