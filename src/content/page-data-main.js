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
        if(url.pathname==='/playlist')return JSON.stringify(['playlist',url.searchParams.get('list')||'']);
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
    // Public, read-only fields of a channel post. Likes, votes and comments
    // stay counts; account actions are not offered.
    function post(value){
        const data=globalThis.MinimalYouTubeSearchData;
        const renderer=value.backstagePostRenderer||value.postRenderer||value.sharedPostRenderer;
        if(!renderer||typeof renderer!=='object')return null;
        const id=typeof renderer.postId==='string'?renderer.postId:'';
        const attachment=renderer.backstageAttachment||{};
        const images=[];
        for(const image of [attachment.backstageImageRenderer,...(attachment.postMultiImageRenderer?.images||[]).map(item=>item.backstageImageRenderer)]){
            const url=image&&data.image(image.image);if(url&&images.length<10)images.push(url);
        }
        const media=attachment.videoRenderer?data.record({videoRenderer:attachment.videoRenderer}):attachment.playlistRenderer?data.record({playlistRenderer:attachment.playlistRenderer}):null;
        const poll=attachment.pollRenderer?{choices:(attachment.pollRenderer.choices||[]).map(choice=>data.label(choice.text).trim()).filter(Boolean).slice(0,10),votes:data.label(attachment.pollRenderer.totalVotes).trim()}:null;
        const text=data.label(renderer.contentText).slice(0,5000);
        if(!text&&!images.length&&!media&&!poll)return null;
        return {kind:'post',id,href:id?'https://www.youtube.com/post/'+encodeURIComponent(id):'',
            author:data.label(renderer.authorText).trim().slice(0,300),avatar:data.image(renderer.authorThumbnail),
            published:data.label(renderer.publishedTimeText).trim().slice(0,100),text,images,
            media:media&&(media.kind==='video'||media.kind==='playlist')?{kind:media.kind,href:media.href,title:media.title,image:media.image}:null,poll,
            likes:data.label(renderer.voteCount).trim().slice(0,40),
            comments:data.label(renderer.actionButtons?.commentActionButtonsRenderer?.replyButton?.buttonRenderer?.text).trim().slice(0,40),group:''};
    }
    // A playlist video in public fields, with the playlist edits YouTube's
    // own menu offers for it (remove, move, save). The edit commands stay
    // here; the renderer only names them.
    const actions=new Map();let actionSequence=0;
    function playlistItem(value){
        const data=globalThis.MinimalYouTubeSearchData;
        const id=String(value.videoId||'');if(!/^[-\w]{11}$/.test(id))return null;
        const list=new URL(location.href).searchParams.get('list')||'';
        const fallback=data.url('/watch?v='+encodeURIComponent(id)+(list?'&list='+encodeURIComponent(list):''));
        const owner=value.shortBylineText||value.ownerText;
        const info=data.label(value.videoInfo).replace(/\s+/g,' ').trim();
        const published=info.split(/\s*[•·]\s*/).find(text=>data.publishedPattern.test(text))||'';
        let duration=data.label(value.lengthText).trim();
        if(!duration)for(const overlay of value.thumbnailOverlays||[]){const text=data.label(overlay.thumbnailOverlayTimeStatusRenderer?.text).trim();if(text){duration=text;break;}}
        const options=[];
        for(const item of value.menu?.menuRenderer?.items||[]){
            const service=item.menuServiceItemRenderer,endpoint=service?.serviceEndpoint,edit=endpoint?.playlistEditEndpoint;
            const api=endpoint?.commandMetadata?.webCommandMetadata?.apiUrl;
            if(!edit||typeof api!=='string'||!/^\/youtubei\/v1\//.test(api))continue;
            const change=(edit.actions||[])[0]||{},label=data.label(service.text).trim();if(!label)continue;
            const kind=/REMOVE/.test(change.action||'')?'remove':/MOVE/.test(change.action||'')?'move':/ADD/.test(change.action||'')?'add':'edit';
            const key='a'+(++actionSequence);
            actions.set(key,{api,payload:edit,kind,change,setVideoId:String(value.setVideoId||''),videoId:id,playlistId:String(edit.playlistId||'')});
            while(actions.size>3000)actions.delete(actions.keys().next().value);
            options.push({id:key,label:label.slice(0,80),kind});
        }
        return {kind:'video',id,href:data.endpoint(value.navigationEndpoint)||fallback,title:(data.label(value.title).trim()||'Unavailable video').slice(0,1000),
            image:data.image(value.thumbnail),channel:{name:data.label(owner).slice(0,500),href:data.endpoint(owner?.runs?.find(run=>run.navigationEndpoint)?.navigationEndpoint)},
            index:data.label(value.index).trim().slice(0,12),duration:duration.slice(0,20),stats:info.slice(0,200),published:published.slice(0,100),
            setVideoId:String(value.setVideoId||'').slice(0,100),playable:value.isPlayable!==false,actions:options,group:'',progress:data.progress(value)};
    }
    function playlistList(root){
        const stack=[root],seen=new Set();let scans=0;
        while(stack.length&&scans++<2000){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            if(item.playlistVideoListRenderer)return item.playlistVideoListRenderer;
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return null;
    }
    function lessonList(root){
        const stack=[root],seen=new Set();let scans=0;
        while(stack.length&&scans++<2000){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            const section=item.sectionListRenderer;
            if(Array.isArray(section?.contents)&&section.contents.some(entry=>(entry?.itemSectionRenderer?.contents||[]).some(child=>/VIDEO/.test(child?.lockupViewModel?.contentType||''))))return section;
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return null;
    }
    // A lesson: a video lockup in a course, in the fields of a playlist row.
    function lessonItem(value){
        const data=globalThis.MinimalYouTubeSearchData;
        const id=String(value.contentId||'');if(!/^[-\w]{11}$/.test(id)||!/VIDEO/.test(value.contentType||''))return null;
        const list=new URL(location.href).searchParams.get('list')||'';
        const command=value.rendererContext?.commandContext?.onTap?.innertubeCommand;
        const href=data.endpoint(command)||data.url('/watch?v='+encodeURIComponent(id)+(list?'&list='+encodeURIComponent(list):''));
        const metadata=value.metadata?.lockupMetadataViewModel||{};
        let duration='';const stack=[value.contentImage];let scans=0;
        while(stack.length&&scans++<400&&!duration){
            const item=stack.pop();if(!item||typeof item!=='object')continue;
            const text=typeof item.text==='string'?item.text.trim():'';if(/^\d{1,3}:\d{2}(?::\d{2})?$/.test(text)){duration=text;break;}
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        const parts=[];
        for(const row of metadata.metadata?.contentMetadataViewModel?.metadataRows||[])for(const part of row.metadataParts||[]){
            let text=data.label(part.text).trim();if(!text)continue;
            // A count shown with the views icon alone names its unit only in its label.
            if(/просмотр|views?\b|Aufrufe/iu.test(String(part.accessibilityLabel||''))&&!/просмотр|views?\b|Aufrufe/iu.test(text))text+=' views';
            parts.push(text);
        }
        const published=parts.find(text=>data.publishedPattern.test(text))||'';
        const avatar=metadata.image?.decoratedAvatarViewModel,owner=avatar?.rendererContext?.commandContext?.onTap?.innertubeCommand;
        const name=String(avatar?.a11yLabel||'').match(/["«“](.+)["»”]\s*$/u)?.[1]||'';
        const index=Number.isInteger(command?.watchEndpoint?.index)?String(command.watchEndpoint.index+1):'';
        return {kind:'video',id,href,title:(data.label(metadata.title).trim()||'Unavailable video').slice(0,1000),image:data.image(value.contentImage),
            channel:{name:name.slice(0,500),href:data.channelURL(data.endpoint(owner))},index,duration:duration.slice(0,20),stats:parts.join(' • ').slice(0,200),
            published:published.slice(0,100),setVideoId:'',playable:true,actions:[],group:'',progress:data.progress(value)};
    }
    function chips(content){
        const data=globalThis.MinimalYouTubeSearchData;
        const bar=content?.richGridRenderer?.header?.feedFilterChipBarRenderer||content?.sectionListRenderer?.header?.feedFilterChipBarRenderer;
        const result=[];
        for(const item of bar?.contents||[]){
            const chip=item.chipCloudChipRenderer||item.chipViewModel;if(!chip)continue;
            const label=data.label(chip.text||chip.title).trim(),value=token(chip.navigationEndpoint||chip.tapCommand||chip);
            if(label&&value)result.push({label:label.slice(0,60),selected:Boolean(chip.isSelected||chip.selected),token:value});
        }
        return result.slice(0,8);
    }
    // Only top-level item renderers become cards. Nested endpoints inside a
    // card (owner links, playlist ids of a video) never add extra records.
    function parse(list,out,group,channel){
        const data=globalThis.MinimalYouTubeSearchData;
        for(const entry of Array.isArray(list)?list:[]){
            if(!entry||typeof entry!=='object'||out.items.length>=600)continue;
            if(entry.continuationItemRenderer){const value=token(entry.continuationItemRenderer);if(value)out.continuation=value;continue;}
            if(entry.continuationItemViewModel){const value=token(entry.continuationItemViewModel);if(value)out.continuation=value;continue;}
            if(out.playlist&&entry.lockupViewModel){const value=lessonItem(entry.lockupViewModel);if(value)out.items.push(value);continue;}
            if(entry.playlistVideoRenderer){const value=playlistItem(entry.playlistVideoRenderer);if(value)out.items.push(value);continue;}
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
            const postValue=entry.backstagePostThreadRenderer?.post||entry.backstagePostRenderer&&entry||entry.postRenderer&&entry||entry.sharedPostRenderer&&entry;
            // Posts belong to a channel's Posts feed only; search never shows them.
            if(postValue){const value=channel?post(postValue):null;if(value)out.items.push(value);continue;}
            if(!channel&&(entry.postRenderer||entry.sharedPostRenderer||entry.backstagePostRenderer))continue;
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
            return Array.isArray(list)?{type:'search',list,content:data}:null;
        }
        if(path==='/playlist'){
            const list=new URL(location.href).searchParams.get('list')||'';
            const browse=[...document.querySelectorAll('ytd-browse')].find(node=>visible(node)&&node.getAttribute('page-subtype')==='playlist')||[...document.querySelectorAll('ytd-browse')].find(visible);
            const tabs=(browse?.data?.contents||browse?.data?.response?.contents)?.twoColumnBrowseResultsRenderer?.tabs;
            const renderer=Array.isArray(tabs)?playlistList(tabs):null;
            // Data for another playlist is a page still in transition.
            if(renderer){
                if(!Array.isArray(renderer.contents)||renderer.playlistId&&renderer.playlistId!==list)return null;
                return {type:'playlist',list:renderer.contents,content:renderer};
            }
            // Courses list their lessons as video lockups in item sections.
            const section=Array.isArray(tabs)?lessonList(tabs):null;
            if(!section)return null;
            const id=String(section.targetId||'').replace(/^VL/,'')||section.contents.map(entry=>entry.itemSectionRenderer?.targetId).find(Boolean)||'';
            if(id&&id!==list)return null;
            return {type:'playlist',list:section.contents,content:section};
        }
        if(!channelPath.test(path)||/\/featured$/.test(path)||/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)$/.test(path))return null;
        const browse=[...document.querySelectorAll('ytd-browse')].find(visible)||document.querySelector('ytd-browse');
        const posts=/\/(?:community|posts)$/.test(path);
        // Posts whose tab data is not on the page still carry their own data
        // on YouTube's post elements: the owned feed reads it from there.
        const fallback=()=>posts&&browse?nodePosts(browse):null;
        const tabs=(browse?.data?.contents||browse?.data?.response?.contents)?.twoColumnBrowseResultsRenderer?.tabs;
        if(!Array.isArray(tabs))return fallback();
        const selected=tabs.map(tab=>tab.tabRenderer||tab.expandableTabRenderer).find(tab=>tab?.selected);
        const url=selected?.endpoint?.commandMetadata?.webCommandMetadata?.url||'';
        // A selected tab for another section is a page still in transition.
        if(!url||url.split('?')[0].replace(/\/$/,'').replace(/\/community$/,'/posts').toLowerCase()!==path.replace(/\/community$/,'/posts').toLowerCase())return fallback();
        const content=selected.content;
        const list=content?.richGridRenderer?.contents||content?.sectionListRenderer?.contents;
        return Array.isArray(list)?{type:posts?'posts':'channel',list,content}:fallback();
    }
    const nodePostLists=new WeakMap();
    function nodePosts(browse){
        const kinds=[['ytd-backstage-post-thread-renderer','backstagePostThreadRenderer'],['ytd-post-renderer','postRenderer'],['ytd-shared-post-renderer','sharedPostRenderer']];
        const selector=kinds.map(([tag])=>tag).join(','),list=[];
        for(const node of browse.querySelectorAll(selector)){
            if(node.parentElement?.closest(selector)||node.closest('[hidden]'))continue;
            const data=node.data||node.__data?.data,key=kinds.find(([tag])=>node.localName===tag)?.[1];
            if(data&&typeof data==='object'&&key)list.push({[key]:data});
        }
        if(!list.length)return null;
        const continuation=[...browse.querySelectorAll('ytd-continuation-item-renderer')].map(node=>node.data||node.__data?.data).filter(Boolean).pop();
        if(continuation)list.push({continuationItemRenderer:continuation});
        // The same posts keep one list, so the model (and loaded pages) stays.
        const first=Object.values(list[0])[0],cached=nodePostLists.get(first);
        if(cached&&cached.length===list.length)return {type:'posts',list:cached,content:null};
        nodePostLists.set(first,list);
        return {type:'posts',list,content:null};
    }
    function model(){
        let found=null;try{found=source();}catch{found=null;}
        if(!found)return null;
        let value=models.get(found.list);
        if(!value){
            value={key:routeKey(),type:found.type,items:[],continuation:'',loading:false,failed:false,chips:[],playlist:found.type==='playlist'};
            try{parse(found.list,value,'',found.type!=='search');value.chips=found.type==='channel'?chips(found.content):[];}catch{return null;}
            models.set(found.list,value);
        }
        return value;
    }
    function publish(){
        const root=document.documentElement;
        const text=current?JSON.stringify({key:current.key,type:current.type,items:current.items,more:Boolean(current.continuation)&&!current.failed,loading:current.loading,chips:current.chips.map(({label,selected})=>({label,selected}))}):'';
        if(text===published)return;
        published=text;
        if(text)root.setAttribute('data-myt-page-model',text);else root.removeAttribute('data-myt-page-model');
        document.dispatchEvent(new Event('minimal-youtube:page-model-updated'));
    }
    document.addEventListener('minimal-youtube:page-model',()=>{current=model();publish();});
    async function load(state,continuation,replace){
        const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{},version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
        if(typeof version!=='string'||!version){state.failed=true;publish();return;}
        state.loading=true;publish();
        const url=new URL(state.type==='search'?'/youtubei/v1/search':'/youtubei/v1/browse',location.origin);url.searchParams.set('prettyPrint','false');
        const key=config('INNERTUBE_API_KEY');if(typeof key==='string'&&key)url.searchParams.set('key',key);
        const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
        try{
            const response=await fetch(url.href,{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json'},
                body:JSON.stringify({continuation,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version}}})});
            if(!response.ok)throw new Error('Continuation failed');
            const data=await response.json();
            const next={items:[],continuation:'',playlist:state.type==='playlist'};
            for(const command of [...(data.onResponseReceivedCommands||[]),...(data.onResponseReceivedActions||[]),...(data.onResponseReceivedEndpoints||[])]){
                const action=command.appendContinuationItemsAction||command.reloadContinuationItemsCommand;
                // A reload names its slot; only the feed's items replace it.
                if(replace&&command.reloadContinuationItemsCommand&&/header/i.test(command.reloadContinuationItemsCommand.slot||''))continue;
                if(Array.isArray(action?.continuationItems))parse(action.continuationItems,next,'',state.type!=='search');
            }
            if(replace)state.items=[];
            const known=new Set(state.items.map(item=>item.href+'|'+item.group));
            for(const item of next.items)if(!known.has(item.href+'|'+item.group)&&state.items.length<600)state.items.push(item);
            state.continuation=next.continuation;state.failed=false;
        }catch{if(!replace)state.failed=true;}
        finally{clearTimeout(timeout);state.loading=false;}
        if(current===state)publish();
    }
    // Playlist edits run as YouTube's own web client sends them: the page's
    // client context and the signed-in session's authorization header.
    async function authorization(){
        const cookies=Object.fromEntries(document.cookie.split(/;\s*/).map(part=>{const index=part.indexOf('=');return [part.slice(0,index),part.slice(index+1)];}));
        const sid=cookies.SAPISID||cookies['__Secure-3PAPISID'];if(!sid)return '';
        const time=Math.floor(Date.now()/1000),digest=await crypto.subtle.digest('SHA-1',new TextEncoder().encode(time+' '+sid+' '+location.origin));
        return 'SAPISIDHASH '+time+'_'+[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
    }
    function report(id,ok,message=''){
        document.documentElement.setAttribute('data-myt-page-model-action-result',JSON.stringify({id,ok,message}));
        document.dispatchEvent(new Event('minimal-youtube:page-model-action-result'));
    }
    async function runAction(state,id){
        const action=actions.get(id);
        const context=config('INNERTUBE_CONTEXT')||{},client=context.client||{},version=client.clientVersion||config('INNERTUBE_CONTEXT_CLIENT_VERSION');
        if(!action||typeof version!=='string'||!version){report(id,false);return;}
        const url=new URL(action.api,location.origin);url.searchParams.set('prettyPrint','false');
        const key=config('INNERTUBE_API_KEY');if(typeof key==='string'&&key)url.searchParams.set('key',key);
        const headers={'Content-Type':'application/json','X-Origin':location.origin,'X-Youtube-Client-Name':String(config('INNERTUBE_CONTEXT_CLIENT_NAME')||1),'X-Youtube-Client-Version':version,'X-Goog-AuthUser':String(config('SESSION_INDEX')??0)};
        const visitor=config('VISITOR_DATA');if(typeof visitor==='string'&&visitor)headers['X-Goog-Visitor-Id']=visitor;
        const page=config('DELEGATED_SESSION_ID');if(typeof page==='string'&&page)headers['X-Goog-PageId']=page;
        try{const auth=await authorization();if(auth)headers.Authorization=auth;}catch{}
        const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
        try{
            const response=await fetch(url.href,{method:'POST',credentials:'include',signal:controller.signal,headers,
                body:JSON.stringify({...action.payload,context:{...context,client:{...client,clientName:client.clientName||'WEB',clientVersion:version}}})});
            const result=await response.json().catch(()=>({}));
            if(!response.ok||result.status&&result.status!=='STATUS_SUCCEEDED')throw new Error('Edit failed');
            // Mirror the edit in this page's list. Saves to other playlists
            // leave it as it is.
            const current=new URL(location.href).searchParams.get('list')||'';
            if(action.playlistId===current||!action.playlistId){
                const index=state.items.findIndex(item=>item.setVideoId&&item.setVideoId===action.setVideoId||!action.setVideoId&&item.id===action.videoId);
                if(index>=0&&action.kind==='remove')state.items.splice(index,1);
                else if(index>=0&&action.kind==='move'){
                    const [item]=state.items.splice(index,1),change=action.change;
                    let target=change.movedSetVideoIdSuccessor?state.items.findIndex(other=>other.setVideoId===change.movedSetVideoIdSuccessor):change.movedSetVideoIdPredecessor?state.items.findIndex(other=>other.setVideoId===change.movedSetVideoIdPredecessor)+1:/AFTER/.test(change.action||'')?0:state.items.length;
                    if(target<0)target=/AFTER/.test(change.action||'')?0:state.items.length;
                    state.items.splice(target,0,item);
                }
                state.items.forEach((item,position)=>{if(/^\d+$/.test(item.index))item.index=String(position+1);});
            }
            report(id,true);
        }catch{report(id,false);}
        finally{clearTimeout(timeout);}
        if(current===state)publish();
    }
    document.addEventListener('minimal-youtube:page-model-action',()=>{
        const state=current,id=document.documentElement.getAttribute('data-myt-page-model-action')||'';
        if(!state||state.type!=='playlist'||state.key!==routeKey()||!actions.has(id))return;
        runAction(state,id);
    });
    document.addEventListener('minimal-youtube:page-model-more',()=>{
        const state=current;
        if(!state||state.loading||!state.continuation||state.failed||state.key!==routeKey())return;
        load(state,state.continuation,false);
    });
    // Sort chips reload the section's feed with their own continuation.
    document.addEventListener('minimal-youtube:page-model-chip',()=>{
        const state=current,index=Number(document.documentElement.getAttribute('data-myt-page-model-chip'));
        const chip=state?.chips?.[index];
        if(!chip||chip.selected||state.loading||state.key!==routeKey())return;
        for(const item of state.chips)item.selected=item===chip;
        load(state,chip.token,true);
    });
    // Public watch page data: title, description with its links and
    // timestamps, chapters, views, date, owner and the playlist panel. Data
    // for another video (a page still in transition) is never published.
    const watchModels=new WeakMap();
    function attributed(value,video){
        const data=globalThis.MinimalYouTubeSearchData;
        if(!value||typeof value!=='object')return null;
        if(typeof value.content==='string'){
            const text=value.content.slice(0,20000),runs=(Array.isArray(value.commandRuns)?value.commandRuns:[]).filter(run=>Number.isInteger(run.startIndex)&&Number.isInteger(run.length)&&run.length>0).sort((a,b)=>a.startIndex-b.startIndex);
            const parts=[];let at=0;
            for(const run of runs){
                if(run.startIndex<at||run.startIndex+run.length>text.length)continue;
                if(run.startIndex>at)parts.push({text:text.slice(at,run.startIndex)});
                const command=run.onTap?.innertubeCommand||run.onTap,watch=command?.watchEndpoint;
                parts.push({text:text.slice(run.startIndex,run.startIndex+run.length),href:data.endpoint(command)||'',seconds:watch&&watch.videoId===video&&Number.isFinite(watch.startTimeSeconds)?watch.startTimeSeconds:null});
                at=run.startIndex+run.length;
            }
            if(at<text.length)parts.push({text:text.slice(at)});
            return parts;
        }
        if(Array.isArray(value.runs))return value.runs.slice(0,2000).map(run=>{const watch=run.navigationEndpoint?.watchEndpoint;return {text:String(run.text||''),href:run.navigationEndpoint?data.endpoint(run.navigationEndpoint):'',seconds:watch&&watch.videoId===video&&Number.isFinite(watch.startTimeSeconds)?watch.startTimeSeconds:null};});
        if(typeof value.simpleText==='string')return [{text:value.simpleText}];
        return null;
    }
    function find(root,test,limit=4000){
        const stack=[root],seen=new Set();let scans=0;
        while(stack.length&&scans++<limit){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            const found=test(item);if(found)return found;
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return null;
    }
    function watchModel(){
        const data=globalThis.MinimalYouTubeSearchData;
        if(location.pathname!=='/watch'||!data)return null;
        const video=new URL(location.href).searchParams.get('v')||'';
        const flexy=[...document.querySelectorAll('ytd-watch-flexy')].find(node=>!node.hidden)||document.querySelector('ytd-watch-flexy');
        const response=flexy?.data?.contents?flexy.data:flexy?.data?.response||flexy?.__data?.data;
        if(!response||response.currentVideoEndpoint?.watchEndpoint?.videoId!==video)return null;
        let model=watchModels.get(response);if(model)return model;
        const results=response.contents?.twoColumnWatchNextResults,contents=results?.results?.results?.contents||[];
        const primary=contents.find(item=>item.videoPrimaryInfoRenderer)?.videoPrimaryInfoRenderer||{};
        const secondary=contents.find(item=>item.videoSecondaryInfoRenderer)?.videoSecondaryInfoRenderer||{};
        const panels=response.engagementPanels||[];
        const body=find(panels,item=>item.expandableVideoDescriptionBodyRenderer)?.expandableVideoDescriptionBodyRenderer;
        const header=find(panels,item=>item.videoDescriptionHeaderRenderer)?.videoDescriptionHeaderRenderer||{};
        const description=attributed(body?.attributedDescriptionBodyText,video)||attributed(secondary.attributedDescription,video)||attributed(secondary.description,video)||[];
        const chapters=[];
        const markers=find(panels,item=>item.macroMarkersListRenderer&&(item.macroMarkersListRenderer.contents||[]).some(entry=>entry.macroMarkersListItemRenderer)&&item);
        for(const entry of markers?.macroMarkersListRenderer?.contents||[]){
            const item=entry.macroMarkersListItemRenderer;if(!item)continue;
            const at=item.onTap?.watchEndpoint?.startTimeSeconds;
            const title=data.label(item.title).trim();
            if(Number.isFinite(at)&&title&&!chapters.some(chapter=>chapter.seconds===at))chapters.push({title:title.slice(0,300),time:data.label(item.timeDescription).trim().slice(0,20),seconds:at});
        }
        if(!chapters.length){
            const bar=find(response.playerOverlays,item=>item.multiMarkersPlayerBarRenderer)?.multiMarkersPlayerBarRenderer;
            for(const map of bar?.markersMap||[])for(const entry of map.value?.chapters||[]){
                const item=entry.chapterRenderer,at=Math.floor((item?.timeRangeStartMillis||0)/1000),title=data.label(item?.title).trim();
                if(item&&title&&!chapters.some(chapter=>chapter.seconds===at))chapters.push({title:title.slice(0,300),time:'',seconds:at});
            }
        }
        chapters.sort((a,b)=>a.seconds-b.seconds);
        const viewText=data.label(primary.viewCount?.videoViewCountRenderer?.originalViewCount)||data.label(primary.viewCount?.videoViewCountRenderer?.viewCount)||data.label(header.views);
        const live=Boolean(primary.viewCount?.videoViewCountRenderer?.isLive);
        const views=!live&&/^\D*([\d][\d\s,.\u00a0\u202f]*)\D*$/.test(viewText)?viewText.replace(/\D/g,''):'';
        const ownerRenderer=secondary.owner?.videoOwnerRenderer||{},ownerRun=ownerRenderer.title?.runs?.find(run=>run.navigationEndpoint);
        const playlist=results?.playlist?.playlist;
        let panel=null;
        if(playlist&&Array.isArray(playlist.contents)){
            const items=[];
            for(const entry of playlist.contents.slice(0,500)){
                const item=entry.playlistPanelVideoRenderer;if(!item||!/^[-\w]{3,64}$/.test(String(item.videoId||'')))continue;
                items.push({id:item.videoId,title:data.label(item.title).trim().slice(0,500)||'Unavailable video',channel:data.label(item.shortBylineText||item.longBylineText).trim().slice(0,300),
                    duration:data.label(item.lengthText).trim().slice(0,20),index:data.label(item.indexText).trim().slice(0,12),image:data.image(item.thumbnail),
                    href:data.endpoint(item.navigationEndpoint)||data.url('/watch?v='+item.videoId+'&list='+encodeURIComponent(playlist.playlistId||'')),selected:Boolean(item.selected)||item.videoId===video,progress:data.progress(item)});
            }
            panel={id:String(playlist.playlistId||''),title:data.label(playlist.title).trim().slice(0,500),owner:data.label(playlist.ownerName||playlist.longBylineText||playlist.shortBylineText).trim().slice(0,300),
                total:Number(playlist.totalVideos)||items.length,current:Number.isInteger(playlist.localCurrentIndex)?playlist.localCurrentIndex:Number.isInteger(playlist.currentIndex)?playlist.currentIndex:items.findIndex(item=>item.selected),
                infinite:Boolean(playlist.isInfinite),items};
        }
        const viewers=live&&/\d/.test(viewText)?(viewText.match(/\d[\d\s,.\u00a0\u202f]*/)?.[0]||'').replace(/\D/g,'').slice(0,12):'';
        model={video,title:data.label(primary.title).trim().slice(0,1000),description,chapters,views,live,viewers,
            date:data.label(primary.dateText).trim().slice(0,100)||data.label(header.publishDate).trim().slice(0,100),
            owner:{name:data.label(ownerRenderer.title).trim().slice(0,300),href:data.endpoint(ownerRun?.navigationEndpoint)||'',avatar:data.image(ownerRenderer.thumbnail),subscribers:data.label(ownerRenderer.subscriberCountText).trim().slice(0,100)},
            playlist:panel};
        watchModels.set(response,model);
        return model;
    }
    document.addEventListener('minimal-youtube:watch-model',()=>{
        const root=document.documentElement;let text='';
        if(root.classList.contains('minimal-youtube'))try{const model=watchModel();text=model?JSON.stringify(model):'';}catch{text='';}
        if(root.getAttribute('data-myt-watch-model')!==text){if(text)root.setAttribute('data-myt-watch-model',text);else root.removeAttribute('data-myt-watch-model');}
    });
    // YouTube's search filters, read where YouTube keeps them: the filter
    // strip's own data, the filter dialog command of the newer header, or
    // the page data. Each filter keeps YouTube's own action (its URL).
    function filterGroups(root,limit=20000){
        const data=globalThis.MinimalYouTubeSearchData,groups=[],seen=new Set(),stack=[root],visited=new Set();let scans=0;
        while(stack.length&&scans++<limit&&groups.length<8){
            const item=stack.pop();if(!item||typeof item!=='object'||visited.has(item))continue;visited.add(item);
            const group=item.searchFilterGroupRenderer;
            if(group){
                const title=data.label(group.title).trim(),options=[];
                for(const entry of group.filters||[]){
                    const filter=entry.searchFilterRenderer;if(!filter)continue;
                    const label=data.label(filter.label).trim(),href=data.endpoint(filter.navigationEndpoint);
                    const selected=/SELECTED/.test(filter.status||'')&&!/UNSELECTED/.test(filter.status||'');
                    if(label&&(href||selected))options.push({label:label.slice(0,60),href,selected});
                }
                if(title&&options.length&&!seen.has(title)){seen.add(title);groups.push({title:title.slice(0,60),options:options.slice(0,12)});}
                continue;
            }
            // Result lists are large and hold no filters.
            const children=Object.entries(item).filter(([key,child])=>child&&typeof child==='object'&&(Array.isArray(item)||!/^(?:contents|items|continuationItems)$/.test(key)));
            for(let i=children.length-1;i>=0;i--)stack.push(children[i][1]);
        }
        return groups;
    }
    document.addEventListener('minimal-youtube:search-filters',()=>{
        const root=document.documentElement;let value=null;
        if(root.classList.contains('minimal-youtube')&&location.pathname==='/results'&&globalThis.MinimalYouTubeSearchData){
            try{
                const search=document.querySelector('#myt-search')?.closest('ytd-search')||[...document.querySelectorAll('ytd-search')].find(visible);
                const sources=[
                    ['filter strip',[...(search?.querySelectorAll('ytd-search-sub-menu-renderer,yt-search-sub-menu-view-model')||[])].map(node=>node.data||node.__data?.data)],
                    ['filter dialog',[...(search?.querySelectorAll('ytd-search-header-renderer,yt-search-header-view-model,ytd-search-filter-options-dialog-renderer')||[]),...document.querySelectorAll('ytd-popup-container ytd-search-filter-options-dialog-renderer')].map(node=>node.data||node.__data?.data)],
                    ['page data',[(search?.data?.contents||search?.data?.response?.contents)?.twoColumnSearchResultsRenderer,search?.data?.header||search?.data?.response?.header]]];
                for(const [name,roots]of sources){
                    const groups=filterGroups(roots.filter(Boolean));
                    if(groups.length){value={source:name,groups};break;}
                }
            }catch{value=null;}
        }
        const text=value?JSON.stringify(value):'';
        if(root.getAttribute('data-myt-search-filters-data')!==text){if(text)root.setAttribute('data-myt-search-filters-data',text);else root.removeAttribute('data-myt-search-filters-data');}
    });
    // Public channel identity for the owned header: name, avatar, banner and
    // the verified badge. Account controls are not part of it.
    function largest(root,test){
        const stack=[root],seen=new Set();let scans=0;
        while(stack.length&&scans++<3000){
            const item=stack.pop();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
            for(const [key,child]of Object.entries(item)){if(test(key)&&child&&typeof child==='object')return globalThis.MinimalYouTubeSearchData.image(child);if(child&&typeof child==='object')stack.push(child);}
        }
        return '';
    }
    document.addEventListener('minimal-youtube:channel-identity',()=>{
        const root=document.documentElement,data=globalThis.MinimalYouTubeSearchData;
        if(!root.classList.contains('minimal-youtube')||!data)return;
        let value=null;
        try{
            const browse=[...document.querySelectorAll('ytd-browse')].find(visible)||document.querySelector('ytd-browse');
            const response=browse?.data?.response||browse?.data,meta=response?.metadata?.channelMetadataRenderer,header=response?.header;
            const base=(location.pathname.match(/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)/)?.[0]||'').toLowerCase();
            const urls=[meta?.vanityChannelUrl,meta?.channelUrl,...(Array.isArray(meta?.ownerUrls)?meta.ownerUrls:[])].map(url=>{try{return new URL(url,location.origin).pathname.toLowerCase();}catch{return '';}});
            // Identity for another channel is a page still in transition.
            if(meta&&(urls.includes(base)||base==='/channel/'+String(meta.externalId||'').toLowerCase())){
                const text=JSON.stringify(header||{});
                value={base,title:String(meta.title||'').slice(0,300),avatar:data.image(meta.avatar)||largest(header,key=>/avatar/i.test(key)),
                    banner:largest(header,key=>/banner/i.test(key)&&!/tv|mobile/i.test(key)),
                    verified:/CHECK_CIRCLE|BADGE_STYLE_TYPE_VERIFIED|"verified"/i.test(text)};
            }
        }catch{value=null;}
        const text=value?JSON.stringify(value):'';
        if(root.getAttribute('data-myt-channel-identity')!==text){if(text)root.setAttribute('data-myt-channel-identity',text);else root.removeAttribute('data-myt-channel-identity');}
    });
})();
