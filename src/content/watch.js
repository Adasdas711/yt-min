/* Isolated watch UI. Native player/comments stay in their original DOM parents;
   manual popovers expose only their interactive rectangles above our canvas. */
(() => {
    "use strict";
    const css = `
:host { all:initial!important;position:fixed!important;inset:0!important;width:100%!important;height:100%!important;min-width:0!important;max-width:none!important;max-height:none!important;margin:0!important;padding:0!important;border:0!important;display:block!important;isolation:isolate!important;filter:none!important;transform:none!important;box-shadow:none!important;overflow:hidden!important;background:var(--bg)!important;color:var(--ink)!important;font:16px/1.6 Arial,sans-serif!important;color-scheme:only light!important; --bg:#f9f9fb; --surface:#fff; --soft:#f0f0f4; --ink:#18181b; --muted:#71717c; --border:#e3e3e9; --link:#315dca; font:16px/1.6 Arial,sans-serif; color:var(--ink); }
:host([dark]) { color-scheme:only dark!important; --bg:#101012; --surface:#19191d; --soft:#24242b; --ink:#f4f4f5; --muted:#a0a0ac; --border:#303039; --link:#b6caff; }
:host::before,:host::after { content:none!important;display:none!important; }
*,*::before,*::after { box-sizing:border-box; } [hidden] { display:none!important; }
.viewport { position:fixed;inset:0;overflow:auto;overscroll-behavior:contain;scroll-behavior:auto;background:var(--bg);color:var(--ink);scrollbar-color:var(--border) var(--bg); }
a { color:var(--link);text-decoration:none;overflow-wrap:anywhere; } a:hover { text-decoration:underline; }
button,input { font:inherit; } button,a,input { -webkit-tap-highlight-color:transparent; }
button { display:inline-flex;align-items:center;justify-content:center;gap:9px;min-height:44px;padding:10px 17px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);font-size:16px;font-weight:500;line-height:1.3;cursor:pointer;white-space:nowrap;flex-shrink:0; }
button:hover { background:var(--soft); } button:disabled { opacity:.55;cursor:default; }
:focus-visible { outline:2px solid var(--muted);outline-offset:3px; }
svg { width:20px;height:20px;flex:none; } h1,h2,p { margin:0; } h2 { font-size:22px;font-weight:600;letter-spacing:-.4px;line-height:1.4; }
.header { position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:center;gap:24px;height:76px;padding:12px 24px;background:var(--bg); }
.brand { display:flex;align-items:center;gap:10px;color:var(--ink);flex:none;text-decoration:none!important; }
.brand svg { width:40px;height:30px;color:#ff0033; }.brand span { font-size:25px;font-weight:700;letter-spacing:-1px; }
.search { display:flex;align-items:center;width:min(640px,100%);height:48px;border:1px solid var(--border);border-radius:15px;background:var(--surface);padding:0 16px; }
.search:focus-within { border-color:var(--muted); }.search input { width:100%;min-width:0;height:100%;padding:0;border:0;outline:none;background:transparent;color:var(--ink);font-size:17px;line-height:normal; }
.search input::placeholder { color:var(--muted); }.search button { min-height:30px;width:30px;padding:0;border:0;background:transparent;font-size:25px; }
main { max-width:1328px;margin:0 auto;padding:20px 24px 72px; }
.layout { display:grid;grid-template-columns:minmax(0,1fr);gap:28px; }.layout.has-sidecar { grid-template-columns:minmax(0,1fr) 340px; }
.media { width:100%;aspect-ratio:16/9;background:#000;border-radius:18px; }.sidecar { min-height:540px;border-radius:16px;background:var(--surface); }
.details { max-width:960px;margin:28px auto 0;min-width:0; } h1 { font-size:28px;line-height:1.35;font-weight:650;letter-spacing:-.6px;overflow-wrap:anywhere; }
.meta-row { display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px;margin:22px 0 28px; }
.owner { display:flex;align-items:center;gap:12px;min-width:0;flex-wrap:wrap; }.owner-link { display:flex;align-items:center;gap:12px;color:var(--ink);min-width:0; }.owner img { width:46px;height:46px;border-radius:50%;object-fit:cover;flex:none; }.owner-name { font-size:17px;font-weight:600; }.owner small { display:block;color:var(--muted);font-size:14px; }
.owner .primary { min-height:36px;height:36px;padding:0 14px;border-radius:10px;font-size:14px;line-height:1.25; }
.actions { display:flex;align-items:center;gap:9px;flex-wrap:wrap;min-width:0; }.primary { background:var(--ink);color:var(--bg);border-color:transparent; }.primary:hover { opacity:.9;background:var(--ink); }
.more-actions { display:flex; }.more-popup { position:fixed;inset:auto;margin:0;padding:6px;width:min(260px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;border:1px solid var(--border);border-radius:14px;background:var(--surface);color:var(--ink);box-shadow:0 12px 36px #0002; }.more-popup::backdrop { background:transparent; }.more-popup button { display:flex;width:100%;justify-content:flex-start;white-space:normal;text-align:left;border:0;background:transparent; }.more-popup button:hover,.more-popup button:focus-visible { background:var(--soft); }.more-popup button:focus-visible { outline-offset:-2px; }
#myt-comments-toggle { display:inline-flex;align-items:center;gap:9px; }.description { border:1px solid var(--border);border-radius:20px;background:var(--surface);padding:28px; }
.stats { font-size:14px;font-weight:500;color:var(--muted);margin-bottom:16px; }.prose { font-size:17px;line-height:1.8;overflow-wrap:anywhere;white-space:pre-wrap; }.prose p { margin:0 0 18px; }.prose ul,.prose ol { padding-left:24px; }.prose:not(.expanded) { max-height:9em;overflow:hidden; }.expand { margin-top:18px;background:transparent; }
.section { margin-top:32px; }.section-head { display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px; }.hint { color:var(--muted);font-size:15px;line-height:1.6; }
.chapter-list { display:flex;flex-flow:row nowrap;gap:12px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x proximity;scrollbar-color:var(--border) transparent;padding-bottom:12px; }.chapter { flex:0 0 300px;scroll-snap-align:start;display:grid;grid-template-columns:64px minmax(0,1fr) 18px;gap:16px;text-align:left;white-space:normal;justify-content:initial;min-height:76px;padding:18px 20px;border-color:transparent;background:var(--surface);border-radius:14px; }
.chapter:hover { background:var(--soft); }.chapter[aria-current=true] { background:var(--soft);border-color:var(--border); }.chapter time { font-size:15px;font-variant-numeric:tabular-nums;color:var(--muted); }.chapter-title { min-width:0;overflow-wrap:anywhere;font-size:18px;line-height:1.45;font-weight:500; }.chapter svg { width:18px;color:var(--muted); }
.people { display:flex;flex-wrap:wrap;gap:12px; }.person { display:flex;align-items:center;gap:14px;padding:16px 20px;border:1px solid var(--border);border-radius:14px;background:var(--surface);color:var(--ink);font-size:17px;font-weight:500; }.person img { width:48px;height:48px;border-radius:50%;object-fit:cover; }
.transcript-card { padding:26px;border:1px solid var(--border);border-radius:20px;background:var(--surface); }.transcript-intro { display:flex;align-items:center;gap:16px; }.transcript-icon { display:grid;place-items:center;width:48px;height:48px;flex:none;border-radius:14px;background:var(--soft);color:var(--ink); }.transcript-copy { flex:1;min-width:0; }.transcript-copy h2 { margin-bottom:5px; }.transcript-head { display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap; }
.transcript-content { margin-top:24px;padding-top:24px;border-top:1px solid var(--border); }.transcript-search { width:100%;height:46px;padding:0 14px;border:1px solid var(--border);border-radius:11px;background:var(--bg);color:var(--ink);font-size:16px; }.segments { display:flex;flex-direction:column;gap:5px;max-height:520px;overflow:auto;margin-top:16px;scrollbar-color:var(--border) transparent; }.segment { display:grid;grid-template-columns:70px minmax(0,1fr);gap:16px;align-items:start;justify-content:initial;text-align:left;white-space:normal;padding:14px 12px;border:0;background:transparent;font-size:16px;font-weight:400;line-height:1.65; }.segment span { min-width:0;overflow-wrap:anywhere; }.segment time { color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums; }.segment:hover { background:var(--soft); }.transcript-status { padding:20px 0;color:var(--muted);font-size:16px; }
.socials { display:flex;flex-wrap:wrap;gap:10px; }.social { display:inline-flex;align-items:center;justify-content:center;gap:12px;min-height:44px;padding:10px 16px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);font-size:16px;line-height:1.4; }.social:hover { background:var(--soft);text-decoration:none; }
.comments { height:600px;margin-top:20px;border:1px solid var(--border);border-radius:16px;background:var(--surface); }.comments-section { margin-top:32px; }
.section,.comments-section { scroll-margin-top:96px; }
@media(max-width:600px) { .section,.comments-section { scroll-margin-top:82px; } }
:host([theater]) main { max-width:none; }:host([theater]) .details { max-width:960px; }:host([theater]) .media { max-height:80vh;aspect-ratio:auto;height:min(75vw,80vh);border-radius:0; }
@media(max-width:900px) { .layout.has-sidecar { grid-template-columns:minmax(0,1fr); }.sidecar { height:440px;min-height:0; } h1 { font-size:25px; } main { padding-inline:20px; } }
@media(max-width:600px) { .header { height:66px;padding:10px 16px;gap:14px; }.brand svg { width:32px;height:24px; }.brand span { display:none; }.search { height:44px; }.search input { font-size:16px; } main { padding:12px 16px 48px; }.media { border-radius:12px; }.details { margin-top:24px; } h1 { font-size:23px; }.meta-row { gap:16px; }.actions { width:100%; }.actions button { flex:1 1 auto; }.description { padding:22px 20px;border-radius:16px; }.prose { font-size:16px;line-height:1.8; }.chapter { flex-basis:280px;grid-template-columns:60px minmax(0,1fr) 18px;gap:12px;padding:16px; }.chapter-title { font-size:17px; } h2 { font-size:21px; }.transcript-card { padding:22px 20px; }.transcript-head>button { width:100%; }.transcript-intro { align-items:start; }.segment { grid-template-columns:55px minmax(0,1fr);gap:12px; }.person { width:100%; }.section { margin-top:28px; } }
`;
    const words = {
        ru: { search:"Поиск на YouTube", clear:"Очистить поиск", description:"Описание", more:"Показать полностью", less:"Свернуть", chapters:"Эпизоды", people:"Упомянутые люди", transcript:"Расшифровка видео", transcriptHint:"Читайте текст и переходите к нужному моменту видео.", showTranscript:"Открыть расшифровку", hideTranscript:"Свернуть", find:"Найти в расшифровке", loading:"Загружаем расшифровку…", unavailable:"Текст пока не загрузился. Попробуйте ещё раз.", retry:"Повторить", noResults:"Совпадений нет", socials:"Ссылки канала", comments:"Комментарии", subscribe:"Подписаться", share:"Поделиться", save:"Сохранить", menu:"Ещё", otherActions:"Другие действия", video:"Видео" },
        en: { search:"Search YouTube", clear:"Clear search", description:"Description", more:"Show more", less:"Show less", chapters:"Chapters", people:"Mentioned people", transcript:"Video transcript", transcriptHint:"Read along and jump to any moment in the video.", showTranscript:"Open transcript", hideTranscript:"Collapse", find:"Search transcript", loading:"Loading transcript…", unavailable:"The transcript has not loaded yet. Please try again.", retry:"Try again", noResults:"No matches", socials:"Channel links", comments:"Comments", subscribe:"Subscribe", share:"Share", save:"Save", menu:"More", otherActions:"Other actions", video:"Video" }
    };
    const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${({play:'<path d="m9 5 10 7-10 7Z"/>', transcript:'<path d="M5 3h14v18H5Z"/><path d="M8 8h8M8 12h8M8 16h5"/>', arrow:'<path d="m7 17 10-10M7 7h10v10"/>', share:'<path d="m15 4 6 6-6 6v-4C8 12 5 14 3 19c0-8 3-12 12-12Z"/>', save:'<path d="M6 3h12v18l-6-4-6 4Z"/>', menu:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'})[name] || ''}</svg>`;
    const text = element => element?.textContent.replace(/\s+/g," ").trim() || "";
    const seconds = value => {
        const parts = value?.trim().split(":");
        if (!parts?.length || parts.some(part => !/^\d+$/.test(part))) return null;
        return parts.reduce((total,part) => total*60+Number(part),0);
    };
    const safeURL = (value, image=false) => {
        try { if(typeof value!=='string'||!value.trim())return null;const url = new URL(value,location.href); return /^(https?:|mailto:)$/.test(url.protocol) || (image && url.protocol === "data:" && /^data:image\/(?:png|jpeg|webp|gif|svg\+xml);/i.test(value)) ? url.href : null; }
        catch { return null; }
    };
    class WatchView {
        constructor(options) {
            this.options=options; this.native=options.native; this.islands=new Map(); this.fullscreenNodes=new Map(); this.expanded=false; this.transcriptOpen=false; this.signature=""; this.sources=new Map(); this.sequence=0; this.nativePanelState=null;
            this.host=document.createElement("div"); this.host.id="myt-watch"; this.host.setAttribute("popover","manual");
            this.surface=document.createElement("div"); this.shadow=this.surface.attachShadow({mode:"open"});this.host.append(this.surface);
            this.shadow.innerHTML=`<style>${css}</style><div class="viewport"><header class="header"><a class="brand" href="/" aria-label="YouTube"><svg viewBox="0 0 28 20" fill="currentColor" aria-hidden="true"><rect width="28" height="20" rx="6"/><path d="m11 5 8 5-8 5Z" fill="#fff"/></svg><span>YouTube</span></a><form class="search" action="/results" method="get" role="search"><input name="search_query" id="watch-search" autocomplete="off"><button type="button" id="watch-clear" hidden aria-label="Clear">×</button></form></header><main><div class="layout"><div class="media" aria-label="YouTube player"></div><aside class="sidecar" hidden></aside></div><article class="details"><h1 id="watch-title"></h1><div class="meta-row"><div class="owner"></div><div class="actions"></div></div><section class="description" aria-label="Description"><div class="stats"></div><div class="prose" id="watch-description"></div><button class="expand" aria-expanded="false" aria-controls="watch-description"></button></section><section class="section" id="watch-chapters" hidden><div class="section-head"><h2></h2></div><div class="chapter-list"></div></section><section class="section" id="watch-people" hidden><div class="section-head"><h2></h2></div><div class="people"></div></section><section class="section transcript-card" id="watch-transcript" hidden><div class="transcript-head"><div class="transcript-intro"><span class="transcript-icon">${icon('transcript')}</span><div class="transcript-copy"><h2></h2><p class="hint"></p></div></div><button class="transcript-toggle" aria-expanded="false" aria-controls="watch-transcript-content"></button></div><div class="transcript-content" id="watch-transcript-content" hidden><input class="transcript-search" type="search"><div class="segments"></div><p class="transcript-status" role="status"></p><button class="transcript-retry" hidden></button></div></section><section class="section" id="watch-socials" hidden><div class="section-head"><h2></h2></div><div class="socials"></div></section><section class="comments-section" id="watch-comments" hidden><h2></h2><div class="comments"></div></section></article></main></div>`;
            this.q=selector=>this.shadow.querySelector(selector);this.viewport=this.q('.viewport');
            this.q('.expand').onclick=()=>{this.expanded=!this.expanded;const description=this.descriptionData(this.native.querySelector('ytd-watch-metadata,ytd-video-primary-info-renderer,ytd-video-secondary-info-renderer'));(this.expanded?description.expand:description.root?.querySelector('#collapse'))?.click();this.updateExpanded();};
            this.q('.transcript-toggle').onclick=()=>this.toggleTranscript();
            this.q('.transcript-search').oninput=()=>this.renderTranscript();
            this.q('.chapter-list').addEventListener('wheel',event=>{if(!event.deltaX&&event.deltaY&&!event.ctrlKey){const list=event.currentTarget;if(list.scrollWidth>list.clientWidth){const before=list.scrollLeft;list.scrollLeft+=event.deltaY;if(list.scrollLeft!==before)event.preventDefault();}}},{passive:false});
            this.q('.transcript-retry').onclick=()=>this.loadTranscript();
            const input=this.q('#watch-search'),clear=this.q('#watch-clear');
            input.oninput=()=>{clear.hidden=!input.value;};input.onkeydown=event=>{if(event.key==='Escape'){event.preventDefault();input.value='';clear.hidden=true;}};clear.onclick=()=>{input.value="";clear.hidden=true;input.focus();};
            this.q('form').onsubmit=event=>{input.value=input.value.trim();if(!input.value){event.preventDefault();input.focus();}};
            this.shadow.addEventListener('keydown',event=>{if(event.target.matches('input,textarea,[contenteditable],button,a')){if(event.key==='/'&&!event.target.matches('input,textarea,[contenteditable]')){event.preventDefault();input.focus();}event.stopPropagation();}});
            this.shortcut=event=>{if(event.key==='/'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!event.isComposing&&!event.composedPath().some(node=>node instanceof Element&&node.matches('input,textarea,[contenteditable]'))){event.preventDefault();input.focus();}};document.addEventListener('keydown',this.shortcut);
            this.shadow.addEventListener('click',event=>{
                const action=event.target.closest('[data-watch-action],#myt-comments-toggle');
                if(action){
                    this.closeMore();
                    if(action.dataset.watchAction==='transcript')this.toggleTranscript();
                    this.reveal(action.id==='myt-comments-toggle'?'.comments-section':'#watch-transcript');
                    return;
                }
                const control=event.target.closest('[data-source]');if(!control)return;
                if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||event.button>0)return;
                const source=this.sources.get(control.dataset.source);if(!source)return;
                event.preventDefault();
                if(control.hasAttribute('data-seconds')) this.seek(Number(control.dataset.seconds),source);
                else {
                    const inMore=control.closest('.more-popup');
                    this.anchorAction(source,inMore?this.q('.more-toggle'):control);
                    if(inMore)this.closeMore();
                    source.click();
                }
            });
            this.nativeWheel=event=>{
                if(document.fullscreenElement||event.ctrlKey||!event.deltaY||Math.abs(event.deltaX)>Math.abs(event.deltaY))return;
                const path=event.composedPath().filter(node=>node instanceof Element),target=path[0];
                const media=target?.closest('[data-myt-watch-island="media"]'),ownPage=path.includes(this.viewport);
                if(!media&&!ownPage)return;
                if(media&&target.closest('.ytp-settings-menu,.ytp-popup,.ytp-panel,.ytp-volume-area,.ytp-volume-panel,[role="menu"],[role="dialog"],[role="listbox"],[role="slider"]'))return;
                if(ownPage){
                    for(const node of path){
                        if(node===this.viewport)break;
                        if(node.matches('.more-popup,[role="slider"]')||(node.matches('.chapter-list')&&node.scrollWidth>node.clientWidth))return;
                        if(node.scrollHeight>node.clientHeight+1&&/^(auto|scroll)$/.test(getComputedStyle(node).overflowY))return;
                    }
                }
                const unit=event.deltaMode===WheelEvent.DOM_DELTA_PAGE?this.viewport.clientHeight:event.deltaMode===WheelEvent.DOM_DELTA_LINE?20:1;
                const before=this.viewport.scrollTop;this.viewport.scrollBy({top:event.deltaY*unit,behavior:'instant'});
                if(this.viewport.scrollTop!==before){event.preventDefault();event.stopPropagation();this.position();}
            };
            window.addEventListener('wheel',this.nativeWheel,{capture:true,passive:false});
            this.geometry=()=>{this.position();if(this.q('.more-popup')?.matches(':popover-open'))this.positionMore();};
            this.viewport.addEventListener('scroll',()=>{
                if(this.q('.more-popup')?.matches(':popover-open')){
                    const rect=this.q('.more-toggle').getBoundingClientRect();
                    // Opening a focused popover can deliver an already-pending
                    // scroll event. Dismiss only when its anchor actually moved.
                    if(this.moreAnchor&&Math.abs(rect.y-this.moreAnchor.y)>.5)this.closeMore();
                }
                this.position();
            },{passive:true});window.addEventListener('resize',this.geometry);
            this.observer=new ResizeObserver(this.geometry);this.observer.observe(this.q('main'));this.observer.observe(this.q('.media'));
            this.fullscreen=()=>this.syncFullscreen();document.addEventListener('fullscreenchange',this.fullscreen);
            // A shown popover cannot itself enter fullscreen. Release only the
            // player wrapper before YouTube's own click/key handler requests it.
            this.fullscreenIntent=event=>{
                const path=event.composedPath().filter(node=>node instanceof Element),target=path[0];
                const button=event.type==='click'&&target?.closest('.ytp-fullscreen-button');
                const doubleClick=event.type==='dblclick'&&target?.closest('[data-myt-watch-island="media"]')&&!target.closest('button,.ytp-settings-menu,.ytp-panel');
                const shortcut=event.type==='keydown'&&event.key?.toLowerCase()==='f'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!path.some(node=>node.matches('input,textarea,[contenteditable],button,a,[role="menu"]'));
                if(!document.fullscreenElement&&(button||doubleClick||shortcut))this.prepareFullscreen();
            };
            for(const type of ['click','dblclick','keydown'])window.addEventListener(type,this.fullscreenIntent,true);
            this.fullscreenError=()=>this.resumeFullscreen();document.addEventListener('fullscreenerror',this.fullscreenError);
            this.sourceLoad=()=>{if(this.host.isConnected&&this.options.video!==undefined)this.sync(this.options);};this.native.addEventListener('load',this.sourceLoad,true);
            this.videoTime=()=>this.updateCurrentChapter();this.media=this.native.querySelector('video');this.media?.addEventListener('timeupdate',this.videoTime);
            document.documentElement.append(this.host);document.documentElement.dataset.mytWatchUi="";this.native.dataset.mytWatchSource="";
            if(document.fullscreenElement)this.syncFullscreen();else this.open(this.host);
        }
        open(node) { if(node.isConnected&&!node.matches(':popover-open')) { try{node.showPopover();}catch{} } }
        key(node) { const id=String(++this.sequence);this.sources.set(id,node);return id; }
        node(tag,className,value) {const node=document.createElement(tag);if(className)node.className=className;if(value)node.textContent=value;return node;}
        button(label,source,iconName) {const node=this.node('button','',label);node.type='button';if(iconName)node.insertAdjacentHTML('afterbegin',icon(iconName));if(source)node.dataset.source=this.key(source);return node;}
        reveal(selector) {
            const section=this.q(selector);if(!section||section.hidden)return;
            section.scrollIntoView({behavior:'instant',block:'start'});this.position();
            const title=section.querySelector('h2');if(title){title.tabIndex=-1;title.focus({preventScroll:true});}
        }
        prepareFullscreen() {
            if(this.fullscreenPending)return;
            const player=this.nativePlayer();if(!player)return;
            this.fullscreenPending=true;this.restore(player);
            clearTimeout(this.fullscreenTimer);
            this.fullscreenTimer=setTimeout(()=>this.resumeFullscreen(),600);
        }
        resumeFullscreen() {
            clearTimeout(this.fullscreenTimer);this.fullscreenPending=false;
            if(!document.fullscreenElement&&this.host.isConnected){this.restoreFullscreenLayout();this.open(this.host);this.sync(this.options);}
        }
        syncFullscreen() {
            clearTimeout(this.fullscreenTimer);this.fullscreenPending=false;
            if(document.fullscreenElement){
                this.closeMore();
                for(const[node,state]of this.islands){
                    if(state.kind==='media')this.restore(node);
                    else if(node.matches(':popover-open'))node.hidePopover();
                }
                if(this.host.matches(':popover-open'))this.host.hidePopover();
                this.updateFullscreenLayout();
            }else this.resumeFullscreen();
        }
        restoreFullscreenLayout() {
            for(const[node,original]of this.fullscreenNodes){
                if(original===null)node.removeAttribute('data-myt-fullscreen-part');
                else node.setAttribute('data-myt-fullscreen-part',original);
            }
            this.fullscreenNodes.clear();
        }
        updateFullscreenLayout() {
            const fullscreen=document.fullscreenElement;
            if(!fullscreen)return;
            const video=fullscreen.matches('video')?fullscreen:(fullscreen.querySelector('video.html5-main-video')||fullscreen.querySelector('video'));
            if(!video)return;
            const wanted=new Map([[video,'video']]);
            // Repair only the chain that sizes the active video. Cached native
            // inline sizes can otherwise leave a fullscreen player painting black.
            if(video!==fullscreen)for(let node=video.parentElement;node;node=node.parentElement){
                wanted.set(node,'container');if(node===fullscreen)break;
            }
            let changed=false;
            for(const[node,original]of this.fullscreenNodes)if(!wanted.has(node)){
                if(original===null)node.removeAttribute('data-myt-fullscreen-part');
                else node.setAttribute('data-myt-fullscreen-part',original);
                this.fullscreenNodes.delete(node);changed=true;
            }
            for(const[node,kind]of wanted){
                if(!this.fullscreenNodes.has(node))this.fullscreenNodes.set(node,node.getAttribute('data-myt-fullscreen-part'));
                if(node.getAttribute('data-myt-fullscreen-part')!==kind){node.setAttribute('data-myt-fullscreen-part',kind);changed=true;}
            }
            if(changed)this.resizeNativePlayer();
        }
        resizeNativePlayer() {
            cancelAnimationFrame(this.resizeFrame);
            this.resizeFrame=requestAnimationFrame(()=>{
                if(!this.host.isConnected)return;
                window.dispatchEvent(new Event('resize'));
                this.native.dispatchEvent(new CustomEvent('yt-resize',{bubbles:true,composed:true}));
            });
        }
        closeMore(focus=false) {
            const popup=this.q('.more-popup');
            if(popup?.matches(':popover-open'))popup.hidePopover();
            if(focus)this.q('.more-toggle')?.focus();
        }
        positionMore(popup=this.q('.more-popup')) {
            const toggle=this.q('.more-toggle');
            if(!popup||!toggle)return;
            const rect=toggle.getBoundingClientRect();
            this.moreAnchor={x:rect.x,y:rect.y};
            const width=Math.min(260,window.innerWidth-32);
            popup.style.left=Math.max(16,Math.min(rect.right-width,window.innerWidth-width-16))+'px';
            const height=popup.offsetHeight||120;
            const below=window.innerHeight-rect.bottom-24;
            const above=rect.top-24;
            const openAbove=height>below&&above>below;
            popup.style.maxHeight=Math.max(44,openAbove?above:below)+'px';
            popup.style.top=openAbove?'auto':rect.bottom+8+'px';
            popup.style.bottom=openAbove?window.innerHeight-rect.top+8+'px':'auto';
        }
        moreActions(share,nativeMenu) {
            const group=this.node('div','more-actions');
            const toggle=this.button(this.copy.menu,null,'menu');
            toggle.className='more-toggle';toggle.id='watch-more-toggle';
            toggle.setAttribute('popovertarget','watch-more-menu');
            toggle.setAttribute('aria-controls','watch-more-menu');
            toggle.setAttribute('aria-haspopup','menu');toggle.setAttribute('aria-expanded','false');
            const popup=this.node('div','more-popup');popup.id='watch-more-menu';
            popup.setAttribute('popover','auto');popup.setAttribute('role','menu');
            popup.setAttribute('aria-labelledby',toggle.id);
            const comments=this.options.commentsButton;
            if(comments){comments.setAttribute('role','menuitem');comments.setAttribute('aria-controls','watch-comments');comments.tabIndex=-1;popup.append(comments);}
            if(this.transcriptAvailable){const transcript=this.button(this.copy.transcript,null,'transcript');transcript.className='transcript-menu-toggle';transcript.dataset.watchAction='transcript';transcript.setAttribute('role','menuitem');transcript.setAttribute('aria-controls','watch-transcript');transcript.setAttribute('aria-expanded',String(this.transcriptOpen));transcript.tabIndex=-1;popup.append(transcript);}
            if(share){const item=this.button(this.copy.share,share,'share');item.setAttribute('role','menuitem');item.tabIndex=-1;popup.append(item);}
            if(nativeMenu){const other=this.button(this.copy.otherActions,nativeMenu,'menu');other.setAttribute('role','menuitem');other.tabIndex=-1;popup.append(other);}
            popup.firstElementChild.autofocus=true;
            popup.addEventListener('beforetoggle',event=>{if(event.newState==='open')this.positionMore(popup);});
            popup.addEventListener('toggle',()=>{const open=popup.matches(':popover-open');toggle.setAttribute('aria-expanded',String(open));if(open)this.positionMore(popup);});
            popup.addEventListener('keydown',event=>{
                const items=[...popup.querySelectorAll('button')],index=items.indexOf(this.shadow.activeElement);
                let next;
                if(event.key==='ArrowDown')next=(index+1)%items.length;
                else if(event.key==='ArrowUp')next=(index+items.length-1)%items.length;
                else if(event.key==='Home')next=0;
                else if(event.key==='End')next=items.length-1;
                else if(event.key==='Escape'){event.preventDefault();this.closeMore(true);}
                else if(event.key==='Tab')this.closeMore();
                if(next!==undefined){event.preventDefault();items[next].focus();}
            });
            group.append(toggle,popup);return group;
        }
        link(source,className,label) {const node=this.node('a',className,label);const href=safeURL(source.href||source.getAttribute('href'));if(href){node.href=href;node.dataset.source=this.key(source);}return node;}
        image(source) {
            if (!source) return null;
            const values = [source.currentSrc, source.getAttribute('src'), source.getAttribute('data-src'), source.getAttribute('data-thumb')];
            if (source.srcset && !source.srcset.startsWith('data:')) values.push(...source.srcset.split(',').map(part => part.trim().split(/\s+/)[0]).reverse());
            const urls = [...new Set(values.map(value => safeURL(value, true)).filter(Boolean))];
            if (!urls.length) return null;
            const node = this.node('img');
            node.alt = ''; node.decoding = 'async'; node.referrerPolicy = source.referrerPolicy;
            node.onerror = () => { if (urls.length) node.src = urls.shift(); else node.remove(); };
            node.src = urls.shift();
            return node;
        }
        channelOwner(metadata) {
            const owner = metadata?.querySelector('ytd-video-owner-renderer, #owner') || this.native.querySelector('ytd-video-owner-renderer');
            if (!owner) return {};
            const nameNode = owner.querySelector('ytd-channel-name #text a, #channel-name #text a, ytd-channel-name a, #channel-name a, #channel-name, ytd-channel-name, #text');
            const nameLink = nameNode?.matches('a[href]') ? nameNode : nameNode?.querySelector('a[href]');
            const link = nameLink || owner.querySelector('a[href]');
            const clean = nameNode?.cloneNode(true);
            clean?.querySelectorAll('tp-yt-paper-tooltip, yt-tooltip, [role="tooltip"], [hidden], [aria-hidden="true"], yt-icon, yt-icon-shape').forEach(node => node.remove());
            const name = text(clean) || text(link);
            const images = [...owner.querySelectorAll('#avatar img, #avatar-section img, #channel-avatar img, yt-avatar-shape img, img')];
            const avatar = images.find(img => img.closest('#avatar, #avatar-section, #channel-avatar, yt-avatar-shape') && (img.naturalWidth || img.getAttribute('src') || img.getAttribute('data-src'))) || images.find(img => img.naturalWidth > 1) || images[0];
            return { owner, link, name, avatar };
        }
        descriptionData(metadata) {
            const root = this.native.querySelector('ytd-watch-metadata #description, ytd-video-secondary-info-renderer #description, ytd-video-description-body-renderer, ytd-structured-description-content-renderer');
            const scope = root || metadata;
            if (!scope) return {};
            const selectors = ['#attributed-description-text', '#description-inline-expander #expanded', '#expanded', 'ytd-video-description-body-renderer', '#attributed-description-container', '#description-text', '#attributed-snippet-text', '#snippet'];
            let body;
            for (const selector of selectors) {
                const candidate = scope.matches(selector) ? scope : scope.querySelector(selector);
                if (candidate && text(candidate)) { body = candidate; break; }
            }
            const expand = scope.querySelector('#expand, #more, [data-expander]');
            return { root, body: body || root, expand };
        }
        renderDescription(data) {
            const prose = this.q('.prose');
            prose.replaceChildren();
            if (data.body) this.copyProse(data.body, prose, true);
            this.q('.description').hidden = !data.root && !prose.textContent.trim();
            this.q('.description').setAttribute('aria-label',this.copy.description);
            this.q('.stats').textContent = this.statsText(data.root);
            this.q('.expand').hidden = prose.textContent.trim().length < 220 && !data.expand;
            this.updateExpanded();
        }
        statsText(root) {
            const info = root?.querySelector('#info-container, #info') || this.native.querySelector('ytd-watch-info-text #info, ytd-video-primary-info-renderer #info, #info-strings');
            const semantic = node => {
                if (node.nodeType === Node.TEXT_NODE) return node.data.trim();
                if (!(node instanceof Element) || node.matches('tp-yt-paper-tooltip, yt-tooltip, [role="tooltip"], [aria-hidden="true"]') || (node !== info && node.matches('button, [role="button"]'))) return '';
                const label = node.getAttribute('aria-label') || node.getAttribute('aria-valuetext');
                if (label) return label;
                // A rolling digit contains 0..9 for animation, not the count.
                if (/rolling.?number|animated.?rolling/i.test(node.localName + ' ' + node.getAttribute('class'))) {
                    return node.getAttribute('data-value') || node.getAttribute('value') || node.getAttribute('title') || '';
                }
                return [...node.childNodes].map(semantic).filter(Boolean).join(' ');
            };
            const readable = info ? semantic(info).replace(/\s+/g, ' ').trim() : '';
            const viewMatch = readable.match(/\d[\d\s.,]*\s*(?:(?:тыс\.?|млн|млрд|[kmb])\s*)?(?:просмотр[а-яё]*|views?)/iu);
            let views = viewMatch?.[0].trim() || readable.match(/no views|нет просмотров|без просмотров/iu)?.[0] || '';
            if (views.replace(/\D/g, '').length > 18) views = '';
            const expected = this.options.video;
            const localMeta = selector => this.native.querySelector(selector);
            const canonical = document.querySelector('link[rel="canonical"]');
            let sameVideo = false;
            try { sameVideo = Boolean(expected && canonical && new URL(canonical.href).searchParams.get('v') === expected); } catch {}
            const meta = selector => localMeta(selector) || (sameVideo ? document.querySelector(selector) : null);
            if (!views) {
                const value = meta('meta[itemprop="interactionCount"], meta[itemprop="viewCount"]')?.content || '';
                const number = value.match(/^(?:UserPlays:)?(\d{1,16})$/)?.[1];
                if (number && Number.isSafeInteger(Number(number))) {
                    const count = Number(number), ru = this.options.language === 'ru';
                    const suffix = ru ? ({one:'просмотр',few:'просмотра',many:'просмотров',other:'просмотров'}[new Intl.PluralRules('ru').select(count)]) : (count === 1 ? 'view' : 'views');
                    views = new Intl.NumberFormat(ru ? 'ru-RU' : 'en-US').format(count) + ' ' + suffix;
                }
            }
            const relative = readable.match(/\d+\s*(?:секунд[а-я]*|минут[а-я]*|час[а-я]*|день|дня|дней|недел[а-я]*|месяц[а-я]*|мес\.?|лет|год[а-я]*|г\.)\s+назад|\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago/iu);
            const absolute = readable.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\s+\d{1,2}\s*,?\s*\d{4}|\d{1,2}\s+(?:янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|сент|окт|ноя|дек)[а-яё.]*\s+\d{4}(?:\s*г\.)?/iu);
            let date = relative?.[0] || absolute?.[0] || '';
            if (!date) {
                const published = meta('meta[itemprop="datePublished"], meta[itemprop="uploadDate"]')?.content;
                if (published && /^\d{4}-\d{2}-\d{2}/.test(published)) {
                    const value = new Date(published);
                    if (Number.isFinite(value.getTime())) date = new Intl.DateTimeFormat(this.options.language === 'ru' ? 'ru-RU' : 'en-US', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(value);
                }
            }
            return [views, date].filter(Boolean).join(' · ');
        }
        nativePlayer() {
            const video = this.native.querySelector('#movie_player video, ytd-player video, video.html5-main-video, video');
            return video?.closest('ytd-player') || video?.closest('#movie_player') || video?.closest('#player') || this.native.querySelector('ytd-player, #movie_player');
        }

        island(node,kind,box) {
            if(!node)return;
            if(!this.islands.has(node)){this.islands.set(node,{tabindex:node.getAttribute('tabindex'),popover:node.getAttribute('popover'),style:node.getAttribute('style'),properties:['--myt-island-x','--myt-island-y','--myt-island-w','--myt-island-h','--myt-island-clip'].map(name=>[name,node.style.getPropertyValue(name),node.style.getPropertyPriority(name)]),kind});node.setAttribute('popover','manual');node.dataset.mytWatchIsland=kind;if(kind==='anchor')node.tabIndex=-1;this.open(node);}
            this.islands.get(node).box=box;if(!document.fullscreenElement)this.open(node);
            return node;
        }
        restore(node) {
            const state=this.islands.get(node);if(!state)return;
            try{if(node.matches(':popover-open'))node.hidePopover();}catch{}
            if(state.popover===null)node.removeAttribute('popover');else node.setAttribute('popover',state.popover);
            for(const[name,value,priority]of state.properties){if(value)node.style.setProperty(name,value,priority);else node.style.removeProperty(name);}
            if(state.style===null&&!node.style.length)node.removeAttribute('style');
            if(state.kind==='anchor'){if(state.tabindex===null)node.removeAttribute('tabindex');else node.setAttribute('tabindex',state.tabindex);}delete node.dataset.mytWatchIsland;this.islands.delete(node);
        }
        anchorAction(source,control) { if(source.tagName==='BUTTON'||source.matches('[role="button"]')){const rect=control.getBoundingClientRect();this.island(source,'anchor',()=>control.isConnected?control.getBoundingClientRect():rect);this.position();} }
        seek(time,source) {
            // Let native chapter handlers notify YouTube, then seek the same media
            // element (including native controls/current playback state).
            if(source)source.click();
            const video=this.native.querySelector('video');if(video&&Number.isFinite(time)){try{video.currentTime=time;}catch{}}
            this.updateCurrentChapter();
        }
        copyProse(source,target,isRoot=false) {
            if(source.nodeType===Node.TEXT_NODE){if(!source.data.trim()&&/\n[\t ]{2,}/.test(source.data))return;target.append(document.createTextNode(source.data));return;}
            if(!(source instanceof Element)||source.matches('script,style,button,tp-yt-paper-tooltip,yt-tooltip,[role="tooltip"],#info-container,#info,#expand,#collapse')||(!isRoot&&source.matches('[role="button"],ytd-structured-description-content-renderer,[data-myt-description-section]')))return;
            if(!isRoot&&/description.*section-(renderer|view-model)$/.test(source.localName))return;
            if(source.tagName==='A') {const url=safeURL(source.href);if(url){const node=this.link(source,'',text(source));const parsed=new URL(url);const time=parsed.searchParams.get('t')||parsed.searchParams.get('start');if(parsed.pathname==='/watch'&&time&&/^\d+s?$/.test(time))node.dataset.seconds=parseInt(time,10);target.append(node);}else target.append(document.createTextNode(text(source)));return;}
            const tag=source.tagName.toLowerCase(),allowed=['p','br','strong','b','em','i','ul','ol','li'];
            const node=allowed.includes(tag)?document.createElement(tag):document.createDocumentFragment();
            for(const child of source.childNodes)this.copyProse(child,node);target.append(node);
        }
        updateExpanded() {this.q('.prose').classList.toggle('expanded',this.expanded);this.q('.expand').textContent=this.expanded?this.copy.less:this.copy.more;this.q('.expand').setAttribute('aria-expanded',String(this.expanded));this.position();}
        sync(options) {
            this.options=options;this.copy=words[options.language]||words.en;const c=this.copy;
            const media=this.native.querySelector('video');if(media!==this.media){this.media?.removeEventListener('timeupdate',this.videoTime);this.media=media;this.media?.addEventListener('timeupdate',this.videoTime);}
            if(document.fullscreenElement){this.updateFullscreenLayout();return;}
            if(this.fullscreenPending)return;
            this.surface.toggleAttribute('dark',options.dark);this.surface.toggleAttribute('theater',this.native.hasAttribute('theater'));if(this.host.lang!==options.language)this.host.lang=options.language;
            const input=this.q('#watch-search');input.placeholder=c.search;input.setAttribute('aria-label',c.search);this.q('#watch-clear').setAttribute('aria-label',c.clear);
            const metadata=this.native.querySelector('ytd-watch-metadata,ytd-video-primary-info-renderer,ytd-video-secondary-info-renderer');
            const descriptionData=this.descriptionData(metadata),description=descriptionData.root;
            const ownerData=this.channelOwner(metadata);
            this.transcriptAvailable=Boolean(this.native.querySelector('ytd-video-description-transcript-section-renderer,ytd-transcript-renderer'));
            if(!this.transcriptAvailable&&this.transcriptOpen)this.closeTranscript();
            const sectionData=[...this.native.querySelectorAll('ytd-macro-markers-list-item-renderer,ytd-info-card-contents-renderer,ytd-video-description-channel-section-renderer')].map(node=>[text(node),node.querySelector('a[href]')?.href]);
            // Only native source data forms this signature. Typing, focus and scroll
            // in our shadow tree do not rebuild controls or disturb selection.
            const signature=JSON.stringify([options.video,options.language,Boolean(options.commentsButton),this.transcriptAvailable,text(metadata),text(ownerData.owner),text(descriptionData.body),sectionData,[...this.native.querySelectorAll('ytd-watch-metadata a[href],ytd-video-secondary-info-renderer a[href],ytd-watch-metadata img,ytd-video-secondary-info-renderer img,#description a[href],#description img')].map(node=>[node.href,node.currentSrc||node.getAttribute('src'),node.getAttribute('srcset'),node.getAttribute('data-src'),node.naturalWidth])]);
            if(signature!==this.signature){
                if(this.video!==options.video){this.video=options.video;this.expanded=false;this.closeTranscript();this.viewport.scrollTop=0;}
                this.signature=signature;this.sources.clear();this.sequence=0;
                this.q('#watch-title').textContent=text(metadata?.querySelector('h1'))||document.title.replace(/ - YouTube$/,'')||c.video;
                const owner=this.q('.owner');owner.replaceChildren();
                const {owner:nativeOwner,link:ownerLink,name:ownerName,avatar}=ownerData;
                if(ownerLink){const link=this.link(ownerLink,'owner-link');const img=this.image(avatar);if(img)link.append(img);const name=this.node('span','owner-name',ownerName);const sub=text(nativeOwner.querySelector('#owner-sub-count,#subscriber-count'));if(sub)name.append(this.node('small','',sub));link.append(name);owner.append(link);}
                const subscribe=nativeOwner?.querySelector('#subscribe-button button,ytd-subscribe-button-renderer button,yt-subscribe-button-view-model button');if(subscribe){const b=this.button(text(subscribe)||c.subscribe,subscribe);b.className='primary';owner.append(b);}
                this.closeMore();
                const actions=this.q('.actions');for(const child of [...actions.children])if(child!==options.commentsButton)child.remove();
                const nativeActions=metadata?.querySelector('#actions,#menu-container');
                const sources={};
                if(nativeActions){
                    const used=new Set();
                    for(const[kind,pattern]of[['share',/share|поделиться/i],['save',/save|сохранить/i],['menu',/more|ещё|еще/i]]){
                        const source=[...nativeActions.querySelectorAll('button')].find(b=>!b.closest('[data-myt-votes],#myt-comments-toggle')&&!used.has(b)&&pattern.test(`${b.id} ${b.getAttribute('aria-label')||''} ${text(b)}`));
                        if(source){used.add(source);sources[kind]=source;}
                    }
                    if(sources.save)actions.append(this.button(c.save,sources.save,'save'));
                }
                if(sources.share||sources.menu||options.commentsButton||this.transcriptAvailable)actions.append(this.moreActions(sources.share,sources.menu));
                this.renderDescription(descriptionData);
                const chapters=this.q('.chapter-list');chapters.replaceChildren();
                for(const card of this.native.querySelectorAll('ytd-macro-markers-list-item-renderer')){const source=card.querySelector('a[href],button,[role="button"]')||card;const time=text(card.querySelector('#time,#timestamp,.timestamp'));const at=seconds(time);const title=text(card.querySelector('#title,h3,.macro-markers'));if(at===null||!title)continue;const b=this.button('',source);b.className='chapter';b.dataset.seconds=at;b.append(this.node('time','',time),this.node('span','chapter-title',title));b.insertAdjacentHTML('beforeend',icon('play'));chapters.append(b);}
                this.q('#watch-chapters').hidden=!chapters.children.length;this.q('#watch-chapters h2').textContent=c.chapters;
                const people=this.q('.people');people.replaceChildren();
                for(const card of this.native.querySelectorAll('ytd-info-card-contents-renderer')){const source=card.querySelector('a[href]');if(!source)continue;const name=text(card.querySelector('#title,h3'));if(!name)continue;const a=this.link(source,'person');const img=this.image(card.querySelector('img'));if(img)a.append(img);a.append(this.node('span','',name));people.append(a);}
                this.q('#watch-people').hidden=!people.children.length;this.q('#watch-people h2').textContent=c.people;
                const channel=this.native.querySelector('ytd-video-description-channel-section-renderer');const socials=this.q('.socials');socials.replaceChildren();
                for(const source of channel?.querySelectorAll('a[href],button')||[]){const label=(text(source)||source.getAttribute('aria-label')||'').replace(/\s*↗\s*$/u,'');if(!label)continue;const a=source.tagName==='A'?this.link(source,'social',label):this.button(label,source);a.className='social';a.insertAdjacentHTML('beforeend',icon('arrow'));socials.append(a);}
                this.q('#watch-socials').hidden=!socials.children.length;this.q('#watch-socials h2').textContent=c.socials;
            }
            const stats=this.statsText(description);if(this.q('.stats').textContent!==stats)this.q('.stats').textContent=stats;this.q('.stats').hidden=!stats;
            this.q('#watch-transcript').hidden=!this.transcriptOpen||!this.transcriptAvailable;this.q('#watch-transcript h2').textContent=c.transcript;this.q('#watch-transcript .hint').textContent=c.transcriptHint;this.q('.transcript-toggle').textContent=this.transcriptOpen?c.hideTranscript:c.showTranscript;this.q('.transcript-search').placeholder=c.find;this.q('.transcript-search').setAttribute('aria-label',c.find);this.q('.transcript-retry').textContent=c.retry;
            this.q('.comments-section').hidden=!options.commentsOpen;this.q('.comments-section h2').textContent=c.comments;
            const player=this.nativePlayer();
            for(const[node,state]of this.islands)if(state.kind==='media'&&node!==player)this.restore(node);
            if(player&&!document.fullscreenElement&&!this.fullscreenPending)this.island(player,'media',()=>this.q('.media').getBoundingClientRect());
            const comments=options.commentsOpen&&(this.native.querySelector('ytd-comments')||this.native.querySelector('ytd-engagement-panel-section-list-renderer[target-id*="comments"],ytd-engagement-panel-section-list-renderer[data-target-id*="comments"]'));
            for(const[node,state]of this.islands)if(state.kind==='comments'&&node!==comments)this.restore(node);
            if(comments)this.island(comments,'comments',()=>this.q('.comments').getBoundingClientRect());
            const sidecar=this.native.querySelector('ytd-playlist-panel-renderer#playlist:not([hidden]),#playlist:not([hidden]) ytd-playlist-panel-renderer:not([hidden])');
            this.q('.sidecar').hidden=!sidecar;this.q('.layout').classList.toggle('has-sidecar',!!sidecar);
            for(const[node,state]of this.islands)if(state.kind==='sidecar'&&node!==sidecar)this.restore(node);
            if(sidecar)this.island(sidecar,'sidecar',()=>this.q('.sidecar').getBoundingClientRect());
            const popups=document.querySelector('ytd-popup-container');if(popups)this.island(popups,'popups',()=>({x:0,y:0,width:innerWidth,height:innerHeight}));
            if(this.transcriptOpen)this.renderTranscript();this.position();this.updateCurrentChapter();
        }
        position() {
            if(!this.host.isConnected||document.fullscreenElement||this.fullscreenPending)return;
            const headerBottom=this.q('.header').getBoundingClientRect().bottom;
            for(const[node,state]of this.islands){if(!node.isConnected){this.restore(node);continue;}if(!state.box)continue;const b=state.box();if(state.kind==='media'&&(state.width!==b.width||state.height!==b.height)){state.width=b.width;state.height=b.height;this.resizeNativePlayer();}const props={'--myt-island-x':`${b.x}px`,'--myt-island-y':`${b.y}px`,'--myt-island-w':`${b.width}px`,'--myt-island-h':`${b.height}px`,'--myt-island-clip':['media','comments','sidecar'].includes(state.kind)?`${Math.max(0,headerBottom-b.y)}px`:'0px'};for(const[k,v]of Object.entries(props))if(node.style.getPropertyValue(k)!==v)node.style.setProperty(k,v);}
        }
        updateCurrentChapter() {const time=this.native.querySelector('video')?.currentTime||0;const chapters=[...this.shadow.querySelectorAll('.chapter')];const current=chapters.findLast?chapters.findLast(b=>Number(b.dataset.seconds)<=time):chapters.filter(b=>Number(b.dataset.seconds)<=time).pop();for(const b of chapters){const value=String(b===current);if(b.getAttribute('aria-current')!==value)b.setAttribute('aria-current',value);}}
        toggleTranscript() {if(this.transcriptOpen){this.closeTranscript();}else{this.transcriptOpen=true;this.q('#watch-transcript').hidden=false;this.q('.transcript-content').hidden=false;this.q('.transcript-toggle').setAttribute('aria-expanded','true');this.loadTranscript();}this.q('.transcript-toggle').textContent=this.copy.hideTranscript;this.q('.transcript-menu-toggle')?.setAttribute('aria-expanded',String(this.transcriptOpen));this.position();}
        loadTranscript() {
            const source=this.native.querySelector('ytd-video-description-transcript-section-renderer button');
            const panel=this.native.querySelector('ytd-engagement-panel-section-list-renderer[target-id*="transcript"]');
            if(panel&&!this.nativePanelState)this.nativePanelState={node:panel,attrs:['visibility','hidden','aria-hidden'].map(name=>[name,panel.getAttribute(name)])};
            source?.click();this.transcriptLoading=true;clearTimeout(this.transcriptTimeout);this.transcriptTimeout=setTimeout(()=>{this.transcriptLoading=false;this.renderTranscript();},8000);this.renderTranscript();
        }
        renderTranscript() {
            if(this.transcriptOpen&&!this.nativePanelState){
                const panel=this.native.querySelector('ytd-engagement-panel-section-list-renderer[target-id*="transcript"]');
                if(panel)this.nativePanelState={node:panel,attrs:[['visibility','ENGAGEMENT_PANEL_VISIBILITY_HIDDEN'],['hidden',null],['aria-hidden',panel.hasAttribute('aria-hidden')?'true':null]]};
            }
            const rows=[...this.native.querySelectorAll('ytd-transcript-segment-renderer,transcript-segment-view-model,yt-transcript-segment-view-model')];
            const data=rows.map(row=>{const time=text(row.querySelector('.segment-timestamp,#start-offset,time'))||text(row).match(/^\d+(?::\d+){1,2}/)?.[0]||'';const value=text(row.querySelector('.segment-text,#segment-text'))||text(row).slice(time.length).trim();return{row,time,value,at:seconds(time)};}).filter(r=>r.at!==null&&r.value);
            if(data.length){this.transcriptLoading=false;clearTimeout(this.transcriptTimeout);}
            const query=this.q('.transcript-search').value.toLocaleLowerCase();const filtered=data.filter(r=>r.value.toLocaleLowerCase().includes(query));
            const signature=JSON.stringify([data.map(r=>[r.time,r.value]),query,this.transcriptLoading,this.options.language]);
            if(signature===this.transcriptSignature)return;this.transcriptSignature=signature;
            const list=this.q('.segments');list.replaceChildren();for(const r of filtered){const b=this.button('');b.className='segment';b.append(this.node('time','',r.time),this.node('span','',r.value));b.onclick=()=>this.seek(r.at,r.row.querySelector('button,a')||null);list.append(b);}
            this.q('.transcript-status').textContent=data.length?(filtered.length?'':this.copy.noResults):(this.transcriptLoading?this.copy.loading:this.copy.unavailable);this.q('.transcript-retry').hidden=!!data.length||this.transcriptLoading;this.q('.transcript-search').hidden=!data.length;
        }
        closeTranscript() {this.transcriptOpen=false;clearTimeout(this.transcriptTimeout);if(this.q){this.q('#watch-transcript').hidden=true;this.q('.transcript-menu-toggle')?.setAttribute('aria-expanded','false');this.q('.transcript-content').hidden=true;this.q('.transcript-toggle').setAttribute('aria-expanded','false');}if(this.nativePanelState){for(const[name,value]of this.nativePanelState.attrs){if(value===null)this.nativePanelState.node.removeAttribute(name);else this.nativePanelState.node.setAttribute(name,value);}this.nativePanelState=null;}}
        destroy() {this.restoreFullscreenLayout();clearTimeout(this.fullscreenTimer);for(const type of ['click','dblclick','keydown'])window.removeEventListener(type,this.fullscreenIntent,true);document.removeEventListener('fullscreenerror',this.fullscreenError);this.closeMore();this.closeTranscript();cancelAnimationFrame(this.resizeFrame);this.observer.disconnect();document.removeEventListener('keydown',this.shortcut);window.removeEventListener('wheel',this.nativeWheel,true);window.removeEventListener('resize',this.geometry);document.removeEventListener('fullscreenchange',this.fullscreen);this.media?.removeEventListener('timeupdate',this.videoTime);this.native.removeEventListener('load',this.sourceLoad,true);delete this.native.dataset.mytWatchSource;for(const node of [...this.islands.keys()])this.restore(node);this.host.remove();delete document.documentElement.dataset.mytWatchUi;}
    }
    globalThis.MinimalYouTubeWatch=WatchView;
})();
