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
    const channelStyles=`
      :host{all:initial!important;--ink:var(--myt-ink);--muted:var(--myt-muted);--surface:var(--myt-surface);--soft:var(--myt-soft);--border:var(--myt-border);display:block!important;position:relative!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;color:var(--ink)!important}
      :host::before,:host::after{content:none!important;display:none!important}
      *{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none;cursor:pointer}button{font:inherit;cursor:pointer}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}
      ${globalThis.MinimalYouTubeWatch?.subscriptionStyles||''}
      .surface.channel-card{grid-template-columns:80px minmax(0,1fr) 20px;width:100%;max-width:none;min-height:128px;padding:20px;gap:6px 16px;border-radius:16px}
      .avatar{display:grid;place-items:center;width:80px;height:80px;overflow:hidden;border-radius:50%;background:var(--myt-soft);font-size:28px;font-weight:600}
      .owner .avatar img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
      .heading{display:flex;align-items:baseline;gap:5px;min-width:0}.name{font-size:18px;font-weight:600;line-height:1.35;overflow-wrap:anywhere}.verified{flex:none;width:14px;height:14px;align-self:center;color:var(--muted)}
      .metadata{margin:0;overflow-wrap:anywhere;color:var(--muted)}
      @media(max-width:600px){.surface.channel-card{grid-template-columns:64px minmax(0,1fr) 18px;gap:4px 12px;padding:16px}.avatar{width:64px;height:64px}.name{font-size:17px}}
    `;
    const channelText=node=>{
        if(!node)return '';
        const copy=node.cloneNode(true);
        copy.querySelectorAll('button,[role="button"],script,style,svg,yt-icon,ytd-badge-supported-renderer,tp-yt-paper-tooltip,yt-tooltip,[hidden],[aria-hidden="true"],[aria-label="Verified"]').forEach(child=>child.remove());
        return text(copy);
    };

    class ChannelCard {
        constructor(source,queue,container){
            this.source=source;this.queue=queue;this.container=container;this.parts=new Set();
            this.host=document.createElement('div');this.host.dataset.mytSearchChannelCard='';this.host.lang='en';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=`<style>${channelStyles}</style><article class="surface channel-card"><button class="subscribe channel-subscribe" type="button" aria-pressed="false" aria-describedby="search-subscription-status" disabled></button><div class="owner"><a class="avatar avatar-link" data-myt-search-avatar-link><span class="initial" aria-hidden="true"></span><img alt="" decoding="async" hidden></a><div class="info owner-text"><div class="heading"><a class="name owner-link owner-name"></a><svg class="verified" role="img" aria-label="Verified" viewBox="0 0 24 24" hidden><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="m7 12 3 3 7-7" fill="none" stroke="var(--surface)" stroke-width="2"/></svg></div></div></div><span class="subscription-state" id="search-subscription-status" aria-live="polite"></span><p class="metadata stats" hidden></p></article>`;
            this.q=selector=>this.shadow.querySelector(selector);
            this.subscription=globalThis.MinimalYouTubeWatch.createSubscriptionController({q:this.q,readState:()=>this.subscriptionState(),prepareAction:button=>this.prepareSubscriptionAction(button)});
            this.q('img').onerror=()=>{const image=this.q('img');this.failedImage=image.getAttribute('src');if(this.fallbackImage&&image.src!==this.fallbackImage){image.src=this.fallbackImage;image.hidden=false;return;}image.hidden=true;this.q('.initial').hidden=false;};
            this.q('img').onload=()=>{if(this.q('img').naturalWidth<=1){this.q('img').onerror();return;}this.q('.initial').hidden=true;};
            for(const link of [this.q('.avatar'),this.q('.name')])link.addEventListener('click',event=>{
                if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||!this.link?.isConnected)return;
                event.preventDefault();event.stopPropagation();this.link.click();
            });
            this.q('.subscribe').addEventListener('click',()=>this.subscription.toggleSubscription());
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
            const href=safeURL(cached?.url)?.href||this.link?.href||(handle?safeURL('/'+handle)?.href:'')||'';
            for(const link of [this.q('.avatar'),this.q('.name')]){if(href){if(link.href!==href)link.href=href;}else link.removeAttribute('href');}
            if(this.q('.name').textContent!==name)this.q('.name').textContent=name;
            this.q('.avatar').setAttribute('aria-label','Open channel '+name);
            if(this.q('.initial').textContent!==name.slice(0,1))this.q('.initial').textContent=name.slice(0,1);
            const srcset=image?.getAttribute('data-srcset')||image?.getAttribute('srcset')||'';
            this.fallbackImage=cached?.image||'';
            const src=[image?.getAttribute('data-src'),...srcset.split(',').reverse().map(value=>value.trim().split(/\s+/)[0]),image?.currentSrc,image?.getAttribute('src'),this.fallbackImage].find(value=>value&&value!==this.failedImage&&(safeURL(value)||/^data:image\//i.test(value)))||'';
            if(this.q('img').getAttribute('src')!==src){this.q('.initial').hidden=false;if(src)this.q('img').src=src;else this.q('img').removeAttribute('src');this.q('img').hidden=!src;}
            const description=source.querySelector('#description,#description-text,.channel-description')||source.querySelector('#channel-info p:last-of-type');
            const values=[...source.querySelectorAll('#channel-handle,#subscribers,#subscriber-count,#channel-stats,#metadata-line')].map(channelText).filter(Boolean);
            if(!values.length){const first=source.querySelector('#channel-info p,#info-section p');if(first&&first!==description)values.push(channelText(first));}
            if(!values.length)for(const node of source.querySelectorAll('yt-formatted-string,p,span')){
                const value=channelText(node);
                if(/^@[^\s·•]+(?:\s*[·•].*)?$/u.test(value)||/^[\d.,]+\s*(?:[kmb]|тыс\.?|млн\.?)?\s+(?:subscribers?|подписчик[а-яё]*|Abonnenten)(?:\s*[·•].*)?$/iu.test(value))values.push(value);
            }
            if(!values.length)values.push(...(cached?.metadata||[]));
            const metadata=[...new Set(values)].filter(value=>!values.some(other=>other!==value&&other.includes(value))).join(' · ').replace(/(\d[\d.,\s]*(?:[kmb]|тыс\.?|млн\.?|млрд\.?|Tsd\.?|Mio\.?|Mrd\.?)?)\s+(?:подписчик[а-яё]*|Abonnenten)(?=$|[\s·•])/giu,(_,count)=>count.replace(/\s*(тыс\.?|Tsd\.?)$/iu,'K').replace(/\s*(млн\.?|Mio\.?)$/iu,'M').replace(/\s*(млрд\.?|Mrd\.?)$/iu,'B').trim()+' subscribers');
            const metadataNode=this.q('.metadata');if(metadataNode.textContent!==metadata)metadataNode.textContent=metadata;metadataNode.hidden=!metadata;
            this.q('.verified').toggleAttribute('hidden',!source.querySelector('.badge-style-type-verified,.badge-style-type-verified-artist,[aria-label="Verified"],[aria-label="Проверено"],[aria-label="Bestätigt"]'));
            const state=this.subscriptionState();
            this.subscription.update({owner:source,name,subscriptionName:name},href||name);
            if(this.anchor&&(this.anchor.button!==state.button||!this.subscription.subscriptionPending))this.clearAnchor();
            const container=this.container||source;if(this.host.parentElement!==container)container.append(this.host);
            for(const part of this.parts)if(part.parentElement!==source){part.removeAttribute('data-myt-search-channel-source');this.parts.delete(part);}
            for(const part of source.children)if(part!==this.host&&!this.parts.has(part)){part.setAttribute('data-myt-search-channel-source','');this.parts.add(part);}
            this.positionAnchor();
        }
        prepareSubscriptionAction(button){
            this.clearAnchor();
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
            this.observer.disconnect();this.source.removeEventListener('load',this.queue,true);this.subscription.destroy();this.clearAnchor();
            this.host.remove();for(const part of this.parts)part.removeAttribute('data-myt-search-channel-source');this.parts.clear();
        }
    }


    const sourceSelector='ytd-video-renderer,ytd-grid-video-renderer,ytd-compact-video-renderer,ytd-playlist-renderer,ytd-grid-playlist-renderer,ytd-radio-renderer,ytd-channel-renderer,yt-lockup-view-model';
    const shelfSelector='ytd-shelf-renderer,grid-shelf-view-model,ytd-rich-section-renderer';
    // Rendering must also work with an already loaded extension manifest which
    // does not list the newer optional MAIN data adapter yet.
    const youtubeURL=value=>{const url=safeURL(value);return url?.protocol==='https:'&&/(^|\.)youtube\.com$/.test(url.hostname)?url.href:'';};
    const channelURL=value=>{const href=youtubeURL(value);return href&&channelPath.test(new URL(href).pathname)?href:'';};
    const headingCopy=new Map([
        ['Watch again',['Посмотреть еще раз','Посмотреть ещё раз','Посмотреть снова','Смотреть ещё раз','Erneut ansehen']],
        ['For you',['Для вас','Für dich','Für Sie']],['Previously watched',['Вы уже смотрели','Bereits angesehen']],
        ['Related videos',['Похожие видео','Ähnliche Videos']],['People also watched',['Другие также посмотрели','Andere haben auch angesehen']],
    ].flatMap(([english,values])=>[english,...values].map(value=>[value.toLocaleLowerCase(),english])));
    const heading=value=>headingCopy.get(value.trim().toLocaleLowerCase())||value.replace(/^(?:Новые видео на канале|Последние видео (?:на канале|от)|Neueste Videos von)\s+/iu,'Latest from ');
    const node=(tag,className,value)=>{const result=document.createElement(tag);if(className)result.className=className;if(value)result.textContent=value;return result;};
    const styles=`
      :host{all:initial!important;display:block!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;font:16px/1.45 Arial,sans-serif!important;color:var(--myt-ink)!important;position:relative!important}
      *{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}button{font:inherit;cursor:pointer}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}
      .toolbar{display:flex;align-items:center;justify-content:space-between;padding:0 0 16px;margin-bottom:24px;border-bottom:1px solid var(--myt-border)}
      .filters-toggle,.close-filters{display:inline-flex;align-items:center;gap:10px;min-height:44px;padding:9px 14px;border:0;border-radius:12px;background:transparent;color:inherit;font-weight:600}
      .filters-toggle:hover,.close-filters:hover{background:var(--myt-soft)}.filters-toggle svg{width:24px;height:24px}.filter-panel{padding:20px;margin-bottom:24px;border:1px solid var(--myt-border);border-radius:18px;background:var(--myt-surface)}.filter-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.filter-head h2{margin:0;font-size:20px}
      .filter-groups{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:20px}.filter-group h3{margin:0 0 12px;font-size:16px}.filter-group a{display:block;padding:8px 0;color:var(--myt-muted);font-size:14px}.filter-group a:is(:hover,:focus-visible),.filter-group a[aria-current=true]{color:var(--myt-ink);text-decoration:underline}
      .channels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-bottom:24px}
      .stream,.group-stream{display:flex;flex-direction:column;gap:20px}.row{display:grid;gap:20px;align-items:stretch;min-width:0}
      .media{display:flex;flex-direction:column;gap:14px;min-width:0;height:100%;padding:12px 12px 18px;border-radius:18px;background:var(--myt-surface);transition:background .12s}
      .media:is(:hover,:focus-within){background:var(--myt-soft)}.cover{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:var(--myt-soft)}.cover img{display:block;width:100%;height:100%;object-fit:cover}.media-info{display:flex;flex-direction:column;justify-content:center;gap:12px;min-width:0;padding:0 3px}
      .media-title{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere;font-size:20px;line-height:1.35;font-weight:700}
      .media-channel{display:block;overflow-wrap:anywhere;color:var(--myt-muted);font-size:18px;font-weight:500;line-height:1.4}.media-channel:is(:hover,:focus-visible){color:var(--myt-ink)}
      .media.playlist{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);align-items:center;gap:20px;padding-bottom:12px}.media.playlist .cover{width:100%}.playlist-badge{position:absolute;right:8px;bottom:8px;padding:4px 8px;border-radius:6px;background:#000b;color:#fff;font-size:13px}
      .group{min-width:0;padding:20px;border-radius:22px;background:var(--myt-soft)}.group h2{margin:0 0 18px;padding-inline-end:.2em;overflow:visible;overflow-wrap:anywhere;font:italic 900 40px/1.05 "MYT Barlow Condensed","MYT Cyrillic Condensed","Arial Narrow",sans-serif;text-transform:uppercase;letter-spacing:-.025em}
      .empty{padding:32px 0;color:var(--myt-muted)}@media(max-width:700px){.filter-groups{grid-template-columns:repeat(2,minmax(0,1fr))}.channels{grid-template-columns:1fr}.media-title{font-size:18px}.media-channel{font-size:17px}.media.playlist{grid-template-columns:1fr;gap:14px;padding-bottom:18px}.group{padding:16px}.group h2{font-size:32px}.row{gap:16px}}
    `;
    class MediaCard{
        constructor(source,kind){
            this.source=source;this.host=node('article','media '+kind);this.host.dataset.kind=kind;
            this.cover=node('a','cover');this.image=node('img');this.image.alt='';this.image.decoding='async';this.cover.append(this.image);
            this.info=node('div','media-info');this.title=node('a','media-title');this.owner=node('a','media-channel');this.info.append(this.title,this.owner);
            this.host.append(this.cover,this.info);
            if(kind==='playlist'){this.badge=node('span','playlist-badge','Playlist');this.cover.append(this.badge);}
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
        }
        destroy(){this.host.remove();}
    }
    const filterGroups=[
        ['Upload date',[['Last hour',1,1],['Today',1,2],['This week',1,3],['This month',1,4],['This year',1,5]]],
        ['Type',[['Video',2,1],['Channel',2,2],['Playlist',2,3],['Movie',2,4]]],
        ['Duration',[['Under 4 minutes',3,1],['4–20 minutes',3,2],['Over 20 minutes',3,3]]],
        ['Features',[['Live',8,1],['HD',4,1],['Subtitles/CC',5,1],['Creative Commons',6,1]]],
        ['Sort by',[['Relevance',0,0],['Upload date',0,2],['View count',0,3],['Rating',0,1]]],
    ];
    function filterURL(field,value){
        // YouTube's public search-parameter protobuf: preserve existing fields
        // when adding a filter rather than resetting another selected group.
        const current=new URL(location.href),parts=[];let bytes=[];
        try{bytes=[...atob(decodeURIComponent(current.searchParams.get('sp')||''))].map(char=>char.charCodeAt(0));}catch{}
        const parse=input=>{
            const result=[];let i=0;const integer=()=>{let value=0,shift=0;while(i<input.length&&shift<35){const byte=input[i++];value|=(byte&127)<<shift;if(!(byte&128))return value;shift+=7;}throw Error('Invalid search parameter');};
            while(i<input.length){const start=i,tag=integer();if((tag&7)===0){const number=integer();result.push({field:tag>>3,wire:0,number,raw:input.slice(start,i)});}else if((tag&7)===2){const size=integer(),data=input.slice(i,i+size);i+=size;if(i>input.length)throw Error('Invalid search parameter');result.push({field:tag>>3,wire:2,data,raw:input.slice(start,i)});}else throw Error('Unknown search parameter');}return result;
        };
        let root=[];try{if(bytes.length<1024)root=parse(bytes);}catch{}
        if(field===0){for(const part of root)if(part.field!==1)parts.push(...part.raw);if(value)parts.unshift(8,value);}
        else{
            let filters=[];try{filters=parse(root.find(part=>part.field===2&&part.wire===2)?.data||[]);}catch{}
            const inner=filters.filter(part=>part.field!==field).flatMap(part=>part.raw);inner.push(field<<3,value);
            for(const part of root)if(part.field!==2)parts.push(...part.raw);parts.push(18,inner.length,...inner);
        }
        if(parts.length)current.searchParams.set('sp',btoa(String.fromCharCode(...parts)));else current.searchParams.delete('sp');
        return current.href;
    }
    // Install native-page isolation with the renderer itself. Updating the
    // renderer cannot leave an older CSS asset painting a second search UI.
    const nativeStyles=`/* Search owns its complete visible stream. Native controllers and their
   continuation paths retain their parents; only pagination has layout below it. */
html.minimal-youtube[data-myt-search-ui],html.minimal-youtube[data-myt-search-ui] body {
    height:auto !important;max-height:none !important;overflow-y:auto !important;overflow-x:hidden !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search {
    display:block !important;position:relative !important;box-sizing:border-box !important;
    width:100% !important;max-width:1280px !important;margin:0 auto !important;padding:28px 24px 48px !important;
}
html.minimal-youtube[data-myt-search-ui] #myt-search { margin:0 !important;padding:0 !important; }
html.minimal-youtube[data-myt-search-ui] ytd-page-manager { margin-left:0 !important;margin-right:0 !important;width:100% !important;min-width:0 !important;height:auto !important;max-height:none !important;overflow:visible !important; }
html.minimal-youtube[data-myt-search-ui] ytd-search > :not(#myt-search):not([data-myt-search-continuation-path]),
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-native-root]:not([data-myt-search-continuation-path]),
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-continuation-path] > :not([data-myt-search-continuation-path]) {
    display:block !important;position:absolute !important;inset:0 auto auto 0 !important;width:0 !important;height:0 !important;
    min-width:0 !important;min-height:0 !important;margin:0 !important;padding:0 !important;
    overflow:hidden !important;visibility:hidden !important;opacity:0 !important;pointer-events:none !important;contain:strict !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search [data-myt-search-continuation-path] {
    display:contents !important;position:static !important;width:auto !important;height:auto !important;
    visibility:visible !important;opacity:1 !important;overflow:visible !important;contain:none !important;
}
html.minimal-youtube[data-myt-search-ui] ytd-search ytd-continuation-item-renderer[data-myt-search-continuation-path] {
    display:block !important;height:2px !important;min-height:2px !important;pointer-events:none !important;
}
@media(max-width:600px){html.minimal-youtube[data-myt-search-ui] ytd-search{padding:20px 16px 40px !important;}}`;
    class Search{
        constructor(){
            this.nativeStyle=node('style');this.nativeStyle.id='myt-search-native-style';this.nativeStyle.textContent=nativeStyles;document.documentElement.append(this.nativeStyle);
            this.cards=new Map();this.channels=new Map();this.groups=new Map();this.sources=new Map();this.sequence=0;this.nativeNodes=new Set();this.open=false;
            this.host=node('div');this.host.id='myt-search';this.host.lang='en';this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML='<style>'+styles+'</style><div class="toolbar"><button class="filters-toggle" aria-expanded="false" aria-controls="search-filters"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18M3 18h18"/><circle cx="8" cy="6" r="3" fill="var(--myt-bg)"/><circle cx="16" cy="18" r="3" fill="var(--myt-bg)"/></svg>Filters</button></div><section id="search-filters" class="filter-panel" aria-label="Search filters" hidden><div class="filter-head"><h2>Search filters</h2><button class="close-filters">Close</button></div><div class="filter-groups"></div></section><div class="channels" aria-label="Channels"></div><div class="stream"></div><p class="empty" hidden>No results found.</p>';
            this.q=selector=>this.shadow.querySelector(selector);
            this.q('.filters-toggle').onclick=()=>this.toggleFilters(!this.open);this.q('.close-filters').onclick=()=>this.toggleFilters(false,true);
            this.shadow.addEventListener('keydown',event=>{if(event.key==='Escape'&&this.open){event.preventDefault();this.toggleFilters(false,true);}});
            this.resize=new ResizeObserver(()=>this.layout());this.resize.observe(this.host);
            this.observer=new MutationObserver(records=>{
                if(records.every(record=>record.type==='attributes'&&record.attributeName?.startsWith('data-myt-search-')))return;
                let rebuild=false;
                for(const record of records){
                    const target=record.target instanceof Element?record.target:record.target.parentElement,source=target?.closest(sourceSelector);
                    const textOnly=record.type==='characterData'||record.type==='childList'&&[...record.addedNodes,...record.removedNodes].every(node=>node.nodeType===Node.TEXT_NODE);
                    const imageOnly=record.type==='attributes'&&['src','srcset','data-src','data-srcset','href'].includes(record.attributeName);
                    if(source&&this.cards.has(source)&&(textOnly||imageOnly)){
                        if(!textOnly||target.closest('h3,ytd-channel-name,#channel-info,a'))this.queueCard(source);
                    }else rebuild=true;
                }
                if(rebuild)this.queue();
            });
            this.selectionNodes=new Set();this.selectionObserver=new MutationObserver(()=>this.queue());
            this.changed=()=>this.queue();document.addEventListener('yt-page-data-updated',this.changed);document.addEventListener('yt-rendererstamper-finished',this.changed);
        }
        static isPlaylist(card){return card.matches('ytd-playlist-renderer,ytd-grid-playlist-renderer,ytd-radio-renderer,[is-playlist],[content-type="playlist"],[data-content-type="playlist"]')||!!card.querySelector('yt-collection-thumbnail-view-model,yt-collections-stack,ytd-thumbnail-overlay-side-panel-renderer')||safeURL(card.querySelector(titleSelector)?.href)?.pathname==='/playlist';}
        queue(){if(this.frame)return;this.frame=requestAnimationFrame(()=>{this.frame=0;const searches=document.querySelectorAll('ytd-search');if(searches.length)this.sync(searches);});}
        queueCard(source){
            if(!this.cards.has(source)){this.queue();return;}
            this.pendingCards ||=new Set();this.pendingCards.add(source);if(this.cardFrame)return;
            this.cardFrame=requestAnimationFrame(()=>{this.cardFrame=0;for(const source of this.pendingCards){const card=this.cards.get(source);if(card&&source.isConnected){if(Search.isPlaylist(source)!==(card.host.dataset.kind==='playlist')){this.queue();continue;}const data=this.read(source,card.host.dataset.kind,card.record);if(data)card.update(data);else this.queue();}}this.pendingCards.clear();});
        }
        toggleFilters(open,focus=false){this.open=open;this.q('.filter-panel').hidden=!open;this.q('.filters-toggle').setAttribute('aria-expanded',String(open));if(open)this.renderFilters();if(focus)this.q('.filters-toggle').focus();}
        renderFilters(){
            const available=new Map();
            for(const option of this.snapshot?.filters||[]){const label=englishFilter(option.label)||option.label;if(youtubeURL(option.href))available.set(label,{href:option.href});}
            for(const option of document.querySelectorAll('ytd-search-filter-renderer a[href],ytd-search-filter-group-renderer a[href]')){
                const label=englishFilter(text(option))||text(option);available.set(label,{href:option.href,source:option});
            }
            const signature=JSON.stringify([location.href,[...available].map(([key,item])=>[key,item.href])]);if(signature===this.filterSignature)return;this.filterSignature=signature;
            const container=this.q('.filter-groups');container.replaceChildren();
            for(const [title,options]of filterGroups){
                const group=node('div','filter-group');group.append(node('h3','',title));
                for(const [label,field,value]of options){
                    const item=available.get(label),link=node('a','',label);link.href=item?.href||filterURL(field,value);
                    link.setAttribute('aria-current',String(new URL(link.href).searchParams.get('sp')===new URL(location.href).searchParams.get('sp')));
                    if(item?.source)link.onclick=event=>{if(!event.button&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();item.source.click();this.toggleFilters(false,true);}};
                    group.append(link);
                }
                container.append(group);
            }
        }
        read(source,kind,record){
            const anchors=[...source.querySelectorAll('a[href]')];
            const title=source.querySelector(titleSelector);
            const main=(title?.matches('a[href]')?title:title?.closest('a[href]')||title?.querySelector('a[href]'))||anchors.find(link=>{const url=safeURL(link.href);return kind==='video'?url?.pathname==='/watch':url?.pathname==='/playlist'||url?.searchParams.has('list');});
            const owner=source.querySelector('ytd-channel-name a[href],#channel-info a[href],.ytLockupMetadataViewModelMetadata a[href],a[href^="/@"]')||anchors.find(link=>channelURL(link.href));
            const href=youtubeURL(main?.href||record?.href);
            if(!href||kind==='video'&&(new URL(href).pathname!=='/watch'||!new URL(href).searchParams.has('v')))return null;
            let image=coverImage(source)||record?.image;
            const parsed=new URL(href);if(!image&&parsed.searchParams.get('v')?.match(/^[-\w]{11}$/))image='https://i.ytimg.com/vi/'+parsed.searchParams.get('v')+'/hqdefault.jpg';
            return {kind,href,title:text(title)||text(main)||record?.title||'Video',image,channel:{name:text(owner)||record?.channel?.name||'',href:channelURL(owner?.href||record?.channel?.href)}};
        }
        sync(searches){
            if(!this.nativeStyle.isConnected)document.documentElement.append(this.nativeStyle);
            document.documentElement.setAttribute('data-myt-search-ui','');
            const candidates=[...searches],selectionNodes=new Set();
            for(const item of candidates)for(let parent=item;parent&&parent!==document.body;parent=parent.parentElement)selectionNodes.add(parent);
            if(selectionNodes.size!==this.selectionNodes.size||[...selectionNodes].some(item=>!this.selectionNodes.has(item))){
                this.selectionObserver.disconnect();this.selectionNodes=selectionNodes;
                for(const item of selectionNodes)this.selectionObserver.observe(item,{attributes:true,attributeFilter:['hidden','aria-hidden','class','style']});
            }
            const search=candidates.find(item=>!item.closest('[hidden],[aria-hidden="true"]')&&item.getClientRects().length&&getComputedStyle(item).visibility!=='hidden')||candidates[0];if(!search)return;
            if(this.search!==search){
                this.search?.removeEventListener('load',this.changed,true);
                this.observer.disconnect();this.search=search;
                this.observer.observe(search,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['href','src','srcset','data-src','data-srcset','class','hidden','aria-label','aria-pressed','subscribed','is-subscribed','disabled']});
                search.addEventListener('load',this.changed,true);
            }
            if(this.host.parentElement!==search)search.prepend(this.host);
            const sources=[...search.querySelectorAll(sourceSelector)].filter(source=>!source.parentElement.closest(sourceSelector)&&!source.closest('[data-myt-hidden],[data-myt-hidden-section],ytd-reel-shelf-renderer')&&!/\bshorts\b|коротки[еех]\s+(?:видео|ролик)/iu.test(text(source.closest(shelfSelector)?.querySelector('#title-container,#header,h2'))));
            const wanted=new Set(sources);
            for(const source of sources){
                let kind=source.matches('ytd-channel-renderer,[content-type="channel"],[data-content-type="channel"]')?'channel':Search.isPlaylist(source)?'playlist':'video';
                if(!this.sources.has(source)){const key='result-'+(++this.sequence);this.sources.set(source,key);source.setAttribute('data-myt-search-source-key',key);}
                source.setAttribute('data-myt-search-source-kind',kind);
            }
            document.dispatchEvent(new Event('minimal-youtube:search-snapshot'));
            try{this.snapshot=JSON.parse(document.documentElement.getAttribute('data-myt-search-snapshot')||'{}');}catch{this.snapshot={};}
            const records=new Map((this.snapshot.records||[]).map(record=>[record.key,record])),channelCache=new Map();
            try{for(const value of JSON.parse(document.documentElement.getAttribute('data-myt-search-channels')||'[]'))channelCache.set(value.id,value);}catch{}
            const stream=[],groups=new Map();
            for(const source of sources){
                const record=records.get(this.sources.get(source)),kind=record?.kind||source.getAttribute('data-myt-search-source-kind');
                if(kind==='channel'){
                    this.cards.get(source)?.destroy();this.cards.delete(source);
                    let card=this.channels.get(source);if(!card){card=new ChannelCard(source,()=>this.queue(),this.q('.channels'));this.channels.set(source,card);}card.update(channelCache,record||null);continue;
                }
                this.channels.get(source)?.destroy();this.channels.delete(source);
                const value=this.read(source,kind,record);if(!value)continue;
                let card=this.cards.get(source);if(card&&card.host.dataset.kind!==kind){card.destroy();card=null;}if(!card){card=new MediaCard(source,kind);this.cards.set(source,card);}card.record=record;card.update(value);
                const shelf=source.closest(shelfSelector),header=shelf?.querySelector('#title-container,#header,h2,[role="heading"]'),label=channelText(header?.querySelector('#title,h2,h3,.ytShelfHeaderLayoutTitle')||header);
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
            this.q('.channels').hidden=!this.channels.size;this.q('.empty').hidden=Boolean(this.channels.size||stream.length);
            this.prepareNative(search);this.layout();if(this.open)this.renderFilters();
        }
        prepareNative(search){
            // Keep native controllers in place. Only continuation paths contribute
            // height after our rendered results, so native pagination still sees
            // its sentinel at the actual end of the stream.
            for(const child of search.children)if(child!==this.host){child.setAttribute('data-myt-search-native-root','');this.nativeNodes.add(child);}
            const paths=new Set();
            for(const continuation of search.querySelectorAll('ytd-continuation-item-renderer'))for(let parent=continuation;parent&&parent!==search;parent=parent.parentElement)paths.add(parent);
            for(const source of this.nativeNodes)if(source.hasAttribute('data-myt-search-continuation-path')&&!paths.has(source))source.removeAttribute('data-myt-search-continuation-path');
            for(const path of paths){path.setAttribute('data-myt-search-continuation-path','');this.nativeNodes.add(path);}
        }
        layout(){
            if(!this.host.isConnected||!this.stream)return;
            const width=this.host.clientWidth,columns=width<560?1:width<900?2:3;
            this.place(this.q('.stream'),this.stream,columns);
            for(const group of this.groups.values())this.place(group.stream,group.items,columns===3&&[2,4].includes(group.items.length)?2:columns);
        }
        place(container,items,columns){
            // Preserve source order and fixed units; native wrappers never
            // reserve cells. A playlist occupies exactly two video columns.
            const signature=items.map(item=>item.host.dataset.kind+':'+(item.host.dataset.href||item.title?.textContent||'')).join('|')+':'+columns;
            if(container.dataset.layout===signature&&items.every(item=>item.host.isConnected))return;
            container.dataset.layout=signature;let row=null,used=0,content=[];
            const flush=()=>{if(!row)return;row.style.gridTemplateColumns='repeat('+columns+',minmax(0,1fr))';content.push(row);row=null;used=0;};
            for(const item of items){
                if(item.items){flush();content.push(item.host);continue;}
                const units=Math.min(columns,item.host.dataset.kind==='playlist'?2:1);
                if(row&&used+units>columns)flush();
                if(!row)row=node('div','row');item.host.style.gridColumn='span '+units;row.append(item.host);used+=units;
                if(used===columns)flush();
            }
            flush(false);container.replaceChildren(...content);
        }
        destroy(){
            this.nativeStyle.remove();
            this.selectionObserver.disconnect();this.selectionNodes.clear();
            document.documentElement.removeAttribute('data-myt-search-ui');
            cancelAnimationFrame(this.cardFrame);this.pendingCards?.clear();
            cancelAnimationFrame(this.frame);this.observer.disconnect();this.resize.disconnect();this.search?.removeEventListener('load',this.changed,true);
            document.removeEventListener('yt-page-data-updated',this.changed);document.removeEventListener('yt-rendererstamper-finished',this.changed);
            for(const card of [...this.cards.values(),...this.channels.values()])card.destroy();
            for(const source of this.sources.keys()){source.removeAttribute('data-myt-search-source-key');source.removeAttribute('data-myt-search-source-kind');}
            for(const native of this.nativeNodes){native.removeAttribute('data-myt-search-native-root');native.removeAttribute('data-myt-search-continuation-path');}
            this.host.remove();this.cards.clear();this.channels.clear();this.sources.clear();
        }
    }
    Search.playlistSelector=playlistSelector;Search.filterScopeSelector=filterScopeSelector;
    globalThis.MinimalYouTubeSearch=Search;
})();
