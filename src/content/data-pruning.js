/* Runs in YouTube's MAIN world before its bootstrap. Feed data is discarded
   before renderers/cache retain it. No player responses, credentials or media
   requests are intercepted and no copy of removed data is kept. */
(() => {
    "use strict";
    if (globalThis.__minimalYouTubeDataPruning) return;
    Object.defineProperty(globalThis, "__minimalYouTubeDataPruning", { value: true });
    const nativeParse = JSON.parse;
    const nativeResponseJSON = Response.prototype.json;
    const shorts = new Set(["reelShelfRenderer", "reelItemRenderer", "shortsShelfRenderer", "shortsLockupViewModel", "shortsLockupViewModelV2"]);
    const related = new Set(["compactVideoRenderer", "compactPlaylistRenderer", "compactRadioRenderer", "videoRenderer", "playlistRenderer", "radioRenderer", "lockupViewModel", "richItemRenderer", "relatedChipCloudRenderer", "continuationItemRenderer"]);
    const relatedTargets = new Set(["watch-next-feed", "watch-next-feed-recommendations", "watch-secondary-results"]);
    let processed = new WeakSet();
    let enabled = false;
    let initialDescriptor;
    let initialValue;
    let initialHook = false;

    function initialGet() { return initialDescriptor?.get ? initialDescriptor.get.call(window) : initialValue; }
    function initialSet(value) {
        const result = trim(value);
        if (initialDescriptor?.set) initialDescriptor.set.call(window, result);
        else initialValue = result;
    }
    function shortItem(item) {
        if (!item || typeof item !== "object") return false;
        if (Object.keys(item).some(key => shorts.has(key))) return true;
        if (item.richShelfRenderer?.isShorts === true) return true;
        if (item.richSectionRenderer) return shortItem(item.richSectionRenderer.content);
        if (item.richItemRenderer) return shortItem(item.richItemRenderer.content);
        const url = item.videoRenderer?.navigationEndpoint?.commandMetadata?.webCommandMetadata?.url;
        return typeof url === "string" && /^\/shorts(?:\/|$)/.test(url);
    }
    function hiddenShelf(item) {
        const content = item?.richSectionRenderer?.content || item;
        const shelf = content?.shelfRenderer || content?.richShelfRenderer;
        if (!shelf) return false;
        const title = shelf.title?.simpleText || shelf.title?.runs?.map(run => run.text).join("") || "";
        if (location.pathname === "/results") return /^(latest(?: videos)? from|new videos from|новые видео на канале|последние видео (?:на канале|от))\s+/iu.test(title);
        return /^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/.test(location.pathname) && /^(new uploads|новые (?:видео|загрузки)|последние (?:видео|загрузки))(?=$|\s)/iu.test(title);
    }
    function compact(array, remove) {
        let kept = 0;
        for (const item of array) if (!remove(item)) array[kept++] = item;
        const removed = array.length - kept;
        array.length = kept;
        return removed;
    }
    function trimRecommendations(root) {
        const seen = new WeakSet();
        function visit(node) {
            if (!node || typeof node !== "object" || seen.has(node)) return 0;
            seen.add(node);
            if (node.playlistPanelRenderer || node.liveChatRenderer || node.engagementPanelSectionListRenderer ||
                /comments/.test(node.itemSectionRenderer?.targetId || "")) return 0;
            let removed = 0;
            if (Array.isArray(node)) {
                removed += compact(node, item => item && Object.keys(item).some(key => related.has(key)));
                for (const child of node) removed += visit(child);
            } else {
                for (const child of Object.values(node)) removed += visit(child);
                if (removed && ((Array.isArray(node.contents) && !node.contents.length) ||
                    (Array.isArray(node.results) && !node.results.length))) delete node.continuations;
            }
            return removed;
        }
        return visit(root);
    }
    function feed(data) {
        if (data?.streamingData || data?.playabilityStatus || data?.videoDetails) return false;
        const contents = data?.contents;
        return Boolean(contents?.twoColumnWatchNextResults || contents?.twoColumnSearchResultsRenderer ||
            contents?.twoColumnBrowseResultsRenderer || contents?.singleColumnBrowseResultsRenderer ||
            data?.onResponseReceivedActions || data?.onResponseReceivedCommands || data?.onResponseReceivedEndpoints ||
            data?.continuationContents);
    }
    function trim(data) {
        if (!enabled || !data || typeof data !== "object" || !feed(data) || processed.has(data)) return data;
        try {
            let removed = 0;
            const secondary = data.contents?.twoColumnWatchNextResults?.secondaryResults;
            if (secondary) removed += trimRecommendations(secondary);
            const seen = new WeakSet();
            const stack = [data];
            while (stack.length) {
                const node = stack.pop();
                if (!node || typeof node !== "object" || seen.has(node)) continue;
                seen.add(node);
                if (Array.isArray(node)) {
                    removed += compact(node, item => shortItem(item) || hiddenShelf(item));
                    for (const child of node) if (child && typeof child === "object") stack.push(child);
                    continue;
                }
                // These fields are only used to start hover/animated previews.
                // Static thumbnails and the click/navigation endpoint stay intact.
                if (node.inlinePlaybackEndpoint) { delete node.inlinePlaybackEndpoint; removed++; }
                if (node.richThumbnail?.movingThumbnailRenderer) { delete node.richThumbnail; removed++; }
                const action = node.appendContinuationItemsAction || node.reloadContinuationItemsCommand;
                if (action && relatedTargets.has(action.targetId) && Array.isArray(action.continuationItems)) {
                    removed += trimRecommendations(action.continuationItems);
                }
                for (const value of Object.values(node)) if (value && typeof value === "object") stack.push(value);
            }
            processed.add(data);
            if (removed && document.documentElement && !document.documentElement.hasAttribute("data-myt-pruned")) {
                document.documentElement.setAttribute("data-myt-pruned", "");
            }
        } catch { /* Unexpected A/B-test data must not break native parsing. */ }
        return data;
    }
    function parse(...args) { return trim(Reflect.apply(nativeParse, this, args)); }
    function responseJSON(...args) { return Reflect.apply(nativeResponseJSON, this, args).then(trim); }
    function install() {
        JSON.parse = parse;
        Response.prototype.json = responseJSON;
        const descriptor = Object.getOwnPropertyDescriptor(window, "ytInitialData");
        if (!descriptor || descriptor.configurable) {
            initialDescriptor = descriptor;
            initialValue = descriptor?.value;
            Object.defineProperty(window, "ytInitialData", { configurable: true, enumerable: true, get: initialGet, set: initialSet });
            initialHook = true;
            const value = initialGet();
            if (value) initialSet(value);
        }
    }
    function uninstall() {
        if (JSON.parse === parse) JSON.parse = nativeParse;
        if (Response.prototype.json === responseJSON) Response.prototype.json = nativeResponseJSON;
        if (initialHook && Object.getOwnPropertyDescriptor(window, "ytInitialData")?.set === initialSet) {
            const value = initialGet();
            if (initialDescriptor?.get || initialDescriptor?.set) Object.defineProperty(window, "ytInitialData", initialDescriptor);
            else Object.defineProperty(window, "ytInitialData", { ...(initialDescriptor || { configurable: true, enumerable: true, writable: true }), value });
            initialValue = undefined;
            initialDescriptor = undefined;
        }
        initialHook = false;
    }
    function configure(value) {
        if (enabled === value) return;
        enabled = value;
        if (enabled) { processed = new WeakSet(); install(); }
        else uninstall();
    }
    document.addEventListener("minimal-youtube:optimization", event => {
        if (typeof event.detail?.enabled === "boolean") configure(event.detail.enabled);
    });
    // This script is registered only while focus mode is enabled.
    configure(true);
})();
