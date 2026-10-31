(() => {
    "use strict";

    const root = document.documentElement;
    const hiddenAttribute = "data-myt-hidden";
    const hiddenElements = new Set();
    const pendingRoots = new Set();
    const nativeShorts = [
        "ytd-reel-shelf-renderer", "ytd-reel-item-renderer",
        "ytd-reel-video-renderer", "yt-shorts-lockup-view-model", "ytm-shorts-lockup-view-model",
        "yt-shorts-shelf-view-model", "ytd-rich-shelf-renderer[is-shorts]",
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
        title: "Что посмотрим?", description: "Только то, что вы ищете. Без рекомендаций и Shorts.",
        search: "Поиск на YouTube", submit: "Найти", clear: "Очистить поиск",
        hint: "Enter — искать · / — перейти к поиску", label: "Поиск видео",
    } : {
        title: "What will you watch?", description: "Just what you came for. No recommendations. No Shorts.",
        search: "Search YouTube", submit: "Search", clear: "Clear search",
        hint: "Enter to search · / to focus", label: "Search videos",
    };
    let enabled = false;
    let currentURL = "";
    let home = null;
    let query = "";
    let frame = 0;
    let storageRevision = 0;

    function shortsDestination(value) {
        let url;
        try { url = new URL(value, location.href); } catch { return null; }
        if (url.origin !== location.origin) return null;
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

    function scanShorts(scope) {
        if (!(scope instanceof Element) && scope !== document) return;
        const select = selector => [
            ...(scope instanceof Element && scope.matches(selector) ? [scope] : []),
            ...scope.querySelectorAll(selector),
        ];
        for (const shelf of select(nativeShorts)) {
            hide(shelf.closest("ytd-rich-section-renderer, ytd-rich-item-renderer") || shelf);
        }
        for (const anchor of select("a[href]")) {
            if (shortsDestination(anchor.href) === null) continue;
            hide(anchor.closest("ytd-rich-item-renderer") || anchor.closest(cardSelector) || anchor);
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
        const container = document.createElement("main");
        container.id = "myt-home";
        container.className = "myt-home";
        container.setAttribute("aria-labelledby", "myt-heading");
        container.innerHTML = `
            <a class="myt-home__brand" href="/" aria-label="YouTube">
                <svg class="myt-home__mark" viewBox="0 0 44 32" aria-hidden="true"><rect x="1" y="1" width="42" height="30" rx="10" fill="#ff0033"/><path d="m18 9 12 7-12 7Z" fill="white"/></svg>
                <span class="myt-home__wordmark">YouTube</span>
            </a>
            <span class="myt-home__eyebrow">MINIMAL YOUTUBE</span>
            <h1 class="myt-home__title" id="myt-heading">${copy.title}</h1>
            <p class="myt-home__description">${copy.description}</p>
            <form class="myt-search" role="search" action="/results" method="get" accept-charset="UTF-8">
                <svg class="myt-search__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg>
                <input class="myt-search__input" id="myt-query" name="search_query" type="search" autocomplete="off" aria-label="${copy.label}" placeholder="${copy.search}">
                <button class="myt-search__clear" type="button" aria-label="${copy.clear}" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
                <button class="myt-search__submit" type="submit">${copy.submit}<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></button>
            </form>
            <p class="myt-home__hint">${copy.hint}</p>`;
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

    function updateRoute(force = false) {
        if (!enabled) return;
        const urlChanged = currentURL !== location.href;
        if (!force && !urlChanged && (location.pathname !== "/" || home?.isConnected)) return;
        currentURL = location.href;
        const destination = shortsDestination(currentURL);
        if (destination !== null) {
            root.dataset.mytPage = "shorts";
            location.replace(destination);
            return;
        }
        const path = location.pathname;
        root.dataset.mytPage = path === "/" ? "home" : path === "/watch" ? "watch" :
            channelRoute.test(path) ? "channel" : "other";
        if (path === "/") {
            if (!home?.isConnected) home = createHome();
        } else if (home) {
            home.remove();
            home = null;
        }
        if (urlChanged || force) {
            refreshHidden([document]);
            scanShorts(document);
        }
    }

    function cleanTitle() {
        const next = document.title.replace(/^\(\d+\)\s*/, "");
        if (next !== document.title) document.title = next;
    }

    function schedule() {
        if (!enabled || frame) return;
        frame = requestAnimationFrame(() => {
            frame = 0;
            if (!enabled) return;
            updateRoute();
            refreshHidden([...pendingRoots]);
            for (const node of pendingRoots) {
                if (node.isConnected) scanShorts(node);
            }
            pendingRoots.clear();
            cleanTitle();
        });
    }

    const observer = new MutationObserver(records => {
        for (const record of records) {
            if (record.type === "attributes") {
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

    function setEnabled(value) {
        if (enabled === value) return;
        enabled = value;
        root.classList.toggle("minimal-youtube", enabled);
        if (enabled) {
            observer.observe(document.documentElement, {
                subtree: true, childList: true, characterData: true,
                attributes: true, attributeFilter: ["href", "aria-label", "is-shorts"],
            });
            updateRoute(true);
            cleanTitle();
        } else {
            observer.disconnect();
            cancelAnimationFrame(frame);
            frame = 0;
            pendingRoots.clear();
            for (const element of hiddenElements) element.removeAttribute(hiddenAttribute);
            hiddenElements.clear();
            home?.remove();
            home = null;
            currentURL = "";
            delete root.dataset.mytPage;
        }
    }

    document.addEventListener("yt-navigate-finish", () => {
        if (enabled) { updateRoute(true); schedule(); }
    });
    window.addEventListener("popstate", () => { if (enabled) { updateRoute(true); schedule(); } });
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

    chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== "local" || !Object.hasOwn(changes, "enabled")) return;
        storageRevision++;
        const value = changes.enabled.newValue;
        setEnabled(typeof value === "undefined" ? true : Boolean(value));
    });
    const initialRevision = storageRevision;
    chrome.storage.local.get("enabled", data => {
        if (initialRevision !== storageRevision) return;
        // A storage error must never hide YouTube or leave a blank document.
        const error = chrome.runtime?.lastError;
        if (error) console.warn("Minimal YouTube: could not read settings.");
        setEnabled(typeof data?.enabled === "undefined" ? true : Boolean(data.enabled));
    });
})();
