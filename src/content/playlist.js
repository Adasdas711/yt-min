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
    const summaryCSS=`${shared}.panel{padding:24px;min-height:calc(100dvh - 120px);background:var(--myt-soft,#24242a);border:1px solid var(--myt-border);border-radius:24px}.cover{max-width:360px;margin-bottom:20px;border-radius:16px}h1{font-size:26px;font-weight:700;line-height:1.2;letter-spacing:-.65px;overflow-wrap:anywhere}.owner{display:flex;align-items:center;gap:9px;margin:16px 0 10px;min-width:0}.owner img{width:28px;height:28px;border-radius:50%;object-fit:cover}.owner a{min-width:0;overflow-wrap:anywhere}.owner a:hover{text-decoration:underline}.stats{font-size:14px;line-height:1.6;color:var(--myt-muted)}.description{margin-top:18px;font:14px/1.65 "SFMono-Regular",Menlo,Consolas,monospace;color:var(--myt-muted);overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:4;overflow:hidden}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}.actions button{min-height:40px;padding:9px 14px;font-weight:600}.actions .menu{width:40px;padding:0}@media(max-width:900px){.panel{min-height:0}}@media(min-width:601px) and (max-width:900px){.panel{display:grid;grid-template-columns:240px minmax(0,1fr);gap:0 24px}.cover{grid-column:1;grid-row:1/6;align-self:start;width:100%;margin:0}h1,.owner,.stats,.description,.actions{grid-column:2}}@media(max-width:600px){.panel{padding:20px}}`;
    const rowCSS=`${shared}:host{display:grid;grid-template-columns:24px 168px minmax(0,1fr) 36px;align-items:center;gap:14px;padding:12px;border:1px solid var(--myt-border);border-radius:20px;background:var(--myt-surface,#19191d)}:host(:hover),:host(:focus-within){background:var(--myt-soft)}:host([data-current]){border-color:var(--myt-accent)}.index{font-size:13px;text-align:center;color:var(--myt-muted);font-variant-numeric:tabular-nums}h3{font-size:17px;font-weight:600;line-height:1.4}.title{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere}.metadata{margin-top:5px}.duration{position:absolute;right:5px;bottom:5px;padding:1px 5px;border-radius:5px;background:#000b;color:white;font-size:11px;font-variant-numeric:tabular-nums}.menu{width:36px;height:36px;padding:0;border:0;background:transparent;color:var(--myt-muted)}.meta{min-width:0}@media(max-width:600px){:host{grid-template-columns:112px minmax(0,1fr) 28px;gap:10px;padding:10px;border-radius:18px}.index{display:none}h3{font-size:15px}.cover{border-radius:10px}.menu{width:28px}}`;
    class Card {
        constructor(owner,summary=false){
            this.owner=owner;this.host=document.createElement('div');this.host.dataset.mytOwnedPlaylistCard=summary?'summary':'video';
            if(summary)this.host.id='myt-playlist-summary';
            this.shadow=this.host.attachShadow({mode:'open'});
            this.shadow.innerHTML=summary?`<style>${summaryCSS}</style><section class="panel"><a class="cover" data-action="play"><img alt="" decoding="async"></a><h1></h1><div class="owner"><img alt="" decoding="async"><a data-action="channel"></a></div><p class="stats"></p><p class="description"></p><div class="actions"><button data-action="play">${icon('play')}<span>Play all</span></button><button data-action="shuffle">${icon('shuffle')}<span>Shuffle</span></button><button class="menu" data-action="share" aria-label="Share">${icon('share')}</button><button class="menu" data-action="menu" aria-label="Playlist actions">${icon('menu')}</button></div></section>`:`<style>${rowCSS}</style><span class="index"></span><a class="cover" data-action="play"><img alt="" loading="lazy" decoding="async"><span class="duration"></span></a><div class="meta"><h3><a class="title" data-action="play"></a></h3><p class="metadata"></p></div><button class="menu" data-action="menu" aria-label="Video actions">${icon('menu')}</button>`;
            this.summary=summary;this.q=s=>this.shadow.querySelector(s);
            this.shadow.addEventListener('click',event=>{
                const control=event.target.closest('[data-action]');if(!control)return;
                event.stopPropagation();
                if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
                const source=this.actions?.[control.dataset.action];
                if(source?.isConnected){event.preventDefault();this.owner.activate(source,control,['menu','share'].includes(control.dataset.action));}
            });
            this.q('.cover img').onerror=()=>{this.q('.cover img').hidden=true;};
        }
        text(selector,value){const node=this.q(selector);if(node.textContent!==value)node.textContent=value;}
        update(data){
            this.actions=data.actions;
            const signature=JSON.stringify([data.title,data.author,data.stats,data.image,data.avatar,data.description,data.index,data.duration,data.current,Object.entries(data.actions).map(([kind,node])=>[kind,!!node,node?.getAttribute('href'),!!node?.matches(':disabled,[aria-disabled="true"]')])]);
            if(this.signature===signature)return;this.signature=signature;
            const img=this.q('.cover img');if(img.getAttribute('src')!==data.image){if(data.image)img.src=data.image;else img.removeAttribute('src');img.hidden=!data.image;}
            this.q('.cover').hidden=this.summary&&!data.image;
            this.text(this.summary?'h1':'.title',data.title);
            if(this.summary){const owner=this.q('.owner a');if(owner.textContent!==data.author)owner.textContent=data.author;this.q('.owner').hidden=!data.author;}
            this.text(this.summary?'.stats':'.metadata',data.stats);this.q(this.summary?'.stats':'.metadata').hidden=!data.stats;
            for(const link of this.shadow.querySelectorAll('a[data-action]')){
                const href=url(data.actions[link.dataset.action]?.href||'');
                if(href&&link.getAttribute('href')!==href)link.href=href;else if(!href)link.removeAttribute('href');
            }
            for(const button of this.shadow.querySelectorAll('button[data-action]')){
                const source=data.actions[button.dataset.action];button.hidden=!source;
                const disabled=Boolean(source?.matches(':disabled,[aria-disabled="true"]'));if(button.disabled!==disabled)button.disabled=disabled;
            }
            if(this.summary){
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
        }
        static rows(list){return [...list.querySelectorAll(rowSelector)].filter(row=>!row.parentElement.closest(rowSelector)&&!row.closest('[hidden],[aria-hidden="true"]')&&row.style.display!=='none');}
        setSource(source){if(source===this.source)return;this.stopMenu();this.restoreAnchors();this.source.removeEventListener('load',this.load,true);this.source=source;source.addEventListener('load',this.load,true);}
        readSummary(){
            const source=this.source,authorLink=channel(source),author=clean(authorLink);
            const title=clean(source.querySelector('h1,#title,.dynamic-text-view-model-wiz__h1'))||document.title.replace(/^\(\d+\)\s*| - YouTube$/g,'')||'Playlist';
            const thumbnail=source.querySelector('ytd-thumbnail img,ytd-playlist-video-thumbnail-renderer img,ytd-hero-playlist-thumbnail-renderer img,yt-thumbnail-view-model img,#hero-image img,.thumbnail-wrapper img')||source.querySelector('img');
            const stats=clean(source.querySelector('#stats,.metadata-stats,.ytContentMetadataViewModelMetadataRow,.yt-content-metadata-view-model__metadata-row,yt-content-metadata-view-model'));
            const descriptionNode=source.querySelector('#description,yt-description-preview-view-model');
            const controls=[...source.querySelectorAll('button,a[role="button"],yt-icon-button')].map(node=>node.querySelector('button')||node).filter(node=>!descriptionNode?.contains(node));
            const find=pattern=>controls.find(node=>pattern.test(label(node)));
            const play=find(/play all|watch all|воспроизвести|смотреть все/iu)||source.querySelector('a[href*="/watch?"]')||this.list.querySelector('a[href*="/watch?"]');
            return {title,author,avatar:image([...source.querySelectorAll('a[href] img')].find(img=>img.closest('a').href===authorLink?.href)),image:image(thumbnail)||image(this.list.querySelector('img')),stats,description:clean(descriptionNode),actions:{play,channel:authorLink,shuffle:find(/shuffle|перемешать/iu),share:find(/share|поделиться/iu),menu:find(/actions|menu|действия|ещё|еще|^more$|^[⋯⋮…]$/iu)}};
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
                return clean(copy).split(/[·•]/).map(text=>text.trim()).filter(text=>text&&text!==author).join(' · ');
            }).filter(Boolean))].join(' · ');
            const duration=[...row.querySelectorAll('ytd-thumbnail-overlay-time-status-renderer,.badge-shape-wiz__text,.yt-badge-shape__text,.ytThumbnailOverlayBadgeViewModelBadgeText')].map(clean).find(value=>/^\d{1,3}:\d{2}(?::\d{2})?$/.test(value))||'';
            return {title:clean(row.querySelector('#video-title,#video-title-link,h3'))||clean(play)||'Unavailable video',author:clean(authorLink),stats:metadata,image:image(row.querySelector('ytd-thumbnail img,yt-thumbnail-view-model img,img'))||fallback,duration,index:clean(row.querySelector('#index-container,#index')).match(/\d+/)?.[0]||String(index+1),current:row.hasAttribute('selected')&&row.getAttribute('selected')!=='false'||row.getAttribute('aria-current')==='true',actions:{play,channel:authorLink,menu:row.querySelector('#menu button,ytd-menu-renderer button,button[aria-label*="actions" i]')}};
        }
        sync(){
            this.card.update(this.readSummary());
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
        destroy(){this.stopMenu();this.source.removeEventListener('load',this.load,true);this.restoreAnchors();this.host.remove();for(const[row,state]of this.rows)this.restoreRow(row,state);this.rows.clear();}
    }
    globalThis.MinimalYouTubePlaylist=Playlist;
})();
