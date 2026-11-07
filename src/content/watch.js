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
.layout { display:grid;grid-template-columns:minmax(0,1fr); }.primary { min-width:0; }.layout.has-sidecar { grid-template-columns:minmax(0,1fr) clamp(300px,24vw,400px);align-items:stretch; }
.media { width:100%;max-width:1280px;margin:0 auto;aspect-ratio:16/9;background:#000;border-radius:18px; }.sidecar { min-width:0;min-height:var(--playlist-min-height,240px);border-radius:16px 0 0 16px;background:var(--surface); }.has-sidecar .sidecar { align-self:stretch; }
.media[aria-busy=true] { position:relative;background:var(--surface); }.media[aria-busy=true]::after { content:'Loading video…';position:absolute;inset:0;display:grid;place-items:center;color:var(--muted);font-size:16px; }
main.has-sidecar { max-width:none;padding:0 0 72px; }main.has-sidecar .primary { padding:20px 24px 0; }
.details { max-width:960px;margin:28px auto 0;min-width:0;min-height:calc(100dvh - 148px); }
main.has-sidecar .details { min-height:0; }
@media(min-width:901px) {
    :host(:not([theater])) .has-sidecar .primary { display:contents; }
    :host(:not([theater])) .has-sidecar .media { grid-column:1;grid-row:1;width:calc(100% - 48px);margin:20px auto 0; }
    :host(:not([theater])) .has-sidecar .details { grid-column:1 / -1;grid-row:2;justify-self:center;width:calc(100% - 48px); }
    :host(:not([theater])) .has-sidecar .sidecar { grid-column:2;grid-row:1;align-self:start;height:var(--playlist-player-height,320px);min-height:0;margin-top:20px; }
}
#watch-title { --title-ink:var(--ink);font-family:"MYT Barlow Condensed","MYT Cyrillic Condensed","Arial Narrow",sans-serif;font-size:32px;font-weight:900;font-style:italic;text-transform:uppercase;line-height:.60;letter-spacing:-.025em;color:var(--title-ink);-webkit-text-fill-color:var(--title-ink);-webkit-text-stroke:0 transparent;overflow:visible;overflow-wrap:anywhere; }
:host([dark]) #watch-title { --title-ink:#fff; }
#watch-title .title-outline { -webkit-text-fill-color:transparent;-webkit-text-stroke:.5px var(--title-ink); }
.meta-row { display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;margin:22px 0 0; }
.channel-card { position:relative;display:grid;grid-template-columns:var(--owner-avatars,46px) minmax(0,1fr) 20px;align-items:center;gap:2px 14px;flex:0 1 auto;width:fit-content;max-width:min(520px,100%);min-width:0;min-height:78px;padding:14px 24px;border:1px solid var(--border);border-radius:999px;background:var(--surface);color:var(--ink); }
.channel-card[data-subscribed=true] { background:#c91f37;border-color:#c91f37;--ink:#fff;--muted:#ffe7eb; }.channel-card[data-subscribed=true] .owner img { box-shadow:0 0 0 1px #ffffff66; }
.channel-card:has(.channel-subscribe:hover:not(:disabled)) { background:var(--soft); }.channel-card[data-subscribed=true]:has(.channel-subscribe:hover:not(:disabled)) { background:#b51b31;border-color:#b51b31; }
.channel-subscribe { position:absolute;inset:0;width:100%;height:100%;padding:0;border:0;border-radius:inherit;background:transparent;color:inherit; }.channel-subscribe:hover { background:transparent; }.channel-subscribe:disabled { opacity:1; }.channel-subscribe:focus-visible { outline:2px solid #62626e;outline-offset:3px; }
@media(prefers-reduced-motion:no-preference) { .channel-card:has(.channel-subscribe:active:not(:disabled)) { transform:scale(.98); } }
.owner { display:contents;pointer-events:none; }.avatar-link { position:relative;grid-column:1;grid-row:1 / 3;display:block;pointer-events:auto; }.owner-text { position:relative;grid-column:2;grid-row:1;align-self:end;min-width:0; }.owner-link { color:var(--ink);pointer-events:auto; }.owner img { display:block;width:46px;height:46px;border-radius:50%;object-fit:cover; }.owner-name { overflow-wrap:anywhere;font-size:17px;font-weight:600; }
.avatar-group { position:relative;grid-column:1;grid-row:1 / 3;display:flex;align-items:center; }.avatar-group .avatar-link { flex:none;width:46px;height:46px;margin-left:-12px;border:2px solid var(--surface);border-radius:50%;background:var(--surface); }.avatar-group .avatar-link:first-child { margin-left:0; }.avatar-group .avatar-link:focus-visible { z-index:1; }.avatar-group .avatar-link img { width:100%;height:100%; }.channel-card[data-subscribed=true] .avatar-group .avatar-link { border-color:#c91f37; }.owner-names { display:flex;align-items:baseline;flex-wrap:wrap;gap:0 6px; }.owner-separator { color:var(--muted); }.owner button.owner-link,.owner button.avatar-link { min-height:0;padding:0;border:0;background:transparent;font:inherit;text-align:left;white-space:normal; }.owner button.owner-name { font-size:17px;font-weight:600; }.owner button.owner-link:hover { text-decoration:none; }.owner button.avatar-link { border-radius:50%; }.avatar-group button.avatar-link { border:2px solid var(--surface); }
.owner .owner-name { min-width:0;max-width:100%; }.owner button.owner-name { display:inline;flex-shrink:1; }
.owner .owner-name { border-radius:5px;text-decoration:none; }.owner .owner-name:is(:hover,:focus-visible) { text-decoration:none;background:color-mix(in srgb,var(--ink) 9%,transparent);box-shadow:0 0 0 3px color-mix(in srgb,var(--ink) 9%,transparent); }
.subscription-state { position:relative;grid-column:3;grid-row:1 / 3;display:flex;align-items:center;pointer-events:none;color:var(--ink); }.subscription-state svg { width:18px;height:18px; }.channel-card .stats { position:relative;grid-column:2;grid-row:2;align-self:start;pointer-events:none;font-size:13px;line-height:1.5; }.channel-card:not(:has(.avatar-link img)) { grid-template-columns:minmax(0,1fr) 20px; }.channel-card:not(:has(.avatar-link img)) .owner-text,.channel-card:not(:has(.avatar-link img)) .stats { grid-column:1; }.channel-card:not(:has(.avatar-link img)) .subscription-state { grid-column:2; }.sr-only { position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0; }
.actions { display:flex;align-items:center;gap:9px;flex-wrap:wrap;min-width:0; }
.more-actions { display:flex; }.more-toggle { width:44px;min-width:44px;padding:10px; }.more-popup { position:fixed;inset:auto;margin:0;padding:6px;width:min(260px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;border:1px solid var(--border);border-radius:14px;background:var(--surface);color:var(--ink);box-shadow:0 12px 36px #0002; }.more-popup::backdrop { background:transparent; }.more-popup button { display:flex;width:100%;justify-content:flex-start;white-space:normal;text-align:left;border:0;background:transparent; }.more-popup button:hover,.more-popup button:focus-visible { background:var(--soft); }.more-popup button:focus-visible { outline-offset:-2px; }
#myt-comments-toggle { display:inline-flex;align-items:center;gap:9px; }.description { margin-top:28px;border:1px solid var(--border);border-radius:20px;background:var(--surface);padding:28px; }
.stats { font-size:14px;font-weight:500;color:var(--muted);margin:0; }.prose { font-family:"SFMono-Regular","SF Mono",Menlo,Monaco,Consolas,"Liberation Mono",ui-monospace,monospace;font-size:17px;font-weight:400;line-height:1.75;letter-spacing:normal;font-variant-ligatures:none;overflow-wrap:anywhere;white-space:pre-wrap; }.prose p { margin:0 0 18px; }.prose ul,.prose ol { padding-left:24px; }.prose:not(.expanded) { max-height:8.75em;overflow:hidden; }.expand { display:flex;width:100%;margin-top:18px;background:transparent; }
.channel-card .stats { display:flex;align-items:flex-start;gap:6px; }.views-icon { display:inline-flex;flex:none;margin-top:3px; }.views-icon svg { width:14px;height:14px; }.stats-value { min-width:0; }
.prose a { font-weight:700; }.prose .link-symbol { display:inline-block;width:.95em;height:.95em;margin-right:.3em;vertical-align:-.12em;pointer-events:none; }
.section { margin-top:32px; }.section-head { display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px; }.hint { color:var(--muted);font-size:15px;line-height:1.6; }
.chapter-list { display:flex;flex-flow:row nowrap;gap:12px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x proximity;scrollbar-color:var(--border) transparent;padding-bottom:12px; }.chapter { flex:0 0 220px;scroll-snap-align:start;display:grid;grid-template-columns:minmax(0,1fr);gap:8px;align-content:start;text-align:left;white-space:normal;justify-content:initial;min-height:112px;padding:16px;border-color:var(--border);--chapter-bg:var(--surface);background:var(--chapter-bg);border-radius:24px; }
.chapter:nth-child(even) { --chapter-bg:var(--soft); }.chapter:hover { background:color-mix(in srgb,var(--chapter-bg) 94%,var(--ink) 6%); }.chapter[aria-current=true] { --chapter-bg:#c91f37;background:var(--chapter-bg);border-color:#c91f37;color:#fff; }.chapter[aria-current=true]:hover { background:#b51b31;border-color:#b51b31; }.chapter[aria-current=true] time { color:#fff; }.chapter[aria-current=true] time { font-weight:600; }.chapter time { grid-column:1;grid-row:1;font-size:15px;font-variant-numeric:tabular-nums;color:var(--muted); }.chapter-title { grid-column:1 / -1;grid-row:2;min-width:0;overflow-wrap:anywhere;font-size:18px;line-height:1.45;font-weight:500;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden; }.chapter svg { grid-column:2;grid-row:1;width:18px;height:18px;color:var(--muted); }
.people { display:flex;flex-wrap:wrap;gap:12px; }.person { display:flex;align-items:center;gap:14px;padding:16px 20px;border:1px solid var(--border);border-radius:14px;background:var(--surface);color:var(--ink);font-size:17px;font-weight:500; }.person img { width:48px;height:48px;border-radius:50%;object-fit:cover; }
.transcript-card { padding:26px;border:1px solid var(--border);border-radius:20px;background:var(--surface); }.transcript-intro { display:flex;align-items:center;gap:16px; }.transcript-icon { display:grid;place-items:center;width:48px;height:48px;flex:none;border-radius:14px;background:var(--soft);color:var(--ink); }.transcript-copy { flex:1;min-width:0; }.transcript-copy h2 { margin-bottom:5px; }.transcript-head { display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap; }
.transcript-content { margin-top:24px;padding-top:24px;border-top:1px solid var(--border); }.transcript-search { width:100%;height:46px;padding:0 14px;border:1px solid var(--border);border-radius:11px;background:var(--bg);color:var(--ink);font-size:16px; }.segments { display:flex;flex-direction:column;gap:5px;max-height:520px;overflow:auto;margin-top:16px;scrollbar-color:var(--border) transparent; }.segment { display:grid;grid-template-columns:70px minmax(0,1fr);gap:16px;align-items:start;justify-content:initial;text-align:left;white-space:normal;padding:14px 12px;border:0;background:transparent;font-size:16px;font-weight:400;line-height:1.65; }.segment span { min-width:0;overflow-wrap:anywhere; }.segment time { color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums; }.segment:hover { background:var(--soft); }.transcript-status { padding:20px 0;color:var(--muted);font-size:16px; }
.socials { display:flex;flex-wrap:wrap;gap:10px; }.social { display:inline-flex;align-items:center;justify-content:center;gap:12px;min-height:44px;padding:10px 16px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);font-size:16px;line-height:1.4; }.social:hover { background:var(--soft);text-decoration:none; }
.comments { height:600px;margin-top:20px;border:1px solid var(--border);border-radius:16px;background:var(--surface); }.comments-section { margin-top:32px; }
.section,.comments-section { scroll-margin-top:96px; }
@media(max-width:600px) { .section,.comments-section { scroll-margin-top:82px; }:host([theater]) main { padding-bottom:48px; }:host([theater]) .details { width:calc(100% - 32px); } }
:host([theater]) main { max-width:none;padding:0 0 72px; }:host([theater]) .details { max-width:960px;width:calc(100% - 48px); }:host([theater]) .media { max-width:none;max-height:none;aspect-ratio:var(--myt-video-aspect,16 / 9);height:auto;border-radius:0; }
:host([theater]) .has-sidecar .primary { display:contents; }:host([theater]) .has-sidecar .media { grid-column:1 / -1;grid-row:1; }:host([theater]) .has-sidecar .details { grid-column:1;grid-row:2;justify-self:center;margin:0; }:host([theater]) .has-sidecar .sidecar { grid-column:2;grid-row:2; }:host([theater]) .layout.has-sidecar { row-gap:28px; }
:host([theater]) main,:host([theater]) .layout,:host([theater]) .media { width:100%;min-width:0;max-width:100%; }:host([theater]) .layout { overflow-x:clip; }
@media(max-width:900px) { .layout.has-sidecar { grid-template-columns:minmax(0,1fr); } main { padding-inline:20px; }main.has-sidecar .primary { padding:20px 20px 0; }.has-sidecar .sidecar { width:calc(100% - 40px);margin:28px auto 0;border-radius:16px; }:host([theater]) .has-sidecar .details { width:calc(100% - 40px); }:host([theater]) .has-sidecar .sidecar { grid-column:1;grid-row:3;margin-top:0; } }
@media(max-width:600px) { .header { height:66px;padding:10px 16px;gap:14px; }.brand svg { width:32px;height:24px; }.brand span { display:none; }.search { height:44px; }.search input { font-size:16px; } main { padding:12px 16px 48px; }.media { border-radius:12px; }.details { margin-top:24px;min-height:calc(100dvh - 114px); }.meta-row { gap:12px; }.channel-card { grid-template-columns:var(--owner-avatars-small,40px) minmax(0,1fr) 18px;padding:12px 18px;gap:2px 10px; }.owner img { width:40px;height:40px; }.actions { width:100%; }.actions button { flex:1 1 auto; }.description { padding:22px 20px;border-radius:16px; }.prose { font-size:16px;line-height:1.75; }.chapter { flex-basis:min(200px,calc((100% - 12px) / 2));padding:14px 12px;border-radius:20px; }.chapter-title { font-size:17px; } h2 { font-size:21px; }.avatar-group .avatar-link { width:40px;height:40px; }.transcript-card { padding:22px 20px; }.transcript-head>button { width:100%; }.transcript-intro { align-items:start; }.segment { grid-template-columns:55px minmax(0,1fr);gap:12px; }.person { width:100%; }.section { margin-top:28px; } }
`;
    const words = {
        ru: { search:"Поиск на YouTube", clear:"Очистить поиск", description:"Описание", more:"Показать полностью", less:"Свернуть", chapters:"Эпизоды", people:"Упомянутые люди", transcript:"Расшифровка видео", transcriptHint:"Читайте текст и переходите к нужному моменту видео.", showTranscript:"Открыть расшифровку", hideTranscript:"Свернуть", find:"Найти в расшифровке", loading:"Загружаем расшифровку…", unavailable:"Текст пока не загрузился. Попробуйте ещё раз.", retry:"Повторить", noResults:"Совпадений нет", socials:"Ссылки канала", comments:"Комментарии", subscribe:"Подписаться", subscribed:"Вы подписаны", subscribeChannel:"Подписаться на канал", unsubscribeChannel:"Отписаться от канала", subscribing:"Подписываем…", unsubscribing:"Отписываем…", share:"Поделиться", openPlaylist:"Открыть плейлист", closePlaylist:"Закрыть плейлист", menu:"Ещё", otherActions:"Другие действия", video:"Видео" },
        en: { search:"Search YouTube", clear:"Clear search", description:"Description", more:"Show more", less:"Show less", chapters:"Chapters", people:"Mentioned people", transcript:"Video transcript", transcriptHint:"Read along and jump to any moment in the video.", showTranscript:"Open transcript", hideTranscript:"Collapse", find:"Search transcript", loading:"Loading transcript…", unavailable:"The transcript has not loaded yet. Please try again.", retry:"Try again", noResults:"No matches", socials:"Channel links", comments:"Comments", subscribe:"Subscribe", subscribed:"Subscribed", subscribeChannel:"Subscribe to", unsubscribeChannel:"Unsubscribe from", subscribing:"Subscribing…", unsubscribing:"Unsubscribing…", share:"Share", openPlaylist:"Open playlist", closePlaylist:"Close playlist", menu:"More", otherActions:"Other actions", video:"Video" }
    };
    const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${({transcript:'<path d="M5 3h14v18H5Z"/><path d="M8 8h8M8 12h8M8 16h5"/>', arrow:'<path d="m7 17 10-10M7 7h10v10"/>', share:'<path d="m15 4 6 6-6 6v-4C8 12 5 14 3 19c0-8 3-12 12-12Z"/>', close:'<path d="m6 6 12 12M18 6 6 18"/>', playlist:'<path d="M8 6h12M8 12h12M8 18h12M3 6h.01M3 12h.01M3 18h.01"/>', eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>', link:'<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>', menu:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'})[name] || ''}</svg>`;
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
    const titleFontLoads=new Map();
    function loadTitleFonts(title) {
        if(typeof globalThis.FontFace!=='function'||typeof globalThis.chrome?.runtime?.getURL!=='function')return Promise.resolve();
        const fonts=[['MYT Barlow Condensed','BarlowCondensed-BlackItalic.ttf']];
        if(/[\u0400-\u052f]/u.test(title))fonts.push(['MYT Cyrillic Condensed','MinimalCondensed-BlackItalic.ttf']);
        for(const [family,file] of fonts){
            if(titleFontLoads.has(file))continue;
            const load=(async()=>{
                const response=await fetch(chrome.runtime.getURL('src/assets/fonts/'+file));
                if(!response.ok)throw new Error('Title font unavailable');
                const face=new FontFace(family,await response.arrayBuffer(),{style:'italic',weight:'900',display:'swap'});
                await face.load();document.fonts.add(face);
            })().catch(()=>{});
            titleFontLoads.set(file,load);
        }
        return Promise.all(fonts.map(([,file])=>titleFontLoads.get(file)));
    }
    class WatchView {
        constructor(options) {
            this.options=options; this.native=options.native; this.islands=new Map(); this.fullscreenNodes=new Map(); this.expanded=false; this.transcriptOpen=false; this.signature=""; this.sources=new Map(); this.sequence=0; this.nativePanelState=null;
            this.host=document.createElement("div"); this.host.id="myt-watch"; this.host.setAttribute("popover","manual");
            this.surface=document.createElement("div"); this.shadow=this.surface.attachShadow({mode:"open"});this.host.append(this.surface);
            this.shadow.innerHTML=`<style>${css}</style><div class="viewport"><header class="header"><a class="brand" href="/" aria-label="YouTube"><svg viewBox="0 0 28 20" fill="currentColor" aria-hidden="true"><rect width="28" height="20" rx="6"/><path d="m11 5 8 5-8 5Z" fill="#fff"/></svg><span>YouTube</span></a><form class="search" action="/results" method="get" role="search"><input name="search_query" id="watch-search" autocomplete="off"><button type="button" id="watch-clear" hidden aria-label="Clear">×</button></form></header><main><div class="layout"><div class="primary"><div class="media" aria-label="YouTube player"></div><article class="details"><h1 id="watch-title"></h1><div class="meta-row"><div class="channel-card" hidden><button type="button" class="channel-subscribe" data-watch-action="subscription" aria-describedby="watch-subscription-status" disabled></button><div class="owner"></div><span class="subscription-state" id="watch-subscription-status" aria-live="polite"></span><div class="stats" hidden><span class="views-icon" hidden>${icon('eye')}</span><span class="stats-value"></span></div></div><div class="actions"></div></div><section class="section" id="watch-chapters" hidden aria-label="Chapters"><div class="chapter-list"></div></section><section class="description" aria-label="Description"><div class="prose" id="watch-description"></div><button class="expand" aria-expanded="false" aria-controls="watch-description"></button></section><section class="section" id="watch-people" hidden><div class="section-head"><h2></h2></div><div class="people"></div></section><section class="section transcript-card" id="watch-transcript" hidden><div class="transcript-head"><div class="transcript-intro"><span class="transcript-icon">${icon('transcript')}</span><div class="transcript-copy"><h2></h2><p class="hint"></p></div></div><button class="transcript-toggle" aria-expanded="false" aria-controls="watch-transcript-content"></button></div><div class="transcript-content" id="watch-transcript-content" hidden><input class="transcript-search" type="search"><div class="segments"></div><p class="transcript-status" role="status"></p><button class="transcript-retry" hidden></button></div></section><section class="section" id="watch-socials" hidden><div class="section-head"><h2></h2></div><div class="socials"></div></section><section class="comments-section" id="watch-comments" hidden><h2></h2><div class="comments"></div></section></article></div><aside class="sidecar" hidden></aside></div></main></div>`;
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
                    if(action.dataset.watchAction==='subscription'){event.preventDefault();this.toggleSubscription();return;}
                    if(action.dataset.watchAction==='playlist'){event.preventDefault();this.openPlaylist();return;}
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
            this.geometry=()=>{
                if(this.notifyingResize||this.geometryFrame)return;
                this.geometryFrame=requestAnimationFrame(()=>{
                    this.geometryFrame=0;if(!this.host.isConnected)return;
                    if(document.fullscreenElement||this.fullscreenPending){this.updateFullscreenLayout(this.fullscreenPreview||document.fullscreenElement);this.resizeNativePlayer();return;}
                    const width=this.q('#watch-title').clientWidth;
                    if(width!==this.titleLineWidth&&width!==this.queuedTitleWidth){
                        this.queuedTitleWidth=width;clearTimeout(this.titleTimer);
                        // Measure the outlined first line once resizing settles,
                        // rather than rewriting the title for every dragged pixel.
                        this.titleTimer=setTimeout(()=>{this.queuedTitleWidth=null;if(this.host.isConnected){this.layoutTitle();this.position();}},100);
                    }
                    this.syncPlaylistMinimum();this.position();if(this.q('.more-popup')?.matches(':popover-open'))this.positionMore();
                });
            };
            this.viewport.addEventListener('scroll',()=>{
                if(this.q('.more-popup')?.matches(':popover-open')){
                    const rect=this.q('.more-toggle').getBoundingClientRect();
                    // Opening a focused popover can deliver an already-pending
                    // scroll event. Dismiss only when its anchor actually moved.
                    if(this.moreAnchor&&Math.abs(rect.y-this.moreAnchor.y)>.5)this.closeMore();
                }
                if(this.positionedScroll!==this.viewport.scrollTop)this.position();
            },{passive:true});window.addEventListener('resize',this.geometry);
            this.observer=new ResizeObserver(this.geometry);this.observer.observe(this.q('main'));this.observer.observe(this.q('.media'));this.observer.observe(this.q('.details'));
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
            this.sourceLoad=event=>{
                if(!(event.target instanceof Element)||!event.target.matches('img')||!event.target.closest('#owner,ytd-video-owner-renderer,yt-video-owner-renderer,yt-video-owner-view-model,yt-avatar-stack-view-model,ytd-info-card-contents-renderer')||this.sourceFrame)return;
                this.sourceFrame=requestAnimationFrame(()=>{this.sourceFrame=0;if(this.host.isConnected)this.sync(this.options);});
            };this.native.addEventListener('load',this.sourceLoad,true);
            this.videoTime=event=>this.updateCurrentChapter(event.type==='seeked');this.videoMetadata=()=>{this.syncTheaterAspect();this.position();this.resizeNativePlayer(true);};this.media=this.native.querySelector('video');for(const type of ['timeupdate','seeked'])this.media?.addEventListener(type,this.videoTime);for(const type of ['loadedmetadata','resize'])this.media?.addEventListener(type,this.videoMetadata);
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
            this.fullscreenPending=true;this.fullscreenPreview=player;
            this.closeMore();player.setAttribute('data-myt-fullscreen-pending','');
            // Paint the native frame at full size in the same click. Preserve its
            // positioning state until the browser enters fullscreen; the native
            // button handler can request it as soon as its popover is hidden.
            this.updateFullscreenLayout(player);
            for(const node of this.islands.keys())if(node.matches(':popover-open'))node.hidePopover();
            if(this.host.matches(':popover-open'))this.host.hidePopover();
            clearTimeout(this.fullscreenTimer);
            this.fullscreenTimer=setTimeout(()=>this.resumeFullscreen(),600);
        }
        clearFullscreenPreview() {
            this.fullscreenPreview?.removeAttribute('data-myt-fullscreen-pending');this.fullscreenPreview=null;
        }
        resumeFullscreen() {
            clearTimeout(this.fullscreenTimer);this.fullscreenPending=false;
            this.clearFullscreenPreview();
            if(!document.fullscreenElement&&this.host.isConnected){this.restoreFullscreenLayout();this.open(this.host);this.sync(this.options);this.resizeNativePlayer();}
        }
        syncFullscreen() {
            clearTimeout(this.fullscreenTimer);this.fullscreenPending=false;
            this.clearFullscreenPreview();
            if(document.fullscreenElement){
                this.closeMore();
                for(const[node,state]of this.islands){
                    if(state.kind==='media')this.restore(node);
                    else if(node.matches(':popover-open'))node.hidePopover();
                }
                if(this.host.matches(':popover-open'))this.host.hidePopover();
                this.updateFullscreenLayout();this.resizeNativePlayer();
            }else this.resumeFullscreen();
        }
        restoreFullscreenLayout() {
            for(const[node,original]of this.fullscreenNodes){
                if(original===null)node.removeAttribute('data-myt-fullscreen-part');
                else node.setAttribute('data-myt-fullscreen-part',original);
            }
            this.fullscreenNodes.clear();
        }
        updateFullscreenLayout(fullscreen=document.fullscreenElement) {
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
        syncTheaterAspect() {
            const width=this.media?.videoWidth,height=this.media?.videoHeight;
            if(width>0&&height>0){const ratio=width+' / '+height;if(this.surface.style.getPropertyValue('--myt-video-aspect')!==ratio)this.surface.style.setProperty('--myt-video-aspect',ratio);}
        }
        resizeNativePlayer(force=false) {
            if(force)this.resizedSize=null;
            if(this.resizeFrame)return;
            this.resizeFrame=requestAnimationFrame(()=>{
                this.resizeFrame=0;
                if(!this.host.isConnected)return;
                const player=document.fullscreenElement||this.nativePlayer(),box=player?.getBoundingClientRect();
                if(!box||box.width<=0||box.height<=0)return;
                const size=[Math.round(box.width),Math.round(box.height),Boolean(document.fullscreenElement),Boolean(this.fullscreenPending)].join(':');
                if(this.resizedPlayer===player&&this.resizedMedia===this.media&&this.resizedSize===size)return;
                this.resizedPlayer=player;this.resizedMedia=this.media;this.resizedSize=size;
                this.notifyingResize=true;
                try{window.dispatchEvent(new Event('resize'));}finally{this.notifyingResize=false;}
                this.native.dispatchEvent(new CustomEvent('yt-resize',{bubbles:true,composed:true}));
                this.native.dispatchEvent(new CustomEvent('minimal-youtube:player-resize',{bubbles:true,composed:true,detail:{width:box.width,height:box.height}}));
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
            const toggle=this.button('',null,'menu');
            toggle.setAttribute('aria-label',this.copy.menu);toggle.title=this.copy.menu;
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
            const selector='ytd-video-owner-renderer,yt-video-owner-renderer,yt-video-owner-view-model,#owner';
            const owners=[...(metadata?.querySelectorAll(selector)||[]),...this.native.querySelectorAll(selector)];
            const visibleOwners=owners.filter(node=>!node.closest('[hidden],[aria-hidden="true"]'));
            const owner=visibleOwners.find(node=>node.querySelector('a[href],yt-attributed-string,yt-avatar-stack-view-model,ytd-channel-name,#channel-name'))||visibleOwners[0];
            if(!owner)return {};
            const cleanText=node=>{
                const copy=node?.cloneNode(true);
                copy?.querySelectorAll('tp-yt-paper-tooltip,yt-tooltip,[role="tooltip"],[hidden],[aria-hidden="true"],yt-icon,yt-icon-shape,#subscriber-count,#owner-sub-count').forEach(child=>child.remove());
                return text(copy);
            };
            const nameNode=owner.querySelector('ytd-channel-name #text a,#channel-name #text a,ytd-channel-name a,#channel-name a,#channel-name,ytd-channel-name,#attributed-channel-name,yt-attributed-string,#text');
            const preferred=[...owner.querySelectorAll('yt-avatar-stack-view-model img,#avatar img,#avatar-section img,#channel-avatar img,yt-avatar-shape img')];
            const images=preferred.length?preferred:[...owner.querySelectorAll('img')].filter(img=>!img.matches('.badge,[aria-hidden="true"]'));
            const groups=new Map();
            for(const link of owner.querySelectorAll('a[href]')){
                let url;try{url=new URL(link.href,location.href);}catch{continue;}
                if(!/^(?:www\.)?youtube\.com$/.test(url.hostname)||!/^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)\/?$/.test(url.pathname))continue;
                const key=url.pathname.replace(/\/$/,'').toLowerCase();
                const item=groups.get(key)||{link,name:'',avatar:null};
                const name=cleanText(link);
                if(name){item.name=name;item.link=link;}
                item.avatar||=link.querySelector('img');groups.set(key,item);
            }
            const channels=[...groups.values()];
            for(const [i,item] of channels.entries()){
                item.avatar||=images[i]||null;
                item.name||=channels.length===1?cleanText(nameNode):'';
                item.name||=item.avatar?.getAttribute('alt')||new URL(item.link.href).pathname.split('/').pop();
            }
            // Collaborations can expose an attributed title and an avatar stack
            // which open a native authors panel, instead of channel anchors.
            const opener=nameNode?.closest('button,[role="button"]')||nameNode?.querySelector('button,[role="button"]')||owner.querySelector('yt-avatar-stack-view-model button,yt-avatar-stack-view-model [role="button"],#channel-name button');
            if(!channels.length){const name=cleanText(nameNode)||cleanText(owner.querySelector('yt-avatar-stack-view-model'));if(name)channels.push({name,link:opener,avatar:images[0]||null});}
            const avatars=[],seen=new Set();
            for(const [i,image] of images.entries()){
                const item=channels.find(channel=>channel.avatar===image)||channels[i];
                const src=image.currentSrc||image.getAttribute('src')||image.getAttribute('data-src'),key=src+'|'+(item?.link?.getAttribute('href')||i);if(!src||seen.has(key))continue;seen.add(key);
                avatars.push({image,link:item?.link||opener,name:item?.name||channels.map(channel=>channel.name).join(' · ')});
            }
            const first=channels[0]||{};
            return {owner,channels,avatars,name:channels.map(channel=>channel.name).join(' · '),subscriptionName:first.name,link:first.link,avatar:first.avatar,collaborative:channels.length>1||avatars.length>1};
        }
        renderOwner(data) {
            const owner=this.q('.owner'),card=this.q('.channel-card');owner.replaceChildren();
            const control=(source,className,label)=>{
                if(source?.matches('a[href]'))return this.link(source,className,label);
                const node=source?this.button(label,source):this.node('span',className,label);node.className=className;return node;
            };
            const avatars=data.avatars||[],shown=avatars.slice(0,3),group=shown.length>1?this.node('div','avatar-group'):owner;
            card.toggleAttribute('data-collaborative',Boolean(data.collaborative));
            for(const [name,size,step] of [['--owner-avatars',46,34],['--owner-avatars-small',40,28]]){
                if(shown.length>1)card.style.setProperty(name,(size+step*(shown.length-1))+'px');else card.style.removeProperty(name);
            }
            for(const avatar of shown){const img=this.image(avatar.image);if(!img)continue;const link=control(avatar.link,'avatar-link');link.title=avatar.name;link.setAttribute('aria-label',avatar.name);link.append(img);group.append(link);}
            if(group!==owner)owner.append(group);
            const content=this.node('div','owner-text'),names=this.node('div','owner-names');
            for(const channel of data.channels||[]){if(names.childNodes.length)names.append(this.node('span','owner-separator','·'));names.append(control(channel.link,'owner-link owner-name',channel.name));}
            if(names.childNodes.length){content.append(names);owner.append(content);}
        }
        setTitle(value) {
            if(this.titleText===value)return;
            this.titleText=value;this.titleNeedsLayout=true;this.layoutTitle();
            loadTitleFonts(value).then(()=>{
                if(this.host.isConnected&&this.titleText===value){this.titleNeedsLayout=true;this.layoutTitle();this.position();}
            });
        }
        layoutTitle() {
            const title=this.q('#watch-title'),width=title.clientWidth,value=this.titleText;
            if(!width||!value||(!this.titleNeedsLayout&&this.titleLineWidth===width))return;
            this.titleNeedsLayout=false;this.titleLineWidth=width;title.textContent=value;
            const node=title.firstChild,range=document.createRange();range.setStart(node,0);range.setEnd(node,1);
            const top=range.getBoundingClientRect().top,tolerance=parseFloat(getComputedStyle(title).lineHeight)/2;
            let low=1,high=value.length;
            while(low<high){
                const end=Math.ceil((low+high)/2);range.setEnd(node,end);
                if([...range.getClientRects()].some(rect=>rect.top>top+tolerance))high=end-1;else low=end;
            }
            // Chromium does not apply text-stroke on ::first-line. A single
            // inline span follows the measured native wrap and keeps copying intact.
            title.replaceChildren(this.node('span','title-outline',value.slice(0,low)),document.createTextNode(value.slice(low)));
        }
        chapterData() {
            const selector='ytd-macro-markers-list-item-renderer';
            const cards=new Set([...this.native.querySelectorAll(`ytd-video-description-chapters-section-renderer ${selector}`),...this.native.querySelectorAll(selector)]);
            const chapters=new Map();
            for(const card of cards){
                const source=card.querySelector('a[href],button,[role="button"]')||card;
                const href=source.getAttribute('href');
                if(href){try{const video=new URL(href,location.href).searchParams.get('v');if(video&&video!==this.options.video)continue;}catch{continue;}}
                const time=text(card.querySelector('#time,#timestamp,.timestamp')),at=seconds(time),title=text(card.querySelector('#title,h3,.macro-markers'));
                // Description and engagement panels can contain the same timeline.
                if(at!==null&&title&&!chapters.has(at))chapters.set(at,{source,time,at,title});
            }
            return [...chapters.values()].sort((a,b)=>a.at-b.at);
        }
        subscriptionState(owner) {
            const button=owner?.querySelector('#subscribe-button button,ytd-subscribe-button-renderer button,yt-subscribe-button-view-model button');
            if(!button)return {button:null,subscribed:false,disabled:true};
            let subscribed;
            for(let node=button;node&&node!==owner;node=node.parentElement){
                for(const name of ['subscribed','is-subscribed'])if(node.hasAttribute(name)){subscribed=node.getAttribute(name)!=='false';break;}
                if(subscribed!==undefined)break;
            }
            if(subscribed===undefined&&button.hasAttribute('aria-pressed'))subscribed=button.getAttribute('aria-pressed')==='true';
            const labels=[text(button),(button.getAttribute('aria-label')||'').trim()];
            if(subscribed===undefined&&labels.some(label=>/^(?:subscribe\b|подписаться|abonnieren|suscribirse)/iu.test(label)))subscribed=false;
            if(subscribed===undefined&&labels.some(label=>/^(?:subscribed\b|unsubscribe\b|вы подписаны|отписаться|отменить подписку|настройки уведомлений|notification settings|abonniert|suscrito|abonné|inscrito)/iu.test(label)))subscribed=true;
            if(subscribed===undefined)subscribed=['true','menu'].includes(button.getAttribute('aria-haspopup'));
            return {button,subscribed,disabled:button.matches(':disabled,[aria-disabled="true"],[aria-busy="true"]')};
        }
        syncSubscription(data) {
            this.subscriptionData=data;
            const state=this.subscriptionState(data.owner);
            if(this.subscriptionPending&&(this.subscriptionPending.video!==this.options.video||this.subscriptionPending.subscribed!==state.subscribed))this.clearSubscription();
            const pending=Boolean(this.subscriptionPending),card=this.q('.channel-card'),button=this.q('.channel-subscribe'),status=this.q('.subscription-state');
            this.q('.owner').hidden=!data.name;
            card.setAttribute('data-subscribed',String(state.subscribed));
            button.hidden=!state.button;button.disabled=pending||state.disabled;
            button.setAttribute('aria-pressed',String(state.subscribed));button.setAttribute('aria-busy',String(pending));
            button.setAttribute('aria-label',`${state.subscribed?this.copy.unsubscribeChannel:this.copy.subscribeChannel} ${data.subscriptionName||data.name||''}`.trim());
            status.hidden=!state.button;
            const label=pending?(state.subscribed?this.copy.unsubscribing:this.copy.subscribing):(state.subscribed?this.copy.subscribed:this.copy.subscribe);
            if(status.dataset.label!==label){
                status.dataset.label=label;
                status.innerHTML=state.subscribed?`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>`:'';
                status.append(this.node('span','sr-only',label));
            }
        }
        clearSubscription(restore=false) {
            clearTimeout(this.subscriptionTimer);this.subscriptionPending=null;
            this.cleanSubscriptionPopups(restore);
            if(this.subscriptionMasks?.size)this.subscriptionTimer=setTimeout(()=>this.clearSubscription(true),2000);
            else{this.subscriptionObserver?.disconnect();this.subscriptionObserver=null;}
        }
        subscriptionPanelTarget(node) {
            const popups=node.closest('ytd-popup-container');let target=node;
            for(let parent=node;parent&&parent!==popups;parent=parent.parentElement){
                if(parent.matches('tp-yt-paper-dialog,dialog,[role="dialog"],[role="alertdialog"],ytd-menu-popup-renderer,yt-menu-popup-renderer,yt-dialog-view-model,yt-confirm-dialog-renderer,ytd-confirm-dialog-renderer,yt-confirm-dialog-view-model,ytd-confirm-dialog-view-model'))target=parent;
            }
            return target;
        }
        subscriptionPopupPassThrough(node) {
            const pattern=/^(?:sign in|log in|войдите|войти|вход в|anmelden|iniciar sesión|se connecter|accedi|fazer login|something went wrong|error\b|что-то пошло не так|произошла ошибка|ошибка|share\b|поделиться|save to\b|сохранить|report\b|пожаловаться)/iu;
            return [text(node.querySelector('h1,h2,[role="heading"],#title')),text(node.querySelector('#confirm-button')),node.getAttribute('aria-label')||'',text(node)].some(value=>pattern.test(value));
        }
        prepareSubscriptionPopups() {
            const pending=this.subscriptionPending,popups=document.querySelector('ytd-popup-container');
            if(!pending?.subscribed||!popups)return;
            const targets=new Set([...popups.querySelectorAll('tp-yt-paper-dialog,dialog,[role="dialog"],[role="alertdialog"],ytd-menu-popup-renderer,yt-menu-popup-renderer,yt-dialog-view-model,yt-confirm-dialog-renderer,ytd-confirm-dialog-renderer,yt-confirm-dialog-view-model,ytd-confirm-dialog-view-model')].map(node=>this.subscriptionPanelTarget(node)));
            for(const target of targets){
                if(pending.existingPanels.has(target)||!pending.visible(target)||this.subscriptionPopupPassThrough(target))continue;
                // Native dialogs can paint their shell and heading before their
                // confirm button mounts. Cover the entire outer panel first.
                this.maskSubscriptionPopup(target);
            }
        }
        cleanSubscriptionPopups(restore=false) {
            for(const [node,value] of this.subscriptionMasks||[]){
                const closed=!node.isConnected||node.closest('[hidden],[aria-hidden="true"]')||!node.getClientRects().length||getComputedStyle(node).visibility==='hidden'||(node.matches('tp-yt-iron-overlay-backdrop')&&!node.hasAttribute('opened'));
                const reused=!node.matches('tp-yt-iron-overlay-backdrop')&&this.subscriptionPopupPassThrough(node);
                if(restore||closed||reused){if(value===null)node.removeAttribute('data-myt-subscription-transient');else node.setAttribute('data-myt-subscription-transient',value);this.subscriptionMasks.delete(node);}
            }
            if(!this.subscriptionPending&&!this.subscriptionMasks?.size){clearTimeout(this.subscriptionTimer);this.subscriptionObserver?.disconnect();this.subscriptionObserver=null;}
        }
        maskSubscriptionPopup(node) {
            const target=this.subscriptionPanelTarget(node);
            this.subscriptionMasks||=new Map();
            if(!this.subscriptionMasks.has(target)){this.subscriptionMasks.set(target,target.getAttribute('data-myt-subscription-transient'));target.setAttribute('data-myt-subscription-transient','');}
            this.maskSubscriptionBackdrops();
        }
        maskSubscriptionBackdrops() {
            if(!this.subscriptionMasks?.size)return;
            for(const backdrop of document.querySelectorAll('tp-yt-iron-overlay-backdrop[opened]')){
                if(!this.subscriptionMasks.has(backdrop)){this.subscriptionMasks.set(backdrop,backdrop.getAttribute('data-myt-subscription-transient'));backdrop.setAttribute('data-myt-subscription-transient','');}
            }
        }
        toggleSubscription() {
            if(this.subscriptionPending)return;
            const data=this.subscriptionData||{},state=this.subscriptionState(data.owner);
            if(!state.button?.isConnected||state.disabled)return;
            this.animateSubscriptionPress();
            clearTimeout(this.subscriptionTimer);this.subscriptionObserver?.disconnect();this.subscriptionObserver=null;this.cleanSubscriptionPopups();
            this.closeMore();
            const visible=node=>Boolean(node.getClientRects().length&&getComputedStyle(node).visibility!=='hidden'&&getComputedStyle(node).display!=='none');
            const popups=document.querySelector('ytd-popup-container');
            const existing=popups?[...popups.querySelectorAll('ytd-menu-service-item-renderer,ytd-menu-navigation-item-renderer,yt-list-item-view-model,[role="menuitem"],#confirm-button,button,[role="button"]')].filter(visible):[];
            const panels=popups?[...popups.querySelectorAll('tp-yt-paper-dialog,dialog,[role="dialog"],[role="alertdialog"],ytd-menu-popup-renderer,yt-menu-popup-renderer,yt-dialog-view-model,yt-confirm-dialog-renderer,ytd-confirm-dialog-renderer,yt-confirm-dialog-view-model,ytd-confirm-dialog-view-model')].map(node=>this.subscriptionPanelTarget(node)).filter(visible):[];
            this.subscriptionPending={video:this.options.video,subscribed:state.subscribed,visible,existing:new Set(existing),existingPanels:new Set(panels)};
            this.subscriptionObserver=new MutationObserver(records=>{
                if(records.some(record=>{const target=record.target instanceof Element?record.target:record.target.parentElement;return data.owner?.contains(target)||target?.closest('ytd-popup-container,tp-yt-iron-overlay-backdrop')||[...record.addedNodes].some(node=>node instanceof Element&&(node.matches('ytd-popup-container,tp-yt-iron-overlay-backdrop')||node.querySelector('ytd-popup-container')));})){if(this.subscriptionPending)this.continueSubscription();else{this.maskSubscriptionBackdrops();this.cleanSubscriptionPopups();}}
            });
            this.subscriptionObserver.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['subscribed','is-subscribed','aria-pressed','aria-label','aria-busy','hidden','aria-hidden','disabled','aria-disabled','style','class','open','opened']});
            this.subscriptionTimer=setTimeout(()=>{this.clearSubscription(true);this.syncSubscription(this.subscriptionData||{});},6000);
            this.syncSubscription(data);
            try{state.button.click();this.continueSubscription();}catch{this.clearSubscription(true);this.syncSubscription(data);}
        }
        animateSubscriptionPress() {
            this.subscriptionPress?.cancel();this.subscriptionPress=null;
            if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
            const card=this.q('.channel-card');if(typeof card.animate!=='function')return;
            const animation=card.animate([{transform:'scale(.98)'},{transform:'scale(1)'}],{duration:180,easing:'cubic-bezier(.2,.8,.2,1)'});
            this.subscriptionPress=animation;
            animation.onfinish=()=>{if(this.subscriptionPress===animation)this.subscriptionPress=null;};
        }
        continueSubscription() {
            const pending=this.subscriptionPending;
            if(!pending)return;
            this.prepareSubscriptionPopups();
            this.cleanSubscriptionPopups();
            this.maskSubscriptionBackdrops();
            this.syncSubscription(this.subscriptionData||{});
            if(this.subscriptionPending!==pending||!pending.subscribed)return;
            const popups=document.querySelector('ytd-popup-container');
            if(!popups)return;
            const unsubscribe=/\bunsubscribe\b|отписаться|отменить подписку|отказаться от подписки|abo beenden|se désabonner|cancelar (?:suscripción|inscrição)|annulla iscrizione/iu;
            const available=node=>!pending.existing.has(node)&&pending.visible(node)&&!node.matches(':disabled,[aria-disabled="true"]')&&unsubscribe.test((node.getAttribute('aria-label')||'')+' '+text(node));
            if(!pending.menuClicked){
                const item=[...popups.querySelectorAll('ytd-menu-service-item-renderer,ytd-menu-navigation-item-renderer,yt-list-item-view-model,[role="menuitem"]')].find(available);
                if(item){this.maskSubscriptionPopup(item);pending.menuClicked=true;item.click();this.continueSubscription();return;}
            }
            if(!pending.confirmClicked){
                const confirm=[...popups.querySelectorAll('yt-confirm-dialog-renderer #confirm-button,ytd-confirm-dialog-renderer #confirm-button,[role="dialog"] #confirm-button,yt-confirm-dialog-view-model button,ytd-confirm-dialog-view-model button,yt-dialog-view-model button,[role="dialog"] button,dialog button,[role="dialog"] [role="button"]')].find(node=>{
                    if(pending.existing.has(node)||!pending.visible(node)||node.matches(':disabled,[aria-disabled="true"]'))return false;
                    const panel=this.subscriptionPanelTarget(node),label=(node.getAttribute('aria-label')||'')+' '+text(node);
                    if(this.subscriptionPopupPassThrough(panel)||!unsubscribe.test(text(panel)))return false;
                    return unsubscribe.test(label)||Boolean(node.closest('#confirm-button'))||/^(?:yes|да|confirm|подтвердить)$/iu.test(label.trim());
                });
                if(confirm){this.maskSubscriptionPopup(confirm);pending.confirmClicked=true;(confirm.querySelector('button')||confirm).click();this.continueSubscription();}
            }
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
            this.descriptionRoot=data.root;
            const prose = this.q('.prose');
            prose.replaceChildren();
            if (data.body) this.copyProse(data.body, prose, true);
            this.q('.description').hidden = !data.root && !prose.textContent.trim();
            this.q('.description').setAttribute('aria-label',this.copy.description);
            this.q('.expand').hidden = prose.textContent.trim().length < 220 && !data.expand;
            this.updateExpanded();
        }
        syncStats() {
            if(!this.host.isConnected)return;
            const stats=this.statsText(this.descriptionRoot?.isConnected?this.descriptionRoot:null),node=this.q('.stats');
            const value=node.querySelector('.stats-value');if(value.textContent!==stats)value.textContent=stats;
            const eye=node.querySelector('.views-icon');if(eye.hidden===this.statsHasViews)eye.hidden=!this.statsHasViews;
            if(node.hidden!==!stats)node.hidden=!stats;
            const card=this.q('.channel-card'),hidden=!this.subscriptionData?.owner&&!stats;
            if(card.hidden!==hidden)card.hidden=hidden;
        }
        compactViews(value) {
            if(!value)return '';
            const unit=value.match(/(тыс\.?|млн\.?|млрд\.?|[kmb])\s*(?:просмотр[а-яё]*|views?)$/iu)?.[1].toLowerCase();
            const digits=value.match(/[\d][\d\s.,]*/u)?.[0].replace(/\s/g,'');
            let count=digits?(unit?Number(digits.replace(',','.')):Number(digits.replace(/[.,]/g,''))):(/no views|нет просмотров|без просмотров/iu.test(value)?0:NaN);
            if(unit)count*=({k:1e3,m:1e6,b:1e9,'тыс':1e3,'млн':1e6,'млрд':1e9})[unit.replace('.','')]||1;
            count=Math.round(count);
            if(!Number.isSafeInteger(count)||count<0)return '';
            const locale=this.options.language==='ru'?'ru-RU':'en-US';
            if(this.viewsLocale!==locale){this.viewsLocale=locale;this.viewsFormat=new Intl.NumberFormat(locale,{notation:'compact',maximumSignificantDigits:3});}
            return this.viewsFormat.format(count).toLowerCase().replace(/\s+/g,' ').replace(/млн$/u,'млн.').replace(/млрд$/u,'млрд.');
        }
        publicationDate(meta,info,readable) {
            const locale=this.options.language==='ru'?'ru-RU':'en-GB';
            if(this.dateLocale!==locale){this.dateLocale=locale;this.dateFormat=new Intl.DateTimeFormat(locale,{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});}
            const format=(year,month,day)=>{
                const date=new Date(Date.UTC(year,month-1,day));
                return year>=1000&&date.getUTCFullYear()===year&&date.getUTCMonth()===month-1&&date.getUTCDate()===day?this.dateFormat.format(date).replace(/\s+/g,' '):'';
            };
            const parse=value=>{
                if(!value)return '';
                let match=value.match(/\b(\d{4})-(\d{2})-(\d{2})(?=T|\s|$)/u);
                if(match)return format(+match[1],+match[2],+match[3]);
                match=value.match(/\b(\d{1,2})([./])(\d{1,2})\2(\d{4})\b/u);
                if(match){const us=match[2]==='/'&&/^en(?:-us)?$/iu.test(document.documentElement.lang);return format(+match[4],+(us?match[1]:match[3]),+(us?match[3]:match[1]));}
                const english=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
                match=value.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s+(\d{4})\b/iu);
                if(match)return format(+match[3],english.indexOf(match[1].toLowerCase())+1,+match[2]);
                match=value.match(/\b(\d{1,2})\.?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z.]*\s+(\d{4})\b/iu);
                if(match)return format(+match[3],english.indexOf(match[2].toLowerCase())+1,+match[1]);
                match=value.match(/(\d{1,2})\.?\s+(янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек)[а-яё.]*\s+(\d{4})/iu);
                if(match){const month=['янв','фев','мар','апр','ма','июн','июл','авг','сен','окт','ноя','дек'].findIndex(prefix=>match[2].toLowerCase().startsWith(prefix));return format(+match[3],month+1,+match[1]);}
                return '';
            };
            const candidates=[meta('meta[itemprop="datePublished"]')?.content,meta('meta[itemprop="uploadDate"]')?.content,info?.querySelector('time[datetime]')?.getAttribute('datetime'),readable,info?.getAttribute('title'),text(info)];
            for(const value of candidates){const date=parse(value);if(date)return date;}
            const details=[...(info?.querySelectorAll('tp-yt-paper-tooltip,yt-tooltip,[role="tooltip"],[title]')||[]),...this.native.querySelectorAll('ytd-watch-info-text #date-text,ytd-watch-info-text tp-yt-paper-tooltip,ytd-video-primary-info-renderer #date')];
            for(const node of details){const date=parse(node.getAttribute('title')||text(node));if(date)return date;}
            return '';
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
            const count=this.compactViews(views);this.statsHasViews=Boolean(count);
            return [count,this.publicationDate(meta,info,readable)].filter(Boolean).join(' · ');
        }
        nativePlayer() {
            const video = this.native.querySelector('#movie_player video, ytd-player video, video.html5-main-video, video');
            return video?.closest('ytd-player') || video?.closest('#movie_player') || video?.closest('#player') || this.native.querySelector('ytd-player, #movie_player');
        }

        island(node,kind,box) {
            if(!node)return;
            if(!this.islands.has(node)){this.islands.set(node,{tabindex:node.getAttribute('tabindex'),popover:node.getAttribute('popover'),style:node.getAttribute('style'),properties:['--myt-island-x','--myt-island-y','--myt-island-w','--myt-island-h','--myt-island-clip',...(kind==='sidecar'?['transform','clip-path']:[])].map(name=>[name,node.style.getPropertyValue(name),node.style.getPropertyPriority(name)]),kind});node.setAttribute('popover','manual');node.dataset.mytWatchIsland=kind;if(kind==='anchor')node.tabIndex=-1;this.open(node);}
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
            this.updateCurrentChapter(true);
        }
        copyProse(source,target,isRoot=false) {
            if(source.nodeType===Node.TEXT_NODE){if(!source.data.trim()&&/\n[\t ]{2,}/.test(source.data))return;target.append(document.createTextNode(source.data));return;}
            if(!(source instanceof Element)||source.matches('script,style,button,tp-yt-paper-tooltip,yt-tooltip,[role="tooltip"],#info-container,#info,#expand,#collapse')||(!isRoot&&source.matches('[role="button"],ytd-structured-description-content-renderer,[data-myt-description-section]')))return;
            if(!isRoot&&/description.*section-(renderer|view-model)$/.test(source.localName))return;
            if(source.tagName==='A') {const url=safeURL(source.href);if(url){const node=this.link(source,'',text(source));node.insertAdjacentHTML('afterbegin',icon('link'));node.firstElementChild.classList.add('link-symbol');const parsed=new URL(url);const time=parsed.searchParams.get('t')||parsed.searchParams.get('start');if(parsed.pathname==='/watch'&&time&&/^\d+s?$/.test(time))node.dataset.seconds=parseInt(time,10);target.append(node);}else target.append(document.createTextNode(text(source)));return;}
            const tag=source.tagName.toLowerCase(),allowed=['p','br','strong','b','em','i','ul','ol','li'];
            const node=allowed.includes(tag)?document.createElement(tag):document.createDocumentFragment();
            for(const child of source.childNodes)this.copyProse(child,node);target.append(node);
        }
        updateExpanded() {this.q('.prose').classList.toggle('expanded',this.expanded);this.q('.expand').textContent=this.expanded?this.copy.less:this.copy.more;this.q('.expand').setAttribute('aria-expanded',String(this.expanded));this.position();}
        sync(options) {
            options={...options,language:"en"};this.options=options;this.copy=words.en;const c=this.copy;
            const media=this.native.querySelector('video');if(media!==this.media){for(const type of ['timeupdate','seeked'])this.media?.removeEventListener(type,this.videoTime);for(const type of ['loadedmetadata','resize'])this.media?.removeEventListener(type,this.videoMetadata);this.media=media;for(const type of ['timeupdate','seeked'])this.media?.addEventListener(type,this.videoTime);for(const type of ['loadedmetadata','resize'])this.media?.addEventListener(type,this.videoMetadata);}
            this.syncTheaterAspect();
            if(document.fullscreenElement){this.updateFullscreenLayout();return;}
            if(this.fullscreenPending){this.updateFullscreenLayout(this.fullscreenPreview);return;}
            this.surface.toggleAttribute('dark',options.dark);this.surface.toggleAttribute('theater',this.native.hasAttribute('theater'));if(this.host.lang!==options.language)this.host.lang=options.language;
            const input=this.q('#watch-search');input.placeholder=c.search;input.setAttribute('aria-label',c.search);this.q('#watch-clear').setAttribute('aria-label',c.clear);
            const metadata=this.native.querySelector('ytd-watch-metadata,ytd-video-primary-info-renderer,ytd-video-secondary-info-renderer');
            this.q('.details').hidden=!metadata;this.q('.media').setAttribute('aria-busy',String(!metadata));
            const descriptionData=this.descriptionData(metadata);
            this.descriptionRoot=descriptionData.root;
            const ownerData=this.channelOwner(metadata);
            const nativeActions=metadata?.querySelector('#actions,#menu-container');
            this.transcriptAvailable=Boolean(this.native.querySelector('ytd-video-description-transcript-section-renderer,ytd-transcript-renderer'));
            if(!this.transcriptAvailable&&this.transcriptOpen)this.closeTranscript();
            const sectionData=[...this.native.querySelectorAll('ytd-macro-markers-list-item-renderer,ytd-info-card-contents-renderer,ytd-video-description-channel-section-renderer')].map(node=>[text(node),node.querySelector('a[href]')?.href]);
            // Only native source data forms this signature. Typing, focus and scroll
            // in our shadow tree do not rebuild controls or disturb selection.
            const signature=JSON.stringify([options.video,options.language,Boolean(options.commentsButton),this.transcriptAvailable,text(metadata?.querySelector('h1'))||document.title,ownerData.name,(ownerData.avatars||[]).map(a=>[a.image.currentSrc||a.image.getAttribute('src'),a.image.naturalWidth]),text(nativeActions),text(descriptionData.body),sectionData,[...this.native.querySelectorAll('ytd-watch-metadata a[href],ytd-video-secondary-info-renderer a[href],ytd-watch-metadata img,ytd-video-secondary-info-renderer img,#description a[href],#description img')].map(node=>[node.href,node.currentSrc||node.getAttribute('src'),node.getAttribute('srcset'),node.getAttribute('data-src'),node.naturalWidth])]);
            if(signature!==this.signature||[...this.sources.values()].some(node=>!node.isConnected)){
                if(this.video!==options.video){this.video=options.video;this.expanded=false;this.closeTranscript();this.viewport.scrollTop=0;}
                this.signature=signature;this.sources.clear();this.sequence=0;
                this.setTitle(text(metadata?.querySelector('h1'))||document.title.replace(/ - YouTube$/,'')||c.video);
                this.renderOwner(ownerData);
                this.closeMore();
                const actions=this.q('.actions');for(const child of [...actions.children])if(child!==options.commentsButton)child.remove();
                const sources={};
                if(nativeActions){
                    const used=new Set();
                    for(const[kind,pattern]of[['share',/share|поделиться/i],['menu',/more|ещё|еще/i]]){
                        const source=[...nativeActions.querySelectorAll('button')].find(b=>!b.closest('[data-myt-votes],#myt-comments-toggle')&&!used.has(b)&&pattern.test(`${b.id} ${b.getAttribute('aria-label')||''} ${text(b)}`));
                        if(source){used.add(source);sources[kind]=source;}
                    }
                }
                if(sources.share||sources.menu||options.commentsButton||this.transcriptAvailable)actions.append(this.moreActions(sources.share,sources.menu));
                this.renderDescription(descriptionData);
                const chapters=this.q('.chapter-list');chapters.replaceChildren();this.chapterButtons=[];this.chapterStarts=[];this.currentChapter=null;this.followedChapter=null;
                for(const {source,time,at,title} of this.chapterData()){const b=this.button('',source);b.className='chapter';b.title=title;b.dataset.seconds=at;b.setAttribute('aria-current','false');b.append(this.node('time','',time),this.node('span','chapter-title',title));chapters.append(b);this.chapterButtons.push(b);this.chapterStarts.push(at);}
                this.q('#watch-chapters').hidden=!chapters.children.length;this.q('#watch-chapters').setAttribute('aria-label',c.chapters);
                const people=this.q('.people');people.replaceChildren();
                for(const card of this.native.querySelectorAll('ytd-info-card-contents-renderer')){const source=card.querySelector('a[href]');if(!source)continue;const name=text(card.querySelector('#title,h3'));if(!name)continue;const a=this.link(source,'person');const img=this.image(card.querySelector('img'));if(img)a.append(img);a.append(this.node('span','',name));people.append(a);}
                this.q('#watch-people').hidden=!people.children.length;this.q('#watch-people h2').textContent=c.people;
                const channel=this.native.querySelector('ytd-video-description-channel-section-renderer');const socials=this.q('.socials');socials.replaceChildren();
                for(const source of channel?.querySelectorAll('a[href],button')||[]){const label=(text(source)||source.getAttribute('aria-label')||'').replace(/\s*↗\s*$/u,'');if(!label)continue;const a=source.tagName==='A'?this.link(source,'social',label):this.button(label,source);a.className='social';a.insertAdjacentHTML('beforeend',icon('arrow'));socials.append(a);}
                this.q('#watch-socials').hidden=!socials.children.length;this.q('#watch-socials h2').textContent=c.socials;
            }
            this.syncSubscription(ownerData);
            this.syncStats();
            this.q('#watch-transcript').hidden=!this.transcriptOpen||!this.transcriptAvailable;this.q('#watch-transcript h2').textContent=c.transcript;this.q('#watch-transcript .hint').textContent=c.transcriptHint;this.q('.transcript-toggle').textContent=this.transcriptOpen?c.hideTranscript:c.showTranscript;this.q('.transcript-search').placeholder=c.find;this.q('.transcript-search').setAttribute('aria-label',c.find);this.q('.transcript-retry').textContent=c.retry;
            this.q('.comments-section').hidden=!options.commentsOpen;this.q('.comments-section h2').textContent=c.comments;
            const player=this.nativePlayer();
            for(const[node,state]of this.islands)if(state.kind==='media'&&node!==player)this.restore(node);
            if(player&&!document.fullscreenElement&&!this.fullscreenPending)this.island(player,'media',()=>this.q('.media').getBoundingClientRect());
            const comments=options.commentsOpen&&(this.native.querySelector('ytd-comments')||this.native.querySelector('ytd-engagement-panel-section-list-renderer[target-id*="comments"],ytd-engagement-panel-section-list-renderer[data-target-id*="comments"]'));
            for(const[node,state]of this.islands)if(state.kind==='comments'&&node!==comments)this.restore(node);
            if(comments)this.island(comments,'comments',()=>this.q('.comments').getBoundingClientRect());
            const candidate=this.native.querySelector('ytd-playlist-panel-renderer#playlist,#playlist ytd-playlist-panel-renderer');
            const candidateCollapsed=Boolean(candidate&&this.isPlaylistCollapsed(candidate));
            const list=new URL(location.href).searchParams.get('list');
            const panel=candidate&&(list||this.playlistVideo===options.video||candidate!==this.playlistPanel&&!candidateCollapsed)?candidate:null;
            const intent=this.playlistIntent?.video===options.video&&(!this.playlistIntent.list||!list||this.playlistIntent.list===list)?this.playlistIntent.open:undefined;
            const collapsed=Boolean(panel&&(intent===false||intent!==true&&candidateCollapsed)),sidecar=collapsed?null:panel;
            if(sidecar)this.preparePlaylistExpanded(sidecar);
            this.syncPlaylistControl(panel,collapsed);
            this.q('.sidecar').hidden=!sidecar;this.q('.layout').classList.toggle('has-sidecar',!!sidecar);this.q('main').classList.toggle('has-sidecar',!!sidecar);
            this.observePlaylist(sidecar);
            for(const[node,state]of this.islands)if(state.kind==='sidecar'&&node!==sidecar)this.restore(node);
            if(sidecar)this.island(sidecar,'sidecar',()=>this.q('.sidecar').getBoundingClientRect());
            const popups=document.querySelector('ytd-popup-container');if(popups)this.island(popups,'popups',()=>({x:0,y:0,width:innerWidth,height:innerHeight}));
            if(this.transcriptOpen)this.renderTranscript();this.layoutTitle();this.position();this.updateCurrentChapter();
        }
        isPlaylistCollapsed(panel) {
            const wrapper=panel.closest('#playlist');
            for(const node of new Set([panel,wrapper].filter(Boolean))){
                if(node.hidden||node.getAttribute('aria-hidden')==='true'||node.getAttribute('aria-expanded')==='false'||(node.hasAttribute('collapsed')&&node.getAttribute('collapsed')!=='false')||node.classList.contains('is-collapsed')||node.classList.contains('collapsed'))return true;
            }
            const known=panel.querySelector('#expand-button,#expand-collapse-button'),toggle=known?.querySelector('button')||known;
            if(toggle&&this.playlistControlVisible(toggle,panel)&&(toggle.getAttribute('aria-expanded')==='false'||/(?:open|show|expand).*playlist|(?:открыть|показать|развернуть|раскрыть).*плейлист/iu.test((toggle.getAttribute('aria-label')||'')+' '+(toggle.getAttribute('title')||''))))return true;
            const items=panel.querySelector('#items');
            return Boolean(items&&(items.hidden||items.getAttribute('aria-hidden')==='true'||items.style.display==='none'));
        }
        playlistHeaderControls(panel) {
            const header=panel.querySelector('#header-contents,#header');
            const controls=new Set([...panel.querySelectorAll('#expand-button,#expand-collapse-button,#collapse-button,#close-button'),...(header?.querySelectorAll('button,[role="button"]')||[])]);
            return [...controls].map(node=>node.matches('button')?node:node.querySelector('button')||node).filter(node=>!node.closest('[data-myt-playlist-close]'));
        }
        playlistControlVisible(control,panel) {
            for(let node=control;node&&node!==panel;node=node.parentElement)if(node.hidden||node.getAttribute('aria-hidden')==='true'||getComputedStyle(node).display==='none')return false;
            return true;
        }
        playlistControlLabel(control) {return control.getAttribute('aria-label')||control.getAttribute('title')||control.parentElement?.getAttribute('aria-label')||text(control);}
        playlistOpener(panel) {
            return this.playlistHeaderControls(panel).find(control=>this.playlistControlVisible(control,panel)&&!/(?:close|hide|collapse|закрыть|скрыть|свернуть)/iu.test(this.playlistControlLabel(control))&&(/(?:open|show|expand|открыть|показать|развернуть|раскрыть)/iu.test(this.playlistControlLabel(control))||control.id==='expand-button'));
        }
        playlistCloser(panel) {
            return this.playlistHeaderControls(panel).find(control=>this.playlistControlVisible(control,panel)&&/(?:close|hide|collapse|закрыть|скрыть|свернуть)/iu.test(this.playlistControlLabel(control)));
        }
        markPlaylistChrome(node,attribute) {
            if(!node)return;this.playlistChrome||=new Map();
            if(!this.playlistChrome.has(node))this.playlistChrome.set(node,{attribute,value:null});
            if(!node.hasAttribute(attribute))node.setAttribute(attribute,'');
        }
        restorePlaylistChrome() {
            this.playlistCloseButton?.remove();this.playlistCloseButton=null;
            for(const[node,{attribute,value}]of this.playlistChrome||[]){if(value===null)node.removeAttribute(attribute);else node.setAttribute(attribute,value);}
            this.playlistChrome?.clear();this.playlistChromePanel=null;
        }
        maskPlaylistControls(panel) {
            for(const control of this.playlistHeaderControls(panel)){
                const label=this.playlistControlLabel(control),known=control.matches('#expand-button,#expand-collapse-button,#collapse-button,#close-button')||control.closest('#expand-button,#expand-collapse-button,#collapse-button,#close-button');
                if(known||/(?:playlist|плейлист)/iu.test(label)&&/(?:open|show|expand|close|hide|collapse|открыть|показать|развернуть|раскрыть|закрыть|скрыть|свернуть)/iu.test(label))this.markPlaylistChrome(control.closest('yt-icon-button')||control,'data-myt-playlist-native-toggle');
            }
            this.markPlaylistChrome(panel.querySelector('#header-contents,#header'),'data-myt-playlist-owned-header');
        }
        preparePlaylistExpanded(panel) {
            if(this.playlistChromePanel!==panel){this.restorePlaylistChrome();this.playlistChromePanel=panel;}
            for(const[node,{attribute,value}]of this.playlistChrome||[])if(!panel.contains(node)){if(value===null)node.removeAttribute(attribute);else node.setAttribute(attribute,value);this.playlistChrome.delete(node);}
            const opener=this.playlistOpener(panel);
            this.playlistExpansionAttempts||=new WeakMap();
            const marker=opener&&this.playlistControlLabel(opener)+'|'+panel.hidden+'|'+panel.getAttribute('collapsed');
            if(opener&&!opener.matches(':disabled,[aria-disabled="true"]')&&this.playlistExpansionAttempts.get(opener)!==marker){this.playlistExpansionAttempts.set(opener,marker);opener.click();}
            for(const node of new Set([panel,panel.closest('#playlist')].filter(Boolean))){node.removeAttribute('hidden');node.removeAttribute('collapsed');node.classList.remove('collapsed','is-collapsed');if(node.getAttribute('aria-hidden')==='true')node.setAttribute('aria-hidden','false');if(node.getAttribute('aria-expanded')==='false')node.setAttribute('aria-expanded','true');}
            const items=panel.querySelector('#items');if(items){items.removeAttribute('hidden');if(items.getAttribute('aria-hidden')==='true')items.setAttribute('aria-hidden','false');if(items.style.display==='none')items.style.removeProperty('display');}
            this.maskPlaylistControls(panel);
            if(!this.playlistCloseButton){const button=document.createElement('button');button.type='button';button.className='myt-playlist-close';button.dataset.mytPlaylistClose='';button.innerHTML=icon('close');button.onclick=event=>{event.preventDefault();event.stopPropagation();this.closePlaylist();};this.playlistCloseButton=button;}
            const close=this.playlistCloseButton;if(close.parentElement!==panel)panel.append(close);close.hidden=false;close.title=this.copy.closePlaylist;close.setAttribute('aria-label',this.copy.closePlaylist);
        }
        closePlaylist() {
            const panel=this.playlistPanel;if(!panel)return;
            this.playlistIntent={video:this.options.video,list:new URL(location.href).searchParams.get('list'),open:false};
            const closer=this.playlistCloser(panel);if(closer&&!closer.matches(':disabled,[aria-disabled="true"]'))closer.click();
            this.sync(this.options);
        }
        syncPlaylistControl(panel,collapsed) {
            this.playlistPanel=panel;this.playlistCollapsed=collapsed;this.playlistVideo=panel?this.options.video:null;
            this.playlistNativeCollapsed=Boolean(panel&&this.isPlaylistCollapsed(panel));
            this.playlistStateObserver?.disconnect();
            if(panel){
                this.playlistStateObserver||=new MutationObserver(records=>{
                    const meaningful=records.some(record=>{
                        const target=record.target instanceof Element?record.target:record.target.parentElement;
                        if(!target||target.closest('[data-myt-playlist-close]')||target.closest('#items'))return false;
                        if(record.type==='attributes')return true;
                        return [...record.addedNodes,...record.removedNodes].some(node=>node instanceof Element&&!node.matches('[data-myt-playlist-close]')&&(node.matches('#header,#header-contents,#container,button,yt-icon-button')||node.querySelector('button,yt-icon-button')));
                    });
                    if(!meaningful||!this.playlistPanel?.isConnected)return;
                    this.maskPlaylistControls(this.playlistPanel);
                    const changed=this.isPlaylistCollapsed(this.playlistPanel)!==this.playlistNativeCollapsed;
                    if((changed||!this.playlistCollapsed)&&!this.sourceFrame)this.sourceFrame=requestAnimationFrame(()=>{this.sourceFrame=0;if(this.host.isConnected)this.sync(this.options);});
                });
                // Listen to the header and its ancestor chain, not the virtualized
                // item subtree: scrolling can recycle hundreds of row attributes.
                const stateOptions={childList:true,attributes:true,attributeFilter:['collapsed','hidden','aria-hidden','aria-expanded','aria-label','title']};
                const header=panel.querySelector('#header-contents,#header');
                this.playlistStateObserver.observe(panel,header?stateOptions:{...stateOptions,subtree:true});
                if(header){
                    this.playlistStateObserver.observe(header,{...stateOptions,subtree:true});
                    for(let node=header.parentElement;node&&node!==panel;node=node.parentElement)this.playlistStateObserver.observe(node,stateOptions);
                }
                const wrapper=panel.closest('#playlist');if(wrapper&&wrapper!==panel)this.playlistStateObserver.observe(wrapper,{attributes:true,attributeFilter:['collapsed','hidden','aria-hidden','aria-expanded','class']});
            }else this.restorePlaylistChrome();
            if(this.playlistCloseButton)this.playlistCloseButton.hidden=collapsed||!panel;
            if(!this.playlistButton&&panel){this.playlistButton=this.button('');this.playlistButton.className='playlist-toggle';this.playlistButton.dataset.watchAction='playlist';}
            const button=this.playlistButton;if(!button)return;
            const actions=this.q('.actions');if(button.parentElement!==actions)actions.prepend(button);
            button.hidden=!panel||!collapsed;button.disabled=Boolean(panel&&this.playlistOpener(panel)?.matches(':disabled,[aria-disabled="true"]'));
            if(button.dataset.language!==this.options.language){button.dataset.language=this.options.language;button.replaceChildren();button.insertAdjacentHTML('afterbegin',icon('playlist'));button.append(document.createTextNode(this.copy.openPlaylist));}
            button.title=this.copy.openPlaylist;button.setAttribute('aria-expanded',String(!collapsed));
        }
        openPlaylist() {
            const panel=this.playlistPanel;if(!panel?.isConnected)return;
            this.closeMore();this.playlistIntent={video:this.options.video,list:new URL(location.href).searchParams.get('list'),open:true};
            this.playlistExpansionAttempts=new WeakMap();
            this.sync(this.options);
        }
        observePlaylist(source) {
            this.playlistSource=source;
            const nodes=[source,source?.querySelector('#header')].filter(Boolean);
            for(const node of this.playlistNodes||[])if(!nodes.includes(node))this.observer.unobserve(node);
            for(const node of nodes)if(!this.playlistNodes?.includes(node))this.observer.observe(node);
            this.playlistNodes=nodes;
            if(source)this.syncPlaylistPlayerHeight();
            else {this.surface.style.removeProperty('--playlist-min-height');this.surface.style.removeProperty('--playlist-player-height');}
        }
        syncPlaylistPlayerHeight() {
            const height=this.q('.media').getBoundingClientRect().height;if(!height)return;
            const value=height+'px';
            if(this.surface.style.getPropertyValue('--playlist-player-height')!==value)this.surface.style.setProperty('--playlist-player-height',value);
        }
        syncPlaylistMinimum() {
            const source=this.playlistSource;if(!source?.isConnected)return;
            this.syncPlaylistPlayerHeight();
            const rows=[source.querySelector('ytd-playlist-panel-video-renderer'),source.querySelector('ytd-playlist-panel-video-renderer ~ ytd-playlist-panel-video-renderer')].filter(Boolean);
            const first=rows[0]?.getBoundingClientRect(),second=rows[1]?.getBoundingClientRect();
            if(!first?.height)return;
            const panel=source.getBoundingClientRect(),list=source.querySelector('#items'),header=source.querySelector('#header');
            const controls=list?Math.max(0,list.getBoundingClientRect().top-panel.top):(header?.getBoundingClientRect().height||64);
            const gap=second?Math.max(0,Math.min(32,second.top-first.bottom)):0;
            const minimum=Math.ceil(controls+first.height+(second?.height||first.height)+gap+2)+'px';
            if(this.surface.style.getPropertyValue('--playlist-min-height')!==minimum)this.surface.style.setProperty('--playlist-min-height',minimum);
        }
        position() {
            if(!this.host.isConnected||document.fullscreenElement||this.fullscreenPending)return;
            this.positionedScroll=this.viewport.scrollTop;
            const headerBottom=this.q('.header').getBoundingClientRect().bottom;
            // Read all rectangles before writing styles: multiple native islands
            // otherwise alternate forced layout and style invalidation on scroll.
            const boxes=[];
            for(const[node,state]of this.islands){if(!node.isConnected){this.restore(node);continue;}if(state.box)boxes.push([node,state,state.box()]);}
            for(const[node,state,b]of boxes){if(state.kind==='media'&&(state.width!==b.width||state.height!==b.height)){state.width=b.width;state.height=b.height;this.resizeNativePlayer();}const clip=Math.max(0,headerBottom-b.y);if(state.kind==='sidecar'){const transform=`translate3d(${b.x}px,${b.y}px,0)`,mask=`inset(${clip}px 0 0)`;if(node.style.getPropertyValue('transform')!==transform)node.style.setProperty('transform',transform,'important');if(node.style.getPropertyValue('clip-path')!==mask)node.style.setProperty('clip-path',mask,'important');}const props={'--myt-island-x':`${b.x}px`,'--myt-island-y':`${b.y}px`,'--myt-island-w':`${b.width}px`,'--myt-island-h':`${b.height}px`,'--myt-island-clip':['media','comments','sidecar'].includes(state.kind)?`${Math.max(0,headerBottom-b.y)}px`:'0px'};for(const[k,v]of Object.entries(props)){if(state.kind==='sidecar'&&['--myt-island-x','--myt-island-y','--myt-island-clip'].includes(k))continue;if(node.style.getPropertyValue(k)!==v)node.style.setProperty(k,v);}}
        }
        updateCurrentChapter(follow=false) {
            const time=this.media?.currentTime||0,starts=this.chapterStarts||[];
            let low=0,high=starts.length;
            while(low<high){const mid=(low+high)>>>1;if(starts[mid]<=time)low=mid+1;else high=mid;}
            const current=this.chapterButtons?.[low-1]||null,previous=this.currentChapter;
            if(current!==previous){previous?.setAttribute('aria-current','false');current?.setAttribute('aria-current','true');this.currentChapter=current;}
            if(!current||(!follow&&current===this.followedChapter))return;
            const list=this.q('.chapter-list'),width=list.clientWidth;
            if(!width)return;
            this.followedChapter=current;
            const frame=list.getBoundingClientRect(),card=current.getBoundingClientRect();
            // Move only the chapter rail, keeping the video and page in place.
            if(card.left<frame.left-1||card.right>frame.left+width+1)list.scrollTo({left:list.scrollLeft+card.left-frame.left-(width-card.width)/2,behavior:'auto'});
        }
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
        destroy() {this.playlistStateObserver?.disconnect();this.restorePlaylistChrome();clearTimeout(this.titleTimer);cancelAnimationFrame(this.geometryFrame);cancelAnimationFrame(this.sourceFrame);this.subscriptionPress?.cancel();this.subscriptionPress=null;this.clearSubscription(true);this.clearFullscreenPreview();this.restoreFullscreenLayout();clearTimeout(this.fullscreenTimer);for(const type of ['click','dblclick','keydown'])window.removeEventListener(type,this.fullscreenIntent,true);document.removeEventListener('fullscreenerror',this.fullscreenError);this.closeMore();this.closeTranscript();cancelAnimationFrame(this.resizeFrame);this.observer.disconnect();document.removeEventListener('keydown',this.shortcut);window.removeEventListener('wheel',this.nativeWheel,true);window.removeEventListener('resize',this.geometry);document.removeEventListener('fullscreenchange',this.fullscreen);for(const type of ['timeupdate','seeked'])this.media?.removeEventListener(type,this.videoTime);for(const type of ['loadedmetadata','resize'])this.media?.removeEventListener(type,this.videoMetadata);this.native.removeEventListener('load',this.sourceLoad,true);delete this.native.dataset.mytWatchSource;for(const node of [...this.islands.keys()])this.restore(node);this.host.remove();delete document.documentElement.dataset.mytWatchUi;window.dispatchEvent(new Event('resize'));}
    }
    globalThis.MinimalYouTubeWatch=WatchView;
})();
