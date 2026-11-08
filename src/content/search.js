/* Isolated channel/playlist cards and a controller for native search filters. */
(() => {
    'use strict';
    const channelPath=/^\/(?:@|channel\/|c\/|user\/)/;
    const text=node=>node?.textContent.replace(/\s+/g,' ').trim()||'';
    const filterScopeSelector='ytd-search-sub-menu-renderer,ytd-search-filter-dialog-renderer,yt-search-filter-dialog-view-model,ytd-search-filter-group-renderer,yt-chip-cloud-chip-renderer';
    // SPA responses can retain the profile language even when the page uses
    // hl=en. Only translate native filter UI, never result titles or queries.
    const filterCopy=new Map([
        ['Filters','Фильтры','Filter'],['Search filters','Фильтры поиска','Suchfilter'],
        ['Close','Закрыть','Schließen'],['Apply','Применить','Anwenden'],
        ['Reset','Сбросить','Zurücksetzen'],['Clear all','Сбросить все','Alle löschen'],
        ['Cancel','Отмена','Abbrechen'],['Done','Готово','Fertig'],
        ['Upload date','Дата загрузки','По дате загрузки','Hochladedatum'],['Type','Тип','Typ'],
        ['Duration','Длительность','Dauer'],['Features','Особенности','Funktionen','Eigenschaften'],
        ['Sort by','Упорядочить','Сортировать по','Sortieren nach'],
        ['Last hour','За последний час','Letzte Stunde'],['Today','Сегодня','За сегодня','Heute'],
        ['This week','На этой неделе','За эту неделю','Diese Woche'],
        ['This month','В этом месяце','За этот месяц','Diesen Monat'],
        ['This year','В этом году','За этот год','Dieses Jahr'],
        ['Video','Видео','Video'],['Channel','Канал','Kanal'],['Playlist','Плейлист','Playlist'],['Movie','Фильм','Film'],
        ['Under 4 minutes','Менее 4 минут','Короче 4 минут','Unter 4 Minuten'],
        ['Under 3 minutes','Менее 3 минут','Короче 3 минут','Unter 3 Minuten'],
        ['4–20 minutes','4–20 минут','4–20 Minuten','4 bis 20 Minuten'],
        ['3–20 minutes','3–20 минут','3–20 Minuten','3 bis 20 Minuten'],
        ['Over 20 minutes','Более 20 минут','Длиннее 20 минут','Über 20 Minuten'],
        ['Live','В прямом эфире','Прямой эфир','Трансляции','Live'],
        ['Subtitles/CC','С субтитрами','Субтитры','Untertitel'],
        ['Creative Commons','Лицензия Creative Commons','Creative Commons'],
        ['Location','Местоположение','Standort'],['Purchased','Купленные','Куплено','Gekauft'],
        ['Relevance','По релевантности','Релевантность','Relevanz'],
        ['View count','По числу просмотров','Число просмотров','Anzahl der Aufrufe','Aufrufanzahl'],
        ['Rating','По рейтингу','Рейтинг','Bewertung'],
        ['All','Все','Alle'],['Videos','Videos'],['Channels','Каналы','Kanäle'],
        ['Playlists','Плейлисты','Playlists'],['Movies','Фильмы','Filme'],
        ['Unwatched','Не просмотрено','Непросмотренные','Nicht angesehen'],
        ['Watched','Просмотрено','Просмотренные','Angesehen'],
        ['Recently uploaded','Недавно загружено','Недавно загруженные','Kürzlich hochgeladen'],
    ].flatMap(([english,...labels])=>labels.map(label=>[label.toLocaleLowerCase('en').replace(/[\s\u00a0]+/g,' ').replace(/[-–—]/g,'-'),english])));
    const englishFilter=value=>filterCopy.get(value.trim().toLocaleLowerCase('en').replace(/[\s\u00a0]+/g,' ').replace(/[-–—]/g,'-'));
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
    const stylesheet=`:host{display:block;min-width:0;height:100%;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--myt-ink)}*{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}a:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}.surface{display:flex;align-items:center;gap:28px;min-height:160px;height:100%;padding:14px;border-radius:16px;background:var(--myt-card-bg,var(--myt-surface,#19191d))}.surface:hover,.surface:focus-within{background:var(--myt-card-hover-bg,var(--myt-soft))}.cover{position:relative;display:grid;place-items:center;flex:0 0 54%;max-width:none;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:var(--myt-soft)}.cover img{position:absolute;width:100%;height:100%;object-fit:cover}.cover svg{width:36px;height:36px;color:var(--myt-muted)}.info{min-width:0;flex:1;align-self:stretch;display:flex;flex-direction:column;justify-content:center;gap:14px;padding:18px 10px}h3{margin:0;font-size:17px;line-height:1.4;font-weight:600}.title{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}.owner{display:block;margin:0;color:var(--myt-muted);overflow-wrap:anywhere}.owner:hover{text-decoration:underline}.updated{margin:0;font-size:13px;color:var(--myt-muted);overflow-wrap:anywhere}.count{position:absolute;right:10px;bottom:10px;max-width:calc(100% - 20px);padding:4px 8px;border-radius:8px;background:#000c;color:#fff;font-size:12px;font-weight:600;line-height:1.5;pointer-events:none}@media(max-width:600px){.surface{display:block;padding:12px}.cover{width:100%}.info{padding:18px 4px 8px;gap:10px}h3{font-size:17px}}`;

    class PlaylistCard {
        constructor(source){
            this.source=source;this.parts=new Set();this.host=document.createElement('div');this.host.dataset.mytSearchPlaylistCard='';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${stylesheet}</style><article class="surface"><a class="cover" aria-label="Open playlist"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M3 5h16M3 10h16M3 15h9m3-1 6 4-6 4Z"/></svg><img alt="" loading="lazy" decoding="async"><span class="count"></span></a><div class="info"><h3><a class="title"></a></h3><a class="owner"></a><p class="updated"></p></div></article>`;
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

    const channelStyles=`
      :host{all:initial!important;display:block!important;position:relative!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;color:var(--myt-ink)!important}
      :host::before,:host::after{content:none!important;display:none!important}
      *{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none;cursor:pointer}button{font:inherit;cursor:pointer}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}
      .surface{display:grid;grid-template-columns:80px minmax(0,1fr) auto;align-items:center;gap:16px;min-height:110px}
      .avatar{display:grid;place-items:center;position:relative;width:80px;height:80px;overflow:hidden;border-radius:50%;background:var(--myt-soft);font-size:28px;font-weight:600;flex:none}
      .avatar img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.info{min-width:0;display:flex;flex-direction:column;gap:6px;overflow-wrap:anywhere}
      .heading{display:flex;align-items:baseline;gap:5px;min-width:0}.name{font-size:18px;font-weight:600;line-height:1.35;overflow-wrap:anywhere}.verified{flex:none;width:14px;height:14px;align-self:center;color:var(--myt-muted)}
      .metadata,.description{margin:0;font-size:13px;line-height:1.5;color:var(--myt-muted)}.description{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
      .subscribe{display:inline-flex;align-items:center;justify-content:center;gap:9px;min-width:0;max-width:100%;min-height:44px;padding:10px 20px;border:1px solid var(--myt-border);border-radius:999px;background:var(--myt-surface);color:var(--myt-ink);font:500 16px/1.3 Arial,sans-serif;transition:none;white-space:nowrap}
      .subscribe:hover:not(:disabled){background:var(--myt-soft)}.subscribe[aria-pressed=true]{background:#c91f37;border-color:#c91f37;color:#fff}.subscribe[aria-pressed=true]:hover:not(:disabled){background:#b51b31;border-color:#b51b31}.subscribe svg{width:18px;height:18px;flex:none}.subscribe:disabled{opacity:.55;cursor:default}
      @media(max-width:600px){.surface{grid-template-columns:80px minmax(0,1fr);row-gap:12px}.subscribe{grid-column:2;justify-self:start}.name{font-size:17px}}
    `;
    const channelText=node=>{
        if(!node)return '';
        const copy=node.cloneNode(true);
        copy.querySelectorAll('button,[role="button"],script,style,svg,yt-icon,ytd-badge-supported-renderer,tp-yt-paper-tooltip,yt-tooltip,[hidden],[aria-hidden="true"],[aria-label="Verified"]').forEach(child=>child.remove());
        return text(copy);
    };

    class ChannelCard {
        constructor(source,queue){
            this.source=source;this.queue=queue;this.parts=new Set();
            this.host=document.createElement('div');this.host.dataset.mytSearchChannelCard='';this.host.lang='en';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${channelStyles}</style><article class="surface"><a class="avatar" data-myt-search-avatar-link><span class="initial" aria-hidden="true"></span><img alt="" decoding="async" hidden></a><div class="info"><div class="heading"><a class="name"></a><svg class="verified" role="img" aria-label="Verified" viewBox="0 0 24 24" hidden><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="m7 12 3 3 7-7" fill="none" stroke="var(--myt-card-bg)" stroke-width="2"/></svg></div><p class="metadata" hidden></p><p class="description" hidden></p></div><button class="subscribe" data-myt-search-subscribe="false" aria-pressed="false" hidden><svg aria-hidden="true" viewBox="0 0 24 24" hidden><path d="m5 12 4 4L19 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Subscribe</span></button></article>`;
            this.q=selector=>this.shadow.querySelector(selector);
            this.q('img').onerror=()=>{this.q('img').hidden=true;this.q('.initial').hidden=false;};
            this.q('img').onload=()=>{this.q('.initial').hidden=true;};
            for(const link of [this.q('.avatar'),this.q('.name')])link.addEventListener('click',event=>{
                if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||!this.link?.isConnected)return;
                event.preventDefault();event.stopPropagation();this.link.click();
            });
            this.q('.subscribe').addEventListener('click',()=>this.subscribe());
            this.observer=new MutationObserver(records=>{
                if(this.host.isConnected&&records.every(record=>record.type==='childList'&&[...record.addedNodes,...record.removedNodes].every(node=>node===this.host)))return;
                queue();
            });
            this.observer.observe(source,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['href','src','srcset','data-src','data-srcset','class','aria-label','title','aria-pressed','aria-disabled','aria-busy','subscribed','is-subscribed','disabled']});
            source.addEventListener('load',queue,true);
        }
        subscriptionState(){
            const state=globalThis.MinimalYouTubeWatch?.readSubscriptionState?.(this.source);
            if(state?.button)return state;
            const button=[...this.source.querySelectorAll('button')].find(node=>/^(?:subscribe\b|subscribed\b|подписаться|вы подписаны|abonnieren|abonniert)/iu.test((node.getAttribute('aria-label')||text(node)).trim()));
            return {button,subscribed:button?.getAttribute('aria-pressed')==='true'||/^(?:subscribed\b|вы подписаны|abonniert)/iu.test(text(button)),disabled:!button||button.matches(':disabled,[aria-disabled="true"],[aria-busy="true"]')};
        }
        update(){
            const source=this.source;
            const anchors=[...source.querySelectorAll('a[href]')].filter(node=>{const url=safeURL(node.href);return url?.protocol==='https:'&&(url.hostname==='youtube.com'||url.hostname.endsWith('.youtube.com'))&&channelPath.test(url.pathname);});
            const image=source.querySelector('#avatar img,yt-avatar-shape img,#avatar-section img,.yt-spec-avatar-shape__image')||source.querySelector('img');
            this.link=anchors.find(link=>image&&link.contains(image))||anchors[0];
            let name='';
            for(const selector of ['ytd-channel-name #text','#channel-title #text','ytd-channel-name a','ytd-channel-name','#channel-title','#channel-info h3','#info-section h3','h3','a#main-link']){
                name=channelText(source.querySelector(selector));if(name)break;
            }
            name ||= anchors.map(channelText).find(Boolean)||'Channel';
            const href=this.link?.href||'';
            for(const link of [this.q('.avatar'),this.q('.name')]){if(href){if(link.href!==href)link.href=href;}else link.removeAttribute('href');}
            if(this.q('.name').textContent!==name)this.q('.name').textContent=name;
            this.q('.avatar').setAttribute('aria-label','Open channel '+name);
            if(this.q('.initial').textContent!==name.slice(0,1))this.q('.initial').textContent=name.slice(0,1);
            const srcset=image?.getAttribute('data-srcset')||image?.getAttribute('srcset')||'';
            const src=[image?.getAttribute('data-src'),...srcset.split(',').reverse().map(value=>value.trim().split(/\s+/)[0]),image?.currentSrc,image?.getAttribute('src')].find(value=>value&&(safeURL(value)||/^data:image\//i.test(value)))||'';
            if(this.q('img').getAttribute('src')!==src){this.q('.initial').hidden=false;if(src)this.q('img').src=src;else this.q('img').removeAttribute('src');this.q('img').hidden=!src;}
            const description=source.querySelector('#description,#description-text,.channel-description')||source.querySelector('#channel-info p:last-of-type');
            const values=[...source.querySelectorAll('#channel-handle,#subscribers,#subscriber-count,#channel-stats,#metadata-line')].map(channelText).filter(Boolean);
            if(!values.length){const first=source.querySelector('#channel-info p,#info-section p');if(first&&first!==description)values.push(channelText(first));}
            if(!values.length)for(const node of source.querySelectorAll('yt-formatted-string,p,span')){
                const value=channelText(node);
                if(/^@[^\s·•]+(?:\s*[·•].*)?$/u.test(value)||/^[\d.,]+\s*(?:[kmb]|тыс\.?|млн\.?)?\s+(?:subscribers?|подписчик[а-яё]*|Abonnenten)(?:\s*[·•].*)?$/iu.test(value))values.push(value);
            }
            const metadata=[...new Set(values)].filter(value=>!values.some(other=>other!==value&&other.includes(value))).join(' · ').replace(/(\d[\d.,\s]*(?:[kmb]|тыс\.?|млн\.?)?)\s+(?:подписчик[а-яё]*|Abonnenten)(?=$|[\s·•])/giu,'$1 subscribers');
            for(const[selector,value]of [['.metadata',metadata],['.description',channelText(description)]]){const node=this.q(selector);if(node.textContent!==value)node.textContent=value;node.hidden=!value;}
            this.q('.verified').toggleAttribute('hidden',!source.querySelector('.badge-style-type-verified,.badge-style-type-verified-artist,[aria-label="Verified"],[aria-label="Проверено"],[aria-label="Bestätigt"]'));
            const state=this.subscriptionState(),control=this.q('.subscribe');
            control.hidden=!state.button;control.disabled=Boolean(state.disabled);
            const value=String(Boolean(state.subscribed));
            if(control.getAttribute('aria-pressed')!==value)control.setAttribute('aria-pressed',value);
            if(control.dataset.mytSearchSubscribe!==value)control.dataset.mytSearchSubscribe=value;
            control.setAttribute('aria-label',(state.subscribed?'Unsubscribe from ':'Subscribe to ')+name);
            const label=state.subscribed?'Subscribed':'Subscribe';if(this.q('.subscribe span').textContent!==label)this.q('.subscribe span').textContent=label;
            this.q('.subscribe svg').toggleAttribute('hidden',!state.subscribed);
            if(this.anchor&&this.anchor.button!==state.button)this.clearAnchor();
            if(this.host.parentElement!==source)source.append(this.host);
            for(const part of this.parts)if(part.parentElement!==source){part.removeAttribute('data-myt-search-channel-source');this.parts.delete(part);}
            for(const part of source.children)if(part!==this.host&&!this.parts.has(part)){part.setAttribute('data-myt-search-channel-source','');this.parts.add(part);}
            this.positionAnchor();
        }
        subscribe(){
            const state=this.subscriptionState();if(!state.button||state.disabled)return;
            const control=this.q('.subscribe');
            this.press?.cancel();
            if(!matchMedia('(prefers-reduced-motion: reduce)').matches)this.press=control.animate([{transform:'scale(.98)'},{transform:'scale(1)'}],{duration:180,easing:'cubic-bezier(.2,.8,.2,1)'});
            this.clearAnchor();
            const button=state.button;
            if(typeof button.showPopover==='function'){
                // Leave the native control in its original DOM. A transparent
                // popover gives YouTube the visible button's rectangle for menus.
                this.anchor={button,popover:button.getAttribute('popover'),tabindex:button.getAttribute('tabindex'),aria:button.getAttribute('aria-hidden'),style:button.getAttribute('style'),properties:new Map()};
                button.setAttribute('popover','manual');
                button.setAttribute('tabindex','-1');button.setAttribute('aria-hidden','true');
                this.positionAnchor();
                try{button.showPopover();}catch{this.clearAnchor();}
                if(this.anchor){
                    this.anchor.observer=new MutationObserver(()=>{if(this.anchor&&button.getAttribute('style')!==this.anchor.appliedStyle)this.positionAnchor();});
                    this.anchor.observer.observe(button,{attributes:true,attributeFilter:['style']});
                    this.anchorMove=()=>this.positionAnchor();
                    this.anchorDismiss=event=>{
                        if(event.type==='keydown'&&event.key!=='Escape')return;
                        this.clearAnchor();
                        if(event.type==='keydown')queueMicrotask(()=>{if(this.host.isConnected)this.q('.subscribe').focus({preventScroll:true});});
                    };
                    window.addEventListener('resize',this.anchorMove);
                    document.addEventListener('scroll',this.anchorMove,true);
                    document.addEventListener('pointerdown',this.anchorDismiss,true);
                    document.addEventListener('keydown',this.anchorDismiss,true);
                }
            }
            button.click();this.queue();
        }
        positionAnchor(){
            if(!this.anchor)return;
            const {button,properties}=this.anchor,rect=this.q('.subscribe').getBoundingClientRect();
            if(this.anchor.appliedStyle!==undefined&&button.getAttribute('style')!==this.anchor.appliedStyle)this.anchor.externalStyle=true;
            const values={position:'fixed',right:'auto',bottom:'auto',left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',height:rect.height+'px','min-width':'0','max-width':'none','min-height':'0','max-height':'none',margin:'0',padding:'0',display:'inline-flex',visibility:'visible',opacity:'0','pointer-events':'none','box-sizing':'border-box',transform:'none',translate:'none'};
            for(const[name,value]of Object.entries(values)){
                const previous=properties.get(name);
                if(!previous||button.style.getPropertyValue(name)!==previous.applied||button.style.getPropertyPriority(name)!=='important')properties.set(name,{value:button.style.getPropertyValue(name),priority:button.style.getPropertyPriority(name)});
                if(button.style.getPropertyValue(name)!==value||button.style.getPropertyPriority(name)!=='important')button.style.setProperty(name,value,'important');
                properties.get(name).applied=button.style.getPropertyValue(name);
            }
            this.anchor.appliedStyle=button.getAttribute('style');
        }
        clearAnchor(){
            if(!this.anchor)return;
            const {button,popover,tabindex,aria,style,properties,appliedStyle,externalStyle,observer}=this.anchor;this.anchor=null;
            observer?.disconnect();
            const unchanged=!externalStyle&&button.getAttribute('style')===appliedStyle;
            if(button.matches(':popover-open'))button.hidePopover();
            if(button.getAttribute('popover')==='manual'){if(popover===null)button.removeAttribute('popover');else button.setAttribute('popover',popover);}
            for(const[name,value]of [['tabindex',tabindex],['aria-hidden',aria]]){if(value===null)button.removeAttribute(name);else button.setAttribute(name,value);}
            for(const[name,state]of properties)if(button.style.getPropertyValue(name)===state.applied&&button.style.getPropertyPriority(name)==='important'){if(state.value)button.style.setProperty(name,state.value,state.priority);else button.style.removeProperty(name);}
            if(unchanged){if(style===null)button.removeAttribute('style');else button.setAttribute('style',style);}
            else if(style===null&&!button.style.cssText)button.removeAttribute('style');
            window.removeEventListener('resize',this.anchorMove);document.removeEventListener('scroll',this.anchorMove,true);
            document.removeEventListener('pointerdown',this.anchorDismiss,true);document.removeEventListener('keydown',this.anchorDismiss,true);
        }
        destroy(){
            this.observer.disconnect();this.source.removeEventListener('load',this.queue,true);this.press?.cancel();this.clearAnchor();
            this.host.remove();for(const part of this.parts)part.removeAttribute('data-myt-search-channel-source');this.parts.clear();
        }
    }

    class Search {
        constructor(){this.cards=new Map();this.channels=new Map();this.filters=new Map();this.filterLabels=new Map();this.layout=new Map();this.metadata=new Map();this.click=event=>this.toggleFilter(event);document.addEventListener('click',this.click,true);}
        static isPlaylist(card){
            if(card.matches('ytd-playlist-renderer,ytd-grid-playlist-renderer'))return true;
            if(!card.matches('yt-lockup-view-model'))return false;
            if(card.matches('[is-playlist],[content-type="playlist"],[data-content-type="playlist"]'))return true;
            if(card.querySelector('yt-collection-thumbnail-view-model,yt-collections-stack,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer,.ytCollectionThumbnailViewModelHost'))return true;
            const main=card.querySelector(titleSelector);return safeURL(main?.href)?.pathname==='/playlist';
        }
        sync(searches){
            cancelAnimationFrame(this.cardFrame);this.cardFrame=0;this.pendingCards?.clear();
            const wanted=new Set();
            const raw=document.documentElement.getAttribute('data-myt-search-playlists')||'';
            if(raw!==this.metadataRaw){this.metadataRaw=raw;this.metadata.clear();try{const values=JSON.parse(raw);if(Array.isArray(values))for(const value of values.slice(-200))if(typeof value.id==='string')this.metadata.set(value.id,{image:safeURL(value.image)?.href||'',count:countNumber(value.count)});}catch{}}
            this.syncLayout(searches);
            this.syncChannels(searches);
            this.syncFilterLabels(searches);
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
        queueCard(source){
            this.pendingCards ||=new Set();this.pendingCards.add(source);
            if(this.cardFrame)return;
            this.cardFrame=requestAnimationFrame(()=>{this.cardFrame=0;for(const source of this.pendingCards)if(source.isConnected)(this.cards.get(source)||this.channels.get(source))?.update(this.metadata);this.pendingCards.clear();});
        }
        syncFilterLabels(searches){
            const wanted=new Map();
            const translate=(node,attribute='')=>{
                const value=attribute?node.getAttribute(attribute):node.data;
                if(value===null)return;
                const previous=this.filterLabels.get(node)?.get(attribute);
                const english=englishFilter(value);
                if(previous&&value!==previous.translated)this.filterLabels.get(node).delete(attribute);
                if(!english&&value!==previous?.translated)return;
                if(!wanted.has(node))wanted.set(node,new Set());wanted.get(node).add(attribute);
                if(!english||value.trim()===english)return;
                if(!this.filterLabels.has(node))this.filterLabels.set(node,new Map());
                const translated=value.replace(/\S(?:[\s\S]*\S)?/,english);
                this.filterLabels.get(node).set(attribute,{original:value,translated});
                if(attribute)node.setAttribute(attribute,translated);else node.data=translated;
            };
            const scopes=new Set(document.querySelectorAll('ytd-search-filter-dialog-renderer,yt-search-filter-dialog-view-model,ytd-search-filter-group-renderer'));
            for(const search of searches)for(const scope of search.querySelectorAll(filterScopeSelector))scopes.add(scope);
            for(const scope of scopes){
                const walk=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT,{acceptNode:node=>node.parentElement.closest('script,style,input,textarea,[contenteditable]')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
                while(walk.nextNode())translate(walk.currentNode);
                for(const node of [scope,...scope.querySelectorAll('[aria-label],[title]')])for(const attribute of ['aria-label','title'])translate(node,attribute);
            }
            for(const[node,attributes]of this.filterLabels){
                for(const[attribute,state]of attributes)if(!wanted.get(node)?.has(attribute)){
                    this.restoreFilterLabel(node,attribute,state);attributes.delete(attribute);
                }
                if(!attributes.size)this.filterLabels.delete(node);
            }
        }
        restoreFilterLabel(node,attribute,state){
            if((attribute?node.getAttribute(attribute):node.data)!==state.translated)return;
            if(attribute)node.setAttribute(attribute,state.original);else node.data=state.original;
        }
        syncChannels(searches){
            const wanted=new Set();
            for(const search of searches)for(const source of search.querySelectorAll('[data-myt-search-channel]')){
                wanted.add(source);let card=this.channels.get(source);
                if(!card){card=new ChannelCard(source,()=>this.queueCard(source));this.channels.set(source,card);}card.update();
            }
            for(const[source,card]of this.channels)if(!wanted.has(source)){card.destroy();this.channels.delete(source);}
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
                    if(!name||/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu.test(name))continue;
                    special.add(container);mark(container,'special');mark(header,'special-heading');mark(heading,'heading-text');
                    this.headingLabels ||= new WeakMap();
                    if(this.headingLabels.get(heading)!==name){this.headingLabels.set(heading,name);globalThis.MinimalYouTubeWatch?.loadTitleFonts?.(name);}
                    const grid=container.querySelector(':scope > #contents,:scope > #content');
                    if(grid)for(const nested of grid.querySelectorAll('[data-myt-search-grid]'))mark(nested,'flat');
                    const videos=[...container.querySelectorAll('[data-myt-search-video]')];
                    if(videos.length===4&&!container.querySelector('[data-myt-search-playlist],[data-myt-search-channel]'))mark(container,'balanced','2');
                }
                const inSpecial=node=>[...special].some(container=>container===node||container.contains(node));
                const flows=[...search.querySelectorAll('ytd-section-list-renderer > #contents')].filter(list=>!inSpecial(list));
                const roots=[...search.querySelectorAll(result)].filter(node=>!node.parentElement.closest(result)&&!node.closest('[data-myt-hidden],[data-myt-hidden-section],[hidden],[aria-hidden="true"]'));
                if(roots.length>1&&!flows.some(flow=>roots.every(node=>flow.contains(node)))){
                    let common=roots[0].parentElement;
                    while(common&&common!==search&&!roots.every(node=>common.contains(node)))common=common.parentElement;
                    if(common&&common!==search&&!inSpecial(common))flows.push(common);
                }
                for(const list of flows)mark(list,'flow');
                for(const node of roots){
                    const unit=[...special].find(container=>container.contains(node))||node;
                    const flow=flows.find(list=>list.contains(unit));
                    if(!flow)continue;
                    for(let wrapper=unit.parentElement;wrapper&&wrapper!==flow;wrapper=wrapper.parentElement)if(!inSpecial(wrapper)&&!wrapper.matches('[data-myt-search-cell],[data-myt-search-channel-cell],[data-myt-search-playlist-cell]'))mark(wrapper,'flat');
                }
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
        destroy(){cancelAnimationFrame(this.cardFrame);this.pendingCards?.clear();document.removeEventListener('click',this.click,true);for(const card of this.cards.values())card.destroy();this.cards.clear();for(const card of this.channels.values())card.destroy();this.channels.clear();for(const[node,attributes]of this.filterLabels)for(const[attribute,state]of attributes)this.restoreFilterLabel(node,attribute,state);this.filterLabels.clear();for(const[panel,state]of this.filters)this.restoreFilter(panel,state);this.filters.clear();for(const[node,attributes]of this.layout)for(const name of attributes.keys())node.removeAttribute(name);this.layout.clear();this.metadata.clear();}
    }
    Search.playlistSelector=playlistSelector;
    Search.filterScopeSelector=filterScopeSelector;
    globalThis.MinimalYouTubeSearch=Search;
})();
