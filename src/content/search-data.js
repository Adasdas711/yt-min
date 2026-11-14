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
            return text.match(/([\d][\d\s,.]*\+?)\s*(?:videos?|видео|ролик\S*|lessons?|урок\S*|lektion\S*|episodes?|эпизод\S*|выпуск\S*)/iu)?.[1]?.trim()||(/^[\d][\d\s,.]*\+?$/.test(text)?text:'');
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
    // A course: its lockup type, or a lesson count on its cover badge.
    const lessonPattern=/\d\s*(?:lessons?|урок\S*|lektion\S*)/iu;
    function isCourse(value){
        if(/COURSE/.test(String(value.contentType||'')))return true;
        const stack=[value.contentImage,value.thumbnailRenderer,value.videoCountText,value.metadata],seen=new Set();let scanned=0;
        while(stack.length&&scanned++<1200){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            for(const [key,child]of Object.entries(item)){
                if(typeof child==='string'){if(key!=='url'&&(lessonPattern.test(child)||/^(?:iconName|iconType|imageName)$/.test(key)&&/SCHOOL|COURSE|GRADUATION/i.test(child)))return true;}
                else if(key!=='title'&&child&&typeof child==='object')stack.push(child);
            }
        }
        return false;
    }
    // How much of a video the viewer has watched (0-100): the resume bar on
    // its cover, in legacy (percentDurationWatched) or lockup (startPercent) data.
    function progress(value){
        if(!value||typeof value!=='object')return 0;
        const stack=[value.thumbnailOverlays,value.contentImage,value.thumbnail?.thumbnailOverlays,value.thumbnailRenderer],seen=new Set();let scans=0;
        while(stack.length&&scans++<600){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            for(const key of ['percentDurationWatched','startPercent'])if(typeof item[key]==='number'&&item[key]>0)return Math.min(100,Math.round(item[key]));
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return 0;
    }
    // A video that is streaming now: YouTube marks it with a LIVE thumbnail
    // overlay or badge style; its view line counts current viewers.
    const watchingPattern=/\bwatching\b|смотрят|зрител/iu;
    function liveState(value){
        let live=false;const stack=[value.badges,value.thumbnailOverlays,value.contentImage,value.thumbnail?.thumbnailOverlays];let scans=0;
        while(stack.length&&scans++<600&&!live){
            const item=stack.pop();if(!item||typeof item!=='object')continue;
            for(const [key,child]of Object.entries(item)){
                if(typeof child==='string'){if(/^(?:style|badgeStyle|iconType)$/.test(key)&&/(?:^|_)LIVE(?:_NOW)?(?:$|_)/.test(child)&&!/UPCOMING/.test(child)){live=true;break;}}
                else if(child&&typeof child==='object')stack.push(child);
            }
        }
        let viewers=[label(value.viewCountText),label(value.shortViewCountText)].find(text=>watchingPattern.test(text))||'';
        const metadata=value.metadata?.lockupMetadataViewModel||value.metadata||{};
        if(!viewers)for(const row of metadata.metadata?.contentMetadataViewModel?.metadataRows||metadata.metadataRows||[])for(const part of row.metadataParts||[]){const text=label(part.text).trim();if(!viewers&&watchingPattern.test(text))viewers=text;}
        if(viewers)live=true;
        return {live,viewers:viewers.trim().slice(0,60)};
    }
    const publishedPattern=/\bago\b|назад|^(?:streamed|premiered|scheduled)\b|^(?:трансляция|премьера)/iu;
    function record(input,hint=''){
        if(!input||typeof input!=='object')return null;
        let kind=hint,value=input;
        for(const [key,type] of [['videoRenderer','video'],['gridVideoRenderer','video'],['compactVideoRenderer','video'],['playlistRenderer','playlist'],['gridPlaylistRenderer','playlist'],['radioRenderer','playlist'],['channelRenderer','channel'],['gridChannelRenderer','channel'],['lockupViewModel','']])if(input[key]){value=input[key];kind=type;break;}
        // Courses, podcasts and albums are playlists with their own lockup type.
        if(value.contentType)kind=/PLAYLIST|COURSE|PODCAST|ALBUM|SERIES/.test(value.contentType)?'playlist':/CHANNEL/.test(value.contentType)?'channel':/VIDEO/.test(value.contentType)?'video':kind;
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
                for(const text of label(part.text).split(/\s*[•·]\s*/))if(!published&&publishedPattern.test(text.trim()))published=text.trim();
            }
        }
        return {kind,id,href,title,image:avatar,channel,handle,metadata:metadataText.slice(0,kind==='channel'?8:4),count:kind==='playlist'?playlistCount(value):'',...(kind==='playlist'&&isCourse(value)?{course:true}:{}),published:published.slice(0,100),...(kind==='video'?{...liveState(value),progress:progress(value)}:{})};
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
    globalThis.MinimalYouTubeSearchData={progress,label,url,youtube,channelURL,endpoint,image,playlistCount,isCourse,lessonPattern,record,collect,publishedPattern,watchingPattern};
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
