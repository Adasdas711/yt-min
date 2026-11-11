/* Public search records shared by the MAIN data bridge and isolated renderer. */
(() => {
    'use strict';
    if(globalThis.MinimalYouTubeSearchData)return;
    const label=value=>typeof value==='string'?value:typeof value?.simpleText==='string'?value.simpleText:typeof value?.content==='string'?value.content:Array.isArray(value?.runs)?value.runs.map(run=>run.text||'').join(''):'';
    const url=value=>{try{const parsed=new URL(value,'https://www.youtube.com');return parsed.protocol==='https:'?parsed.href:'';}catch{return '';}};
    const youtube=value=>{const href=url(value);if(!href)return '';const parsed=new URL(href);return /(^|\.)youtube\.com$/.test(parsed.hostname)?href:'';};
    const channelURL=value=>{const href=youtube(value);return href&&/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)/.test(new URL(href).pathname)?href:'';};
    function endpoint(value){
        if(!value||typeof value!=='object')return '';
        value=value.innertubeCommand||value;
        const direct=value.commandMetadata?.webCommandMetadata?.url||value.urlEndpoint?.url;
        if(direct)return youtube(direct);
        if(value.watchEndpoint?.videoId)return url('/watch?v='+encodeURIComponent(value.watchEndpoint.videoId)+(value.watchEndpoint.playlistId?'&list='+encodeURIComponent(value.watchEndpoint.playlistId):''));
        if(value.browseEndpoint){const browse=value.browseEndpoint;return youtube(browse.canonicalBaseUrl||(/^UC/.test(browse.browseId||'')?'/channel/'+browse.browseId:''));}
        return '';
    }
    function image(root){
        let best='',width=-1;const seen=new Set(),stack=[root];let scans=0;
        while(stack.length&&scans++<1500){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            if(typeof item.url==='string'&&item.url.length<4096){const href=url(item.url),size=Number(item.width)||0;if(href&&size>width){best=href;width=size;}}
            for(const value of Object.values(item))if(value&&typeof value==='object')stack.push(value);
        }
        return best;
    }
    function playlistCount(value){
        const parse=input=>{
            const text=(typeof input==='number'?String(input):label(input)).replace(/[\u00a0\u202f]/g,' ').trim();
            return text.match(/([\d][\d\s,.]*\+?)\s*(?:videos?|видео|ролик\S*)/iu)?.[1]?.trim()||(/^[\d][\d\s,.]*\+?$/.test(text)?text:'');
        };
        for(const input of [value.videoCount,value.videoCountText,value.videoCountShortText]){const count=parse(input);if(count)return count;}
        const stack=[value.contentImage,value.thumbnailRenderer,value.metadata?.lockupMetadataViewModel?.metadata||value.metadata?.metadata||value.metadata],seen=new Set();let scanned=0;
        while(stack.length&&scanned++<1200){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            const count=parse(item.text)||parse(item);if(count)return count;
            for(const [key,child]of Object.entries(item))if(key!=='title'&&child&&typeof child==='object')stack.push(child);
        }
        return '';
    }
    const publishedPattern=/\bago\b|назад|^(?:streamed|premiered|scheduled)\b|^(?:трансляция|премьера)/iu;
    function record(input,hint=''){
        if(!input||typeof input!=='object')return null;
        let kind=hint,value=input;
        for(const [key,type] of [['videoRenderer','video'],['gridVideoRenderer','video'],['compactVideoRenderer','video'],['playlistRenderer','playlist'],['gridPlaylistRenderer','playlist'],['radioRenderer','playlist'],['channelRenderer','channel'],['gridChannelRenderer','channel'],['lockupViewModel','']])if(input[key]){value=input[key];kind=type;break;}
        if(value.contentType)kind=/PLAYLIST/.test(value.contentType)?'playlist':/CHANNEL/.test(value.contentType)?'channel':/VIDEO/.test(value.contentType)?'video':kind;
        kind ||= value.channelId?'channel':value.playlistId?'playlist':value.videoId?'video':'';
        const metadata=value.metadata?.lockupMetadataViewModel||value.metadata||{};
        const title=label(value.title||metadata.title).trim().slice(0,1000);
        const navigation=value.navigationEndpoint||value.rendererContext?.commandContext?.onTap?.innertubeCommand||value.onTap?.innertubeCommand;
        let href=endpoint(navigation);
        const id=String(value.videoId||value.playlistId||value.channelId||value.contentId||navigation?.browseEndpoint?.browseId||'');
        if(!href&&id)href=url(kind==='video'?'/watch?v='+encodeURIComponent(id):kind==='playlist'?'/playlist?list='+encodeURIComponent(id):kind==='channel'?'/channel/'+encodeURIComponent(id):'');
        if(!kind||!href)return null;
        const owner=value.ownerText||value.shortBylineText||value.longBylineText;
        let channel={name:label(owner).slice(0,500),href:endpoint(owner?.runs?.find(run=>run.navigationEndpoint)?.navigationEndpoint)};
        if(!channel.name){
            const rows=metadata.metadata?.contentMetadataViewModel?.metadataRows||metadata.metadataRows||[];
            for(const row of rows)for(const part of row.metadataParts||[]){
                const name=label(part.text),command=part.text?.commandRuns?.[0]?.onTap||part.onTap;
                const href=channelURL(endpoint(command));if(name&&href){channel={name:name.slice(0,500),href};break;}
            }
        }
        const rows=kind==='channel'?(metadata.metadata?.contentMetadataViewModel?.metadataRows||metadata.metadataRows||[]):[];
        const metadataText=[...new Set([label(value.subscriberCountText),label(value.videoCountText),...rows.flatMap(row=>(row.metadataParts||[]).map(part=>label(part.text)))].filter(Boolean))];
        const handle=metadataText.find(text=>/^@\S+$/.test(text))||'';
        const avatar=image([value.thumbnail,value.thumbnails,value.avatar,value.contentImage]);
        // Upload date: the renderer's own field, or the dated part of a lockup.
        let published='';
        if(kind==='video'){
            published=label(value.publishedTimeText).trim();
            if(!published)for(const row of metadata.metadata?.contentMetadataViewModel?.metadataRows||metadata.metadataRows||[])for(const part of row.metadataParts||[]){
                const text=label(part.text).trim();if(!published&&publishedPattern.test(text))published=text;
            }
        }
        return {kind,id,href,title,image:avatar,channel,handle,metadata:metadataText.slice(0,kind==='channel'?8:4),count:kind==='playlist'?playlistCount(value):'',published:published.slice(0,100)};
    }
    function collect(root){
        const records=[],filters=[],seen=new Set(),stack=[root];let scans=0;
        while(stack.length&&scans++<40000){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            const result=record(item);if(result)records.push(result);
            if(item.searchFilterRenderer){const filter=item.searchFilterRenderer,href=endpoint(filter.navigationEndpoint);if(href)filters.push({label:label(filter.label),href});}
            const values=Array.isArray(item)?item:Object.values(item);for(let i=values.length-1;i>=0;i--)if(values[i]&&typeof values[i]==='object')stack.push(values[i]);
        }
        return {records,filters};
    }
    globalThis.MinimalYouTubeSearchData={label,url,youtube,channelURL,endpoint,image,playlistCount,record,collect,publishedPattern};
    // Static MAIN injection also serves the first page after installation,
    // before the background has registered its optional response-pruning hook.
    if(typeof document!=='undefined'&&!globalThis.chrome?.runtime?.id)document.addEventListener('minimal-youtube:search-snapshot',()=>{
        if(globalThis.__minimalYouTubeDataPruning||location.pathname!=='/results'||!document.documentElement?.hasAttribute('data-myt-search-ui'))return;
        const search=document.querySelector('#myt-search')?.closest('ytd-search')||document.querySelector('ytd-search');
        const publicData=collect(search?.data||globalThis.ytInitialData),records=[];
        for(const source of document.querySelectorAll('[data-myt-search-source-key]')){
            const kind=source.getAttribute('data-myt-search-source-kind');let value;
            for(const data of [source.data,source.__data?.data,source.__data?.data?.data]){value=record(data,kind)||collect(data).records.find(item=>item.kind===kind);if(value)break;}
            if(!value){const hrefs=[...source.querySelectorAll('a[href]')].map(link=>link.href);value=publicData.records.find(item=>hrefs.includes(item.href));}
            if(value)records.push({key:source.getAttribute('data-myt-search-source-key'),...value});
        }
        const snapshot=JSON.stringify({records,filters:publicData.filters.slice(0,100)});
        if(document.documentElement.getAttribute('data-myt-search-snapshot')!==snapshot)document.documentElement.setAttribute('data-myt-search-snapshot',snapshot);
    });
})();
