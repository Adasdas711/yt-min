/* Channel-only identity, English controls and reliable section navigation. */
(() => {
    'use strict';
    const basePattern=/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))(?:\/(.*))?\/?$/;
    const tabsSelector='yt-tab-shape,tp-yt-paper-tab,ytd-expandable-tab-renderer,[role="tab"]';
    const aboutSelector='ytd-about-channel-renderer,yt-about-channel-renderer,ytd-channel-about-metadata-renderer,yt-about-channel-view-model';
    const navigationEvents=['yt-navigate-start','yt-navigate-finish','yt-page-data-updated','yt-navigate-error','yt-navigate-cancel'];
    const compact=new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:2});
    const words=new Map([
        ['Subscribe','Подписаться','Abonnieren'],['Subscribed','Вы подписаны','Подписка оформлена','Abonniert'],
        ['Unsubscribe','Отписаться','Abo beenden'],['Cancel','Отмена','Abbrechen'],['Confirm','Подтвердить','Bestätigen'],
        ['More','Ещё','Еще','Mehr'],['Show more','Показать полностью'],['Show less','Свернуть','Weniger anzeigen'],
        ['Latest','Новые','Недавние','Сначала новые','Neueste'],['Popular','Популярные','Beliebt'],['Oldest','Старые','Сначала старые','Älteste'],
        ['Play all','Смотреть все','Воспроизвести все','Alle wiedergeben'],['Join','Спонсировать','Mitglied werden'],
        ['Share','Поделиться','Teilen'],['All','Все','Alle'],['Personalized','На основе предпочтений','Personalisiert'],
        ['None','Никакие','Keine'],['Notifications','Уведомления','Benachrichtigungen'],['Search','Поиск','Suchen'],
        ['Customize channel','Настроить вид канала','Kanal anpassen'],['Manage videos','Управление видео','Videos verwalten'],
        ['Created playlists','Созданные плейлисты','Erstellte Playlists'],['Sort by','Сортировать','Sortieren nach'],
    ].flatMap(([english,...labels])=>labels.map(label=>[label.toLocaleLowerCase(),english])));
    const sections=[
        ['videos','Videos',/^(videos|видео)$/iu],['streams','Live',/^(live|streams|трансляции|livestreams)$/iu],
        ['playlists','Playlists',/^(playlists|плейлисты)$/iu],['posts','Posts',/^(posts|community|посты|записи|сообщество|beiträge)$/iu],
        ['search','Search',/^(search(?: this channel)?|поиск(?: на канале)?|suchen|kanalsuche)$/iu],
    ];
    function count(value,kind){
        const unit='(thousand|million|billion|trillion|тыс\\.?|млн\\.?|млрд\\.?|трлн\\.?|Tsd\\.?|Mio\\.?|Mrd\\.?|[kmbt])?';
        const label=kind==='subscribers'?'(?:subscribers?|подписчик[а-яё]*|Abonnenten)':'(?:videos?|видео|ролик[а-яё]*)';
        const source=String(value||'').replace(/[\u00a0\u202f]/g,' ').trim();
        const match=source.match(new RegExp('(\\d[\\d\\s.,]*?)\\s*'+unit+'\\s*'+label+'(?=$|[\\s·•*])','iu'));
        if(!match)return '';
        let amount=match[1].replace(/\s/g,''),suffix=(match[2]||'').toLowerCase().replace(/\.$/,'');
        if(!suffix&&/^\d{1,3}(?:[.,]\d{3})+$/.test(amount))amount=amount.replace(/[.,]/g,'');
        else{const decimal=Math.max(amount.lastIndexOf('.'),amount.lastIndexOf(','));if(decimal>=0)amount=amount.slice(0,decimal).replace(/[.,]/g,'')+'.'+amount.slice(decimal+1);}
        const power=/^(k|thousand|тыс|tsd)$/.test(suffix)?3:/^(m|million|млн|mio)$/.test(suffix)?6:/^(b|billion|млрд|mrd)$/.test(suffix)?9:/^(t|trillion|трлн)$/.test(suffix)?12:0;
        const number=Number(amount)*10**power;if(!Number.isFinite(number))return '';
        return compact.formatToParts(number).map(part=>part.type==='compact'?' '+part.value:part.value).join('');
    }
    const svg=kind=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">${kind==='subscribers'?'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>':'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3Z"/>'}</svg>`;
    class Channel {
        static landing(url){
            const match=url.pathname.match(basePattern);
            if(!match||match[2]&&!/^(featured)?\/?$/.test(match[2]))return null;
            const target=new URL(url);target.pathname=match[1]+'/videos';target.searchParams.set('hl','en');target.searchParams.set('persist_hl','1');return target.href;
        }
        static destination(url,language){
            const landing=Channel.landing(url);if(landing)return landing;
            if(!basePattern.test(url.pathname)||!language||/^en(?:-|$)/i.test(language)||url.searchParams.get('hl')==='en')return null;
            const target=new URL(url);target.searchParams.set('hl','en');target.searchParams.set('persist_hl','1');return target.href;
        }
        constructor(){
            this.hidden=new Set();this.text=new Map();this.attributes=new Map();this.aboutNodes=new Map();this.previewNodes=new Map();
            this.descriptionHost=document.createElement('div');this.descriptionHost.id='myt-channel-description';this.descriptionHost.lang='en';
            this.descriptionHost.attachShadow({mode:'open'}).innerHTML=`<style>
                :host{all:initial!important;display:block!important;position:relative!important;box-sizing:border-box!important;width:100%!important;min-width:0!important;max-width:100%!important;margin:14px 0!important;color:var(--myt-ink,#18181b)!important}
                *{box-sizing:border-box}[hidden]{display:none!important}
                section{display:flex;flex-direction:column;align-items:flex-start;gap:4px;padding:0;border:0;border-radius:0;background:transparent}
                p{display:block;width:100%;margin:0;padding:0;font:400 16px/1.8 "SFMono-Regular",Menlo,Monaco,Consolas,"Liberation Mono",ui-monospace,monospace;letter-spacing:normal;text-transform:none;white-space:normal;overflow-wrap:anywhere;color:var(--myt-ink,#18181b)}
                button{display:inline-block;align-self:flex-start;margin:0;padding:0;border:0;border-radius:0;background:transparent;color:var(--myt-ink,#18181b);font:600 16px/1.8 "SFMono-Regular",Menlo,Consolas,monospace;cursor:pointer}
                button:hover{text-decoration:underline}button:focus-visible{outline:2px solid var(--myt-muted,#74747d);outline-offset:3px}button:disabled{opacity:.6;cursor:default}svg{width:14px;height:14px;flex:none}
                dialog{width:min(1040px,calc(100vw - 32px));max-width:calc(100vw - 32px);max-height:calc(100dvh - 48px);margin:auto;padding:0;border:1px solid var(--myt-border,#e5e5ea);border-radius:20px;background:var(--myt-bg,#fff);color:var(--myt-ink,#18181b);overflow:hidden}
                dialog[open]{display:flex;flex-direction:column}dialog::backdrop{background:#0009}dialog header{display:flex;flex:none;align-items:center;justify-content:space-between;gap:20px;padding:20px 24px;border-bottom:1px solid var(--myt-border,#e5e5ea)}h2{margin:0;font:600 20px/1.4 Arial,sans-serif}button.close{font:400 26px/1 Arial,sans-serif;padding:4px;align-self:center}.full-body{min-height:0;overflow:auto;overscroll-behavior:contain;padding:24px}.full-text{white-space:pre-wrap}
                .detail-section{display:block;margin-top:24px;padding-top:20px;border-top:1px solid var(--myt-border,#e5e5ea)}h3{margin:0 0 14px;font:600 18px/1.4 Arial,sans-serif}
                .full-links{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.external-link{display:flex;flex-direction:column;gap:5px;min-width:0;padding:12px;border:1px solid var(--myt-border,#e5e5ea);border-radius:10px;color:inherit;text-decoration:none;overflow-wrap:anywhere}.external-link:hover{background:var(--myt-soft,#f1f1f4)}.link-title{font:600 15px/1.4 Arial,sans-serif}.link-url{font:400 13px/1.5 ui-monospace,monospace;color:var(--myt-muted,#74747d)}
                .full-info{display:grid;grid-template-columns:minmax(90px,130px) minmax(0,1fr);gap:12px 20px;margin:0;font:400 15px/1.5 Arial,sans-serif}.full-info dt{color:var(--myt-muted,#74747d)}.full-info dd{margin:0;overflow-wrap:anywhere}.full-info a{color:inherit}.details-status{margin-top:20px;font:400 14px/1.5 Arial,sans-serif;color:var(--myt-muted,#74747d)}.retry{margin-top:10px;font:600 14px/1.5 Arial,sans-serif;text-decoration:underline}
                .full-body{overflow-x:hidden;scrollbar-gutter:stable;scrollbar-color:var(--myt-muted,#74747d) var(--myt-soft,#f1f1f4)}.full-body:focus-visible{outline:2px solid var(--myt-muted,#74747d);outline-offset:-2px}.full-body::-webkit-scrollbar{width:10px}.full-body::-webkit-scrollbar-track{background:var(--myt-soft,#f1f1f4)}.full-body::-webkit-scrollbar-thumb{background:var(--myt-muted,#74747d);border:2px solid var(--myt-soft,#f1f1f4);border-radius:8px}
                @media(max-width:600px){dialog header,.full-body{padding:16px}}
                @media(max-width:600px){.full-links{grid-template-columns:1fr}.full-info{grid-template-columns:90px minmax(0,1fr);gap:12px}}
                </style><section aria-label="Channel description"><p class="summary"></p><button class="more" type="button" aria-haspopup="dialog">...more</button></section><dialog class="full" aria-label="About this channel"><header><h2>About this channel</h2><button class="close" type="button" aria-label="Close">×</button></header><div class="full-body" tabindex="0" role="region" aria-label="Channel information"><p class="full-text"></p><section class="detail-section links-section" aria-labelledby="channel-links-title" hidden><h3 id="channel-links-title">Links</h3><div class="full-links"></div></section><section class="detail-section info-section" aria-labelledby="channel-info-title" hidden><h3 id="channel-info-title">More info</h3><dl class="full-info"></dl></section><p class="details-status" role="status" hidden></p><button class="retry" type="button" hidden>Retry</button></div></dialog>`;
            this.descriptionText=this.descriptionHost.shadowRoot.querySelector('.summary');
            this.descriptionMore=this.descriptionHost.shadowRoot.querySelector('.more');
            this.descriptionDialog=this.descriptionHost.shadowRoot.querySelector('dialog');
            this.descriptionBody=this.descriptionHost.shadowRoot.querySelector('.full-body');
            this.descriptionClose=this.descriptionHost.shadowRoot.querySelector('.close');
            this.descriptionRetry=this.descriptionHost.shadowRoot.querySelector('.retry');
            this.descriptionClose.addEventListener('click',()=>this.descriptionDialog.close());
            this.descriptionRetry.addEventListener('click',()=>this.requestAbout());
            this.descriptionDialog.addEventListener('close',()=>{
                if(this.descriptionDialog.open)return;
                this.releaseDescriptionScroll();
                if(this.restoreDescriptionFocus!==false&&this.descriptionMore.isConnected)this.descriptionMore.focus({preventScroll:true});
                this.restoreDescriptionFocus=true;
            });
            this.descriptionMore.addEventListener('click',event=>{
                event.stopPropagation();this.openDescription();
            });
            this.aboutUpdated=event=>{
                if(event.target!==this.descriptionSource||!this.descriptionSource.isConnected)return;
                const browse=this.descriptionSource.closest('ytd-browse[page-subtype="channels"]');
                if(browse)this.preview(browse.querySelector(':scope > #header,:scope > #page-header,ytd-c4-tabbed-header-renderer,yt-page-header-view-model,yt-page-header-renderer'));
            };
            document.addEventListener('minimal-youtube:channel-about-updated',this.aboutUpdated);
            this.stats=document.createElement('div');this.stats.id='myt-channel-stats';this.stats.lang='en';
            this.stats.attachShadow({mode:'open'}).innerHTML='<style>:host{display:block;color:var(--myt-muted);font:14px/1.6 Arial,sans-serif}.row{display:flex;align-items:center;flex-wrap:wrap;gap:0 8px}.metric{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}svg{width:15px;height:15px;flex:none}[hidden]{display:none!important}</style><div class="row"></div>';
            this.nav=document.createElement('div');this.nav.id='myt-channel-nav';this.nav.lang='en';
            this.nav.attachShadow({mode:'open'}).innerHTML=`<style>
                :host{display:block!important;min-width:0;font:600 16px/1.4 Arial,sans-serif;color:var(--myt-ink)}*{box-sizing:border-box}[hidden]{display:none!important}
                .toolbar{display:flex;align-items:center;justify-content:center;gap:8px;min-width:0}nav{display:flex;flex:0 1 auto;min-width:0;gap:8px;overflow-x:auto;scrollbar-width:thin;padding:4px 0}a,button{flex:none;color:inherit;font:inherit;text-decoration:none;background:none;border:0;border-bottom:2px solid transparent;padding:12px 16px;cursor:pointer;white-space:nowrap}
                [aria-current=page],button[aria-expanded=true]{border-color:currentColor}a:hover,button:hover{background:var(--myt-soft);border-radius:8px 8px 0 0}a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid currentColor;outline-offset:-2px}
                [data-pending]{opacity:.65;cursor:progress}.navigation-status{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
                .channel-search{display:flex;flex:none;align-items:center;gap:10px;min-width:0}.search-toggle{display:inline-flex;align-items:center;justify-content:center;width:40px;height:44px;padding:0;border:0;border-radius:50%;color:var(--myt-muted)}.search-toggle:hover{border-radius:50%;color:var(--myt-ink)}.search-toggle[aria-expanded=true]{color:var(--myt-ink)}.search-toggle svg{display:block;width:24px;height:24px}
                form{display:flex;flex:none;width:clamp(160px,20vw,292px);margin:0;padding:0}input{appearance:none;-webkit-appearance:none;display:block;box-sizing:border-box;width:100%;min-width:0;flex:1;border:0;border-bottom:2px solid var(--myt-muted);border-radius:0;background:transparent;color:inherit;padding:6px 0;font:400 16px/1.5 Arial,sans-serif;outline:none}input::placeholder{color:var(--myt-muted)}input:focus,input:focus-visible{border-bottom-color:var(--myt-ink);outline:none}input::-webkit-search-decoration{display:none}
                @media(max-width:600px){.toolbar{gap:4px}nav{gap:0}nav a{font-size:14px;padding:12px 9px}.channel-search{gap:8px}form{width:clamp(110px,38vw,190px)}}
                </style><div class="toolbar"><nav aria-label="Channel sections"></nav><div class="channel-search"><button class="search-toggle" data-section="search" type="button" aria-label="Search" title="Search this channel" aria-expanded="false" aria-controls="channel-search-form"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/></svg></button><form id="channel-search-form" role="search" hidden><input name="query" type="search" aria-label="Search this channel" placeholder="Search" autocomplete="off"></form></div></div><span class="navigation-status" role="status" aria-live="polite"></span>`;
            this.searchButton=this.nav.shadowRoot.querySelector('.search-toggle');
            this.nav.shadowRoot.querySelector('input').addEventListener('input',event=>{
                event.stopPropagation();
                if(!event.isComposing&&!event.target.value.trim())this.clearSearchResults();
            });
            this.nav.shadowRoot.querySelector('form').addEventListener('submit',event=>{
                event.preventDefault();event.stopPropagation();
                this.submitSearch();
            });
            this.click=event=>{
                const path=event.composedPath();
                if(path.includes(this.descriptionMore)||path.includes(this.descriptionClose)||path.includes(this.descriptionRetry)){
                    if(event.type==='click'&&!event.button){
                        event.preventDefault();event.stopImmediatePropagation();
                        if(path.includes(this.descriptionMore))this.openDescription();else if(path.includes(this.descriptionRetry))this.requestAbout();else this.descriptionDialog.close();
                    }
                    return;
                }
                if(path.includes(this.descriptionDialog)){event.stopImmediatePropagation();return;}
                if(!path.includes(this.nav))return;
                const link=path.find(node=>node instanceof HTMLAnchorElement);
                if(!link){
                    const button=path.find(node=>node instanceof HTMLButtonElement);
                    if(button){event.stopImmediatePropagation();if(button.dataset.section==='search'){event.preventDefault();this.toggleSearch(button);}}
                    return;
                }
                // Native commands are resolved in MAIN; preserve normal browser
                // behavior for modified clicks and middle-clicks.
                event.stopImmediatePropagation();
                if(!event.button&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();this.open(link.href);}
            };
            this.keydown=event=>{
                const path=event.composedPath();
                if(path.includes(this.nav.shadowRoot.querySelector('input'))){
                    event.stopImmediatePropagation();
                    if(event.key==='Enter'&&!event.isComposing){event.preventDefault();this.submitSearch();}
                    else if(event.key==='Escape'){event.preventDefault();this.closeSearch(true);}
                    return;
                }
                if(path.includes(this.nav)){
                    const link=path.find(node=>node instanceof HTMLAnchorElement),button=path.find(node=>node instanceof HTMLButtonElement);
                    if(link&&event.key==='Enter'){
                        event.stopImmediatePropagation();
                        if(!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();this.open(link.href);}
                        return;
                    }
                    if(button&&(event.key==='Enter'||event.key===' ')){
                        event.preventDefault();event.stopImmediatePropagation();
                        if(!event.repeat){if(button.dataset.section==='search')this.toggleSearch(button);else this.submitSearch();}
                        return;
                    }
                }
                if(event.key==='Escape'&&this.descriptionDialog.open){
                    event.preventDefault();event.stopImmediatePropagation();this.descriptionDialog.close();
                }else if((event.key==='Enter'||event.key===' ')&&(path.includes(this.descriptionMore)||path.includes(this.descriptionClose)||path.includes(this.descriptionRetry))){
                    event.preventDefault();event.stopImmediatePropagation();
                    if(!event.repeat){if(path.includes(this.descriptionMore))this.openDescription();else if(path.includes(this.descriptionRetry))this.requestAbout();else this.descriptionDialog.close();}
                }else if(this.descriptionDialog.open&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
                    const body=this.descriptionBody,steps={ArrowUp:-40,ArrowDown:40,PageUp:-body.clientHeight,PageDown:body.clientHeight,Home:-body.scrollHeight,End:body.scrollHeight,' ':body.clientHeight*(event.shiftKey?-1:1)};
                    if(Object.hasOwn(steps,event.key)){
                        event.preventDefault();event.stopImmediatePropagation();body.scrollBy({top:steps[event.key],behavior:'instant'});
                    }
                }
            };
            // Stop the page's capture handlers before they mistake a shadow
            // dialog event for a wheel/touch gesture on the channel behind it.
            this.descriptionWheel=event=>{
                if(!this.descriptionDialog.open)return;
                event.stopImmediatePropagation();
                if(event.ctrlKey||!event.cancelable)return;
                event.preventDefault();
                if(!this.canScrollDescription(event,event.deltaY)){this.descriptionWheelRemainder=0;return;}
                // A page listener may already have canceled the native action.
                // Move this scrollport directly and retain subpixel trackpad input.
                const body=this.descriptionBody;
                const unit=event.deltaMode===WheelEvent.DOM_DELTA_PAGE?body.clientHeight:event.deltaMode===WheelEvent.DOM_DELTA_LINE?parseFloat(getComputedStyle(body.firstElementChild).lineHeight)||16:1;
                this.descriptionWheelRemainder=(this.descriptionWheelRemainder||0)+event.deltaY*unit;
                const step=Math.trunc(this.descriptionWheelRemainder);this.descriptionWheelRemainder-=step;
                if(step)body.scrollBy({top:step,behavior:'instant'});
            };
            this.descriptionTouchStart=event=>{
                if(!this.descriptionDialog.open)return;
                event.stopImmediatePropagation();this.descriptionTouchY=event.touches.length===1?event.touches[0].clientY:null;
            };
            this.descriptionTouchMove=event=>{
                if(!this.descriptionDialog.open)return;
                event.stopImmediatePropagation();
                if(event.touches.length!==1||this.descriptionTouchY===null)return;
                const y=event.touches[0].clientY,delta=this.descriptionTouchY-y;this.descriptionTouchY=y;
                if(event.cancelable&&!this.canScrollDescription(event,delta))event.preventDefault();
            };
            this.nativeNavigation=event=>{
                const pending=this.navigationPending;if(!pending)return;
                const href=event.detail?.url||event.detail?.endpoint?.commandMetadata?.webCommandMetadata?.url;
                const matches=typeof href==='string'?this.navigationKey(href)===pending.key:this.navigationKey(location.href)===pending.key;
                if(event.type==='yt-navigate-start'&&(matches||!href)){pending.accepted=true;clearTimeout(pending.acceptTimer);}
                else if(matches&&(event.type==='yt-navigate-finish'||event.type==='yt-page-data-updated'))this.cancelNavigation();
                else if((event.type==='yt-navigate-error'&&(matches||!href&&pending.accepted))||(event.type==='yt-navigate-cancel'&&href&&matches))this.fallbackNavigation(pending);
            };
            this.historyNavigation=()=>{this.emptySearch=false;document.documentElement.removeAttribute('data-myt-channel-search-empty');this.cancelNavigation();};
            this.routeNavigation=()=>{
                const pending=this.navigationPending;if(!pending)return;
                const key=this.navigationKey(location.href);
                if(key===pending.key){pending.accepted=true;clearTimeout(pending.acceptTimer);}
                else if(key!==pending.sourceKey)this.cancelNavigation();
            };
            for(const name of navigationEvents)window.addEventListener(name,this.nativeNavigation,true);
            window.addEventListener('popstate',this.historyNavigation);
            window.navigation?.addEventListener('currententrychange',this.routeNavigation);
            window.addEventListener('click',this.click,true);
            window.addEventListener('auxclick',this.click,true);
            window.addEventListener('keydown',this.keydown,true);
            window.addEventListener('wheel',this.descriptionWheel,{capture:true,passive:false});
            window.addEventListener('touchstart',this.descriptionTouchStart,{capture:true,passive:true});
            window.addEventListener('touchmove',this.descriptionTouchMove,{capture:true,passive:false});
        }
        canScrollDescription(event,delta){
            const body=this.descriptionBody;
            return event.composedPath().includes(body)&&(delta<0?body.scrollTop>0:delta>0&&body.scrollTop+body.clientHeight<body.scrollHeight-1);
        }
        releaseDescriptionScroll(){
            if(!this.descriptionScrollLocked)return;
            this.descriptionScrollLocked=false;document.documentElement.removeAttribute('data-myt-channel-description-open');
        }
        requestAbout(){
            if(this.descriptionSource?.isConnected)this.descriptionSource.dispatchEvent(new Event('minimal-youtube:channel-about',{bubbles:true}));
        }
        renderDescription(){
            const shadow=this.descriptionHost.shadowRoot,data=this.descriptionDetails||{},text=this.descriptionFullValue||this.descriptionValue||'';
            const paragraph=shadow.querySelector('.full-text');if(paragraph.textContent!==text)paragraph.textContent=text;
            const webURL=value=>{try{const url=new URL(value,location.origin);return /^https?:$/.test(url.protocol)?url.href:'';}catch{return '';}};
            const links=(Array.isArray(data.links)?data.links:[]).filter(link=>typeof link.url==='string'&&webURL(link.url));
            const linkValue=JSON.stringify(links);
            if(linkValue!==this.descriptionLinksValue){
                this.descriptionLinksValue=linkValue;const list=shadow.querySelector('.full-links');list.replaceChildren();
                for(const link of links){
                    const anchor=document.createElement('a');anchor.className='external-link';anchor.href=webURL(link.url);anchor.target='_blank';anchor.rel='noopener noreferrer';
                    const title=document.createElement('span');title.className='link-title';title.textContent=link.title||new URL(anchor.href).hostname;
                    const url=document.createElement('span');url.className='link-url';url.textContent=anchor.href.replace(/^https?:\/\//,'');
                    anchor.append(title,url);list.append(anchor);
                }
            }
            shadow.querySelector('.links-section').hidden=!links.length;
            let stats=[];try{stats=JSON.parse(this.stats.dataset.value||'[]');}catch{}
            const info={channelUrl:this.base?location.origin+this.base:'',subscribers:stats[1]||'',videos:stats[2]||'',...data.info};
            const infoValue=JSON.stringify(info);
            if(infoValue!==this.descriptionInfoValue){
                this.descriptionInfoValue=infoValue;const list=shadow.querySelector('.full-info');list.replaceChildren();
                for(const [key,title]of [['channelUrl','Channel'],['country','Country'],['joined','Joined'],['subscribers','Subscribers'],['videos','Videos'],['views','Views']]){
                    if(typeof info[key]!=='string'||!info[key].trim())continue;
                    const term=document.createElement('dt');term.textContent=title;const value=document.createElement('dd');
                    const label=info[key].replace(/^Joined\s+/i,'').replace(/\s+(?:subscribers?|videos?|views)$/i,'');
                    if(key==='channelUrl'&&webURL(info[key])){const anchor=document.createElement('a');anchor.href=webURL(info[key]);anchor.target='_blank';anchor.rel='noopener noreferrer';anchor.title=anchor.href;const path=new URL(anchor.href).pathname;anchor.textContent=/^\/@[^/]+\/?$/.test(path)?decodeURI(path.slice(1).replace(/\/$/,'')):label.replace(/^https?:\/\//,'');value.append(anchor);}
                    else value.textContent=label;
                    list.append(term,value);
                }
            }
            shadow.querySelector('.info-section').hidden=!shadow.querySelector('.full-info').childElementCount;
            const status=shadow.querySelector('.details-status');
            const message=data.aboutStatus==='loading'?'Loading channel details…':data.aboutStatus==='error'?'Channel links and details could not be loaded.':'';
            if(status.textContent!==message)status.textContent=message;
            status.hidden=!message;this.descriptionRetry.hidden=data.aboutStatus!=='error';
        }
        openDescription(){
            if(!this.descriptionHost.isConnected||!document.documentElement.classList.contains('minimal-youtube'))return;
            this.renderDescription();
            // Show a usable dialog before attempting YouTube's optional opener.
            // Native controls can be disabled, ignore synthetic events or throw.
            if(!this.descriptionDialog.open){
                this.descriptionScrollLocked=true;document.documentElement.setAttribute('data-myt-channel-description-open','');
                this.descriptionWheelRemainder=0;this.descriptionBody.scrollTop=0;this.descriptionDialog.showModal();this.descriptionBody.focus({preventScroll:true});
            }
            const source=this.descriptionSource;
            if(source?.isConnected){
                const control=source.querySelector('button,[role="button"],.ytDescriptionPreviewViewModelMoreButton,.yt-description-preview-view-model-wiz__more-button,.ytDescriptionPreviewViewModelMoreText,.yt-description-preview-view-model-wiz__more-text')||source;
                try{if(typeof control.click==='function')control.click();}catch{}
            }
            if(this.nativeAboutOpen()){this.restoreDescriptionFocus=false;this.descriptionDialog.close();}
            else this.requestAbout();
        }
        toggleSearch(){
            const form=this.nav.shadowRoot.querySelector('form'),input=form.querySelector('input');
            if(!form.hidden&&input.value.trim()){this.submitSearch();return;}
            if(!input.value.trim())this.clearSearchResults();
            form.hidden=false;this.searchButton.setAttribute('aria-expanded','true');input.focus({preventScroll:true});
        }
        clearSearchResults(){
            this.emptySearch=true;document.documentElement.setAttribute('data-myt-channel-search-empty','');
            this.cancelNavigation();
        }
        closeSearch(focus=false){
            this.nav.shadowRoot.querySelector('form').hidden=true;this.searchButton.setAttribute('aria-expanded','false');
            if(focus)this.searchButton.focus({preventScroll:true});
        }
        submitSearch(){const query=this.nav.shadowRoot.querySelector('input').value.trim();if(query)this.open(this.url('search',query));else this.clearSearchResults();}
        navigationKey(href){
            try{
                const url=new URL(href,location.href);
                const path=url.pathname.replace(/\/$/,'').replace(/\/community$/,'/posts').replace(/^\/@[^/]+/,value=>value.toLowerCase());
                return JSON.stringify([url.origin,path,/\/search$/.test(path)?url.searchParams.get('query')||'':'']);
            }catch{return '';}
        }
        renderNavigationState(){
            const pending=this.navigationPending,href=pending?.href||location.href;
            const section=new URL(href,location.href).pathname.replace(/\/$/,'').split('/').pop();
            const destination=section==='community'?'posts':section,current=destination==='search'?'videos':destination;
            for(const control of this.nav.shadowRoot.querySelectorAll('nav [data-section]')){
                const active=control.dataset.section===current;
                if(active)control.setAttribute('aria-current','page');else control.removeAttribute('aria-current');
                control.toggleAttribute('data-pending',!!pending&&active);
            }
            const busy=String(!!pending);if(this.nav.getAttribute('aria-busy')!==busy)this.nav.setAttribute('aria-busy',busy);
            const status=this.nav.shadowRoot.querySelector('.navigation-status');
            this.searchButton.toggleAttribute('data-pending',!!pending&&destination==='search');
            const message=pending?'Loading '+(sections.find(([key])=>key===destination)?.[1]||'section')+'…':'';
            if(status.textContent!==message)status.textContent=message;
        }
        cancelNavigation(){
            const pending=this.navigationPending;
            if(pending){clearTimeout(pending.acceptTimer);clearTimeout(pending.completeTimer);}
            this.navigationPending=null;this.renderNavigationState();
        }
        fallbackNavigation(pending){
            if(this.navigationPending!==pending)return;
            clearTimeout(pending.acceptTimer);clearTimeout(pending.completeTimer);this.navigationPending=null;
            location.assign(pending.href);
        }
        open(href){
            const url=new URL(href,location.href),search=/\/search\/?$/.test(url.pathname);
            if(!search)url.searchParams.delete('query');
            const key=this.navigationKey(url.href);
            this.emptySearch=false;document.documentElement.removeAttribute('data-myt-channel-search-empty');
            if(!search){this.closeSearch();this.nav.shadowRoot.querySelector('input').value='';}
            if(this.navigationPending?.key===key||!this.navigationPending&&key===this.navigationKey(location.href))return;
            this.cancelNavigation();
            const pending={id:(this.navigationSequence||0)+1,href:url.href,key,sourceKey:this.navigationKey(location.href),accepted:false};
            this.navigationSequence=pending.id;this.navigationPending=pending;this.renderNavigationState();
            // Regular sections use their own document, so repeated tab changes
            // never accumulate stale YouTube controllers or command state.
            if(!search){this.fallbackNavigation(pending);return;}
            this.nav.setAttribute('data-myt-channel-navigation-request',JSON.stringify({id:pending.id,href:pending.href}));
            this.nav.removeAttribute('data-myt-channel-navigation-result');
            this.nav.dispatchEvent(new Event('minimal-youtube:channel-navigate',{bubbles:true}));
            if(this.navigationPending!==pending)return;
            let result={};try{result=JSON.parse(this.nav.getAttribute('data-myt-channel-navigation-result')||'{}');}catch{}
            if(result.id!==pending.id||!result.started){this.fallbackNavigation(pending);return;}
            pending.acceptTimer=setTimeout(()=>{
                if(this.navigationPending===pending&&!pending.accepted&&this.navigationKey(location.href)!==pending.key)this.fallbackNavigation(pending);
            },700);
            pending.completeTimer=setTimeout(()=>this.fallbackNavigation(pending),12000);
        }
        url(section,query){const url=new URL(this.base+'/'+section,location.origin);url.searchParams.set('hl','en');url.searchParams.set('persist_hl','1');if(query)url.searchParams.set('query',query);return url.href;}
        hide(node){if(node&&!this.hidden.has(node)){node.setAttribute('data-myt-channel-source','');this.hidden.add(node);}}
        sync(browse){
            const match=location.pathname.match(basePattern);if(!match)return;
            if(this.base&&this.base!==match[1])this.cancelNavigation();
            this.base=match[1];
            const header=browse.querySelector(':scope > #header,:scope > #page-header,ytd-c4-tabbed-header-renderer,yt-page-header-view-model,yt-page-header-renderer');
            if(header){this.identity(header);this.links(header);}
            this.preview(header);
            this.navigation(browse,match[2]?.replace(/\/$/,'')||'videos');
            this.about();
            if(this.descriptionDialog.open&&this.nativeAboutOpen()){this.restoreDescriptionFocus=false;this.descriptionDialog.close();}
            this.translate(browse);
            for(const node of [...this.hidden])if(!node.isConnected){node.removeAttribute('data-myt-channel-source');this.hidden.delete(node);}
            for(const node of this.text.keys())if(!node.isConnected)this.text.delete(node);
            for(const node of this.attributes.keys())if(!node.isConnected)this.attributes.delete(node);
            for(const [node,names]of this.aboutNodes)if(!node.isConnected){for(const name of names)node.removeAttribute(name);this.aboutNodes.delete(node);}
        }
        nativeAboutOpen(){
            return [...document.querySelectorAll(aboutSelector+',[target-id="engagement-panel-channel-about"],[data-target-id="engagement-panel-channel-about"]')].some(node=>{
                if(!node.closest('dialog[open],tp-yt-paper-dialog,[role="dialog"],[target-id="engagement-panel-channel-about"][visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"],[data-target-id="engagement-panel-channel-about"][visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"]'))return false;
                if(node.closest('[hidden],[aria-hidden="true"],[visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN"]'))return false;
                const bounds=node.getBoundingClientRect();
                for(let parent=node;parent;parent=parent.parentElement){
                    const style=getComputedStyle(parent),clip=parent.getBoundingClientRect();
                    if(Number(style.opacity)===0||style.visibility==='hidden'||style.display==='none')return false;
                    if(/hidden|clip|auto|scroll/.test(style.overflowY)&&Math.min(bounds.bottom,clip.bottom)<=Math.max(bounds.top,clip.top))return false;
                    if(/hidden|clip|auto|scroll/.test(style.overflowX)&&Math.min(bounds.right,clip.right)<=Math.max(bounds.left,clip.left))return false;
                }
                const box=node.getBoundingClientRect(),style=getComputedStyle(node);
                return style.visibility!=='hidden'&&box.width>0&&box.height>0&&box.bottom>0&&box.top<innerHeight&&box.right>0&&box.left<innerWidth;
            });
        }
        preview(header){
            const next=new Map(),mark=(node,part)=>{
                if(!node)return;
                const name='data-myt-channel-description-'+part;
                if(!node.hasAttribute(name))node.setAttribute(name,'');
                if(!next.has(node))next.set(node,new Set());next.get(node).add(name);
            };
            const guard='h1,h2,#channel-name,ytd-channel-name,#avatar,yt-avatar-shape,yt-content-metadata-view-model,#channel-tagline,#myt-channel-stats,ytd-subscribe-button-renderer,yt-subscribe-button-view-model,#subscribe,#subscribe-button,#tabs,#tabs-container,#myt-channel-nav';
            const models=[...header?.querySelectorAll('yt-description-preview-view-model')||[]];
            const sources=models.length?models:[...header?.querySelectorAll('#description-container,#channel-description')||[]].filter(node=>!node.querySelector(guard));
            const source=sources.find(node=>!node.closest('[hidden],[aria-hidden="true"]')&&(node===this.descriptionSource||node.getClientRects().length))||sources[0];
            this.descriptionSource=source||null;
            if(source){
                const controls='button,[role="button"],.ytDescriptionPreviewViewModelMoreButton,.yt-description-preview-view-model-wiz__more-button,.ytDescriptionPreviewViewModelMoreText,.yt-description-preview-view-model-wiz__more-text';
                const textRoot=source.querySelector('.ytDescriptionPreviewViewModelTruncatedText,.yt-description-preview-view-model-wiz__truncated-text,.ytDescriptionPreviewViewModelDescriptionText,.yt-description-preview-view-model-wiz__description-text')||source;
                const copy=textRoot.cloneNode(true);
                copy.querySelectorAll(controls+',script,style,svg,yt-icon,tp-yt-paper-tooltip,yt-tooltip,[hidden]').forEach(node=>node.remove());
                source.dispatchEvent(new Event('minimal-youtube:channel-description',{bubbles:true}));
                let data={};try{data=JSON.parse(source.getAttribute('data-myt-channel-description-data')||'{}');}catch{}
                if(data.base!==this.base.toLowerCase())data={};
                // DOM renderers can contain the same visual and accessibility
                // text. Prefer the single public data value; dedupe complete
                // repeated DOM copies only when that data is unavailable.
                let raw=data.description||copy.textContent;
                if(!data.description){
                    raw=raw.replace(/\s+/gu,' ').trim();const words=raw.split(' ');
                    for(let copies=4;copies>=2;copies--){if(words.length%copies)continue;const size=words.length/copies,part=words.slice(0,size).join(' ');if(Array.from({length:copies},(_,i)=>words.slice(i*size,(i+1)*size).join(' ')).every(value=>value===part)){raw=part;break;}}
                }
                const value=raw.replace(/\s+/gu,' ').trim();
                this.descriptionDetails=data;
                this.descriptionFullValue=data.fullDescription||raw;
                if(this.descriptionValue!==value){
                    this.descriptionValue=value;
                    const chars=typeof Intl.Segmenter==='function'?Array.from(new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(value),part=>part.segment):Array.from(value);
                    let excerpt=value;
                    if(chars.length>180){excerpt=chars.slice(0,180).join('');const boundary=excerpt.lastIndexOf(' ');if(boundary>120)excerpt=excerpt.slice(0,boundary);excerpt=excerpt.trimEnd()+'…';}
                    this.descriptionText.textContent=excerpt;
                }
                this.renderDescription();
                this.descriptionText.hidden=!value;
                const control=source.querySelector(controls);
                const canOpen=!!value||!!this.descriptionFullValue||!!control||source.matches('yt-description-preview-view-model,[role="button"]')||source.hasAttribute('onclick');
                this.descriptionMore.hidden=!canOpen;
                // Insert outside description-only wrappers so their masks and
                // fixed heights cannot affect the independent shadow component.
                let slot=source;
                while(slot.parentElement&&slot.parentElement!==header&&!slot.parentElement.querySelector(guard))slot=slot.parentElement;
                if(value||canOpen){if(this.descriptionHost.nextElementSibling!==slot)slot.before(this.descriptionHost);}
                else this.descriptionHost.remove();
                mark(slot,'source');
                for(let parent=this.descriptionHost.parentElement;parent&&header.contains(parent);parent=parent.parentElement){mark(parent,'parent');if(parent===header)break;}
            }else this.descriptionHost.remove();
            for(const [node,names]of this.previewNodes)for(const name of names)if(!next.get(node)?.has(name))node.removeAttribute(name);
            this.previewNodes=next;
        }
        identity(header){
            const candidates=[...header.querySelectorAll('yt-content-metadata-view-model,#channel-tagline,#channel-handle,#subscriber-count,#subscribers,#videos-count,#video-count')];
            const values=candidates.map(node=>node.textContent.replace(/\s+/g,' ').trim());
            const handle=values.map(value=>value.match(/@[^\s·•*]+/u)?.[0]).find(Boolean)||(this.base.startsWith('/@')?decodeURI(this.base.slice(1)):'');
            const subscribers=values.map(value=>count(value,'subscribers')).find(Boolean)||'';
            const videos=values.map(value=>count(value,'videos')).find(Boolean)||'';
            const first=candidates.find(node=>node.matches('yt-content-metadata-view-model,#channel-tagline'))||candidates[0];
            if(first&&(handle||subscribers||videos)){
                if(this.stats.previousElementSibling!==first)first.after(this.stats);
                const signature=JSON.stringify([handle,subscribers,videos]);
                if(this.stats.dataset.value!==signature){
                    this.stats.dataset.value=signature;const row=this.stats.shadowRoot.querySelector('.row');row.replaceChildren();
                    const add=part=>{if(row.childNodes.length){const separator=document.createElement('span');separator.textContent='·';separator.setAttribute('aria-hidden','true');row.append(separator);}row.append(part);};
                    if(handle){const span=document.createElement('span');span.textContent=handle;add(span);}
                    for(const [kind,value]of [['subscribers',subscribers],['videos',videos]])if(value){const span=document.createElement('span');span.className='metric';span.dataset.kind=kind;span.setAttribute('aria-label',value+' '+kind);const number=document.createElement('span');number.textContent=value;span.append(number);span.insertAdjacentHTML('beforeend',svg(kind));add(span);}
                }
                for(const node of candidates)this.hide(node);
            }else this.stats.remove();
        }
        links(header){
            // Some headers render the external-link row as attribution instead
            // of a channel-external-link view model. Redirect URLs are links too.
            const protectedContent='h1,#channel-name,ytd-channel-name,#avatar,yt-avatar-shape,img,yt-content-metadata-view-model,#channel-tagline,#myt-channel-stats,#myt-channel-nav,yt-description-preview-view-model,#description-container,#channel-description,ytd-subscribe-button-renderer,yt-subscribe-button-view-model';
            for(const anchor of header.querySelectorAll('a[href]')){
                if(anchor.closest(protectedContent)||anchor.querySelector('img'))continue;
                let url;try{url=new URL(anchor.href);if(url.pathname==='/redirect'&&/(^|\.)youtube\.com$/.test(url.hostname))url=new URL(url.searchParams.get('q')||url.searchParams.get('url'));}catch{continue;}
                if(!/^https?:$/.test(url.protocol)||/(^|\.)youtube\.com$/.test(url.hostname))continue;
                let row=anchor;
                for(let parent=anchor.parentElement;parent&&parent!==header;parent=parent.parentElement){
                    if(parent.matches(protectedContent)||parent.querySelector(protectedContent))break;
                    row=parent;
                }
                this.hide(row);
            }
        }
        markAbout(node,part){
            if(!node)return;
            const name='data-myt-channel-about'+(part?'-'+part:'');
            if(!node.hasAttribute(name))node.setAttribute(name,'');
            if(!this.nextAboutNodes.has(node))this.nextAboutNodes.set(node,new Set());
            this.nextAboutNodes.get(node).add(name);
        }
        aboutInfoValue(row){
            const content=row.cloneNode(true);
            content.querySelectorAll('yt-icon,svg,img,tp-yt-paper-tooltip,yt-tooltip,[aria-hidden="true"],script,style').forEach(node=>node.remove());
            if(content.textContent.trim())return true;
            return !!row.querySelector('a[href^="mailto:"],a[href^="tel:"]')||[...row.querySelectorAll('button,[role="button"]')].some(button=>/e-?mail|почт|anzeigen|reveal/iu.test(button.getAttribute('aria-label')||''));
        }
        aboutLinks(source,scope){
            const rowSelector='yt-channel-external-link-view-model,yt-channel-external-link-renderer,ytd-channel-external-link-renderer,.ytChannelExternalLinkViewModelHost';
            const rows=[...source.querySelectorAll(rowSelector+',#primary-links > a')].filter(row=>!row.parentElement.closest(rowSelector));
            const sections=new Set(source.querySelectorAll('#links-section,#links-container,#primary-links,.ytAboutChannelViewModelLinks'));
            const headings=new Map();
            for(const heading of source.querySelectorAll('h2,h3,[role="heading"]')){
                if(!/^(links|ссылки)$/iu.test(heading.textContent.trim()))continue;
                const section=heading.parentElement===source?heading.nextElementSibling:heading.parentElement;
                if(!section||section.matches('h2,h3,[role="heading"]')){this.markAbout(heading,'empty');continue;}
                sections.add(section);headings.set(section,heading);
            }
            if(!this.aboutLinkSignatures.has(scope))this.aboutLinkSignatures.set(scope,new Map());
            const seen=this.aboutLinkSignatures.get(scope);
            const destination=row=>{
                const anchor=row.matches('a[href]')?row:row.querySelector('a[href]');if(!anchor)return '';
                try{
                    let url=new URL(anchor.href);
                    if(/(^|\.)youtube\.com$/.test(url.hostname)&&url.pathname==='/redirect')url=new URL(url.searchParams.get('q')||url.searchParams.get('url'));
                    return /^(https?|mailto|tel):$/.test(url.protocol)?url.href:'';
                }catch{return '';}
            };
            // A native fallback can keep another Links heading and an empty
            // list, or a second hydrated copy with different redirect tokens.
            for(const section of sections){
                if([...sections].some(parent=>parent!==section&&parent.contains(section)))continue;
                this.markAbout(section,'links');
                const items=rows.filter(row=>section.contains(row));
                const keys=[...new Set(items.map(destination).filter(Boolean))].sort();
                const nativeHidden=section.closest('[hidden],[aria-hidden="true"]')||section.style.display==='none';
                const signature=keys.length?JSON.stringify(keys):'';
                const previous=signature&&seen.get(signature);
                const empty=!items.some(row=>destination(row)||row.textContent.trim());
                if(nativeHidden||empty||previous&&previous!==section){
                    this.markAbout(section,'empty');
                    const heading=headings.get(section);if(heading&&!section.contains(heading))this.markAbout(heading,'empty');
                }else if(signature)seen.set(signature,section);
            }
            for(const row of rows){
                this.markAbout(row,'link');this.markAbout(row.parentElement,'link-list');
                this.markAbout(row.querySelector('#icon,yt-icon,yt-img-shadow,yt-image,img,.ytChannelExternalLinkViewModelIcon,.yt-channel-external-link-view-model-wiz__icon'),'icon');
            }
        }
        about(){
            this.nextAboutNodes=new Map();
            this.aboutLinkSignatures=new Map();
            const sources=new Set(document.querySelectorAll(aboutSelector));
            for(const panel of document.querySelectorAll('[target-id="engagement-panel-channel-about"],[data-target-id="engagement-panel-channel-about"]')){
                if(!panel.querySelector(aboutSelector)){
                    const content=panel.querySelector(':scope > #content');
                    if(content)sources.add(content.firstElementChild||content);
                }
            }
            for(const source of sources){
                // Decorate the existing dialog; native links, email verification,
                // focus handling and the close controls retain their DOM nodes.
                this.markAbout(source,'');
                let dialog=null,panel=null;
                for(let parent=source.parentElement;parent&&!parent.matches('ytd-popup-container,body');parent=parent.parentElement){
                    if(parent.matches('dialog,tp-yt-paper-dialog,[role="dialog"]'))dialog=parent;
                    if(parent.matches('ytd-engagement-panel-section-list-renderer')){panel=parent;this.markAbout(parent,'frame');}
                }
                if(dialog)this.markAbout(dialog,'dialog');
                const frame=panel||dialog;
                const scroll=frame?.querySelector(':scope > #content,:scope > #contents,:scope > #contentWrapper')||source;
                this.markAbout(scroll,'scroll');
                for(const description of source.querySelectorAll('#description-container,#channel-description,#description,.ytAboutChannelViewModelDescription')){
                    if(!description.parentElement.closest('[data-myt-channel-about-description]'))this.markAbout(description,'description');
                }
                this.aboutLinks(source,dialog||panel||source);
                for(const heading of source.querySelectorAll('h2,h3,[role="heading"]')){
                    const label=heading.textContent.trim();
                    if(/^(more info|channel details|дополнительная информация|сведения о канале)$/iu.test(label))this.markAbout(heading.parentElement===source?heading.nextElementSibling:heading.parentElement,'info');
                }
                for(const info of source.querySelectorAll('#additional-info-container,#metadata-container,#more-info,.ytAboutChannelViewModelMoreInfo'))this.markAbout(info,'info');
                for(const info of source.querySelectorAll('[data-myt-channel-about-info]')){
                    const rows=[...info.querySelectorAll('tr,yt-about-channel-metadata-view-model,yt-about-channel-info-row-view-model,.ytAboutChannelViewModelMetadataRow,.metadata-row,.info-row')];
                    for(const row of rows){
                        this.markAbout(row,'info-row');this.markAbout(row.parentElement,'info-list');
                        if(!this.aboutInfoValue(row))this.markAbout(row,'empty');
                        this.markAbout(row.querySelector('yt-icon,yt-img-shadow,yt-image,img,svg'),'icon');
                    }
                }
            }
            for(const [node,names]of this.aboutNodes)for(const name of names)if(!this.nextAboutNodes.get(node)?.has(name))node.removeAttribute(name);
            this.aboutNodes=this.nextAboutNodes;this.nextAboutNodes=null;this.aboutLinkSignatures=null;
        }
        navigation(browse,current){
            const tabs=[...browse.querySelectorAll(tabsSelector)].filter(node=>!node.parentElement.closest(tabsSelector));
            if(!tabs.length){
                if(this.navigationPending){const slot=browse.querySelector('#tabs,#tabs-container');if(slot&&!slot.contains(this.nav))slot.prepend(this.nav);this.renderNavigationState();}
                else this.nav.remove();
                return;
            }
            const group=tabs[0].closest('yt-tab-group-shape,tp-yt-paper-tabs')||tabs[0];
            if(this.nav.nextElementSibling!==group)group.before(this.nav);
            const available=new Map();
            for(const tab of tabs){
                const label=tab.textContent.trim()||tab.getAttribute('aria-label')||tab.querySelector('[aria-label]')?.getAttribute('aria-label')||'';
                const anchor=tab.matches('a[href]')?tab:tab.querySelector('a[href]');
                let slug='';try{slug=new URL(anchor?.href||tab.getAttribute('href')||'/',location.href).pathname.split('/').filter(Boolean).at(-1)||'';}catch{}
                const section=sections.find(([key,,pattern])=>key===slug||key==='posts'&&slug==='community'||pattern.test(label)||key==='search'&&tab.matches('ytd-expandable-tab-renderer'));
                if(section)available.set(section[0],{key:section[0],label:section[1],slug:section[0]==='posts'&&slug==='community'?'community':section[0]});
            }
            if(!available.size){
                if(this.navigationPending){this.renderNavigationState();return;}
                this.nav.remove();
                for(const node of [...tabs,group]){node.removeAttribute('data-myt-channel-source');this.hidden.delete(node);}
                return;
            }
            for(const tab of tabs)this.hide(tab);
            // Hide the native scroller too, so it cannot reserve an empty row.
            if(group!==tabs[0])this.hide(group);
            const items=sections.map(([key])=>available.get(key)).filter(Boolean),signature=JSON.stringify([this.base,items]);
            if(this.nav.dataset.items!==signature){
                this.nav.dataset.items=signature;const nav=this.nav.shadowRoot.querySelector('nav');nav.replaceChildren();
                for(const item of items){
                    if(item.key==='search')continue;
                    const control=document.createElement('a');control.textContent=item.label;control.dataset.section=item.key;control.href=this.url(item.slug);
                    nav.append(control);
                }
            }
            this.renderNavigationState();
            const routeKey=this.navigationKey(location.href);
            if(current==='search'&&(this.current!=='search'||this.searchRouteKey!==routeKey)){
                this.nav.shadowRoot.querySelector('form').hidden=false;
                if(!this.emptySearch)this.nav.shadowRoot.querySelector('input').value=new URL(location.href).searchParams.get('query')||'';
                this.searchButton.setAttribute('aria-expanded','true');
                this.searchRouteKey=routeKey;
            }else if(current!=='search'&&this.current==='search'){
                this.closeSearch();
                this.nav.shadowRoot.querySelector('input').value='';
                this.searchRouteKey=null;
            }
            this.current=current;
        }
        translate(browse){
            const scopes=[...browse.querySelectorAll(':scope > #header,:scope > #page-header,ytd-feed-filter-chip-bar-renderer,yt-chip-cloud-renderer'),...document.querySelectorAll('ytd-popup-container [role="menuitem"],ytd-confirm-dialog-renderer')];
            for(const scope of scopes){
                const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let node;
                while(node=walker.nextNode()){
                    const parent=node.parentElement;
                    if(!parent||parent.closest('h1,#channel-name,ytd-channel-name,#channel-tagline,yt-content-metadata-view-model,#myt-channel-nav,#myt-channel-stats'))continue;
                    const description=parent.closest('#description-container,#channel-description,yt-description-preview-view-model');
                    if(description&&!parent.closest('button,[role="button"],.ytDescriptionPreviewViewModelMoreButton,.ytDescriptionPreviewViewModelMoreText,.yt-description-preview-view-model-wiz__more-button'))continue;
                    const translated=words.get(node.data.trim().replace(/^[.…\s]+/u,'').toLocaleLowerCase());if(!translated)continue;
                    this.text.set(node,{original:node.data,applied:translated});node.data=translated;
                }
                for(const element of scope.querySelectorAll('[aria-label],[title],[placeholder]'))for(const name of ['aria-label','title','placeholder']){
                    if(element.closest('h1,#channel-name,ytd-channel-name'))continue;
                    const original=element.getAttribute(name),translated=words.get(original?.trim().toLocaleLowerCase());if(!translated)continue;
                    if(!this.attributes.has(element))this.attributes.set(element,new Map());this.attributes.get(element).set(name,{original,applied:translated});element.setAttribute(name,translated);
                }
            }
        }
        destroy(){
            this.cancelNavigation();
            document.documentElement.removeAttribute('data-myt-channel-search-empty');
            for(const name of navigationEvents)window.removeEventListener(name,this.nativeNavigation,true);
            window.removeEventListener('popstate',this.historyNavigation);
            window.navigation?.removeEventListener('currententrychange',this.routeNavigation);
            document.removeEventListener('minimal-youtube:channel-about-updated',this.aboutUpdated);
            if(this.descriptionDialog.open)this.descriptionDialog.close();
            this.releaseDescriptionScroll();
            window.removeEventListener('wheel',this.descriptionWheel,true);window.removeEventListener('touchstart',this.descriptionTouchStart,true);window.removeEventListener('touchmove',this.descriptionTouchMove,true);
            window.removeEventListener('click',this.click,true);window.removeEventListener('auxclick',this.click,true);window.removeEventListener('keydown',this.keydown,true);this.nav.remove();this.stats.remove();this.descriptionHost.remove();
            for(const node of this.hidden)node.removeAttribute('data-myt-channel-source');this.hidden.clear();
            for(const [node,names]of this.previewNodes)for(const name of names)node.removeAttribute(name);this.previewNodes.clear();
            for(const [node,names]of this.aboutNodes)for(const name of names)node.removeAttribute(name);this.aboutNodes.clear();
            for(const [node,state]of this.text)if(node.data===state.applied)node.data=state.original;
            for(const [node,attrs]of this.attributes)for(const [name,state]of attrs)if(node.getAttribute(name)===state.applied)node.setAttribute(name,state.original);
            this.text.clear();this.attributes.clear();
        }
    }
    globalThis.MinimalYouTubeChannel=Channel;
})();
