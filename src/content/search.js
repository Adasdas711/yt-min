/* Own playlist result cards and a stable controller for native search filters. */
(() => {
    'use strict';
    const channelPath=/^\/(?:@|channel\/|c\/|user\/)/;
    const text=node=>node?.textContent.replace(/\s+/g,' ').trim()||'';
    const safeURL=value=>{if(typeof value!=='string'||!value.trim())return null;try{const url=new URL(value,location.href);return /^https?:$/.test(url.protocol)?url:null;}catch{return null;}};
    const titleSelector='a#video-title,a#video-title-link,h3 a[href],.yt-lockup-metadata-view-model__title,.yt-lockup-metadata-view-model-wiz__title,.ytLockupMetadataViewModelTitle';
    const playlistSelector='ytd-playlist-renderer,ytd-grid-playlist-renderer,yt-lockup-view-model';
    const countSelector='#video-count-text,#video-count,#playlist-video-count,.formatted-video-count-label,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer,yt-thumbnail-overlay-badge-view-model,yt-thumbnail-bottom-overlay-view-model,yt-badge-shape,.ytBadgeShapeText,.yt-badge-shape__text,.badge-shape-wiz__text,[data-video-count]';
    const countNumber=value=>{
        const input=String(value||'').replace(/[\u00a0\u202f]/g,' ').trim();
        return input.match(/([\d][\d\s,.]*\+?)\s*(?:videos?|видео|ролик\S*)/iu)?.[1]?.trim()||(/^[\d][\d\s,.]*\+?$/.test(input)?input:'');
    };
    function coverImage(source){
        const covers=[...source.querySelectorAll('ytd-thumbnail,yt-collection-thumbnail-view-model,yt-thumbnail-view-model,.ytCollectionThumbnailViewModelHost,.ytLockupViewModelContentImage,.yt-lockup-view-model__content-image,.yt-lockup-view-model-wiz__content-image')];
        const images=covers.length?covers.flatMap(node=>[...node.querySelectorAll('img,yt-image,source')]):[...source.querySelectorAll('img,yt-image,source')].filter(node=>!channelPath.test(safeURL(node.closest('a')?.href)?.pathname||''));
        const valid=value=>typeof value==='string'&&value&&!/^data:image\/(?:gif|png);base64,/i.test(value)&&(safeURL(value)||/^data:image\//i.test(value));
        for(const img of images){
            const srcset=img.getAttribute('srcset')||img.getAttribute('data-srcset')||'';
            const options=[img.getAttribute('data-src'),...srcset.split(',').reverse().map(value=>value.trim().split(/\s+/)[0]),img.currentSrc,img.getAttribute('src')];
            const found=options.find(valid);if(found)return found;
        }
        for(const node of covers){const value=getComputedStyle(node).backgroundImage.match(/url\(["']?(.*?)["']?\)/)?.[1];if(valid(value))return value;}
        return '';
    }
    const stylesheet=`:host{display:block;min-width:0;height:100%;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--myt-ink)}*{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}a:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}.surface{display:flex;align-items:center;gap:20px;min-height:128px;height:100%;padding:16px;border-radius:16px;background:var(--myt-card-bg,var(--myt-surface,#19191d))}.surface:hover,.surface:focus-within{background:var(--myt-card-hover-bg,var(--myt-soft))}.cover{position:relative;display:grid;place-items:center;flex:0 0 38%;max-width:280px;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:var(--myt-soft)}.cover img{position:absolute;width:100%;height:100%;object-fit:cover}.cover svg{width:36px;height:36px;color:var(--myt-muted)}.info{min-width:0;flex:1}h3{margin:0;font-size:17px;line-height:1.4;font-weight:600}.title{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}.owner{display:block;margin-top:8px;color:var(--myt-muted);overflow-wrap:anywhere}.owner:hover{text-decoration:underline}.count,.updated{margin:5px 0 0;font-size:13px;color:var(--myt-muted);overflow-wrap:anywhere}@media(max-width:600px){.surface{padding:12px;gap:12px}.cover{flex-basis:38%}h3{font-size:15px}}`;

    class PlaylistCard {
        constructor(source){
            this.source=source;this.parts=new Set();this.host=document.createElement('div');this.host.dataset.mytSearchPlaylistCard='';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${stylesheet}</style><article class="surface"><a class="cover" aria-label="Open playlist"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M3 5h16M3 10h16M3 15h9m3-1 6 4-6 4Z"/></svg><img alt="" loading="lazy" decoding="async"></a><div class="info"><h3><a class="title"></a></h3><a class="owner"></a><p class="count"></p><p class="updated"></p></div></article>`;
            this.q=selector=>this.shadow.querySelector(selector);
            this.q('img').onerror=()=>{this.q('img').hidden=true;};
        }
        update(cache){
            const source=this.source;
            const main=source.querySelector(titleSelector)||source.querySelector('a[href*="/playlist?"],a[href*="list="]');
            const anchors=[...source.querySelectorAll('a[href]')];
            const owner=anchors.find(a=>channelPath.test(safeURL(a.href)?.pathname||'')&&text(a));
            const destination=anchors.map(a=>safeURL(a.href)).find(url=>url?.searchParams.get('list'));
            const stored=cache.get(destination?.searchParams.get('list'));
            const href=destination?new URL('/playlist?list='+encodeURIComponent(destination.searchParams.get('list')),location.origin).href:'';
            const video=anchors.map(a=>safeURL(a.href)?.searchParams.get('v')).find(id=>/^[-\w]{11}$/.test(id||''));
            const src=stored?.image||coverImage(source)||(video?'https://i.ytimg.com/vi/'+video+'/hqdefault.jpg':'');
            // Read metadata independently; creator names can precede count/date.
            const metadata=[...source.querySelectorAll('#video-count-text,#video-count,.formatted-video-count-label,#metadata-line,#published-time-text,#published-time,.yt-content-metadata-view-model__metadata-row,.yt-content-metadata-view-model-wiz__metadata-row,.ytContentMetadataViewModelMetadataRow,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer')].map(text);
            const combined=metadata.join(' · ');
            const badges=[...source.querySelectorAll(countSelector)].flatMap(node=>[node.getAttribute('data-video-count'),text(node),node.getAttribute('aria-label'),node.getAttribute('title')]);
            const count=badges.map(countNumber).find(Boolean)||countNumber(combined)||stored?.count||'';
            let updated=metadata.find(value=>/updated|обновл/iu.test(value))||text(source.querySelector('#published-time-text,#published-time,[data-last-updated]'))||metadata.find(value=>/\bago\b|\btoday\b|\byesterday\b|назад|сегодня|вчера/iu.test(value))||'';
            updated=updated.split(/[·•]/).find(value=>/updated|обновл/iu.test(value))?.trim()||updated;
            if(/updated|обновл/iu.test(updated))updated=updated.replace(/^.*?(?=updated|обновл)/iu,'');
            if(/обновл|назад|сегодня|вчера/iu.test(updated)){
                const match=updated.match(/(\d+)\s*(сек\S*|мин\S*|час\S*|дн\S*|день|дня|недел\S*|мес\S*|год\S*|г\.|лет)/iu);
                const unit=match&&(/сек/iu.test(match[2])?'second':/мин/iu.test(match[2])?'minute':/час/iu.test(match[2])?'hour':/дн|день|дня/iu.test(match[2])?'day':/недел/iu.test(match[2])?'week':/мес/iu.test(match[2])?'month':'year');
                updated=match?'Updated '+new Intl.RelativeTimeFormat('en',{numeric:'auto'}).format(-Number(match[1]),unit):/сегодня/iu.test(updated)?'Updated today':/вчера/iu.test(updated)?'Updated yesterday':'Update time unavailable';
            }
            if(updated&&!/^Updated\b/iu.test(updated))updated='Updated '+updated;
            const data={title:text(main)||'Playlist',owner:text(owner),ownerHref:owner?.href||'',href,src,count:count?count+' videos':'',updated:updated||'Update time unavailable'};
            const signature=JSON.stringify(data);
            if(this.signature!==signature){
                this.signature=signature;
                for(const[key,selector]of [['title','.title'],['owner','.owner'],['count','.count'],['updated','.updated']])this.q(selector).textContent=data[key];
                this.q('.owner').hidden=!data.owner;
                this.q('.count').hidden=!data.count;
                for(const link of [this.q('.cover'),this.q('.title')]){if(href)link.href=href;else link.removeAttribute('href');}
                if(owner)this.q('.owner').href=owner.href;else this.q('.owner').removeAttribute('href');
                const img=this.q('img');if(img.getAttribute('src')!==src){if(src)img.src=src;else img.removeAttribute('src');img.hidden=!src;}
            }
            if(this.host.parentElement!==source)source.append(this.host);
            for(const part of this.parts)if(part.parentElement!==source){part.removeAttribute('data-myt-search-playlist-source');this.parts.delete(part);}
            for(const part of source.children)if(part!==this.host&&!this.parts.has(part)){part.setAttribute('data-myt-search-playlist-source','');this.parts.add(part);}
        }
        destroy(){this.host.remove();for(const part of this.parts)part.removeAttribute('data-myt-search-playlist-source');this.parts.clear();}
    }

    class Search {
        constructor(){this.cards=new Map();this.filters=new Map();this.layout=new Map();this.metadata=new Map();this.click=event=>this.toggleFilter(event);document.addEventListener('click',this.click,true);}
        static isPlaylist(card){
            if(card.matches('ytd-playlist-renderer,ytd-grid-playlist-renderer'))return true;
            if(!card.matches('yt-lockup-view-model'))return false;
            if(card.matches('[is-playlist],[content-type="playlist"],[data-content-type="playlist"]'))return true;
            if(card.querySelector('yt-collection-thumbnail-view-model,yt-collections-stack,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer,.ytCollectionThumbnailViewModelHost'))return true;
            const main=card.querySelector(titleSelector);return safeURL(main?.href)?.pathname==='/playlist';
        }
        sync(searches){
            const wanted=new Set();
            const raw=document.documentElement.getAttribute('data-myt-search-playlists')||'';
            if(raw!==this.metadataRaw){this.metadataRaw=raw;this.metadata.clear();try{const values=JSON.parse(raw);if(Array.isArray(values))for(const value of values.slice(-200))if(typeof value.id==='string')this.metadata.set(value.id,{image:safeURL(value.image)?.href||'',count:countNumber(value.count)});}catch{}}
            this.syncLayout(searches);
            for(const search of searches){
                for(const source of search.querySelectorAll('[data-myt-search-playlist]')){
                    wanted.add(source);let card=this.cards.get(source);if(!card){card=new PlaylistCard(source);this.cards.set(source,card);}card.update(this.metadata);
                }
                for(const header of search.querySelectorAll('ytd-search-sub-menu-renderer')){
                    const panel=header.querySelector('tp-yt-iron-collapse,iron-collapse,#collapse');
                    const button=header.querySelector('button#filter-button,#filter-button button,button[aria-label="Search filters"],button[aria-label="Filters"],button[aria-label="Фильтры"],#filter-button[role="button"]');
                    if(!panel||!button)continue;
                    let state=this.filters.get(panel);
                    if(!state){state={button,open:button.getAttribute('aria-expanded')==='true'||panel.hasAttribute('opened'),hidden:panel.getAttribute('hidden'),aria:panel.getAttribute('aria-hidden'),buttons:new Map()};this.filters.set(panel,state);}
                    state.button=button;
                    if(!state.buttons.has(button))state.buttons.set(button,button.getAttribute('aria-expanded'));
                    this.applyFilter(panel,state);
                }
            }
            for(const[source,card]of this.cards)if(!wanted.has(source)){card.destroy();this.cards.delete(source);}
            for(const[panel,state]of this.filters)if(!panel.isConnected||!panel.closest('ytd-search')){this.restoreFilter(panel,state);this.filters.delete(panel);}
        }
        syncLayout(searches){
            const wanted=new Map(),mark=(node,name,value='')=>{if(!node)return;if(!wanted.has(node))wanted.set(node,new Map());wanted.get(node).set('data-myt-search-'+name,value);};
            const result='[data-myt-search-video],[data-myt-search-playlist],[data-myt-search-channel]';
            const containers='ytd-shelf-renderer,grid-shelf-view-model,ytd-rich-section-renderer,ytd-item-section-renderer';
            for(const search of searches){
                const special=new Set();
                for(const container of search.querySelectorAll(containers)){
                    if(container.closest('[data-myt-hidden],[data-myt-hidden-section]')||!container.querySelector(result))continue;
                    const header=[...container.querySelectorAll('yt-section-header-view-model,yt-section-header-renderer,#title-container,:scope > #header,h2,[role="heading"]')].find(node=>node.closest(containers)===container&&!node.closest(result)&&!node.closest('[data-myt-hidden],[data-myt-hidden-section]'));
                    const heading=header?.querySelector('#title,h2,h3,.ytSectionHeaderViewModelTitle')||header;
                    const name=text(heading);
                    if(!name||/^(shorts|короткие видео|short videos)$/iu.test(name))continue;
                    special.add(container);mark(container,'special');mark(header,'special-heading');
                    const grid=container.querySelector(':scope > #contents,:scope > #content');
                    if(grid)for(const nested of grid.querySelectorAll('[data-myt-search-grid]'))mark(nested,'flat');
                    const videos=[...container.querySelectorAll('[data-myt-search-video]')];
                    if(videos.length===4&&!container.querySelector('[data-myt-search-playlist],[data-myt-search-channel]'))mark(container,'balanced','2');
                }
                const inSpecial=node=>[...special].some(container=>container===node||container.contains(node));
                const flows=[...search.querySelectorAll('ytd-section-list-renderer > #contents')].filter(list=>!inSpecial(list));
                for(const list of flows)mark(list,'flow');
                for(const container of search.querySelectorAll(containers)){
                    if(inSpecial(container)||!container.querySelector(result)||!flows.some(list=>list.contains(container)))continue;
                    mark(container,'flat');
                    for(const inner of container.querySelectorAll(':scope > #contents,[data-myt-search-grid]'))if(!inSpecial(inner))mark(inner,'flat');
                }
            }
            for(const[node,attributes]of this.layout)for(const name of attributes.keys())if(!wanted.get(node)?.has(name))node.removeAttribute(name);
            for(const[node,attributes]of wanted)for(const[name,value]of attributes)if(node.getAttribute(name)!==value)node.setAttribute(name,value);
            this.layout=wanted;
        }
        applyFilter(panel,state){
            const value=state.open?'open':'closed';
            if(panel.dataset.mytSearchFilters!==value)panel.dataset.mytSearchFilters=value;
            if(state.open&&panel.hasAttribute('hidden'))panel.removeAttribute('hidden');
            const aria=String(!state.open);if(panel.getAttribute('aria-hidden')!==aria)panel.setAttribute('aria-hidden',aria);
            if(state.button.getAttribute('aria-expanded')!==String(state.open))state.button.setAttribute('aria-expanded',String(state.open));
        }
        toggleFilter(event){
            for(const[panel,state]of this.filters){
                if(!event.composedPath().includes(state.button))continue;
                event.preventDefault();event.stopImmediatePropagation();state.open=!state.open;this.applyFilter(panel,state);return;
            }
        }
        restoreFilter(panel,state){
            panel.removeAttribute('data-myt-search-filters');
            for(const[name,value]of [['hidden',state.hidden],['aria-hidden',state.aria]]){if(value===null)panel.removeAttribute(name);else panel.setAttribute(name,value);}
            for(const[button,value]of state.buttons){if(value===null)button.removeAttribute('aria-expanded');else button.setAttribute('aria-expanded',value);}
        }
        destroy(){document.removeEventListener('click',this.click,true);for(const card of this.cards.values())card.destroy();this.cards.clear();for(const[panel,state]of this.filters)this.restoreFilter(panel,state);this.filters.clear();for(const[node,attributes]of this.layout)for(const name of attributes.keys())node.removeAttribute(name);this.layout.clear();this.metadata.clear();}
    }
    Search.playlistSelector=playlistSelector;
    globalThis.MinimalYouTubeSearch=Search;
})();
