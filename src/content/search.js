/* Own playlist result cards and a stable controller for native search filters. */
(() => {
    'use strict';
    const channelPath=/^\/(?:@|channel\/|c\/|user\/)/;
    const text=node=>node?.textContent.replace(/\s+/g,' ').trim()||'';
    const safeURL=value=>{if(typeof value!=='string'||!value.trim())return null;try{const url=new URL(value,location.href);return /^https?:$/.test(url.protocol)?url:null;}catch{return null;}};
    const titleSelector='a#video-title,a#video-title-link,h3 a[href],.yt-lockup-metadata-view-model__title,.yt-lockup-metadata-view-model-wiz__title,.ytLockupMetadataViewModelTitle';
    const playlistSelector='ytd-playlist-renderer,ytd-grid-playlist-renderer,yt-lockup-view-model';
    const stylesheet=`:host{display:block;min-width:0;height:100%;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--myt-ink)}*{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}a:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}.surface{display:flex;align-items:center;gap:20px;min-height:128px;height:100%;padding:16px;border-radius:16px;background:var(--myt-card-bg,var(--myt-surface,#19191d))}.surface:hover,.surface:focus-within{background:var(--myt-card-hover-bg,var(--myt-soft))}.cover{position:relative;display:grid;place-items:center;flex:0 0 38%;max-width:280px;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:var(--myt-soft)}.cover img{position:absolute;width:100%;height:100%;object-fit:cover}.cover svg{width:36px;height:36px;color:var(--myt-muted)}.info{min-width:0;flex:1}h3{margin:0;font-size:17px;line-height:1.4;font-weight:600}.title{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}.owner{display:block;margin-top:8px;color:var(--myt-muted);overflow-wrap:anywhere}.owner:hover{text-decoration:underline}.count,.updated{margin:5px 0 0;font-size:13px;color:var(--myt-muted);overflow-wrap:anywhere}@media(max-width:600px){.surface{padding:12px;gap:12px}.cover{flex-basis:38%}h3{font-size:15px}}`;

    class PlaylistCard {
        constructor(source){
            this.source=source;this.parts=new Set();this.host=document.createElement('div');this.host.dataset.mytSearchPlaylistCard='';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${stylesheet}</style><article class="surface"><a class="cover" aria-label="Open playlist"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M3 5h16M3 10h16M3 15h9m3-1 6 4-6 4Z"/></svg><img alt="" loading="lazy" decoding="async"></a><div class="info"><h3><a class="title"></a></h3><a class="owner"></a><p class="count"></p><p class="updated"></p></div></article>`;
            this.q=selector=>this.shadow.querySelector(selector);
            this.q('img').onerror=()=>{this.q('img').hidden=true;};
        }
        update(){
            const source=this.source;
            const main=source.querySelector(titleSelector)||source.querySelector('a[href*="/playlist?"],a[href*="list="]');
            const anchors=[...source.querySelectorAll('a[href]')];
            const owner=anchors.find(a=>channelPath.test(safeURL(a.href)?.pathname||'')&&text(a));
            const destination=anchors.map(a=>safeURL(a.href)).find(url=>url?.searchParams.get('list'));
            const href=destination?new URL('/playlist?list='+encodeURIComponent(destination.searchParams.get('list')),location.origin).href:'';
            const image=source.querySelector('ytd-thumbnail img,yt-collection-thumbnail-view-model img,yt-thumbnail-view-model img,img');
            const src=image?.currentSrc||image?.getAttribute('src')||image?.getAttribute('data-src')||'';
            // Read metadata independently; creator names can precede count/date.
            const metadata=[...source.querySelectorAll('#video-count-text,#video-count,.formatted-video-count-label,#metadata-line,#published-time-text,#published-time,.yt-content-metadata-view-model__metadata-row,.yt-content-metadata-view-model-wiz__metadata-row,.ytContentMetadataViewModelMetadataRow,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer')].map(text);
            const combined=metadata.join(' · ');
            const count=combined.match(/([\d][\d\s,.]*)\s*(?:videos?|видео|ролик\S*)/iu)?.[1]?.trim()||metadata.find(value=>/^[\d][\d\s,.]*$/.test(value));
            let updated=metadata.find(value=>/updated|обновл/iu.test(value))||text(source.querySelector('#published-time-text,#published-time,[data-last-updated]'))||metadata.find(value=>/\bago\b|\btoday\b|\byesterday\b|назад|сегодня|вчера/iu.test(value))||'';
            updated=updated.split(/[·•]/).find(value=>/updated|обновл/iu.test(value))?.trim()||updated;
            if(/updated|обновл/iu.test(updated))updated=updated.replace(/^.*?(?=updated|обновл)/iu,'');
            if(/обновл|назад|сегодня|вчера/iu.test(updated)){
                const match=updated.match(/(\d+)\s*(сек\S*|мин\S*|час\S*|дн\S*|день|дня|недел\S*|мес\S*|год\S*|г\.|лет)/iu);
                const unit=match&&(/сек/iu.test(match[2])?'second':/мин/iu.test(match[2])?'minute':/час/iu.test(match[2])?'hour':/дн|день|дня/iu.test(match[2])?'day':/недел/iu.test(match[2])?'week':/мес/iu.test(match[2])?'month':'year');
                updated=match?'Updated '+new Intl.RelativeTimeFormat('en',{numeric:'auto'}).format(-Number(match[1]),unit):/сегодня/iu.test(updated)?'Updated today':/вчера/iu.test(updated)?'Updated yesterday':'Update time unavailable';
            }
            if(updated&&!/^Updated\b/iu.test(updated))updated='Updated '+updated;
            const data={title:text(main)||'Playlist',owner:text(owner),ownerHref:owner?.href||'',href,src,count:count?count+' videos':'Video count unavailable',updated:updated||'Update time unavailable'};
            const signature=JSON.stringify(data);
            if(this.signature!==signature){
                this.signature=signature;
                for(const[key,selector]of [['title','.title'],['owner','.owner'],['count','.count'],['updated','.updated']])this.q(selector).textContent=data[key];
                this.q('.owner').hidden=!data.owner;
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
        constructor(){this.cards=new Map();this.filters=new Map();this.click=event=>this.toggleFilter(event);document.addEventListener('click',this.click,true);}
        static isPlaylist(card){
            if(card.matches('ytd-playlist-renderer,ytd-grid-playlist-renderer'))return true;
            if(!card.matches('yt-lockup-view-model'))return false;
            if(card.matches('[is-playlist],[content-type="playlist"],[data-content-type="playlist"]'))return true;
            if(card.querySelector('yt-collection-thumbnail-view-model,yt-collections-stack,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer,.ytCollectionThumbnailViewModelHost'))return true;
            const main=card.querySelector(titleSelector);return safeURL(main?.href)?.pathname==='/playlist';
        }
        sync(searches){
            const wanted=new Set();
            for(const search of searches){
                for(const source of search.querySelectorAll('[data-myt-search-playlist]')){
                    wanted.add(source);let card=this.cards.get(source);if(!card){card=new PlaylistCard(source);this.cards.set(source,card);}card.update();
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
        destroy(){document.removeEventListener('click',this.click,true);for(const card of this.cards.values())card.destroy();this.cards.clear();for(const[panel,state]of this.filters)this.restoreFilter(panel,state);this.filters.clear();}
    }
    Search.playlistSelector=playlistSelector;
    globalThis.MinimalYouTubeSearch=Search;
})();
