/* Owned playlist cards. Native nodes only supply data, commands and pagination. */
(() => {
    'use strict';
    const rowSelector='ytd-playlist-video-renderer,yt-lockup-view-model,ytd-video-renderer';
    const icons={play:'<path d="m9 5 11 7-11 7Z"/>',shuffle:'<path d="m18 3 3 3-3 3M18 15l3 3-3 3M3 6h3c5 0 7 12 12 12h3M3 18h3c5 0 7-12 12-12h3"/>',menu:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',share:'<path d="m15 4 6 6-6 6v-4C8 12 5 14 3 19c0-8 3-12 12-12Z"/>'};
    const icon=name=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||''}</svg>`;
    const clean=node=>{const copy=node?.cloneNode(true);copy?.querySelectorAll('button,[role="button"],tp-yt-paper-tooltip,yt-tooltip,[hidden],[aria-hidden="true"],svg,yt-icon').forEach(e=>e.remove());return copy?.textContent.replace(/\s+/g,' ').trim()||'';};
    const url=(value,image=false)=>{if(typeof value!=='string'||!value.trim())return '';try{const u=new URL(value,location.href);return /^https?:$/.test(u.protocol)||(image&&u.protocol==='data:'&&/^data:image\//.test(value))?u.href:'';}catch{return '';}};
    const image=node=>node&&(url(node.currentSrc||node.getAttribute('src')||node.getAttribute('data-src'),true))||'';
    const channel=node=>{const links=[...node.querySelectorAll('a[href]')].filter(a=>{try{return /^\/(?:@|channel\/|c\/|user\/)/.test(new URL(a.href).pathname);}catch{return false;}});return links.find(a=>a.textContent.trim())||links[0];};
    const label=node=>node.getAttribute('aria-label')||node.getAttribute('title')||node.closest('yt-icon-button[aria-label],ytd-button-renderer[aria-label],yt-button-view-model[aria-label]')?.getAttribute('aria-label')||clean(node);
    const shared=`:host{box-sizing:border-box;display:block;min-width:0;width:100%;color:var(--myt-ink,#f4f4f5);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}*{box-sizing:border-box}[hidden]{display:none!important}a{color:inherit;text-decoration:none}button{font:inherit;color:inherit;cursor:pointer}button:disabled{opacity:.5;cursor:default}a:focus-visible,button:focus-visible{outline:2px solid var(--myt-muted);outline-offset:3px}svg{width:20px;height:20px;flex:none}img{display:block}h1,h3,p{margin:0}.muted{color:var(--myt-muted,#92929d)}button{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid var(--myt-border);border-radius:999px;background:var(--myt-surface)}button:hover{background:var(--myt-border)}.cover{display:block;position:relative;aspect-ratio:16/9;overflow:hidden;background:var(--myt-soft);border-radius:12px}.cover img{width:100%;height:100%;object-fit:cover}.metadata{font-size:13px;line-height:1.5;color:var(--myt-muted);overflow-wrap:anywhere}`;
    const summaryCSS=`${shared}.panel{padding:24px;min-height:calc(100dvh - 120px);background:var(--myt-soft,#24242a);border:1px solid var(--myt-border);border-radius:24px}.cover{max-width:360px;margin-bottom:20px;border-radius:16px}h1{font-size:26px;font-weight:700;line-height:1.2;letter-spacing:-.65px;overflow-wrap:anywhere}.owner{display:flex;align-items:center;gap:9px;margin:16px 0 10px;min-width:0}.owner img{width:28px;height:28px;border-radius:50%;object-fit:cover}.owner a{min-width:0;overflow-wrap:anywhere}.owner a:hover{text-decoration:underline}.stats{font-size:14px;line-height:1.6;color:var(--myt-muted)}.description{margin-top:18px;font:14px/1.65 "SFMono-Regular",Menlo,Consolas,monospace;color:var(--myt-muted);overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:4;overflow:hidden}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}.actions button{min-height:40px;padding:9px 14px;font-weight:600}.actions .menu{width:40px;padding:0}.play-all{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:40px;padding:9px 14px;font-weight:600;border:1px solid var(--myt-border);border-radius:999px;background:var(--myt-surface)}.play-all:hover{background:var(--myt-border)}.share-sheet{position:fixed;inset:0;margin:auto;width:min(440px,calc(100vw - 32px));max-height:calc(100dvh - 32px);overflow:auto;padding:24px;border:1px solid var(--myt-border);border-radius:24px;background:var(--myt-surface);color:var(--myt-ink)}.share-sheet::backdrop{background:#0008}.share-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px}.share-head h2{margin:0;font-size:21px}.share-sheet button{min-height:40px;padding:8px 16px}.share-link{display:block;width:100%;margin:0 0 16px;padding:12px;border:1px solid var(--myt-border);border-radius:12px;background:var(--myt-soft);color:inherit;font:13px/1.5 monospace}.share-status{margin-top:12px;color:var(--myt-muted)}@media(max-width:900px){.panel{min-height:0}}@media(min-width:601px) and (max-width:900px){.panel{display:grid;grid-template-columns:240px minmax(0,1fr);gap:0 24px}.cover{grid-column:1;grid-row:1/6;align-self:start;width:100%;margin:0}h1,.owner,.stats,.description,.actions{grid-column:2}}@media(max-width:600px){.panel{padding:20px}}`;
    const rowCSS=`${shared}.watched{position:absolute;left:0;right:0;bottom:0;height:4px;background:#ffffff59;pointer-events:none}.watched[hidden]{display:none}.watched>i{display:block;height:100%;background:#e5202b}:host{display:grid;grid-template-columns:24px 168px minmax(0,1fr) 36px;align-items:center;gap:14px;padding:12px;border:1px solid var(--myt-border);border-radius:20px;background:var(--myt-surface,#19191d)}:host(:hover),:host(:focus-within){background:var(--myt-soft)}:host([data-current]){border-color:var(--myt-accent)}.index{font-size:13px;text-align:center;color:var(--myt-muted);font-variant-numeric:tabular-nums}h3{font-size:17px;font-weight:600;line-height:1.4}.title{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere}.metadata{margin-top:5px}.duration{position:absolute;right:5px;bottom:5px;padding:1px 5px;border-radius:5px;background:#000b;color:white;font-size:11px;font-variant-numeric:tabular-nums}.menu{width:36px;height:36px;padding:0;border:0;background:transparent;color:var(--myt-muted)}.meta{min-width:0}@media(max-width:600px){:host{grid-template-columns:112px minmax(0,1fr) 28px;gap:10px;padding:10px;border-radius:18px}.index{display:none}h3{font-size:15px}.cover{border-radius:10px}.menu{width:28px}}`;
    // Native nodes or plain records ({href}) can back a card's controls.
    const attribute=(node,name)=>typeof node?.getAttribute==='function'?node.getAttribute(name):node?.[name]??null;
    const disabledSource=node=>typeof node?.matches==='function'&&node.matches(':disabled,[aria-disabled="true"]');
    // Native statistics read in English, ages older than four months as a month.
    const english=part=>{const search=globalThis.MinimalYouTubeSearch,dated=search?.publishedLabel?search.publishedLabel(part):part;return search?.englishStat?search.englishStat(dated):dated;};
    const watchedProgress=root=>{const bar=root?.querySelector?.('.ytThumbnailOverlayProgressBarHostWatchedProgressBarSegment,.ytThumbnailOverlayProgressBarHostWatchedProgressBar>div,ytd-thumbnail-overlay-resume-playback-renderer #progress,[class*="WatchedProgressBarSegment"]');const value=parseFloat(bar?.style.width||'');return Number.isFinite(value)&&value>0?Math.min(100,Math.round(value)):0;};
    const route=()=>{const url=new URL(location.href);return url.pathname==='/playlist'?JSON.stringify(['playlist',url.searchParams.get('list')||'']):'';};
    const menuCSS=`:host{all:initial;position:fixed;inset:auto;margin:0;padding:6px;min-width:220px;max-width:min(320px,calc(100vw - 16px));border:1px solid var(--myt-border,#2c2c33);border-radius:16px;background:var(--myt-surface,#19191d);color:var(--myt-ink,#f4f4f5);font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;box-shadow:0 12px 32px #0006}:host(:not(:popover-open)){display:none}button{display:block;width:100%;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}button:hover,button:focus-visible{background:var(--myt-soft,#24242a);outline:none}`;
    class Card {
        constructor(owner,summary=false){
            this.owner=owner;this.host=document.createElement('div');this.host.dataset.mytOwnedPlaylistCard=summary?'summary':'video';
            if(summary)this.host.id='myt-playlist-summary';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=summary?`<style>${summaryCSS}</style><section class="panel"><a class="cover" data-action="play"><img alt="" decoding="async"></a><h1></h1><div class="owner"><img alt="" decoding="async"><a data-action="channel"></a></div><p class="stats"></p><p class="description"></p><div class="actions"><a class="play-all" data-action="play">${icon('play')}<span>Play all</span></a><button data-action="shuffle">${icon('shuffle')}<span>Shuffle</span></button><button class="menu" data-action="share" aria-label="Share">${icon('share')}</button><button class="menu" data-action="menu" aria-label="Playlist actions">${icon('menu')}</button></div></section><div class="share-sheet" popover="auto" role="dialog" aria-label="Share playlist"><div class="share-head"><h2>Share playlist</h2><button class="share-close" aria-label="Close share dialog">×</button></div><input class="share-link" aria-label="Playlist link" readonly><button class="share-copy">Copy link</button><p class="share-status" role="status"></p></div>`:`<style>${rowCSS}</style><span class="index"></span><a class="cover" data-action="play"><img alt="" loading="lazy" decoding="async"><span class="watched" role="img" hidden><i></i></span><span class="duration"></span></a><div class="meta"><h3><a class="title" data-action="play"></a></h3><p class="metadata"></p></div><button class="menu" data-action="menu" aria-label="Video actions">${icon('menu')}</button>`;
            this.summary=summary;this.q=s=>this.shadow.querySelector(s);
            this.shadow.addEventListener('click',event=>{
                const control=event.target.closest('[data-action]');if(!control)return;
                event.stopPropagation();
                if(this.summary&&control.dataset.action==='share'){event.preventDefault();this.owner.share(this);return;}
                if(this.summary&&control.dataset.action==='play'&&this.playHref)return;
                if(this.item&&control.dataset.action==='menu'){event.preventDefault();this.owner.openMenu(this,control);return;}
                if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
                const source=this.actions?.[control.dataset.action];
                if(source?.isConnected){event.preventDefault();this.owner.activate(source,control,['menu','share'].includes(control.dataset.action));}
            });
            this.q('.cover img').onerror=()=>{this.q('.cover img').hidden=true;};
            if(summary){
                this.q('.share-close').onclick=()=>this.q('.share-sheet').hidePopover();
                this.q('.share-copy').onclick=async()=>{
                    const field=this.q('.share-link');
                    try{await navigator.clipboard.writeText(field.value);this.q('.share-status').textContent='Link copied';}
                    catch{field.focus();field.select();this.q('.share-status').textContent='Select and copy the link.';}
                };
            }
        }
        text(selector,value){const node=this.q(selector);if(node.textContent!==value)node.textContent=value;}
        update(data){
            this.actions=data.actions;this.playHref=data.playHref||'';
            const signature=JSON.stringify([data.playHref,data.title,data.author,data.stats,data.image,data.avatar,data.description,data.index,data.duration,data.current,data.progress,Object.entries(data.actions).map(([kind,node])=>[kind,!!node,attribute(node,'href'),disabledSource(node)])]);
            if(this.signature===signature)return;this.signature=signature;
            const img=this.q('.cover img');if(img.getAttribute('src')!==data.image){if(data.image)img.src=data.image;else img.removeAttribute('src');img.hidden=!data.image;}
            this.q('.cover').hidden=this.summary&&!data.image;
            this.text(this.summary?'h1':'.title',data.title);
            const watched=this.q('.watched');if(watched){const progress=data.progress||0;watched.hidden=!progress;watched.firstChild.style.width=progress+'%';watched.setAttribute('aria-label',progress?'Watched '+progress+'%':'');}
            if(this.summary){const owner=this.q('.owner a');if(owner.textContent!==data.author)owner.textContent=data.author;this.q('.owner').hidden=!data.author;}
            this.text(this.summary?'.stats':'.metadata',data.stats);this.q(this.summary?'.stats':'.metadata').hidden=!data.stats;
            for(const link of this.shadow.querySelectorAll('a[data-action]')){
                const href=this.summary&&link.dataset.action==='play'?this.playHref:url(attribute(data.actions[link.dataset.action],'href')||'');
                if(href&&link.getAttribute('href')!==href)link.href=href;else if(!href)link.removeAttribute('href');
            }
            for(const button of this.shadow.querySelectorAll('button[data-action]')){
                const source=data.actions[button.dataset.action];button.hidden=button.dataset.action==='share'?false:!source;
                const disabled=disabledSource(source);if(button.disabled!==disabled)button.disabled=disabled;
            }
            if(this.summary){
                this.q('.play-all').hidden=!this.playHref;
                this.text('.description',data.description);this.q('.description').hidden=!data.description;
                const avatar=this.q('.owner img');if(data.avatar&&avatar.getAttribute('src')!==data.avatar)avatar.src=data.avatar;avatar.hidden=!data.avatar;
            }else{
                this.text('.index',data.index);this.text('.duration',data.duration);this.q('.duration').hidden=!data.duration;
                if(this.host.hasAttribute('data-current')!==data.current)this.host.toggleAttribute('data-current',data.current);
            }
        }
    }
    class Playlist {
        constructor({source,list,onChange}){
            this.source=source;this.list=list;this.rows=new Map();this.anchors=new Map();this.card=new Card(this,true);this.host=this.card.host;
            this.load=event=>{if(event.target instanceof HTMLImageElement)onChange();};source.addEventListener('load',this.load,true);
            // Page data mode: rows come from YouTube's playlist data, not its
            // stamped renderers, and further pages load from its continuation.
            this.dataCards=new Map();this.pending=new Map();
            this.rowsHost=document.createElement('div');this.rowsHost.id='myt-playlist-rows';this.rowsHost.lang='en';
            this.rowsList=document.createElement('div');this.rowsList.className='myt-playlist-items';
            this.empty=document.createElement('p');this.empty.className='myt-playlist-empty';this.empty.textContent='No videos in this playlist.';this.empty.hidden=true;
            this.status=document.createElement('p');this.status.className='myt-playlist-status';this.status.setAttribute('role','status');
            this.more=document.createElement('div');this.more.className='myt-playlist-more';this.more.setAttribute('aria-hidden','true');
            // Loading: placeholder rows first, then dots while more rows load.
            this.skeleton=document.createElement('div');this.skeleton.className='myt-playlist-skeleton';this.skeleton.setAttribute('role','status');this.skeleton.setAttribute('aria-label','Loading videos');this.skeleton.hidden=true;
            for(let index=0;index<6;index++){const row=document.createElement('div');row.className='myt-playlist-skeleton-row';row.innerHTML='<span></span><span></span><span><i></i><i></i></span>';this.skeleton.append(row);}
            this.loadingMore=document.createElement('div');this.loadingMore.className='myt-loading-more';this.loadingMore.setAttribute('role','status');this.loadingMore.setAttribute('aria-label','Loading more');this.loadingMore.hidden=true;this.loadingMore.innerHTML='<span></span><span></span><span></span>';
            this.rowsHost.append(this.status,this.rowsList,this.skeleton,this.empty,this.loadingMore,this.more);
            this.moreObserver=new IntersectionObserver(entries=>{this.moreVisible=entries.some(entry=>entry.isIntersecting);this.requestMore();},{rootMargin:'800px 0px'});this.moreObserver.observe(this.more);
            this.modelChanged=()=>onChange();document.addEventListener('minimal-youtube:page-model-updated',this.modelChanged);
            this.actionResult=()=>{
                let result={};try{result=JSON.parse(document.documentElement.getAttribute('data-myt-page-model-action-result')||'{}');}catch{}
                const card=this.pending.get(result.id);if(!card)return;this.pending.delete(result.id);
                card.host.removeAttribute('aria-busy');
                this.say(result.ok?'':'Could not update the playlist. Try again.');
            };
            document.addEventListener('minimal-youtube:page-model-action-result',this.actionResult);
        }
        pageModel(){
            document.dispatchEvent(new Event('minimal-youtube:page-model'));
            let model=null;try{model=JSON.parse(document.documentElement.getAttribute('data-myt-page-model')||'null');}catch{}
            return model?.type==='playlist'&&Array.isArray(model.items)&&model.key===route()?model:null;
        }
        say(message){
            clearTimeout(this.statusTimer);if(this.status.textContent!==message)this.status.textContent=message;
            if(message)this.statusTimer=setTimeout(()=>{this.status.textContent='';},6000);
        }
        requestMore(){
            if(this.moreVisible&&this.model?.more&&!this.model.loading&&this.rowsHost.isConnected)document.dispatchEvent(new Event('minimal-youtube:page-model-more'));
        }
        readItem(item,index){
            const stats=(item.stats||'').split(/\s*[•·]\s*/).filter(Boolean).map(english).join(' · ');
            return {title:item.title||'Unavailable video',author:item.channel?.name||'',stats,image:url(item.image,true)||'',duration:item.duration||'',
                index:/^\d+$/.test(item.index||'')?item.index:String(index+1),current:false,progress:Number(item.progress)||0,
                actions:{play:url(item.href)?{href:url(item.href)}:null,channel:url(item.channel?.href)?{href:url(item.channel.href)}:null,menu:{href:''}}};
        }
        syncData(model){
            this.model=model;
            for(const [row,state] of this.rows)this.restoreRow(row,state);this.rows.clear();
            if(!this.list.hasAttribute('data-myt-playlist-data'))this.list.setAttribute('data-myt-playlist-data','');
            if(this.rowsHost.parentElement!==this.list||this.list.firstElementChild!==this.rowsHost)this.list.prepend(this.rowsHost);
            const wanted=new Map();
            model.items.forEach((item,index)=>{
                if(item?.kind!=='video')return;
                const key=item.setVideoId||item.href+'|'+index;
                let card=this.dataCards.get(key);if(!card){card=new Card(this);card.host.dataset.mytPlaylistItem='';}
                card.item=item;card.update(this.readItem(item,index));wanted.set(key,card);
            });
            for(const [key,card] of this.dataCards)if(!wanted.has(key))card.host.remove();
            this.dataCards=wanted;
            let previous=null;
            for(const card of wanted.values()){
                const next=previous?previous.nextElementSibling:this.rowsList.firstElementChild;
                if(next!==card.host)this.rowsList.insertBefore(card.host,next);
                previous=card.host;
            }
            this.empty.hidden=Boolean(wanted.size||model.more||model.loading);
            this.skeleton.hidden=Boolean(wanted.size||!model.more&&!model.loading);
            this.loadingMore.hidden=!(wanted.size&&model.loading);
            this.requestMore();
        }
        leaveData(){
            if(!this.model&&!this.rowsHost.isConnected)return;
            this.model=null;this.rowsHost.remove();this.list.removeAttribute('data-myt-playlist-data');
            for(const card of this.dataCards.values())card.host.remove();this.dataCards.clear();
        }
        openMenu(card,control){
            this.stopMenu();this.restoreAnchors();
            if(!this.menu){
                this.menu=document.createElement('div');this.menu.id='myt-playlist-menu';this.menu.setAttribute('popover','auto');this.menu.setAttribute('role','menu');this.menu.lang='en';
                this.menuRoot=this.menu.attachShadow({mode:'open'});
            }
            if(!this.menu.isConnected)document.body.append(this.menu);
            const item=card.item,options=[...(item.actions||[]),{id:'copy',label:'Copy link'}];
            this.menuRoot.replaceChildren(Object.assign(document.createElement('style'),{textContent:menuCSS}),...options.map(option=>{
                const button=document.createElement('button');button.type='button';button.setAttribute('role','menuitem');button.textContent=option.label;
                button.addEventListener('click',async()=>{
                    try{this.menu.hidePopover();}catch{}
                    control.focus();
                    if(option.id==='copy'){try{await navigator.clipboard.writeText(url(item.href));this.say('Link copied');}catch{this.say(url(item.href));}return;}
                    this.pending.set(option.id,card);card.host.setAttribute('aria-busy','true');
                    document.documentElement.setAttribute('data-myt-page-model-action',option.id);
                    document.dispatchEvent(new Event('minimal-youtube:page-model-action'));
                });
                return button;
            }));
            try{this.menu.showPopover();}catch{}
            const rect=control.getBoundingClientRect(),box=this.menu.getBoundingClientRect();
            const top=rect.bottom+8+box.height<=innerHeight-8?rect.bottom+8:Math.max(8,rect.top-box.height-8);
            this.menu.style.setProperty('left',Math.max(8,Math.min(rect.right-box.width,innerWidth-box.width-8))+'px');
            this.menu.style.setProperty('top',top+'px');
            this.menuRoot.querySelector('button')?.focus();
        }
        static rows(list){return [...list.querySelectorAll(rowSelector)].filter(row=>!row.parentElement.closest(rowSelector)&&!row.closest('[hidden],[aria-hidden="true"]')&&row.style.display!=='none');}
        setSource(source){if(source===this.source)return;this.stopMenu();this.restoreAnchors();this.source.removeEventListener('load',this.load,true);this.source=source;source.addEventListener('load',this.load,true);}
        readSummary(){
            const source=this.source,authorLink=channel(source),author=clean(authorLink);
            const title=clean(source.querySelector('h1,#title,.dynamic-text-view-model-wiz__h1,yt-dynamic-sizing-formatted-string'))||document.title.replace(/^\(\d+\)\s*| - YouTube$/g,'')||'Playlist';
            const thumbnail=source.querySelector('ytd-thumbnail img,ytd-playlist-video-thumbnail-renderer img,ytd-hero-playlist-thumbnail-renderer img,yt-thumbnail-view-model img,#hero-image img,.thumbnail-wrapper img')||source.querySelector('img');
            const stats=clean(source.querySelector('#stats,.metadata-stats,.ytContentMetadataViewModelMetadataRow,.yt-content-metadata-view-model__metadata-row,yt-content-metadata-view-model'));
            const descriptionNode=source.querySelector('#description,yt-description-preview-view-model');
            const controls=[...source.querySelectorAll('button,a[role="button"],yt-icon-button')].map(node=>node.querySelector('button')||node).filter(node=>!descriptionNode?.contains(node));
            const find=pattern=>controls.find(node=>pattern.test(label(node)));
            const play=find(/play all|watch all|воспроизвести|смотреть все|^(?:continue|start course|продолжить|начать курс)$/iu)||source.querySelector('a[href*="/watch?"]')||this.list.querySelector('a[href*="/watch?"]');
            let playHref=[...source.querySelectorAll('a[href*="/watch?"]'),...this.list.querySelectorAll('a[href*="/watch?"]')].map(anchor=>url(anchor.href)).find(href=>href&&new URL(href).searchParams.get('v'))||'';
            if(playHref){const target=new URL(playHref),list=new URL(location.href).searchParams.get('list');if(list)target.searchParams.set('list',list);playHref=target.searchParams.get('v')?target.href:'';}
            return {playHref,title,author,stats:english(stats),avatar:image([...source.querySelectorAll('a[href] img')].find(img=>img.closest('a').href===authorLink?.href)),image:image(thumbnail)||image(this.list.querySelector('img')),description:clean(descriptionNode),actions:{play,channel:authorLink,shuffle:find(/shuffle|перемешать/iu),share:find(/share|поделиться/iu),menu:find(/actions|menu|действия|ещё|еще|^more$|^[⋯⋮…]$/iu)}};
        }
        readRow(row,index){
            const play=row.querySelector('a#video-title,a#video-title-link,h3 a[href],a[href*="/watch?"]'),authorLink=channel(row);
            let fallback='';try{const id=new URL(play?.href).searchParams.get('v');if(/^[\w-]{11}$/.test(id||''))fallback='https://i.ytimg.com/vi/'+id+'/mqdefault.jpg';}catch{}
            // Author links also occur inside modern metadata rows. Remove those
            // from the metadata source rather than displaying a second byline.
            const metadataNodes=[...row.querySelectorAll('#video-info,.video-info,.ytContentMetadataViewModelMetadataRow,.yt-content-metadata-view-model__metadata-row')];
            const author=clean(authorLink),metadata=[...new Set(metadataNodes.filter(node=>!metadataNodes.some(parent=>parent!==node&&parent.contains(node))).map(node=>{
                const copy=node.cloneNode(true);let link;while((link=channel(copy)))link.remove();
                copy.querySelectorAll('#byline-container,ytd-channel-name').forEach(node=>node.remove());
                return clean(copy).split(/[·•]/).map(text=>text.trim()).filter(text=>text&&text!==author).map(english).join(' · ');
            }).filter(Boolean))].join(' · ');
            const duration=[...row.querySelectorAll('ytd-thumbnail-overlay-time-status-renderer,.badge-shape-wiz__text,.yt-badge-shape__text,.ytThumbnailOverlayBadgeViewModelBadgeText')].map(clean).find(value=>/^\d{1,3}:\d{2}(?::\d{2})?$/.test(value))||'';
            return {title:clean(row.querySelector('#video-title,#video-title-link,h3'))||clean(play)||'Unavailable video',author:clean(authorLink),stats:metadata,image:image(row.querySelector('ytd-thumbnail img,yt-thumbnail-view-model img,img'))||fallback,duration,index:clean(row.querySelector('#index-container,#index')).match(/\d+/)?.[0]||String(index+1),progress:watchedProgress(row),current:row.hasAttribute('selected')&&row.getAttribute('selected')!=='false'||row.getAttribute('aria-current')==='true',actions:{play,channel:authorLink,menu:row.querySelector('#menu button,ytd-menu-renderer button,button[aria-label*="actions" i]')}};
        }
        sync(){
            const model=this.pageModel(),summary=this.readSummary();
            if(model&&!summary.playHref){const first=model.items.find(item=>item.playable!==false&&url(item.href));if(first)summary.playHref=url(first.href);}
            this.card.update(summary);
            if(model){this.syncData(model);return;}
            this.leaveData();
            const wanted=new Set(Playlist.rows(this.list));
            for(const [row,state] of this.rows)if(!wanted.has(row)){this.restoreRow(row,state);this.rows.delete(row);}
            let index=0;
            for(const row of wanted){
                let state=this.rows.get(row);
                if(!state){if(getComputedStyle(row).display==='none')continue;state={card:new Card(this),parts:new Set()};this.rows.set(row,state);row.setAttribute('data-myt-playlist-row','');}
                // A native rerender can replace its children while keeping the
                // renderer. Reattach only our card; native source nodes stay put.
                if(state.card.host.parentElement!==row)row.append(state.card.host);
                for(const part of state.parts)if(part.parentElement!==row){part.removeAttribute('data-myt-playlist-native-row-part');state.parts.delete(part);}
                for(const part of row.children)if(part!==state.card.host&&!state.parts.has(part)){part.setAttribute('data-myt-playlist-native-row-part','');state.parts.add(part);}
                state.card.update(this.readRow(row,index++));
            }
        }
        share(card){
            this.stopMenu();this.restoreAnchors();
            const target=new URL('/playlist',location.origin),list=new URL(location.href).searchParams.get('list');
            if(list)target.searchParams.set('list',list);
            card.q('.share-link').value=target.href;card.q('.share-status').textContent='';card.q('.share-sheet').showPopover();
        }
        activate(source,control,anchor){
            if(anchor&&source instanceof HTMLElement&&typeof source.showPopover==='function'){
                this.restoreAnchors();
                const properties=['position','inset','left','top','width','height','min-width','max-width','min-height','max-height','margin','padding','box-sizing','opacity','visibility','pointer-events'];
                this.anchors.set(source,{popover:source.getAttribute('popover'),aria:source.getAttribute('aria-hidden'),tabindex:source.getAttribute('tabindex'),style:source.getAttribute('style'),properties:properties.map(name=>[name,source.style.getPropertyValue(name),source.style.getPropertyPriority(name)])});
                const rect=control.getBoundingClientRect();
                source.setAttribute('popover','manual');source.setAttribute('aria-hidden','true');source.tabIndex=-1;source.setAttribute('data-myt-playlist-action-anchor','');
                const values={position:'fixed',inset:'auto',left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',height:rect.height+'px','min-width':'0','max-width':'none','min-height':'0','max-height':'none',margin:'0',padding:'0','box-sizing':'border-box',opacity:'0',visibility:'visible','pointer-events':'none'};
                for(const [name,value]of Object.entries(values))source.style.setProperty(name,value,'important');
                try{source.showPopover();}catch{}
            }
            if(control.dataset.action==='menu')this.startMenu(control);else this.stopMenu();
            source.click();
            if(this.menuControl)this.positionMenus();
        }
        startMenu(control){
            this.stopMenu();this.menuControl=control;this.menuStyles=new Map();this.menuOpened=false;
            control.setAttribute('aria-haspopup','menu');
            this.menuObserver=new MutationObserver(()=>this.positionMenus());
            this.menuObserver.observe(document.querySelector('ytd-popup-container')||document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['style','class','hidden','aria-hidden','opened']});
            this.menuTimer=setTimeout(()=>{if(!this.menuOpened)this.stopMenu();},3000);
            this.menuMove=()=>this.positionMenus();
            this.menuDismiss=event=>{
                if(event.type==='keydown'){if(event.key==='Escape')this.stopMenu();return;}
                if(!event.isTrusted)return;
                if(event.composedPath().includes(control))return;
                if([...this.menuStyles.keys()].some(node=>node.contains(event.target)))return;
                this.stopMenu();
            };
            window.addEventListener('resize',this.menuMove);
            document.addEventListener('scroll',this.menuMove,true);
            document.addEventListener('click',this.menuDismiss,true);
            document.addEventListener('keydown',this.menuDismiss,true);
        }
        positionMenus(){
            const control=this.menuControl;if(!control?.isConnected){this.stopMenu();return;}
            const menus=[...document.querySelectorAll('ytd-popup-container ytd-menu-popup-renderer,ytd-popup-container yt-menu-popup-renderer,ytd-popup-container [role="menu"]')].filter(node=>!node.closest('[hidden],[aria-hidden="true"]')&&getComputedStyle(node).visibility!=='hidden'&&node.getBoundingClientRect().width>0&&node.getBoundingClientRect().height>0);
            if(!menus.length){if(this.menuOpened)this.stopMenu();return;}
            this.menuOpened=true;clearTimeout(this.menuTimer);control.setAttribute('aria-expanded','true');
            const rect=control.getBoundingClientRect();
            for(const menu of menus){
                // Polymer can anchor to the hidden native wrapper instead of
                // its button. Position the actual dropdown without moving it.
                const target=menu.closest('tp-yt-iron-dropdown,iron-dropdown')||menu;
                if(this.menuStyles.has(target))continue;
                const properties=['position','inset','left','right','top','bottom','margin','transform','translate','max-width','max-height','overflow','box-sizing','transition'];
                this.menuStyles.set(target,{style:target.getAttribute('style'),properties:properties.map(name=>[name,target.style.getPropertyValue(name),target.style.getPropertyPriority(name)])});
            }
            for(const target of this.menuStyles.keys()){
                const set=(name,value)=>{if(target.style.getPropertyValue(name)!==value||target.style.getPropertyPriority(name)!=='important')target.style.setProperty(name,value,'important');};
                for(const[name,value]of Object.entries({position:'fixed',right:'auto',bottom:'auto',margin:'0',transform:'none',translate:'none','max-width':Math.max(0,innerWidth-16)+'px',overflow:'auto','box-sizing':'border-box',transition:'none'}))set(name,value);
                const width=target.getBoundingClientRect().width,height=target.scrollHeight;
                const below=Math.max(0,innerHeight-rect.bottom-16),above=Math.max(0,rect.top-16),openAbove=height>below&&above>below;
                const available=Math.max(0,openAbove?above:below),shown=Math.min(height,available);
                set('max-height',available+'px');
                set('left',Math.max(8,Math.min(rect.left,innerWidth-width-8))+'px');
                set('top',Math.max(8,openAbove?rect.top-shown-8:rect.bottom+8)+'px');
            }
        }
        stopMenu(){
            clearTimeout(this.menuTimer);this.menuTimer=null;
            this.menuObserver?.disconnect();this.menuObserver=null;
            if(this.menuMove){window.removeEventListener('resize',this.menuMove);document.removeEventListener('scroll',this.menuMove,true);}
            if(this.menuDismiss){document.removeEventListener('click',this.menuDismiss,true);document.removeEventListener('keydown',this.menuDismiss,true);}
            this.menuControl?.setAttribute('aria-expanded','false');
            for(const[node,state]of this.menuStyles||[]){for(const[name,value,priority]of state.properties){if(value)node.style.setProperty(name,value,priority);else node.style.removeProperty(name);}if(state.style===null&&!node.style.length)node.removeAttribute('style');}
            this.menuStyles?.clear();this.menuControl=null;this.menuMove=null;this.menuDismiss=null;
        }
        restoreAnchors(){for(const [node,state]of this.anchors){try{if(node.matches(':popover-open'))node.hidePopover();}catch{}if(state.popover===null)node.removeAttribute('popover');else node.setAttribute('popover',state.popover);if(state.aria===null)node.removeAttribute('aria-hidden');else node.setAttribute('aria-hidden',state.aria);if(state.tabindex===null)node.removeAttribute('tabindex');else node.setAttribute('tabindex',state.tabindex);for(const[name,value,priority]of state.properties){if(value)node.style.setProperty(name,value,priority);else node.style.removeProperty(name);}if(state.style===null&&!node.style.length)node.removeAttribute('style');node.removeAttribute('data-myt-playlist-action-anchor');}this.anchors.clear();}
        restoreRow(row,state){state.card.host.remove();row.removeAttribute('data-myt-playlist-row');for(const part of state.parts)part.removeAttribute('data-myt-playlist-native-row-part');}
        destroy(){this.leaveData();this.menu?.remove();this.moreObserver.disconnect();clearTimeout(this.statusTimer);document.removeEventListener('minimal-youtube:page-model-updated',this.modelChanged);document.removeEventListener('minimal-youtube:page-model-action-result',this.actionResult);this.stopMenu();this.source.removeEventListener('load',this.load,true);this.restoreAnchors();this.host.remove();for(const[row,state]of this.rows)this.restoreRow(row,state);this.rows.clear();}
    }
    globalThis.MinimalYouTubePlaylist=Playlist;
})();
