/* Owned search cards, channel links and English search filters. */
(() => {
    'use strict';
    const channelPath=/^\/(?:@|channel\/|c\/|user\/)/;
    const text=node=>node?.textContent.replace(/\s+/g,' ').trim()||'';
    const nativeToolbarSelector='ytd-search-sub-menu-renderer,yt-search-sub-menu-view-model,yt-search-header-view-model,ytd-search-header-renderer';
    const filterScopeSelector=nativeToolbarSelector+',ytd-search-filter-dialog-renderer,yt-search-filter-dialog-view-model,ytd-search-filter-group-renderer,yt-chip-cloud-chip-renderer';
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
    // Native visibility identifies cached SPA feeds. Our isolation deliberately
    // gives original cards zero size and hidden visibility, so geometry cannot
    // distinguish them from an inactive YouTube feed after the first render.
    const nativeAvailable=(node,boundary)=>{
        for(let parent=node;parent&&parent!==boundary;parent=parent.parentElement)if(parent.hasAttribute('hidden')||parent.getAttribute('aria-hidden')==='true'||parent.style.display==='none'||parent.style.visibility==='hidden')return false;
        return true;
    };
    const countSelector='#video-count-text,#video-count,#playlist-video-count,.formatted-video-count-label,yt-collection-thumbnail-overlay-view-model,ytd-thumbnail-overlay-side-panel-renderer,yt-thumbnail-overlay-badge-view-model,yt-thumbnail-bottom-overlay-view-model,yt-badge-shape,.ytBadgeShapeText,.yt-badge-shape__text,.badge-shape-wiz__text,[data-video-count]';
    const countNumber=value=>{
        const input=String(value??'').replace(/[\u00a0\u202f]/g,' ').trim();
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
    const channelStyles=`
      :host{all:initial!important;--ink:var(--myt-ink);--muted:var(--myt-muted);--surface:var(--myt-surface);--soft:var(--myt-soft);--border:var(--myt-border);display:block!important;position:relative!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;color:var(--ink)!important}
      :host::before,:host::after{content:none!important;display:none!important}
      *{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none;cursor:pointer}button{font:inherit;cursor:pointer}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}
      .surface.channel-card{position:relative;display:grid;grid-template-columns:80px minmax(0,1fr);align-items:center;width:100%;min-height:128px;padding:20px;gap:6px 16px;border:1px solid var(--border);border-radius:16px;background:var(--surface);color:var(--ink)}
      .channel-card:is(:hover,:focus-visible){background:var(--soft)}
      .owner{display:contents}.avatar{position:relative;grid-column:1;grid-row:1 / 3}.owner-text{grid-column:2;grid-row:1;align-self:end;min-width:0}.stats{grid-column:2;grid-row:2;align-self:start;font-size:13px;line-height:1.5}
      .channel-card:not(:has(.metadata:not([hidden]))) .owner-text{grid-row:1 / 3;align-self:center}
      .avatar{display:grid;place-items:center;width:80px;height:80px;overflow:hidden;border-radius:50%;background:var(--myt-soft);font-size:28px;font-weight:600}
      .owner .avatar img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
      .heading{display:flex;align-items:baseline;gap:5px;min-width:0}.name{font-size:18px;font-weight:600;line-height:1.35;overflow-wrap:anywhere}.verified{flex:none;width:14px;height:14px;align-self:center;color:var(--muted)}
      .metadata{display:flex;align-items:center;flex-wrap:wrap;gap:4px 12px;margin:0;overflow-wrap:anywhere;color:var(--muted)}.subscriber-count{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}.subscriber-icon{width:14px;height:14px;flex:none}
      @media(max-width:600px){.surface.channel-card{grid-template-columns:64px minmax(0,1fr);gap:4px 12px;padding:16px}.avatar{width:64px;height:64px}.name{font-size:17px}}
    `;
    const channelText=node=>{
        if(!node)return '';
        const copy=node.cloneNode(true);
        copy.querySelectorAll('button,[role="button"],script,style,svg,yt-icon,ytd-badge-supported-renderer,tp-yt-paper-tooltip,yt-tooltip,[hidden],[aria-hidden="true"],[aria-label="Verified"]').forEach(child=>child.remove());
        return text(copy);
    };
    const subscriberLabel=/(\d[\d\s.,]*?)\s*(thousand|million|billion|trillion|тыс\.?|млн\.?|млрд\.?|Tsd\.?|Mio\.?|Mrd\.?|[kmbt])?\s*(?:subscribers?|подписчик[а-яё]*|Abonnenten)(?=$|[\s·•])/iu;
    const compactSubscribers=new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:2});
    function subscribers(value){
        const match=String(value??'').replace(/[\u00a0\u202f]/g,' ').match(subscriberLabel);if(!match)return '';
        let amount=match[1].replace(/\s/g,''),unit=(match[2]||'').toLowerCase().replace(/\.$/,'');
        if(!unit&&/^\d{1,3}(?:[.,]\d{3})+$/.test(amount))amount=amount.replace(/[.,]/g,'');
        else{const decimal=Math.max(amount.lastIndexOf('.'),amount.lastIndexOf(','));if(decimal>=0)amount=amount.slice(0,decimal).replace(/[.,]/g,'')+'.'+amount.slice(decimal+1);}
        const power=/^(?:k|thousand|тыс|tsd)$/.test(unit)?3:/^(?:m|million|млн|mio)$/.test(unit)?6:/^(?:b|billion|млрд|mrd)$/.test(unit)?9:/^(?:t|trillion)$/.test(unit)?12:0;
        const count=Number(amount)*10**power;if(!Number.isFinite(count)||count<0)return '';
        const parts=compactSubscribers.formatToParts(count),suffix=parts.find(part=>part.type==='compact')?.value;
        return parts.filter(part=>part.type!=='compact').map(part=>part.value).join('').trim()+(suffix?' '+suffix:'');
    }

    class ChannelCard {
        constructor(source,queue,container){
            this.source=source;this.queue=queue;this.container=container;this.parts=new Set();
            this.host=document.createElement('div');this.host.dataset.mytSearchChannelCard='';this.host.lang='en';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${channelStyles}</style><a class="surface channel-card channel-link" data-myt-search-avatar-link><span class="owner"><span class="avatar"><span class="initial" aria-hidden="true"></span><img alt="" decoding="async" hidden></span><span class="info owner-text"><span class="heading"><span class="name owner-name"></span><svg class="verified" role="img" aria-label="Verified" viewBox="0 0 24 24" hidden><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="m7 12 3 3 7-7" fill="none" stroke="var(--surface)" stroke-width="2"/></svg></span></span></span><span class="metadata stats" hidden><span class="channel-handle" hidden></span><span class="subscriber-count" hidden><span class="subscriber-value"></span><svg class="subscriber-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/></svg></span></span></a>`;
            this.q=selector=>this.shadow.querySelector(selector);
            channelCards.add(this);
            this.q('img').onerror=()=>{const image=this.q('img');this.failedImage=image.getAttribute('src');if(this.fallbackImage&&image.src!==this.fallbackImage){image.src=this.fallbackImage;image.hidden=false;return;}image.hidden=true;this.q('.initial').hidden=false;};
            this.q('img').onload=()=>{if(this.q('img').naturalWidth<=1){this.q('img').onerror();return;}this.q('.initial').hidden=true;};
            this.observer=new MutationObserver(records=>{
                if(this.host.isConnected&&records.every(record=>record.type==='childList'&&[...record.addedNodes,...record.removedNodes].every(node=>node===this.host)))return;
                queue();
            });
            this.observer.observe(source,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['href','src','srcset','data-src','data-srcset','class','aria-label','title','aria-pressed','aria-disabled','aria-busy','subscribed','is-subscribed','disabled']});
            source.addEventListener('load',queue,true);
        }
        update(cache=new Map(),record){
            if(record!==undefined)this.record=record?{...record,name:record.title,url:record.href}:null;
            const source=this.source;
            const anchors=[...source.querySelectorAll('a[href]')].filter(node=>{const url=safeURL(node.href);return url?.protocol==='https:'&&(url.hostname==='youtube.com'||url.hostname.endsWith('.youtube.com'))&&channelPath.test(url.pathname);});
            const image=source.querySelector('#avatar img,yt-avatar-shape img,#avatar-section img,.yt-spec-avatar-shape__image')||source.querySelector('img');
            this.link=anchors.find(link=>image&&link.contains(image))||anchors[0];
            let name='';
            for(const selector of ['ytd-channel-name #text','#channel-title #text','ytd-channel-name a','ytd-channel-name','#channel-title','#channel-info h3','#info-section h3','h3','a#main-link']){
                name=channelText(source.querySelector(selector));if(name)break;
            }
            name ||= anchors.map(channelText).find(Boolean)||'Channel';
            const nativeText=[...source.querySelectorAll('#channel-handle,#channel-stats,#metadata-line')].map(channelText).join(' ')||channelText(source),path=safeURL(this.link?.href)?.pathname;
            const handle=nativeText.match(/@[^\s·•/]+/u)?.[0];
            const matches=[...cache.values()].filter(item=>item.url===path||path==='/channel/'+item.id||(handle&&item.handle===handle));
            const byName=[...cache.values()].filter(item=>item.name===name);
            const cached=this.record||matches[0]||(!path&&!handle&&byName.length===1?byName[0]:null);
            if(cached?.name)name=cached.name;
            const href=channelURL(cached?.url)||channelURL(this.link?.href)||channelURL(handle?'/'+handle:'');
            const link=this.q('.channel-link');if(href){if(link.href!==href)link.href=href;}else link.removeAttribute('href');
            link.setAttribute('aria-label','Open channel '+name);
            if(this.q('.name').textContent!==name)this.q('.name').textContent=name;
            if(this.q('.initial').textContent!==name.slice(0,1))this.q('.initial').textContent=name.slice(0,1);
            const srcset=image?.getAttribute('data-srcset')||image?.getAttribute('srcset')||'';
            this.fallbackImage=cached?.image||'';
            const src=[image?.getAttribute('data-src'),...srcset.split(',').reverse().map(value=>value.trim().split(/\s+/)[0]),image?.currentSrc,image?.getAttribute('src'),this.fallbackImage].find(value=>value&&value!==this.failedImage&&(safeURL(value)||/^data:image\//i.test(value)))||'';
            if(this.q('img').getAttribute('src')!==src){this.q('.initial').hidden=false;if(src)this.q('img').src=src;else this.q('img').removeAttribute('src');this.q('img').hidden=!src;}
            const description=source.querySelector('#description,#description-text,.channel-description')||source.querySelector('#channel-info p:last-of-type');
            const values=[...source.querySelectorAll('#channel-handle,#subscribers,#subscriber-count,#channel-stats,#metadata-line')].map(channelText).filter(Boolean);
            if(!values.length){const first=source.querySelector('#channel-info p,#info-section p');if(first&&first!==description)values.push(channelText(first));}
            for(const node of source.querySelectorAll('yt-formatted-string,p,span')){
                if(description?.contains(node)||node.closest('h3,#channel-title,ytd-channel-name'))continue;
                const value=channelText(node);
                if(/^@[^\s·•]+(?:\s*[·•].*)?$/u.test(value)||/^\d/.test(value)&&subscriberLabel.test(value))values.push(value);
            }
            const metadata=[...values,...(this.record?.metadata||[]),...(cached?.metadata||[]),...(matches[0]?.metadata||[]),...(cache.get(this.record?.id)?.metadata||[])];
            const subscriberCount=metadata.map(subscribers).find(Boolean)||'';
            const channelHandle=handle||cached?.handle||metadata.map(value=>String(value??'').match(/@[^\s·•/]+/u)?.[0]).find(Boolean)||'';
            const handleNode=this.q('.channel-handle'),countNode=this.q('.subscriber-count'),valueNode=this.q('.subscriber-value');
            if(handleNode.textContent!==channelHandle)handleNode.textContent=channelHandle;handleNode.hidden=!channelHandle;
            if(valueNode.textContent!==subscriberCount)valueNode.textContent=subscriberCount;countNode.hidden=!subscriberCount;
            if(subscriberCount)countNode.setAttribute('aria-label',subscriberCount+' subscribers');else countNode.removeAttribute('aria-label');
            this.q('.metadata').hidden=!channelHandle&&!subscriberCount;
            this.q('.verified').toggleAttribute('hidden',!source.querySelector('.badge-style-type-verified,.badge-style-type-verified-artist,[aria-label="Verified"],[aria-label="Проверено"],[aria-label="Bestätigt"]'));
            const container=this.container||source;if(this.host.parentElement!==container)container.append(this.host);
            for(const part of this.parts)if(part.parentElement!==source){part.removeAttribute('data-myt-search-channel-source');this.parts.delete(part);}
            for(const part of source.children)if(part!==this.host&&!this.parts.has(part)){part.setAttribute('data-myt-search-channel-source','');this.parts.add(part);}
        }
        destroy(){
            channelCards.delete(this);this.observer.disconnect();this.source.removeEventListener('load',this.queue,true);
            this.host.remove();for(const part of this.parts)part.removeAttribute('data-myt-search-channel-source');this.parts.clear();
        }
    }


    const sourceSelector='ytd-rich-item-renderer,ytd-rich-grid-media,ytd-video-renderer,ytd-grid-video-renderer,ytd-compact-video-renderer,ytd-playlist-renderer,ytd-grid-playlist-renderer,ytd-radio-renderer,ytd-channel-renderer,yt-lockup-view-model';
    const emptySelector='ytd-message-renderer,yt-message-view-model,ytd-background-promo-renderer';
    const channelHeaderSelector='#myt-channel-nav,#myt-channel-description,yt-page-header-view-model,yt-page-header-renderer,ytd-page-header-renderer,ytd-c4-tabbed-header-renderer';
    const channelExcludedSelector=channelHeaderSelector+',#header,#page-header,#tabs,#tabs-container,#secondary,ytd-popup-container,[role="dialog"]';
    const shelfSelector='ytd-shelf-renderer,grid-shelf-view-model,ytd-rich-section-renderer';
    // Rendering must also work with an already loaded extension manifest which
    // does not list the newer optional MAIN data adapter yet.
    const youtubeURL=value=>{const url=safeURL(value);return url?.protocol==='https:'&&/(^|\.)youtube\.com$/.test(url.hostname)?url.href:'';};
    const channelURL=value=>{const href=youtubeURL(value);return href&&channelPath.test(new URL(href).pathname)?href:'';};
    const channelCards=new Set();
    function routeChannelInput(event){
        if((event.type==='keydown'||event.type==='keyup')&&!['Enter',' ','Tab'].includes(event.key))return;
        const path=event.composedPath();
        for(const card of channelCards){
            const link=card.q('.channel-link');
            if(!card.host.isConnected||!path.includes(link))continue;
            event.stopImmediatePropagation();
            if(event.type==='click'&&!event.button&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey&&channelURL(link.href)){
                event.preventDefault();if(!globalThis.MinimalYouTubeNavigation?.go(link.href))location.assign(link.href);
            }
            return;
        }
    }
    for(const type of ['pointerdown','mousedown','touchstart','click','auxclick','keydown','keyup'])window.addEventListener(type,routeChannelInput,{capture:true,passive:type!=='click'});
    const headingCopy=new Map([
        ['Watch again',['Посмотреть еще раз','Посмотреть ещё раз','Посмотреть снова','Смотреть ещё раз','Erneut ansehen']],
        ['For you',['Для вас','Für dich','Für Sie']],['Previously watched',['Вы уже смотрели','Bereits angesehen']],
        ['Related videos',['Похожие видео','Ähnliche Videos']],['People also watched',['Другие также посмотрели','Andere haben auch angesehen']],
    ].flatMap(([english,values])=>[english,...values].map(value=>[value.toLocaleLowerCase(),english])));
    const heading=value=>headingCopy.get(value.trim().toLocaleLowerCase())||value.replace(/^(?:Новые видео на канале|Последние видео (?:на канале|от)|Neueste Videos von)\s+/iu,'Latest from ');
    const node=(tag,className,value)=>{const result=document.createElement(tag);if(className)result.className=className;if(value)result.textContent=value;return result;};
    const styles=`
      :host{all:initial!important;display:block!important;width:81%!important;margin-inline:auto!important;min-width:0!important;box-sizing:border-box!important;font:16px/1.45 Arial,sans-serif!important;color:var(--myt-ink)!important;position:relative!important}
      *{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}button{font:inherit;cursor:pointer}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}
      .channels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-bottom:24px}
      .stream,.group-stream{display:flex;flex-direction:column;gap:20px}.row{display:grid;gap:20px;align-items:stretch;min-width:0}
      .results-heading{margin:0 0 20px;font:600 18px/1.5 Arial,sans-serif;overflow-wrap:anywhere}
      .media{display:flex;flex-direction:column;gap:14px;min-width:0;height:100%;padding:12px 12px 18px;border-radius:18px;background:var(--myt-surface);transition:background .12s}
      .media:is(:hover,:focus-within){background:var(--myt-soft)}.cover{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:var(--myt-soft)}.cover img{display:block;width:100%;height:100%;object-fit:cover}.media-info{display:flex;flex-direction:column;justify-content:center;gap:12px;min-width:0;padding:0 3px}
      .media-title{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere;font-size:17px;line-height:1.35;font-weight:700}.media.video .media-title{font-size:16px}.media-date{display:block;color:var(--myt-muted);font-size:14px;line-height:1.4}.media-date[hidden]{display:none}
      .media-channel{display:block;overflow-wrap:anywhere;color:var(--myt-muted);font-size:18px;font-weight:500;line-height:1.4}.media-channel:is(:hover,:focus-visible){color:var(--myt-ink)}
      .media.playlist{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);align-items:center;gap:20px;padding-bottom:12px}.media.playlist .cover{width:100%}.playlist-badge{position:absolute;right:8px;bottom:8px;display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:6px;background:#000b;color:#fff;font-size:13px}
      .group{min-width:0;padding:20px;border-radius:22px;background:var(--myt-soft)}.group h2{margin:0 0 18px;padding-inline-end:.2em;overflow:visible;overflow-wrap:anywhere;font:italic 900 40px/1.05 "MYT Barlow Condensed","MYT Cyrillic Condensed","Arial Narrow",sans-serif;text-transform:uppercase;letter-spacing:-.025em}
      :host([data-channel]) .media.playlist{display:flex;flex-direction:column;gap:14px;padding-bottom:18px}:host([data-channel]) .media.playlist .media-title{font-size:16px}.playlist-badge[hidden]{display:none}.playlist-badge svg{width:15px;height:15px;flex:none}.media.playlist :is(.media-info,.playlist-badge){font-family:"SFMono-Regular",Menlo,Monaco,Consolas,"Liberation Mono",ui-monospace,monospace}.media.playlist .media-title{font-weight:600}
      /* Keep 20px gaps fixed while reducing channel column widths by 15%. */
      :host([data-channel]) :is(.row,.results-heading){width:calc(85% + (var(--myt-columns,1) - 1)*3px);margin-inline:auto}
      .empty{padding:32px 0;color:var(--myt-muted)}:host([data-channel]) .empty{display:flex;align-items:center;justify-content:center;min-height:max(240px,calc(100vh - 360px));margin:0;padding:24px 0;text-align:center;font:700 32px/1.3 Arial,sans-serif;color:var(--myt-ink)}:host([data-channel]) .empty[hidden]{display:none}.more{height:1px}
      .chips{display:flex;flex-wrap:wrap;gap:12px;margin:0 auto 24px}.chips[hidden]{display:none}:host([data-channel]) .chips{width:calc(85% + (var(--myt-columns,1) - 1)*3px)}
      .chip{height:32px;margin:0;padding:0 12px;border:0;border-radius:8px;background:var(--myt-soft);color:var(--myt-ink);font:500 14px/32px Roboto,Arial,sans-serif;cursor:pointer}
      .chip:hover{filter:brightness(1.15)}.chip[aria-pressed="true"]{background:var(--myt-ink);color:var(--myt-bg)}.chip:focus-visible{outline:2px solid var(--myt-muted);outline-offset:2px}
      .post{display:block;box-sizing:border-box;width:min(720px,100%);margin:0 auto 20px;padding:20px;border:1px solid var(--myt-border);border-radius:18px;background:var(--myt-surface);color:var(--myt-ink);font:400 15px/1.55 Roboto,Arial,sans-serif}
      .post-head{display:flex;align-items:center;gap:12px;margin-bottom:12px}.post-avatar{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:none;background:var(--myt-soft)}
      .post-author{display:block;font-weight:600}.post-time{color:var(--myt-muted);font-size:13px;text-decoration:none}.post-time:hover{text-decoration:underline}
      .post-text{margin:0 0 12px;white-space:pre-wrap;overflow-wrap:anywhere;font:400 15px/1.7 "SFMono-Regular",Menlo,Monaco,Consolas,"Liberation Mono",ui-monospace,monospace}.post-text:empty{display:none}
      .post-images{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:12px}.post-images img{display:block;width:100%;max-height:560px;object-fit:cover;border-radius:12px;background:var(--myt-soft)}
      .post-media{display:grid;grid-template-columns:minmax(0,200px) minmax(0,1fr);gap:14px;align-items:center;margin-bottom:12px;color:inherit;text-decoration:none}.post-media img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;background:var(--myt-soft)}.post-media span{font-weight:600;overflow-wrap:anywhere}
      .post-poll{display:grid;gap:8px;margin:0 0 8px;padding:0;list-style:none}.post-poll li{padding:10px 14px;border:1px solid var(--myt-border);border-radius:10px}
      .post-meta{display:flex;flex-wrap:wrap;gap:16px;color:var(--myt-muted);font-size:13px}.post-meta:empty{display:none}
      @media(max-width:600px){.post{padding:16px}.post-media{grid-template-columns:1fr}}@media(max-width:700px){.channels{grid-template-columns:1fr}.media-title{font-size:16px}.media.video .media-title{font-size:15px}.media-channel{font-size:17px}.media.playlist{grid-template-columns:1fr;gap:14px;padding-bottom:18px}.group{padding:16px}.group h2{font-size:32px}.row{gap:16px}:host([data-channel]) .row{width:calc(85% + (var(--myt-columns,1) - 1)*2.4px)}}
    `;
    const videoIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3Z"/></svg>';
    // Upload dates older than four months read as month and year. YouTube
    // gives only a relative age, so the month is counted back from today.
    const ageUnits={second:1/86400,minute:1/1440,hour:1/24,day:1,week:7,month:30.44,year:365.25,sec:1/86400,min:1/1440,hr:1/24,wk:7,mo:30.44,yr:365.25,
        'секунд':1/86400,'минут':1/1440,'час':1/24,'дн':1,'день':1,'недел':7,'месяц':30.44,'год':365.25,'лет':365.25};
    function publishedLabel(value){
        // YouTube may wrap numbers in invisible direction marks and append
        // notes such as "(edited)"; both stay out of the way of the match.
        const text=String(value||'').replace(/[\u00ad\u200b-\u200f\u2060-\u2069\ufeff]/g,'').replace(/[\s\u00a0\u202f]+/g,' ').trim();
        const match=text.match(/^(.*?)(\d+)\s*(second|minute|hour|day|week|month|year|секунд|минут|час|день|дн|недел|месяц|год|лет|sec|min|hr|wk|mo|yr)\S*\s+(?:ago|назад)(.*)$/iu);
        if(!match)return text;
        const days=Number(match[2])*ageUnits[match[3].toLowerCase()],suffix=match[4].trim();
        if(!(days>=4*30.44))return text;
        const date=new Date();
        if(/^(month|месяц|mo$)/i.test(match[3]))date.setMonth(date.getMonth()-Number(match[2]));
        else if(/^(year|год|лет|yr$)/i.test(match[3]))date.setFullYear(date.getFullYear()-Number(match[2]));
        else date.setTime(date.getTime()-days*86400000);
        const prefix=match[1].trim();
        return (prefix?prefix+' ':'')+date.toLocaleDateString('en-US',{month:'long',year:'numeric'})+(suffix?' '+suffix:'');
    }
    const datedText=value=>(globalThis.MinimalYouTubeSearchData?.publishedPattern||/\bago\b|назад/iu).test(value);
    // A content type label is not an owner.
    const ownerLine=(name,href)=>/^(?:playlist|плейлист|mix|микс|podcast|подкаст)$/iu.test(name.trim())?{name:'',href:''}:{name,href};
    class MediaCard{
        constructor(source,kind){
            this.source=source;this.host=node('article','media '+kind);this.host.dataset.kind=kind;
            this.cover=node('a','cover');this.image=node('img');this.image.alt='';this.image.decoding='async';this.cover.append(this.image);
            this.info=node('div','media-info');this.title=node('a','media-title');this.owner=node('a','media-channel');this.date=node('span','media-date');this.date.hidden=true;this.info.append(this.title,this.owner,this.date);
            this.host.append(this.cover,this.info);
            // A playlist shows its video count with a video icon, or nothing.
            if(kind==='playlist'){this.badge=node('span','playlist-badge');this.badgeCount=node('span');this.badge.append(this.badgeCount);this.badge.insertAdjacentHTML('beforeend',videoIcon);this.badge.hidden=true;this.cover.append(this.badge);}
            for(const control of [this.cover,this.title,this.owner])control.addEventListener('click',event=>{
                if(event.button||event.ctrlKey||event.metaKey||event.altKey||event.shiftKey)return;
                const main=control===this.title?this.source.querySelector(titleSelector):null;
                const original=main?.href===control.href?main:[...this.source.querySelectorAll('a[href]')].find(link=>link.href===control.href);
                if(original){event.preventDefault();event.stopPropagation();original.click();}
            });
        }
        update(data){
            this.host.dataset.href=data.href;
            for(const control of [this.cover,this.title])if(control.href!==data.href)control.href=data.href;
            if(this.title.textContent!==data.title)this.title.textContent=data.title;
            if(this.owner.textContent!==data.channel.name)this.owner.textContent=data.channel.name;
            this.owner.hidden=!data.channel.name;if(data.channel.href)this.owner.href=data.channel.href;else this.owner.removeAttribute('href');
            if(this.image.getAttribute('src')!==data.image){if(data.image)this.image.src=data.image;else this.image.removeAttribute('src');}
            this.image.hidden=!data.image;
            const date=publishedLabel(data.published);if(this.date.textContent!==date)this.date.textContent=date;this.date.hidden=!date;
            if(this.badge){const count=data.count||'';if(this.badgeCount.textContent!==count)this.badgeCount.textContent=count;this.badge.hidden=!count;this.badge.setAttribute('aria-label',count?count+(count==='1'?' video':' videos'):'');}
        }
        destroy(){this.host.remove();}
    }
    // A channel post in the owned design: public text, images, attachments and
    // counts. Likes, poll votes and comments are not account actions here.
    class PostCard{
        constructor(){this.host=node('article','post');this.host.dataset.kind='post';}
        update(data){
            const signature=JSON.stringify(data);if(this.signature===signature)return;this.signature=signature;
            this.host.dataset.href=data.href||'';
            const head=node('div','post-head'),who=node('div','post-who');
            const avatar=safeURL(data.avatar);if(avatar){const image=node('img','post-avatar');image.alt='';image.decoding='async';image.loading='lazy';image.src=avatar.href;head.append(image);}
            who.append(node('span','post-author',data.author||''));
            const time=node(data.href?'a':'span','post-time',publishedLabel(data.published));if(data.href&&safeURL(data.href))time.href=safeURL(data.href).href;who.append(time);head.append(who);
            const parts=[head,node('p','post-text',data.text||'')];
            const images=(data.images||[]).map(safeURL).filter(Boolean);
            if(images.length){const grid=node('div','post-images');for(const url of images){const image=node('img');image.alt='';image.decoding='async';image.loading='lazy';image.src=url.href;grid.append(image);}parts.push(grid);}
            const media=data.media&&safeURL(data.media.href);
            if(media){const link=node('a','post-media');link.href=media.href;const cover=safeURL(data.media.image);if(cover){const image=node('img');image.alt='';image.decoding='async';image.loading='lazy';image.src=cover.href;link.append(image);}link.append(node('span','',data.media.title||''));parts.push(link);}
            if(data.poll?.choices?.length){const list=node('ul','post-poll');for(const choice of data.poll.choices)list.append(node('li','',choice));parts.push(list);}
            const meta=node('div','post-meta');
            if(data.poll?.votes)meta.append(node('span','',data.poll.votes));
            if(data.likes)meta.append(node('span','',data.likes+' likes'));
            if(data.comments)meta.append(node('span','',/\d/.test(data.comments)?data.comments+' comments':data.comments));
            parts.push(meta);this.host.replaceChildren(...parts);
        }
        destroy(){this.host.remove();}
    }
    const chipLabels=new Map([['новые','Latest'],['популярные','Popular'],['старые','Oldest'],['latest','Latest'],['popular','Popular'],['oldest','Oldest'],['neueste','Latest'],['beliebt','Popular'],['älteste','Oldest']]);
    // Install native-page isolation with the renderer itself. Updating the
    // renderer cannot leave an older CSS asset painting a second search UI.
    const nativeStyles=`/* Search owns result cards. Native filter controls and pagination keep
   their original DOM parents, handlers and browser input. */
html.minimal-youtube[data-myt-search-ui],html.minimal-youtube[data-myt-search-ui] body {
    height:auto !important;max-height:none !important;overflow-y:auto !important;overflow-x:hidden !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search {
    display:flex !important;flex-direction:column !important;position:relative !important;box-sizing:border-box !important;
    width:100% !important;max-width:1280px !important;margin:0 auto !important;padding:28px 24px 48px !important;
}
html.minimal-youtube[data-myt-search-ui] #myt-search { order:0 !important;flex:none !important;width:81% !important;margin:0 auto !important;padding:0 !important; }
html.minimal-youtube[data-myt-search-ui] ytd-page-manager { margin-left:0 !important;margin-right:0 !important;width:100% !important;min-width:0 !important;height:auto !important;max-height:none !important;overflow:visible !important; }
html.minimal-youtube[data-myt-search-ui] ytd-search > :not(#myt-search):not([data-myt-search-layout-path]),
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-native-root]:not([data-myt-search-layout-path]),
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-layout-path]:not([data-myt-search-native-ui]) > :not([data-myt-search-layout-path]) {
    display:block !important;position:absolute !important;inset:0 auto auto 0 !important;width:0 !important;height:0 !important;
    min-width:0 !important;min-height:0 !important;margin:0 !important;padding:0 !important;
    overflow:hidden !important;visibility:hidden !important;opacity:0 !important;pointer-events:none !important;contain:strict !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-layout-path]:not([data-myt-search-native-ui]) {
    display:contents !important;position:static !important;width:auto !important;height:auto !important;
    visibility:visible !important;opacity:1 !important;overflow:visible !important;contain:none !important;
}
/* YouTube lays out a rich grid from its own width: without a box it stamps
   no items when it re-renders after an SPA section change. Without page
   data, keep it as an invisible full-width 2px strip at the end of the
   results; the continuation sentinel inside it stays at the bottom. With
   page data the cards come from data, so the grid keeps its layout path and
   its native sort chips stay visible. */
html.minimal-youtube[data-myt-search-ui]:not([data-myt-page-data]) ytd-search ytd-rich-grid-renderer[data-myt-search-layout-path]:not([data-myt-search-native-ui]) {
    display:block !important;position:absolute !important;inset:auto 0 0 0 !important;width:auto !important;height:2px !important;
    min-height:0 !important;margin:0 !important;padding:0 !important;overflow:hidden !important;
    visibility:hidden !important;pointer-events:none !important;contain:none !important;
}
html.minimal-youtube[data-myt-search-ui]:not([data-myt-page-data]) ytd-search ytd-rich-grid-renderer[data-myt-search-layout-path]:not([data-myt-search-native-ui]) [data-myt-search-layout-path] {
    display:block !important;position:static !important;width:100% !important;height:2px !important;margin:0 !important;padding:0 !important;overflow:hidden !important;
}
html.minimal-youtube[data-myt-search-ui][data-myt-own-chips] ytd-search :is(ytd-feed-filter-chip-bar-renderer, yt-chip-cloud-renderer) { display:none !important; }
html.minimal-youtube[data-myt-search-ui][data-myt-page-data] ytd-search ytd-continuation-item-renderer,
html.minimal-youtube[data-myt-search-ui][data-myt-page-data] ytd-search ytd-continuation-item-renderer[data-myt-search-layout-path]:not([data-myt-search-native-ui]) { display:none !important; }
html.minimal-youtube[data-myt-search-ui] ytd-search ytd-continuation-item-renderer[data-myt-search-layout-path]:not([data-myt-search-native-ui]) {
    display:block !important;order:1 !important;height:2px !important;min-height:2px !important;pointer-events:none !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-toolbar] {
    display:block !important;order:-1 !important;position:relative !important;inset:auto !important;
    box-sizing:border-box !important;flex:none !important;width:81% !important;max-width:none !important;height:auto !important;
    margin:0 auto 24px !important;padding:0 0 16px !important;
    visibility:visible !important;opacity:1 !important;pointer-events:auto !important;overflow:visible !important;contain:none !important;
}
@media(max-width:600px){html.minimal-youtube[data-myt-search-ui] ytd-search{padding:20px 16px 40px !important;}}`;
    class Search{
        constructor(channel=false){
            this.channel=channel;
            this.nativeStyle=node('style');this.nativeStyle.id='myt-search-native-style';this.nativeStyle.textContent=channel?nativeStyles.replaceAll('ytd-search','[data-myt-channel-results]'):nativeStyles;document.documentElement.append(this.nativeStyle);
            this.cards=new Map();this.channels=new Map();this.groups=new Map();this.sources=new Map();this.virtualSources=new Map();this.sequence=0;this.nativeNodes=new Set();this.filterText=new Map();this.filterAttributes=new Map();
            this.host=node('div');this.host.id='myt-search';this.host.lang='en';if(channel)this.host.dataset.channel='';this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML='<style>'+styles+'</style><h2 class="results-heading" lang="ru" hidden>Результаты поиска</h2><div class="channels" aria-label="Channels"></div><div class="chips" role="group" aria-label="Sort" hidden></div><div class="stream"></div><p class="empty" hidden>No results found.</p><div class="more" aria-hidden="true"></div>';
            this.q=selector=>this.shadow.querySelector(selector);
            this.resize=new ResizeObserver(()=>this.layout());this.resize.observe(this.host);
            // Page data loads further results itself; this sentinel replaces
            // the native continuation while results come from that data.
            this.moreVisible=false;
            this.moreObserver=new IntersectionObserver(entries=>{this.moreVisible=entries.some(entry=>entry.isIntersecting);this.requestMore();},{rootMargin:'0px 0px 1200px 0px'});
            this.moreObserver.observe(this.q('.more'));
            this.modelChanged=()=>this.queue();document.addEventListener('minimal-youtube:page-model-updated',this.modelChanged);
            this.observer=new MutationObserver(records=>{
                if(records.every(record=>record.type==='attributes'&&record.attributeName?.startsWith('data-myt-search-')))return;
                let rebuild=false;
                for(const record of records){
                    const target=record.target instanceof Element?record.target:record.target.parentElement,source=target?.closest(sourceSelector);
                    const textOnly=record.type==='characterData'||record.type==='childList'&&[...record.addedNodes,...record.removedNodes].every(node=>node.nodeType===Node.TEXT_NODE);
                    const imageOnly=record.type==='attributes'&&['src','srcset','data-src','data-srcset','href','data-video-count'].includes(record.attributeName);
                    if(source&&this.cards.has(source)&&(textOnly||imageOnly)){
                        if(!textOnly||target.closest('h3,ytd-channel-name,#channel-info,a')||this.cards.get(source).host.dataset.kind==='playlist'&&target.closest(countSelector))this.queueCard(source);
                    }else rebuild=true;
                }
                if(rebuild)this.queue();
            });
            this.selectionNodes=new Set();this.selectionObserver=new MutationObserver(()=>this.queue());
            this.changed=()=>this.queue();document.addEventListener('yt-page-data-updated',this.changed);document.addEventListener('yt-rendererstamper-finished',this.changed);
        }
        static isPlaylist(card){return card.matches('ytd-playlist-renderer,ytd-grid-playlist-renderer,ytd-radio-renderer,[is-playlist],[content-type="playlist"],[data-content-type="playlist"]')||!!card.querySelector('yt-collection-thumbnail-view-model,yt-collections-stack,ytd-thumbnail-overlay-side-panel-renderer')||safeURL(card.querySelector(titleSelector)?.href)?.pathname==='/playlist';}
        prepareChannelRoute(href){
            if(!this.channel)return;
            const url=new URL(href),key=JSON.stringify([url.pathname.replace(/\/$/,''),/\/search\/?$/.test(url.pathname)?url.searchParams.get('query')?.trim()||'':'']);
            if(this.routeKey===key)return;
            this.routeKey=key;
            // Restore native visibility before choosing the incoming feed. Our
            // old root's display override can otherwise reveal a cached search
            // shell that YouTube has hidden using a class on a tab transition.
            this.observer.disconnect();this.search?.removeEventListener('load',this.changed,true);
            this.search?.removeAttribute('data-myt-channel-results');this.restoreNative();this.search=null;
            this.host.remove();
        }
        static channelResults(browse){
            // Discover the feed from its cards instead of depending on a named
            // section/primary wrapper. Use its outer content branch so native
            // inner widths cannot give search a different grid from Videos.
            const available=node=>{
                if(node.closest(channelExcludedSelector)||!nativeAvailable(node,browse.parentElement))return false;
                for(let parent=node;parent&&parent!==browse;parent=parent.parentElement)if(getComputedStyle(parent).display==='none')return false;
                return true;
            };
            const source=[...browse.querySelectorAll(sourceSelector)].find(available)||[...browse.querySelectorAll(emptySelector)].find(node=>!node.closest(channelExcludedSelector)&&nativeAvailable(node,browse.parentElement));
            if(source){
                let contents=source.parentElement;
                while(contents.parentElement&&contents.parentElement!==browse&&!contents.parentElement.querySelector(channelHeaderSelector+',#tabs,#tabs-container'))contents=contents.parentElement;
                if(contents!==browse&&!contents.querySelector(channelHeaderSelector))return contents;
            }
            // Loading and empty feeds have no cards to locate yet.
            const previous=browse.querySelector('[data-myt-channel-results]');
            if(previous&&available(previous))return previous;
            return [...browse.querySelectorAll(':scope > #contents,:scope > #primary,ytd-two-column-browse-results-renderer,ytd-section-list-renderer,ytd-rich-grid-renderer')].find(available)||null;
        }
        queue(){if(this.frame)return;this.frame=requestAnimationFrame(()=>{this.frame=0;const searches=document.querySelectorAll(this.channel?'[data-myt-channel-results]':'ytd-search');if(searches.length)this.sync(searches);});}
        queueCard(source){
            if(!this.cards.has(source)){this.queue();return;}
            this.pendingCards ||=new Set();this.pendingCards.add(source);if(this.cardFrame)return;
            this.cardFrame=requestAnimationFrame(()=>{this.cardFrame=0;for(const source of this.pendingCards){const card=this.cards.get(source);if(card&&source.isConnected){if(Search.isPlaylist(source)!==(card.host.dataset.kind==='playlist')){this.queue();continue;}const data=this.read(source,card.host.dataset.kind,card.record);if(data)card.update(data);else this.queue();}}this.pendingCards.clear();});
        }
        translateFilters(){
            for(const [node,state]of this.filterText)if(!node.isConnected){if(node.data===state.applied)node.data=state.original;this.filterText.delete(node);}
            for(const [node,attributes]of this.filterAttributes)if(!node.isConnected){for(const [name,state]of attributes)if(node.getAttribute(name)===state.applied)node.setAttribute(name,state.original);this.filterAttributes.delete(node);}
            for(const scope of document.querySelectorAll(filterScopeSelector)){
                if(scope.closest('ytd-search')&&scope.closest('ytd-search')!==this.search)continue;
                if(scope.parentElement?.closest(filterScopeSelector))continue;
                const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let item;
                while(item=walker.nextNode()){
                    const current=item.data,translated=englishFilter(current);if(!translated||translated===current.trim())continue;
                    this.filterText.set(item,{original:current,applied:translated});item.data=translated;
                }
                for(const node of [scope,...scope.querySelectorAll('[aria-label],[title]')])for(const name of ['aria-label','title']){
                    const current=node.getAttribute(name);if(!current)continue;const translated=englishFilter(current);if(!translated||translated===current.trim())continue;
                    if(!this.filterAttributes.has(node))this.filterAttributes.set(node,new Map());
                    this.filterAttributes.get(node).set(name,{original:current,applied:translated});node.setAttribute(name,translated);
                }
            }
        }
        read(source,kind,record){
            const anchors=[...source.querySelectorAll('a[href]')];
            const title=source.querySelector(titleSelector);
            const main=(title?.matches('a[href]')?title:title?.closest('a[href]')||title?.querySelector('a[href]'))||anchors.find(link=>{const url=safeURL(link.href);return kind==='video'?url?.pathname==='/watch':url?.pathname==='/playlist'||url?.searchParams.has('list');});
            const owner=source.querySelector('ytd-channel-name a[href],#channel-info a[href],.ytLockupMetadataViewModelMetadata a[href],a[href^="/@"]')||anchors.find(link=>channelURL(link.href));
            const href=youtubeURL(main?.href||record?.href);
            if(!href||kind==='video'&&(new URL(href).pathname!=='/watch'||!new URL(href).searchParams.has('v')))return null;
            const parsed=new URL(href),cached=kind==='playlist'?this.playlistMetadata?.get(parsed.searchParams.get('list')||record?.id):null;
            let image=coverImage(source)||record?.image||cached?.image;
            if(!image&&parsed.searchParams.get('v')?.match(/^[-\w]{11}$/))image='https://i.ytimg.com/vi/'+parsed.searchParams.get('v')+'/hqdefault.jpg';
            const count=kind==='playlist'?([...source.querySelectorAll(countSelector)].map(node=>countNumber(node.getAttribute('data-video-count')||node.getAttribute('aria-label')||text(node))).find(Boolean)||countNumber(record?.count)||countNumber(cached?.count)):'';
            // A channel's own cards need no owner line; it is the page's channel.
            const hideChannel=this.channel;
            const published=kind==='video'?record?.published||[...source.querySelectorAll('#metadata-line span,.inline-metadata-item,.ytContentMetadataViewModelMetadataText,[class*="MetadataText"]')].map(text).find(value=>value&&value.length<100&&datedText(value))||'':'';
            return {kind,href,title:text(title)||text(main)||record?.title||'Video',image,count,published,channel:hideChannel?{name:'',href:''}:ownerLine(text(owner)||record?.channel?.name||'',channelURL(owner?.href||record?.channel?.href))};
        }
        sync(searches){
            if(!this.nativeStyle.isConnected)document.documentElement.append(this.nativeStyle);
            document.documentElement.setAttribute('data-myt-search-ui','');
            const candidates=[...searches],selectionNodes=new Set();
            for(const item of candidates)for(let parent=item;parent&&parent!==document.body;parent=parent.parentElement)selectionNodes.add(parent);
            for(const item of candidates)for(const toolbar of item.querySelectorAll(nativeToolbarSelector))selectionNodes.add(toolbar);
            if(this.channel){selectionNodes.add(document.documentElement);const nav=document.querySelector('#myt-channel-nav');if(nav)selectionNodes.add(nav);}
            if(selectionNodes.size!==this.selectionNodes.size||[...selectionNodes].some(item=>!this.selectionNodes.has(item))){
                this.selectionObserver.disconnect();this.selectionNodes=selectionNodes;
                for(const item of selectionNodes)this.selectionObserver.observe(item,{attributes:true,attributeFilter:['hidden','aria-hidden','class','style','aria-busy','data-myt-channel-search-empty']});
            }
            const search=candidates.find(item=>!item.closest('[hidden],[aria-hidden="true"]')&&item.getClientRects().length&&getComputedStyle(item).visibility!=='hidden')||candidates[0];if(!search)return;
            if(this.search!==search){
                this.search?.removeEventListener('load',this.changed,true);
                this.restoreNative();
                this.observer.disconnect();this.search=search;
                this.observer.observe(search,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['href','src','srcset','data-src','data-srcset','data-video-count','class','hidden','aria-hidden','style','aria-label','aria-pressed','subscribed','is-subscribed','disabled']});
                search.addEventListener('load',this.changed,true);
            }
            if(this.host.parentElement!==search)search.prepend(this.host);
            const nativeSources=[...search.querySelectorAll(sourceSelector)].filter(source=>(!this.channel||nativeAvailable(source,search)&&!source.closest(channelExcludedSelector))&&!source.parentElement.closest(sourceSelector)&&!source.closest('[data-myt-hidden],[data-myt-hidden-section],ytd-reel-shelf-renderer')&&!/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu.test(text(source.closest(shelfSelector)?.querySelector('#title-container,#header,h2'))));
            for(const source of nativeSources){
                let kind=source.matches('ytd-channel-renderer,[content-type="channel"],[data-content-type="channel"]')?'channel':Search.isPlaylist(source)?'playlist':'video';
                if(!this.sources.has(source)){const key='result-'+(++this.sequence);this.sources.set(source,key);source.setAttribute('data-myt-search-source-key',key);}
                source.setAttribute('data-myt-search-source-kind',kind);
            }
            document.dispatchEvent(new Event('minimal-youtube:search-snapshot'));
            try{this.snapshot=JSON.parse(document.documentElement.getAttribute('data-myt-search-snapshot')||'{}');}catch{this.snapshot={};}
            const records=new Map((this.snapshot.records||[]).map(record=>[record.key,record])),channelCache=new Map();
            this.playlistMetadata=new Map();try{for(const value of JSON.parse(document.documentElement.getAttribute('data-myt-search-playlists')||'[]').slice(-200))if(typeof value.id==='string')this.playlistMetadata.set(value.id,value);}catch{}
            try{for(const value of JSON.parse(document.documentElement.getAttribute('data-myt-search-channels')||'[]'))channelCache.set(value.id,value);}catch{}
            // YouTube's page data is the source of results: it always holds
            // the page's items, while its own grid can fail to stamp them.
            // Channel cards in search stay on their native nodes, which keep
            // YouTube's live subscribe controls. Without page data, the
            // native result cards remain the source.
            const model=this.pageModel(),dataRecords=new Map();
            let sources=nativeSources;
            if(model){
                sources=this.channel?[]:nativeSources.filter(source=>(records.get(this.sources.get(source))?.kind||source.getAttribute('data-myt-search-source-kind'))==='channel');
                for(const record of model.items){
                    if(record?.kind==='channel'||typeof record?.href!=='string'||!youtubeURL(record.href))continue;
                    const id=record.href+'|'+(record.group||'');
                    let source=this.virtualSources.get(id);if(!source){source=document.createElement('div');this.virtualSources.set(id,source);}
                    dataRecords.set(source,record);sources.push(source);
                }
            }
            for(const [id,source]of this.virtualSources)if(!dataRecords.has(source))this.virtualSources.delete(id);
            this.model=model;document.documentElement.toggleAttribute('data-myt-page-data',Boolean(model));
            const wanted=new Set(sources);
            const stream=[],groups=new Map();
            for(const source of sources){
                const record=dataRecords.get(source)||records.get(this.sources.get(source)),kind=record?.kind||source.getAttribute('data-myt-search-source-kind');
                if(kind==='channel'){
                    this.cards.get(source)?.destroy();this.cards.delete(source);
                    let card=this.channels.get(source);if(!card){card=new ChannelCard(source,()=>this.queue(),this.q('.channels'));this.channels.set(source,card);}card.update(channelCache,record||null);continue;
                }
                this.channels.get(source)?.destroy();this.channels.delete(source);
                if(kind==='post'){
                    let card=this.cards.get(source);if(card&&!(card instanceof PostCard)){card.destroy();card=null;}
                    if(!card){card=new PostCard();this.cards.set(source,card);}card.update(record);stream.push(card);continue;
                }
                const value=this.read(source,kind,record);if(!value)continue;
                let card=this.cards.get(source);if(card&&card.host.dataset.kind!==kind){card.destroy();card=null;}if(!card){card=new MediaCard(source,kind);this.cards.set(source,card);}card.record=record;card.update(value);
                const dataGroup=dataRecords.get(source)?.group||'';
                const shelf=dataGroup?this.dataGroup(dataGroup):source.closest(shelfSelector),header=dataGroup?null:shelf?.querySelector('#title-container,#header,h2,[role="heading"]'),label=dataGroup||channelText(header?.querySelector('#title,h2,h3,.ytShelfHeaderLayoutTitle')||header);
                if(shelf&&label){
                    let group=groups.get(shelf);if(!group){
                        group=this.groups.get(shelf)||{host:node('section','group'),title:node('h2'),stream:node('div','group-stream')};group.host.dataset.kind='group';
                        const name=heading(label);if(group.title.textContent!==name){group.title.textContent=name;globalThis.MinimalYouTubeWatch?.loadTitleFonts?.(name);}
                        if(!group.title.parentNode)group.host.append(group.title,group.stream);
                        group.items=[];groups.set(shelf,group);stream.push(group);
                    }group.items.push(card);
                }else stream.push(card);
            }
            for(const [source,card]of this.cards)if(!wanted.has(source)){card.destroy();this.cards.delete(source);}
            for(const [source,card]of this.channels)if(!wanted.has(source)){card.destroy();this.channels.delete(source);}
            for(const [source,key]of this.sources)if(!wanted.has(source)){source.removeAttribute('data-myt-search-source-key');source.removeAttribute('data-myt-search-source-kind');this.sources.delete(source);}
            for(const [shelf,group]of this.groups)if(!groups.has(shelf))group.host.remove();this.groups=groups;this.stream=stream;
            const channelContainer=this.q('.channels');let index=0;
            for(const source of sources){const card=this.channels.get(source);if(card){if(channelContainer.children[index]!==card.host)channelContainer.insertBefore(card.host,channelContainer.children[index]||null);index++;}}
            const url=new URL(location.href),query=this.channel&&/\/search\/?$/.test(url.pathname)&&Boolean(url.searchParams.get('query')?.trim());
            const blank=this.channel&&/\/search\/?$/.test(url.pathname)&&(!query||document.documentElement.hasAttribute('data-myt-channel-search-empty'));
            this.q('.results-heading').hidden=!query||blank;this.q('.stream').hidden=blank;
            const busy=this.channel&&document.querySelector('#myt-channel-nav')?.getAttribute('aria-busy')==='true';
            const confirmedEmpty=this.channel&&(model?!model.items.length&&!model.more&&!model.loading:[...search.querySelectorAll('ytd-message-renderer,yt-message-view-model,ytd-background-promo-renderer')].some(node=>nativeAvailable(node,search)));
            this.q('.empty').textContent=this.channel&&!query?(/\/playlists\/?$/.test(url.pathname)?'No playlists yet.':/\/(?:posts|community)\/?$/.test(url.pathname)?'No posts yet.':'No videos yet.'):'No results found.';
            this.renderChips(model);
            this.q('.channels').hidden=!this.channels.size||blank;this.q('.empty').hidden=Boolean(blank||this.channels.size||stream.length||busy||this.channel&&!query&&!confirmedEmpty);
            // One message for an empty search: no heading above it.
            if(!this.q('.empty').hidden)this.q('.results-heading').hidden=true;
            this.prepareNative(search);this.translateFilters();this.layout();this.requestMore();
        }
        pageModel(){
            document.dispatchEvent(new Event('minimal-youtube:page-model'));
            let model=null;try{model=JSON.parse(document.documentElement.getAttribute('data-myt-page-model')||'null');}catch{}
            return model&&Array.isArray(model.items)&&(this.channel?['channel','posts'].includes(model.type):model.type==='search')?model:null;
        }
        renderChips(model){
            const bar=this.q('.chips'),chips=this.channel&&Array.isArray(model?.chips)?model.chips:[];
            const signature=JSON.stringify(chips);
            if(bar.dataset.value!==signature){
                bar.dataset.value=signature;
                bar.replaceChildren(...chips.map((chip,index)=>{
                    const button=node('button','chip',chipLabels.get(String(chip.label).toLocaleLowerCase())||chip.label);button.type='button';
                    button.setAttribute('aria-pressed',String(Boolean(chip.selected)));
                    button.addEventListener('click',()=>{document.documentElement.setAttribute('data-myt-page-model-chip',String(index));document.dispatchEvent(new Event('minimal-youtube:page-model-chip'));});
                    return button;
                }));
            }
            bar.hidden=!chips.length;document.documentElement.toggleAttribute('data-myt-own-chips',chips.length>0);
        }
        dataGroup(label){
            this.dataGroups ||=new Map();
            let key=this.dataGroups.get(label);if(!key){key={label};this.dataGroups.set(label,key);}
            return key;
        }
        requestMore(){
            if(this.moreVisible&&this.model?.more&&!this.model.loading&&this.host.isConnected)document.dispatchEvent(new Event('minimal-youtube:page-model-more'));
        }
        prepareNative(search){
            // Keep native controllers in place. Only continuation paths contribute
            // height after our rendered results, so native pagination still sees
            // its sentinel at the actual end of the stream.
            for(const child of search.children)if(child!==this.host){child.setAttribute('data-myt-search-native-root','');this.nativeNodes.add(child);}
            // Reveal the original toolbar in place. Browser-trusted input and
            // YouTube's delegated handlers keep their original DOM event path.
            const available=node=>nativeAvailable(node,search);
            const paths=new Set(),toolbar=[...search.querySelectorAll(nativeToolbarSelector)].find(available)||[...search.querySelectorAll('button,[role="button"],tp-yt-paper-button')].slice(0,200).find(node=>available(node)&&/^(?:filters|filter|фильтры)$/iu.test(node.getAttribute('aria-label')||text(node)));
            const nativeUI=new Set(toolbar?[toolbar]:[]);
            if(this.channel)for(const control of search.querySelectorAll('ytd-feed-filter-chip-bar-renderer,yt-chip-cloud-renderer'))if(available(control))nativeUI.add(control);
            for(const panel of search.querySelectorAll('ytd-search-filter-dialog-renderer,yt-search-filter-dialog-view-model'))if(!toolbar?.contains(panel))nativeUI.add(panel.closest('dialog,tp-yt-paper-dialog,tp-yt-iron-dropdown,[role="dialog"]')||panel);
            for(const endpoint of [...search.querySelectorAll('ytd-continuation-item-renderer'),...nativeUI])if(!this.channel||available(endpoint))for(let parent=endpoint;parent&&parent!==search;parent=parent.parentElement)paths.add(parent);
            for(const source of this.nativeNodes){
                if(source.hasAttribute('data-myt-search-layout-path')&&!paths.has(source))source.removeAttribute('data-myt-search-layout-path');
                if(source.hasAttribute('data-myt-search-toolbar')&&source!==toolbar)source.removeAttribute('data-myt-search-toolbar');
                if(source.hasAttribute('data-myt-search-native-ui')&&!nativeUI.has(source))source.removeAttribute('data-myt-search-native-ui');
            }
            for(const path of paths){path.setAttribute('data-myt-search-layout-path','');this.nativeNodes.add(path);}
            for(const element of nativeUI)element.setAttribute('data-myt-search-native-ui','');
            if(toolbar)toolbar.setAttribute('data-myt-search-toolbar','');
            if(this.channel)for(const control of nativeUI)control.setAttribute('data-myt-search-toolbar','');
        }

        restoreNative(){
            for(const native of this.nativeNodes){native.removeAttribute('data-myt-search-native-root');native.removeAttribute('data-myt-search-layout-path');native.removeAttribute('data-myt-search-toolbar');native.removeAttribute('data-myt-search-native-ui');}
            this.nativeNodes.clear();
        }

        layout(){
            if(!this.host.isConnected||!this.stream)return;
            const style=getComputedStyle(this.search),width=this.search.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),columns=width<560?1:width<900?2:3;
            if(this.channel&&this.host.style.getPropertyValue('--myt-columns')!==String(columns))this.host.style.setProperty('--myt-columns',String(columns));
            this.place(this.q('.stream'),this.stream,columns);
            for(const group of this.groups.values())this.place(group.stream,group.items,columns===3&&[2,4].includes(group.items.length)?2:columns);
        }
        place(container,items,columns){
            // Preserve source order and fixed units; native wrappers never
            // reserve cells. A playlist occupies exactly two video columns.
            const signature=items.map(item=>item.host.dataset.kind+':'+(item.host.dataset.href||item.title?.textContent||'')).join('|')+':'+columns;
            if(container.dataset.layout===signature&&items.every(item=>item.host.isConnected))return;
            container.dataset.layout=signature;let row=null,used=0,content=[];
            const flush=()=>{if(!row)return;row.style.gridTemplateColumns='repeat('+columns+',minmax(0,1fr))';if(this.channel)row.style.setProperty('--myt-columns',String(columns));content.push(row);row=null;used=0;};
            for(const item of items){
                if(item.items||item.host.dataset.kind==='post'){flush();content.push(item.host);continue;}
                const units=Math.min(columns,!this.channel&&item.host.dataset.kind==='playlist'?2:1);
                if(row&&used+units>columns)flush();
                if(!row)row=node('div','row');item.host.style.gridColumn='span '+units;row.append(item.host);used+=units;
                if(used===columns)flush();
            }
            flush(false);container.replaceChildren(...content);
        }
        destroy(){
            for(const [node,state]of this.filterText)if(node.data===state.applied)node.data=state.original;
            for(const [node,attributes]of this.filterAttributes)for(const [name,state]of attributes)if(node.getAttribute(name)===state.applied)node.setAttribute(name,state.original);
            this.filterText.clear();this.filterAttributes.clear();
            this.nativeStyle.remove();
            this.selectionObserver.disconnect();this.selectionNodes.clear();
            document.documentElement.removeAttribute('data-myt-search-ui');
            cancelAnimationFrame(this.cardFrame);this.pendingCards?.clear();
            cancelAnimationFrame(this.frame);this.observer.disconnect();this.resize.disconnect();this.search?.removeEventListener('load',this.changed,true);
            document.removeEventListener('yt-page-data-updated',this.changed);document.removeEventListener('yt-rendererstamper-finished',this.changed);
            document.removeEventListener('minimal-youtube:page-model-updated',this.modelChanged);this.moreObserver.disconnect();document.documentElement.removeAttribute('data-myt-page-data');document.documentElement.removeAttribute('data-myt-own-chips');
            for(const card of [...this.cards.values(),...this.channels.values()])card.destroy();
            for(const source of this.sources.keys()){source.removeAttribute('data-myt-search-source-key');source.removeAttribute('data-myt-search-source-kind');}
            this.restoreNative();
            this.host.remove();this.cards.clear();this.channels.clear();this.sources.clear();
        }
    }
    Search.playlistSelector=playlistSelector;Search.filterScopeSelector=filterScopeSelector;
    globalThis.MinimalYouTubeSearch=Search;
})();
