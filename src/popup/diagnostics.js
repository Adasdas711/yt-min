/* A diagnostic report of the current YouTube tab, copied from the popup.
   Self-contained: the popup runs this function in the page (MAIN world). It
   reads only page structure and timing: no cookies, account or form data. */
globalThis.minimalYouTubeDiagnostics = function minimalYouTubeDiagnostics() {
    "use strict";
    const H = document.documentElement, q = s => document.querySelector(s);
    const visible = n => Boolean(n?.checkVisibility?.({ checkOpacity: true, checkVisibilityCSS: true }) && n.getClientRects().length);
    const json = v => { try { return JSON.parse(v || "null"); } catch { return null; } };
    const shadowState = (host, selectors) => {
        const root = host?.shadowRoot, out = {};
        for (const s of selectors) { const n = root?.querySelector(s); out[s] = n ? (n.hidden ? "hidden" : "shown") : "missing"; }
        return out;
    };
    const model = json(H.getAttribute("data-myt-page-model"));
    const watch = json(H.getAttribute("data-myt-watch-model"));
    const loaf = { frames: 0, ms: 0, worst: 0, styleLayoutMs: 0, scripts: {} };
    for (const f of performance.getEntriesByType("long-animation-frame")) {
        loaf.frames++; loaf.ms += f.duration; loaf.worst = Math.max(loaf.worst, f.duration);
        if (f.styleAndLayoutStart) loaf.styleLayoutMs += f.startTime + f.duration - f.styleAndLayoutStart;
        for (const s of f.scripts || []) {
            const key = (s.sourceURL || "?").replace(/^[a-z-]+:\/\/[^/]+/, "").replace(/[?#].*$/, "").slice(-60) + " :: " + (s.sourceFunctionName || s.invokerType || "?").slice(0, 40);
            loaf.scripts[key] = (loaf.scripts[key] || 0) + s.duration;
        }
    }
    loaf.scripts = Object.entries(loaf.scripts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => Math.round(v) + "ms " + k);
    for (const k of ["ms", "worst", "styleLayoutMs"]) loaf[k] = Math.round(loaf[k]);
    const network = {};
    for (const e of performance.getEntriesByType("resource")) {
        let k; try { const u = new URL(e.name); k = u.hostname.replace(/^www\./, "") + u.pathname.replace(/\/[^/]{20,}.*$/, "/*").replace(/^\/vi\/.*/, "/vi/*").slice(0, 50); } catch { continue; }
        const g = network[k] ||= { n: 0, kb: 0 }; g.n++; g.kb += (e.transferSize || 0) / 1024;
    }
    const dormant = [...document.querySelectorAll("[data-myt-dormant]")];
    return {
        report: "minimal-youtube-diagnostics",
        time: new Date().toISOString(),
        url: location.pathname + location.search.slice(0, 120),
        browser: (navigator.userAgent.match(/(?:Chrome|Firefox|Edg)\/[\d.]+/) || [""])[0],
        viewport: innerWidth + "x" + innerHeight, dpr: devicePixelRatio,
        uptimeSeconds: Math.round(performance.now() / 1000),
        extension: {
            active: H.classList.contains("minimal-youtube"),
            attributes: [...H.attributes].map(a => a.name).filter(n => n.startsWith("data-myt")),
            page: H.dataset.mytPage || null, previousPage: H.dataset.mytPreviousPage || null,
            loading: H.hasAttribute("data-myt-loading"),
        },
        model: model && { type: model.type, items: model.items?.length, more: model.more, loading: model.loading, chips: model.chips?.length },
        watch: q("ytd-watch-flexy") && {
            dataForThisVideo: Boolean(watch && new URLSearchParams(location.search).get("v") === watch.video),
            islands: [...document.querySelectorAll("[data-myt-watch-island]")].map(n => n.getAttribute("data-myt-watch-island")),
            ownPlaylist: Boolean(q("#myt-watch")?.shadowRoot?.querySelector(".own-playlist")),
            playlistPanels: [...document.querySelectorAll("ytd-playlist-panel-renderer")].map(n => n.getElementsByTagName("*").length + (n.hasAttribute("data-myt-dormant") ? " dormant" : "")),
            comments: document.querySelectorAll("ytd-comment-thread-renderer").length,
            scrollBound: Boolean(q("[data-myt-scroll-bound]")),
        },
        search: q("#myt-search") && {
            ...shadowState(q("#myt-search"), [".skeleton", ".empty", ".loading-more", ".filters"]),
            cards: q("#myt-search").shadowRoot?.querySelectorAll(".media").length || 0,
            channels: q("#myt-search").shadowRoot?.querySelectorAll("[data-myt-search-channel-card]").length || 0,
            layoutPaths: document.querySelectorAll("[data-myt-search-layout-path]").length,
        },
        playlist: q("#myt-playlist-rows") && {
            rows: document.querySelectorAll("#myt-playlist-rows [data-myt-owned-playlist-card]").length,
            skeleton: !q(".myt-playlist-skeleton")?.hidden, empty: !q(".myt-playlist-empty")?.hidden,
        },
        miniplayer: q("ytd-miniplayer") && { visible: visible(q("ytd-miniplayer")), active: q("ytd-app")?.hasAttribute("miniplayer-is-active") || false },
        dom: {
            nodes: document.getElementsByTagName("*").length,
            dormantParts: dormant.length, dormantNodes: dormant.reduce((s, n) => s + n.getElementsByTagName("*").length, 0),
        },
        longFrames: loaf,
        network: Object.entries(network).sort((a, b) => b[1].kb - a[1].kb).slice(0, 15).map(([k, g]) => Math.round(g.kb) + "KB x" + g.n + " " + k),
        memoryMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
    };
};
