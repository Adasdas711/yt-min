(() => {
    "use strict";

    function initialize() {
    const root = document.documentElement;
    const hiddenAttribute = "data-myt-hidden";
    const hiddenElements = new Set();
    const pendingRoots = new Set();
    const nativeShorts = [
        "ytd-reel-shelf-renderer", "ytd-reel-item-renderer",
        "ytd-reel-video-renderer", "yt-shorts-lockup-view-model", "ytm-shorts-lockup-view-model",
        "yt-shorts-shelf-view-model", "ytd-rich-shelf-renderer[is-shorts]",
        "ytm-shorts-lockup-view-model-v2", "yt-shorts-shelf-view-model-v2",
        ".ytShortsLockupViewModelHost", ".shortsLockupViewModelHost", ".ytmShortsLockupViewModelHost",
        "ytd-video-renderer[is-shorts]", "ytd-rich-item-renderer[is-shorts]",
    ].join(",");
    const cardSelector = [
        "ytd-rich-item-renderer", "ytd-video-renderer", "ytd-grid-video-renderer",
        "ytd-compact-video-renderer", "ytd-reel-item-renderer", "yt-lockup-view-model",
        "ytd-guide-entry-renderer", "ytd-mini-guide-entry-renderer",
        "yt-tab-shape", "tp-yt-paper-tab", "[role='tab']",
    ].join(",");
    const tabSelector = "yt-tab-shape, tp-yt-paper-tab, [role='tab'], yt-chip-cloud-chip-renderer";
    const channelRoute = /^\/(?:@[^/]+|(?:channel|c|user)\/[^/]+)(?:\/|$)/;
    const channelShorts = /^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))\/shorts\/?$/;
    const ru = (document.documentElement.lang || navigator.language).toLowerCase().startsWith("ru");
    const copy = ru ? {
        search: "Поиск на YouTube", submit: "Найти", clear: "Очистить поиск",
        label: "Поиск видео", light: "Светлая тема", dark: "Тёмная тема",
        comments: "Комментарии", hideComments: "Скрыть комментарии",
    } : {
        search: "Search YouTube", submit: "Search", clear: "Clear search",
        label: "Search videos", light: "Light theme", dark: "Dark theme",
        comments: "Comments", hideComments: "Hide comments",
    };
    let enabled = false;
    let settingsReady = false;
    let currentURL = "";
    let pendingNavigation = null;
    let navigationSource = "";
    let redirectingURL = "";
    let transitionActive = false;
    let home = null;
    let query = "";
    let frame = 0;
    let storageRevision = 0;
    let theme = null;
    let themeRevision = 0;
    let themeWrite = 0;
    let watchVideo = null;
    let commentsOpen = false;
    let commentsButton = null;
    const voteElements = new Set();
    const searchVideoCards = new Set();
    const commentPanelStates = new Map();
    const voteSelector = [
        "ytd-segmented-like-dislike-button-renderer", "segmented-like-dislike-button-view-model",
        "yt-segmented-like-dislike-button-view-model", "like-button-view-model", "dislike-button-view-model",
        "ytd-like-button-renderer", "ytd-dislike-button-renderer",
        "[target-id='watch-like']", "[target-id='watch-dislike']",
    ].join(",");

    function renderTheme() {
        if (enabled) root.dataset.mytTheme = theme || (root.hasAttribute("dark") ? "dark" : "light");
        else delete root.dataset.mytTheme;
        if (home) home.dataset.mytTheme = root.dataset.mytTheme || "";
        const button = home?.querySelector("#myt-theme-toggle");
        if (!button) return;
        const dark = theme ? theme === "dark" : root.hasAttribute("dark");
        button.dataset.theme = dark ? "dark" : "light";
        const text = dark ? copy.light : copy.dark;
        if (button.querySelector("span").textContent !== text) button.querySelector("span").textContent = text;
        if (button.getAttribute("aria-label") !== text) button.setAttribute("aria-label", text);
    }

    function setCommentsOpen(open) {
        commentsOpen = open;
        if (open) root.dataset.mytComments = "open";
        else delete root.dataset.mytComments;
        if (!open) restoreCommentPanels();
        if (!commentsButton) return;
        commentsButton.setAttribute("aria-expanded", String(open));
        const text = open ? copy.hideComments : copy.comments;
        const label = commentsButton.querySelector("span");
        if (label.textContent !== text) label.textContent = text;
    }

    function restoreCommentPanels() {
        for (const [panel, attributes] of commentPanelStates) {
            for (const [name, value] of attributes) {
                if (value === null) panel.removeAttribute(name);
                else panel.setAttribute(name, value);
            }
        }
        commentPanelStates.clear();
    }

    function syncCommentPanels(watch) {
        const inlineComments = [...watch.querySelectorAll("ytd-comments")].some(element =>
            !element.closest("ytd-engagement-panel-section-list-renderer"));
        if (!commentsOpen || inlineComments) {
            if (commentPanelStates.size) restoreCommentPanels();
            return;
        }
        // Some YouTube layouts render comments only in an engagement panel.
        // Expand that native panel, then restore its exact prior state on close.
        const panel = watch.querySelector('ytd-engagement-panel-section-list-renderer:is([target-id="engagement-panel-comments-section"], [data-target-id="engagement-panel-comments-section"])');
        if (!panel) return;
        if (!commentPanelStates.has(panel)) {
            commentPanelStates.set(panel, ["visibility", "hidden", "aria-hidden"].map(name => [name, panel.getAttribute(name)]));
        }
        if (panel.getAttribute("visibility") !== "ENGAGEMENT_PANEL_VISIBILITY_EXPANDED") {
            panel.setAttribute("visibility", "ENGAGEMENT_PANEL_VISIBILITY_EXPANDED");
        }
        if (panel.hasAttribute("hidden")) panel.removeAttribute("hidden");
        if (panel.getAttribute("aria-hidden") !== "false") panel.setAttribute("aria-hidden", "false");
        if (panel.id) commentsButton.setAttribute("aria-controls", panel.id);
    }

    function resetWatch() {
        setCommentsOpen(false);
        watchVideo = null;
        commentsButton?.remove();
        commentsButton = null;
        for (const element of voteElements) element.removeAttribute("data-myt-votes");
        voteElements.clear();
    }

    function syncSearch(scope = document) {
        for (const card of searchVideoCards) {
            if (!enabled || root.dataset.mytPage !== "search" || !card.isConnected) {
                card.removeAttribute("data-myt-search-video");
                searchVideoCards.delete(card);
            }
        }
        if (!enabled || root.dataset.mytPage !== "search") return;
        const cards = [
            ...(scope instanceof Element && scope.matches("yt-lockup-view-model") ? [scope] : []),
            ...scope.querySelectorAll("yt-lockup-view-model"),
        ];
        for (const card of cards) {
            if (!card.closest("ytd-search")) continue;
            const anchor = card.querySelector("a[href]");
            const url = anchor && new URL(anchor.href, location.href);
            // Playlist/channel lockups keep their native information. Only an
            // ordinary video result gets the compact title/channel treatment.
            const video = url?.origin === location.origin && url.pathname === "/watch" && !url.searchParams.has("list");
            if (video && !searchVideoCards.has(card)) {
                card.setAttribute("data-myt-search-video", "");
                searchVideoCards.add(card);
            } else if (!video) {
                card.removeAttribute("data-myt-search-video");
                searchVideoCards.delete(card);
            }
        }
    }

    function syncWatch() {
        if (!enabled || root.dataset.mytPage !== "watch") {
            if (commentsButton || watchVideo !== null) resetWatch();
            return;
        }
        const video = new URL(location.href).searchParams.get("v") || "";
        if (watchVideo !== video) {
            watchVideo = video;
            setCommentsOpen(false);
        }
        const active = element => !element.closest("[hidden], [aria-hidden='true']") && getComputedStyle(element).display !== "none";
        const watch = [...document.querySelectorAll("ytd-watch-flexy:not([hidden])")].find(active);
        const metadata = watch && [...watch.querySelectorAll("ytd-watch-metadata, ytd-video-primary-info-renderer")].find(active);
        if (!metadata) {
            commentsButton?.remove();
            return;
        }
        const votes = [...metadata.querySelectorAll(voteSelector)];
        for (const element of voteElements) {
            if (!element.isConnected || !metadata.contains(element) || !element.matches(voteSelector)) {
                element.removeAttribute("data-myt-votes");
                voteElements.delete(element);
            }
        }
        for (const element of votes) {
            if (!voteElements.has(element)) {
                element.setAttribute("data-myt-votes", "");
                voteElements.add(element);
            }
        }
        const row = [...metadata.querySelectorAll("#top-level-buttons-computed, #top-level-buttons")].find(active) ||
            votes.find(element => !element.closest("[hidden]"))?.parentElement ||
            [...metadata.querySelectorAll("#actions, #menu-container")].find(active);
        if (!row) {
            commentsButton?.remove();
            return;
        }
        if (!commentsButton) {
            commentsButton = document.createElement("button");
            commentsButton.id = "myt-comments-toggle";
            commentsButton.className = "myt-comments-toggle";
            commentsButton.type = "button";
            commentsButton.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z"/><path d="M7 9h10M7 13h6"/></svg><span></span>';
            commentsButton.addEventListener("click", () => {
                setCommentsOpen(!commentsOpen);
                syncWatch();
            });
        }
        const comments = watch.querySelector("ytd-comments[id]");
        if (comments) commentsButton.setAttribute("aria-controls", comments.id);
        else commentsButton.removeAttribute("aria-controls");
        setCommentsOpen(commentsOpen);
        syncCommentPanels(watch);
        // Keep the native vote DOM for a complete restore when disabled. The new
        // button occupies its slot; share/save/menu buttons remain in their order.
        let slot = votes.find(element => row.contains(element));
        while (slot && slot.parentElement !== row) slot = slot.parentElement;
        if (commentsButton.parentElement !== row || (slot && commentsButton.nextElementSibling !== slot)) {
            row.insertBefore(commentsButton, slot || row.firstChild);
        }
    }

    function shortsDestination(value) {
        let url;
        try { url = new URL(value, location.href); } catch { return null; }
        if (url.protocol !== "https:" || !(url.hostname === "youtube.com" || url.hostname.endsWith(".youtube.com"))) return null;
        if (/^\/shorts(?:\/|$)/.test(url.pathname)) return "/";
        const channel = url.pathname.match(channelShorts);
        return channel ? `${channel[1]}/videos` : null;
    }

    function hide(element) {
        if (!element || hiddenElements.has(element)) return;
        element.setAttribute(hiddenAttribute, "shorts");
        hiddenElements.add(element);
    }

    function isShortsTab(tab) {
        const title = tab.getAttribute("aria-label") || tab.textContent;
        return /^(shorts|короткие видео|short videos)$/i.test(title.trim());
    }

    function hideShortsNode(node) {
        const dedicated = node.closest("ytd-reel-shelf-renderer, yt-shorts-shelf-view-model, yt-shorts-shelf-view-model-v2, ytd-rich-shelf-renderer[is-shorts]");
        if (dedicated) {
            hide(dedicated.closest("ytd-rich-section-renderer") || dedicated);
            return;
        }
        const shelf = node.closest("grid-shelf-view-model, ytd-shelf-renderer, ytd-rich-section-renderer, yt-horizontal-list-renderer");
        // A search shelf can mix regular videos and Shorts. Remove its shell
        // only when all video links are Shorts, so ordinary results survive.
        const hasRegularVideo = shelf && [...shelf.querySelectorAll("a[href]")].some(anchor => {
            if (anchor.closest(nativeShorts) || shortsDestination(anchor.href) !== null) return false;
            try { return /^\/(watch|playlist)$/.test(new URL(anchor.href, location.href).pathname); }
            catch { return false; }
        });
        if (shelf && !hasRegularVideo) hide(shelf);
        else hide(node.closest("ytd-rich-item-renderer") || node.closest(cardSelector) || node);
    }

    function scanShorts(scope) {
        if (!(scope instanceof Element) && scope !== document) return;
        const select = selector => [
            ...(scope instanceof Element && scope.matches(selector) ? [scope] : []),
            ...scope.querySelectorAll(selector),
        ];
        for (const shelf of select(nativeShorts)) {
            hideShortsNode(shelf);
        }
        for (const anchor of select("a[href]")) {
            if (shortsDestination(anchor.href) === null) continue;
            hideShortsNode(anchor);
        }
        for (const badge of select('ytd-thumbnail-overlay-time-status-renderer[overlay-style="SHORTS"], yt-thumbnail-overlay-badge-view-model, .yt-badge-shape__text, .ytBadgeShapeText')) {
            if (badge.getAttribute("overlay-style") === "SHORTS" || isShortsTab(badge)) hideShortsNode(badge);
        }
        for (const tab of select(tabSelector)) {
            if (isShortsTab(tab)) hide(tab);
        }
    }

    // YouTube recycles cards and tab elements during SPA navigation. Re-evaluate
    // previously hidden containers instead of leaving a recycled normal video hidden.
    function refreshHidden(scopes) {
        const previous = [];
        for (const element of hiddenElements) {
            if (!element.isConnected) {
                element.removeAttribute(hiddenAttribute);
                hiddenElements.delete(element);
            } else if (scopes.some(scope => scope.contains(element) || element.contains(scope))) {
                element.removeAttribute(hiddenAttribute);
                hiddenElements.delete(element);
                previous.push(element);
            }
        }
        for (const element of previous) scanShorts(element);
    }

    function createHome() {
        if (!document.body) return null;
        const container = document.createElement("main");
        container.id = "myt-home";
        container.className = "myt-home";
        container.setAttribute("aria-label", "YouTube");
        container.innerHTML = `
            <a class="myt-home__brand" href="/" aria-label="YouTube">
                <svg class="myt-home__mark" viewBox="0 0 44 32" aria-hidden="true"><rect x="1" y="1" width="42" height="30" rx="10" fill="#ff0033"/><path d="m18 9 12 7-12 7Z" fill="white"/></svg>
                <span class="myt-home__wordmark">YouTube</span>
            </a>
            <form class="myt-search" role="search" action="/results" method="get" accept-charset="UTF-8">
                <svg class="myt-search__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg>
                <input class="myt-search__input" id="myt-query" name="search_query" type="search" autocomplete="off" aria-label="${copy.label}" placeholder="${copy.search}">
                <button class="myt-search__clear" type="button" aria-label="${copy.clear}" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
                <button class="myt-search__submit" type="submit" aria-label="${copy.submit}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg></button>
            </form>
            <button class="myt-theme-toggle" id="myt-theme-toggle" type="button">
                <svg class="myt-theme-toggle__sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
                <svg class="myt-theme-toggle__moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M20.8 13A9 9 0 0 1 11 3.2 9 9 0 1 0 20.8 13Z"/></svg>
                <span></span>
            </button>`;
        container.querySelector("#myt-theme-toggle").addEventListener("click", () => {
            const previous = theme;
            const dark = theme ? theme === "dark" : root.hasAttribute("dark");
            theme = dark ? "light" : "dark";
            const writing = ++themeWrite;
            renderTheme();
            chrome.storage.local.set({ theme }, () => {
                const error = chrome.runtime?.lastError;
                if (error && writing === themeWrite) {
                    theme = previous;
                    renderTheme();
                    console.warn("Minimal YouTube: could not save theme.");
                }
            });
        });
        const input = container.querySelector("input");
        const clear = container.querySelector(".myt-search__clear");
        input.value = query;
        clear.hidden = !input.value;
        input.addEventListener("input", () => {
            query = input.value;
            clear.hidden = !query;
        });
        clear.addEventListener("click", () => {
            input.value = query = "";
            clear.hidden = true;
            input.focus();
        });
        input.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                input.value = query = "";
                clear.hidden = true;
            }
        });
        container.querySelector("form").addEventListener("submit", event => {
            input.value = input.value.trim();
            query = input.value;
            clear.hidden = !query;
            if (!query) {
                event.preventDefault();
                input.focus();
            }
            // A native GET form encodes &, #, + and Unicode correctly and retains
            // keyboard submission; do not interpolate the raw query into a URL.
        });
        document.body.append(container);
        requestAnimationFrame(() => {
            if (container.isConnected && document.hasFocus() &&
                (document.activeElement === document.body || document.activeElement.closest("ytd-app"))) {
                input.focus({ preventScroll: true });
            }
        });
        return container;
    }

    function destinationMounted(path) {
        const selector = path === "/watch" ? "ytd-watch-flexy" : path === "/results" ? "ytd-search" :
            channelRoute.test(path) ? "ytd-browse[page-subtype='channels']" : "ytd-page-manager > :not(ytd-browse[page-subtype='home'])";
        return [...document.querySelectorAll(selector)].some(element =>
            !element.closest("[hidden], [aria-hidden='true']") && getComputedStyle(element).display !== "none" && element.getClientRects().length);
    }

    function updateRoute(force = false) {
        if (!enabled) return;
        // Keep the incoming route's styles through the interval between YouTube's
        // navigation-start event, its history update and the replacement DOM.
        if (pendingNavigation && location.href !== navigationSource) pendingNavigation = null;
        const url = new URL(pendingNavigation || location.href);
        const urlChanged = currentURL !== url.href;
        const keepHome = pendingNavigation || (transitionActive && !destinationMounted(url.pathname));
        const releaseHome = home?.isConnected && url.pathname !== "/" && !keepHome;
        if (!force && !urlChanged && !releaseHome && (url.pathname !== "/" || home?.isConnected || !document.body)) return;
        currentURL = url.href;
        const destination = shortsDestination(currentURL);
        if (destination !== null && settingsReady) {
            root.dataset.mytPage = "shorts";
            if (redirectingURL !== currentURL) {
                redirectingURL = currentURL;
                location.replace(destination);
            }
            return;
        }
        redirectingURL = "";
        const path = url.pathname;
        root.dataset.mytPage = path === "/" ? "home" : path === "/watch" ? "watch" : path === "/results" ? "search" :
            channelRoute.test(path) ? "channel" : "other";
        renderTheme();
        if (!settingsReady) return;
        if (path === "/") {
            if (!home?.isConnected) home = createHome();
        } else if (home && !keepHome) {
            home.remove();
            home = null;
        }
        renderTheme();
        syncWatch();
        if (urlChanged || force) {
            refreshHidden([document]);
            scanShorts(document);
            syncSearch();
        }
    }

    function cleanTitle() {
        if (!settingsReady) return;
        const next = document.title.replace(/^\(\d+\)\s*/, "");
        if (next !== document.title) document.title = next;
    }

    function schedule() {
        if (!enabled || frame) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            if (!enabled) return;
            updateRoute();
            renderTheme();
            if (!settingsReady) return;
            syncWatch();
            refreshHidden([...pendingRoots]);
            for (const node of pendingRoots) {
                if (node.isConnected) {
                    scanShorts(node);
                    syncSearch(node);
                }
            }
            pendingRoots.clear();
            cleanTitle();
        });
    }

    const observer = new MutationObserver(records => {
        // Mutation callbacks run before painting. Apply route classes now rather
        // than waiting for a frame or YouTube's late navigation-finish event.
        if (enabled && (location.href !== (pendingNavigation ? navigationSource : currentURL) ||
            (home?.isConnected && root.dataset.mytPage !== "home") ||
            (root.dataset.mytPage === "home" && document.body && !home?.isConnected))) {
            updateRoute();
        }
        for (const record of records) {
            if (record.type === "attributes") {
                if (commentsOpen && commentPanelStates.has(record.target) &&
                    (record.target.hasAttribute("hidden") || record.target.getAttribute("aria-hidden") === "true" ||
                     record.target.getAttribute("visibility") === "ENGAGEMENT_PANEL_VISIBILITY_HIDDEN")) {
                    setCommentsOpen(false);
                }
                // Include the card when its destination changes during DOM reuse.
                pendingRoots.add(record.target.closest(cardSelector) || record.target);
            } else {
                // Tabs can change label without changing the wrapper node.
                const target = record.target instanceof Element ? record.target : record.target.parentElement;
                const container = target?.closest(`${tabSelector}, ${cardSelector}, [${hiddenAttribute}]`);
                if (container) pendingRoots.add(container);
                for (const node of record.addedNodes) {
                    if (node instanceof Element) pendingRoots.add(node);
                }
            }
        }
        schedule();
    });

    const classObserver = new MutationObserver(() => {
        // YouTube can replace the entire html class list while switching views.
        // Reassert the opt-in class in the mutation microtask before next paint.
        if (enabled && !root.classList.contains("minimal-youtube")) root.classList.add("minimal-youtube");
    });

    function setEnabled(value) {
        if (enabled === value) return;
        enabled = value;
        root.classList.toggle("minimal-youtube", enabled);
        if (enabled) {
            classObserver.observe(root, { attributes: true, attributeFilter: ["class"] });
            observer.observe(document.documentElement, {
                subtree: true, childList: true, characterData: true,
                attributes: true, attributeFilter: ["href", "aria-label", "aria-hidden", "visibility", "is-shorts", "dark", "hidden"],
            });
            updateRoute(true);
            cleanTitle();
        } else {
            classObserver.disconnect();
            observer.disconnect();
            cancelAnimationFrame(frame);
            frame = 0;
            pendingRoots.clear();
            for (const element of hiddenElements) element.removeAttribute(hiddenAttribute);
            hiddenElements.clear();
            home?.remove();
            home = null;
            resetWatch();
            syncSearch();
            delete root.dataset.mytTheme;
            currentURL = "";
            pendingNavigation = null;
            redirectingURL = "";
            transitionActive = false;
            delete root.dataset.mytPage;
        }
    }

    function navigationStarted(event) {
        if (!enabled) return;
        const value = event.detail?.url || event.detail?.endpoint?.commandMetadata?.webCommandMetadata?.url;
        if (typeof value === "string") {
            try {
                const incoming = new URL(value, location.href);
                if (incoming.origin === location.origin) {
                    pendingNavigation = incoming.href;
                    navigationSource = location.href;
                    transitionActive = true;
                    if (incoming.pathname !== "/watch" || incoming.searchParams.get("v") !== new URL(location.href).searchParams.get("v")) {
                        resetWatch();
                    }
                }
            } catch { /* A malformed native event must not disrupt navigation. */ }
        }
        updateRoute(true);
        schedule();
    }
    function navigationUpdated() {
        if (!enabled) return;
        updateRoute();
        schedule();
    }
    function navigationFinished() {
        pendingNavigation = null;
        transitionActive = false;
        if (enabled) { updateRoute(true); schedule(); }
    }
    function navigationCommitted() {
        pendingNavigation = null;
        transitionActive = Boolean(home?.isConnected && location.pathname !== "/");
        if (enabled) { updateRoute(true); schedule(); }
    }
    document.addEventListener("yt-navigate-start", navigationStarted);
    for (const name of ["yt-page-data-updated", "yt-page-data-fetched", "yt-navigate-redirect", "yt-data-changed"]) {
        document.addEventListener(name, navigationUpdated);
    }
    for (const name of ["yt-navigate-finish", "yt-navigate-error", "yt-navigate-cancel"]) {
        document.addEventListener(name, navigationFinished);
    }
    window.addEventListener("popstate", navigationCommitted);
    window.addEventListener("pageshow", navigationFinished);
    // Unlike replacing history.pushState in an isolated content-script world,
    // Navigation API events also observe history changes made by page scripts.
    window.navigation?.addEventListener("currententrychange", navigationCommitted);
    document.addEventListener("DOMContentLoaded", navigationUpdated, { once: true });
    document.addEventListener("click", event => {
        if (!enabled) return;
        const anchor = event.composedPath().find(node => node instanceof HTMLAnchorElement);
        if (anchor && shortsDestination(anchor.href) !== null) {
            event.preventDefault();
            event.stopImmediatePropagation();
            location.assign(shortsDestination(anchor.href));
        }
    }, true);
    document.addEventListener("keydown", event => {
        if (!enabled || root.dataset.mytPage !== "home" || event.key !== "/" ||
            event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
        const target = event.target;
        if (target instanceof Element && target.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])")) return;
        event.preventDefault();
        home?.querySelector("input").focus();
    });

    // Some YouTube layouts scroll inside a centered native container. Wheel
    // events over the empty outer gutters never reach that scrollport.
    document.addEventListener("wheel", event => {
        if (!enabled || root.dataset.mytPage === "home" || event.defaultPrevented ||
            event.ctrlKey || !event.deltaY || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
        const target = event.target instanceof Element ? event.target : event.target.parentElement;
        if (!target || target.closest("[role='dialog'], [role='listbox'], tp-yt-paper-dialog, ytd-popup-container, ytd-player, video, iframe, #movie_player, .html5-video-player, .ytp-popup")) return;
        const canScroll = element => {
            if (element.scrollHeight <= element.clientHeight + 1) return false;
            const overflow = getComputedStyle(element).overflowY;
            return /auto|scroll/.test(overflow) ||
                (element === document.scrollingElement && !/hidden|clip/.test(overflow));
        };
        // Leave scrolling inside the native page, comments, menus, etc. alone.
        for (let element = target; element; element = element.parentElement) {
            if (canScroll(element)) return;
        }
        const mainSelector = root.dataset.mytPage === "watch" ? "ytd-watch-flexy" :
            root.dataset.mytPage === "search" ? "ytd-search" : "ytd-browse, ytd-page-manager";
        const main = [...document.querySelectorAll(mainSelector)].find(element =>
            !element.closest("[hidden], [aria-hidden='true']") && getComputedStyle(element).display !== "none");
        let scroller = main;
        while (scroller && !canScroll(scroller)) scroller = scroller.parentElement;
        if (!scroller || scroller.contains(target)) return;
        const unit = event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? scroller.clientHeight :
            event.deltaMode === WheelEvent.DOM_DELTA_LINE ? parseFloat(getComputedStyle(scroller).lineHeight) || 16 : 1;
        const before = scroller.scrollTop;
        scroller.scrollTop += event.deltaY * unit;
        if (scroller.scrollTop !== before) event.preventDefault();
    }, { passive: false });

    chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== "local") return;
        if (Object.hasOwn(changes, "theme")) {
            themeRevision++;
            const value = changes.theme.newValue;
            theme = value === "dark" || value === "light" ? value : null;
            renderTheme();
        }
        if (Object.hasOwn(changes, "enabled")) {
            storageRevision++;
            const value = changes.enabled.newValue;
            settingsReady = true;
            setEnabled(typeof value === "undefined" ? true : Boolean(value));
            if (enabled) { updateRoute(true); cleanTitle(); }
        }
    });
    const initialRevision = storageRevision;
    const initialThemeRevision = themeRevision;
    // This script starts before the application DOM. Install default-on styling
    // immediately; the saved disabled setting removes it as soon as storage returns.
    // Nothing hides the document globally, including on storage/runtime failures.
    setEnabled(true);
    function settingsLoaded(data) {
        settingsReady = true;
        // A storage error must never hide YouTube or leave a blank document.
        const error = chrome.runtime?.lastError;
        if (error) console.warn("Minimal YouTube: could not read settings.");
        if (themeRevision === initialThemeRevision) {
            theme = data?.theme === "dark" || data?.theme === "light" ? data.theme : null;
        }
        if (storageRevision === initialRevision) {
            setEnabled(typeof data?.enabled === "undefined" ? true : Boolean(data.enabled));
        }
        if (enabled) { updateRoute(true); cleanTitle(); schedule(); }
        renderTheme();
    }
    try {
        chrome.storage.local.get(["enabled", "theme"], settingsLoaded);
    } catch {
        settingsLoaded({});
    }
    }

    if (document.documentElement) initialize();
    else {
        const bootstrap = new MutationObserver(() => {
            if (!document.documentElement) return;
            bootstrap.disconnect();
            initialize();
        });
        bootstrap.observe(document, { childList: true });
    }
})();
