/* Runs in YouTube's MAIN world before bootstrap. Discards hidden feed data
   and explicit player ad placements. Stream URLs, formats, authorization and
   playability stay native; discarded data is never copied or backed up. */
(() => {
    "use strict";
    if (globalThis.__minimalYouTubeDataPruning) return;
    Object.defineProperty(globalThis, "__minimalYouTubeDataPruning", { value: true });
    const nativeParse = JSON.parse;
    const nativeResponseJSON = Response.prototype.json;
    const shorts = new Set(["reelShelfRenderer", "reelItemRenderer", "shortsShelfRenderer", "shortsLockupViewModel", "shortsLockupViewModelV2"]);
    const related = new Set(["compactVideoRenderer", "compactPlaylistRenderer", "compactRadioRenderer", "videoRenderer", "playlistRenderer", "radioRenderer", "lockupViewModel", "richItemRenderer", "relatedChipCloudRenderer", "continuationItemRenderer"]);
    const relatedTargets = new Set(["watch-next-feed", "watch-next-feed-recommendations", "watch-secondary-results"]);
    let processed = new WeakSet();
    let enabled = false;
    const initialHooks = new Map();
    // Retain small public card summaries: lazy native thumbnails/avatars may
    // never mount once their source card is visually hidden.
    const searchPlaylists = new Map();
    const searchChannels = new Map();
    const searchRecords=new Map();let searchFilters=[];
    // Read Polymer/view-model data in MAIN as well as response data. SPA search
    // responses may arrive before the URL changes and lazy avatar DOM can stay empty.
    document.addEventListener('minimal-youtube:search-snapshot',()=>{
        const model=globalThis.MinimalYouTubeSearchData;if(!enabled||!model||location.pathname!=='/results')return;
        const records=new Map(searchRecords),filters=[...searchFilters];
        const search=document.querySelector('#myt-search')?.closest('ytd-search')||document.querySelector('ytd-search');
        for(const data of [search?.data,window.ytInitialData]){
            const found=model.collect(data);for(const value of found.records)records.set(value.href,value);filters.push(...found.filters);
        }
        const result=[];
        for(const node of document.querySelectorAll('[data-myt-search-source-key]')){
            const hint=node.getAttribute('data-myt-search-source-kind')||'';
            let value;for(const data of [node.data,node.__data?.data,node.__data?.data?.data]){value=model.record(data,hint)||model.collect(data).records.find(item=>item.kind===hint);if(value)break;}
            if(!value){const href=[...node.querySelectorAll('a[href]')].map(link=>model.youtube(link.href)).find(href=>records.has(href));value=records.get(href);}
            if(!value){const name=(node.querySelector('ytd-channel-name,#channel-title,h3')?.textContent||'').trim();const matches=[...records.values()].filter(item=>item.kind===hint&&item.title===name);if(matches.length===1)value=matches[0];}
            if(value)result.push({key:node.getAttribute('data-myt-search-source-key'),...value});
        }
        const snapshot=JSON.stringify({records:result,filters:filters.slice(0,100)}),root=document.documentElement;
        if(root&&root.getAttribute('data-myt-search-snapshot')!==snapshot)root.setAttribute('data-myt-search-snapshot',snapshot);
    });
    const label=value=>typeof value==='string'?value:value?.simpleText||value?.content||value?.runs?.map(run=>run.text||'').join('')||'';
    function channelSummary(node){
        const legacy=node.channelRenderer||node.gridChannelRenderer,modern=node.lockupViewModel;
        const value=legacy||(/CHANNEL/.test(modern?.contentType||'')?modern:null);
        if(!value)return null;
        const endpoint=value.navigationEndpoint?.browseEndpoint||value.rendererContext?.commandContext?.onTap?.innertubeCommand?.browseEndpoint||{};
        const id=value.channelId||endpoint.browseId||value.contentId;
        if(typeof id!=='string'||!/^UC[-\w]{22}$/.test(id))return null;
        const name=label(value.title||modern?.metadata?.lockupMetadataViewModel?.title).slice(0,300);
        const metadata=[label(value.subscriberCountText),label(value.videoCountText)].filter(text=>text&&text.length<=300);
        let url=endpoint.canonicalBaseUrl||value.navigationEndpoint?.commandMetadata?.webCommandMetadata?.url||'';
        url=url.replace(/^https:\/\/(?:www\.)?youtube\.com(?=\/)/i,'').split(/[?#]/)[0];
        if(!/^\/(?:@[^/]+|channel\/UC[-\w]{22}|(?:c|user)\/[^/]+)\/?$/.test(url))url='/channel/'+id;
        const handle=url.startsWith('/@')?url.slice(1):metadata.find(text=>/^@\S+$/.test(text))||'';
        if(url==='/channel/'+id&&handle)url='/'+handle;
        let image='',width=-1;const stack=[value.thumbnail||value.avatar||value.contentImage];let scans=0;
        while(stack.length&&scans++<800){
            const item=stack.pop();if(!item||typeof item!=='object')continue;
            if(typeof item.url==='string'&&/^https:\/\//.test(item.url)&&item.url.length<2048){const size=Number(item.width)||0;if(size>width){width=size;image=item.url;}}
            for(const child of Object.values(item))if(child&&typeof child==='object')stack.push(child);
        }
        return {id,name,url,handle,image,metadata};
    }
    function playlistSummary(node) {
        const legacy=node.playlistRenderer||node.gridPlaylistRenderer,modern=node.lockupViewModel;
        if(!legacy&&!(modern&&(modern.contentImage?.collectionThumbnailViewModel||/PLAYLIST/.test(modern.contentType||''))))return null;
        const value=legacy||modern,id=value.playlistId||value.contentId;
        if(typeof id!=='string'||!/^[-\w]{2,200}$/.test(id))return null;
        const strings=[];let image='',width=-1;
        const visit=(root,images=false)=>{
            const stack=[root];let visited=0;
            while(stack.length&&visited++<800){
                const item=stack.pop();if(!item)continue;
                if(typeof item==='string'){if(!images&&item.length<200)strings.push(item);continue;}
                if(typeof item!=='object')continue;
                if(images&&typeof item.url==='string'&&/^https:\/\//.test(item.url)&&item.url.length<2048){const size=Number(item.width)||0;if(size>width){image=item.url;width=size;}}
                if(Array.isArray(item)){for(let i=item.length-1;i>=0;i--)stack.push(item[i]);}
                else for(const[key,child]of Object.entries(item))if(images||['text','content','simpleText','runs','metadata','metadataRows','metadataParts','contentMetadataViewModel','lockupMetadataViewModel','badges','thumbnailBadges','thumbnailBadgeViewModel','thumbnailOverlayBadgeViewModel','thumbnailBottomOverlayViewModel','overlays'].includes(key))stack.push(child);
            }
        };
        visit(legacy?.thumbnail||legacy?.thumbnails||modern?.contentImage?.collectionThumbnailViewModel?.primaryThumbnail||modern?.contentImage,true);
        if(legacy?.thumbnailRenderer)visit(legacy.thumbnailRenderer,true);
        visit(legacy?.videoCountText);visit(legacy?.videoCountShortText);visit(modern?.metadata);
        // Count badges can live on the thumbnail rather than in metadata rows.
        const imageStack=[modern?.contentImage];let scans=0;
        while(imageStack.length&&scans++<800){const item=imageStack.pop();if(!item||typeof item!=='object')continue;for(const[key,child]of Object.entries(item)){if(/badge|overlay/i.test(key))visit(child);if(child&&typeof child==='object')imageStack.push(child);}}
        let count=legacy?.videoCount!=null?String(legacy.videoCount):'';
        if(!/^[\d][\d\s,.]*\+?$/.test(count))count=strings.map(text=>text.match(/([\d][\d\s,.]*\+?)\s*(?:videos?|видео|ролик\S*)/iu)?.[1]?.trim()).find(Boolean)||strings.find(text=>/^[\d][\d\s,.]*\+?$/.test(text))||'';
        return image||count?{id,image,count}:null;
    }
    function hookInitial(name) {
        let descriptor = Object.getOwnPropertyDescriptor(window, name);
        if (descriptor && !descriptor.configurable) return;
        let value = descriptor?.value;
        const original = descriptor ? { ...descriptor } : { configurable: true, enumerable: true, writable: true };
        delete original.value;descriptor = undefined;
        const get = () => original.get ? original.get.call(window) : value;
        const set = incoming => {
            const result = trim(incoming);
            if (original.set) original.set.call(window, result);
            else value = result;
        };
        Object.defineProperty(window, name, { configurable: true, enumerable: original.enumerable, get, set });
        initialHooks.set(name, () => {
            if (Object.getOwnPropertyDescriptor(window, name)?.set === set) {
                const current = get();
                Object.defineProperty(window, name, (Object.hasOwn(original, "get") || Object.hasOwn(original, "set")) ? original : { ...original, value: current });
            }
            value = undefined;
        });
        const current = get();if (current) set(current);
    }
    const playerAdKeys = ["playerAds", "adPlacements", "adSlots"];
    function stripPlayerAds(player) {
        if (!player || typeof player !== "object") return;
        const adResponse = player.responseContext && playerAdKeys.some(key => Array.isArray(player[key]));
        if (!(player.playabilityStatus || player.streamingData || player.videoDetails || adResponse)) return;
        for (const key of playerAdKeys) if (Object.hasOwn(player, key)) delete player[key];
    }
    function shortItem(item) {
        if (!item || typeof item !== "object") return false;
        if (Object.keys(item).some(key => shorts.has(key)||/^shorts(?:LockupViewModel|Shelf(?:Renderer|ViewModel))(?:V\d+)?$/.test(key))) return true;
        const header=item.sectionHeaderRenderer||item.sectionHeaderViewModel;
        const headerTitle=header?.title?.simpleText||header?.title?.runs?.map(run=>run.text).join('')||header?.title?.content;
        if(typeof headerTitle==='string'&&/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu.test(headerTitle))return true;
        if (item.richShelfRenderer?.isShorts === true) return true;
        if (item.richSectionRenderer) return shortItem(item.richSectionRenderer.content);
        if (item.richItemRenderer) return shortItem(item.richItemRenderer.content);
        const lockup=item.lockupViewModel;
        if(/SHORTS/.test(lockup?.contentType||'')||item.videoRenderer?.navigationEndpoint?.reelWatchEndpoint||lockup?.rendererContext?.commandContext?.onTap?.innertubeCommand?.reelWatchEndpoint)return true;
        const url = item.videoRenderer?.navigationEndpoint?.commandMetadata?.webCommandMetadata?.url;
        return typeof url === "string" && /^\/shorts(?:\/|$)/.test(url);
    }
    const chatKeys = new Set(["liveChatRenderer", "liveChatReplayRenderer", "liveChatViewModel", "liveChatContinuation"]);
    function chatItem(item) {
        if (!item || typeof item !== "object") return false;
        if (Object.keys(item).some(key => chatKeys.has(key))) return true;
        const panel = item.engagementPanelSectionListRenderer;
        return Boolean(panel && [panel.targetId, panel.panelIdentifier].some(id => /live[-_]?chat/i.test(id || "")));
    }
    // Watch-page panels the owned page never offers: ad panels (incl. the ads
    // business chat) and the search preview. Description, transcript,
    // chapters and comments panels stay: the owned page uses them.
    const unusedPanelTarget = /^(?:engagement-panel-ads(?:-.*)?|PAsearch_preview)$/;
    function unusedPanel(item) {
        const panel = item?.engagementPanelSectionListRenderer;
        return Boolean(panel && [panel.targetId, panel.panelIdentifier].some(id => unusedPanelTarget.test(id || "")));
    }
    function hiddenShelf(item) {
        const content = item?.richSectionRenderer?.content || item;
        const shelf = content?.shelfRenderer || content?.richShelfRenderer;
        if (!shelf) return false;
        const title = shelf.title?.simpleText || shelf.title?.runs?.map(run => run.text).join("") || "";
        if(/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu.test(title))return true;
        if (location.pathname === "/results") return false;
        return /^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/.test(location.pathname) && /^(new uploads|новые (?:видео|загрузки)|последние (?:видео|загрузки))(?=$|\s)/iu.test(title);
    }
    function compact(array, remove) {
        let kept = 0;
        for (const item of array) if (!remove(item)) array[kept++] = item;
        const removed = array.length - kept;
        array.length = kept;
        return removed;
    }
    function trimRecommendations(root) {
        const seen = new WeakSet();
        function visit(node) {
            if (!node || typeof node !== "object" || seen.has(node)) return 0;
            seen.add(node);
            if (node.playlistPanelRenderer || node.liveChatRenderer || node.engagementPanelSectionListRenderer ||
                /comments/.test(node.itemSectionRenderer?.targetId || "")) return 0;
            let removed = 0;
            if (Array.isArray(node)) {
                removed += compact(node, item => item && Object.keys(item).some(key => related.has(key)));
                for (const child of node) removed += visit(child);
            } else {
                for (const child of Object.values(node)) removed += visit(child);
                if (removed && ((Array.isArray(node.contents) && !node.contents.length) ||
                    (Array.isArray(node.results) && !node.results.length))) delete node.continuations;
            }
            return removed;
        }
        return visit(root);
    }
    function feed(data) {
        if (data?.streamingData || data?.playabilityStatus || data?.videoDetails) return false;
        const contents = data?.contents;
        return Boolean(contents?.twoColumnWatchNextResults || contents?.twoColumnSearchResultsRenderer ||
            contents?.twoColumnBrowseResultsRenderer || contents?.singleColumnBrowseResultsRenderer ||
            data?.onResponseReceivedActions || data?.onResponseReceivedCommands || data?.onResponseReceivedEndpoints ||
            data?.continuationContents);
    }
    function trim(data) {
        if (!enabled || !data || typeof data !== "object") return data;
        try { stripPlayerAds(data);stripPlayerAds(data.playerResponse); } catch { /* Immutable/revived player data stays native. */ }
        if (!feed(data) || processed.has(data)) return data;
        if(globalThis.MinimalYouTubeSearchData&&(data.contents?.twoColumnSearchResultsRenderer||location.pathname==='/results')){
            const found=globalThis.MinimalYouTubeSearchData.collect(data);
            if(data.contents?.twoColumnSearchResultsRenderer){searchRecords.clear();searchFilters=[];}
            for(const value of found.records){searchRecords.set(value.href,value);while(searchRecords.size>600)searchRecords.delete(searchRecords.keys().next().value);}
            if(found.filters.length)searchFilters=found.filters.slice(0,100);
        }
        try {
            let removed = 0, playlistDataChanged = false, channelDataChanged = false;
            const secondary = data.contents?.twoColumnWatchNextResults?.secondaryResults;
            if (secondary) removed += trimRecommendations(secondary);
            const seen = new WeakSet();
            const stack = [data];
            while (stack.length) {
                const node = stack.pop();
                if (!node || typeof node !== "object" || seen.has(node)) continue;
                seen.add(node);
                if (Array.isArray(node)) {
                    removed += compact(node, item => shortItem(item) || hiddenShelf(item) || chatItem(item) || unusedPanel(item));
                    for (const child of node) if (child && typeof child === "object") stack.push(child);
                    continue;
                }
                if(location.pathname==='/results'){
                    const channel=channelSummary(node);
                    if(channel){
                        const previous=searchChannels.get(channel.id)||{};
                        const next={...channel,url:channel.url==='/channel/'+channel.id?(previous.url||channel.url):channel.url,handle:channel.handle||previous.handle||'',image:channel.image||previous.image||'',name:channel.name||previous.name||'',metadata:channel.metadata.length?channel.metadata:previous.metadata||[]};
                        if(JSON.stringify(previous)!==JSON.stringify(next)){searchChannels.delete(next.id);searchChannels.set(next.id,next);channelDataChanged=true;while(searchChannels.size>200)searchChannels.delete(searchChannels.keys().next().value);}
                    }
                    const summary=playlistSummary(node);
                    if(summary){
                        const previous=searchPlaylists.get(summary.id)||{};
                        const next={id:summary.id,image:summary.image||previous.image||'',count:summary.count||previous.count||''};
                        if(next.image!==previous.image||next.count!==previous.count){searchPlaylists.delete(next.id);searchPlaylists.set(next.id,next);playlistDataChanged=true;while(searchPlaylists.size>200)searchPlaylists.delete(searchPlaylists.keys().next().value);}
                    }
                }
                // Discard both live and archived chat before an iframe/polling
                // controller is created; player streaming metadata is excluded.
                if (chatItem(node.conversationBar)) { delete node.conversationBar; removed++; }
                for (const key of chatKeys) if (Object.hasOwn(node, key)) { delete node[key]; removed++; }
                // These fields are only used to start hover/animated previews.
                // Static thumbnails and the click/navigation endpoint stay intact.
                if (node.inlinePlaybackEndpoint) { delete node.inlinePlaybackEndpoint; removed++; }
                if (node.richThumbnail?.movingThumbnailRenderer) { delete node.richThumbnail; removed++; }
                const action = node.appendContinuationItemsAction || node.reloadContinuationItemsCommand;
                if (action && relatedTargets.has(action.targetId) && Array.isArray(action.continuationItems)) {
                    removed += trimRecommendations(action.continuationItems);
                }
                for (const value of Object.values(node)) if (value && typeof value === "object") stack.push(value);
            }
            processed.add(data);
            if(playlistDataChanged)document.documentElement?.setAttribute('data-myt-search-playlists',JSON.stringify([...searchPlaylists.values()]));
            if(channelDataChanged)document.documentElement?.setAttribute('data-myt-search-channels',JSON.stringify([...searchChannels.values()]));
            if (removed && document.documentElement && !document.documentElement.hasAttribute("data-myt-pruned")) {
                document.documentElement.setAttribute("data-myt-pruned", "");
            }
        } catch { /* Unexpected A/B-test data must not break native parsing. */ }
        return data;
    }
    function parse(...args) { return trim(Reflect.apply(nativeParse, this, args)); }
    function responseJSON(...args) { return Reflect.apply(nativeResponseJSON, this, args).then(trim); }
    function install() {
        JSON.parse = parse;
        Response.prototype.json = responseJSON;
        hookInitial("ytInitialData");
        hookInitial("ytInitialPlayerResponse");
    }
    function uninstall() {
        if (JSON.parse === parse) JSON.parse = nativeParse;
        if (Response.prototype.json === responseJSON) Response.prototype.json = nativeResponseJSON;
        for (const restore of initialHooks.values()) restore();
        initialHooks.clear();
    }
    function configure(value) {
        if (enabled === value) return;
        enabled = value;
        if (enabled) { processed = new WeakSet(); install(); }
        else {uninstall();searchPlaylists.clear();searchChannels.clear();searchRecords.clear();searchFilters=[];for(const name of ['data-myt-search-playlists','data-myt-search-channels','data-myt-search-snapshot'])document.documentElement?.removeAttribute?.(name);}
    }
    document.addEventListener("minimal-youtube:optimization", event => {
        if (typeof event.detail?.enabled === "boolean") configure(event.detail.enabled);
    });
    // DOM geometry comes from the isolated layout, while YouTube's sizing API
    // lives in MAIN. Updating it also recalculates chapter/seekbar pixel widths.
    document.addEventListener("minimal-youtube:player-resize", event => {
        if (!enabled) return;
        const width = event.detail?.width, height = event.detail?.height;
        if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0 || width > 32768 || height > 32768) return;
        try {
            const player = event.target?.matches?.("ytd-watch-flexy") ? event.target.querySelector("#movie_player") : document.querySelector("ytd-watch-flexy:not([hidden]) #movie_player");
            const api = typeof player?.setSize === "function" ? player : player?.closest("ytd-player")?.getApiInterface?.();
            if (typeof api?.setSize === "function") api.setSize(Math.round(width), Math.round(height));
        } catch { /* Native controls keep working when an API variant differs. */ }
    });
    // This script is registered only while focus mode is enabled.
    configure(true);
})();
