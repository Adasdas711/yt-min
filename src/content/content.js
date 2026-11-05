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
    const defaultLanguage = (root.lang || navigator.language).toLowerCase().startsWith("ru") ? "ru" : "en";
    const messages = {
    "ru": {
        "search": "Поиск на YouTube",
        "clear": "Очистить поиск",
        "label": "Поиск видео",
        "light": "Светлая тема",
        "dark": "Тёмная тема",
        "comments": "Комментарии",
        "hideComments": "Скрыть комментарии",
        "settings": "Настройки",
        "close": "Закрыть настройки",
        "account": "Аккаунт YouTube",
        "accountInfo": "Вход, выход и смена аккаунта на официальных страницах YouTube и Google.",
        "manage": "Управление аккаунтом",
        "signin": "Войти",
        "switchAccount": "Сменить аккаунт",
        "signout": "Выйти",
        "cookies": "Cookies YouTube",
        "cookieInfo": "Только cookies YouTube. Их удаление может потребовать повторного входа.",
        "loading": "Загрузка…",
        "deleteCookies": "Удалить cookies YouTube",
        "confirmCookies": "Удалить все cookies YouTube в этом профиле?",
        "confirm": "Удалить",
        "cancel": "Отмена",
        "cookieError": "Не удалось получить доступ к cookies. Проверьте разрешения расширения.",
        "saveError": "Не удалось сохранить настройку. Попробуйте ещё раз.",
        "cookieCount": "Cookies:",
        "cookieDeleted": "Удалено:",
        "language": "Язык",
        "system": "Как на YouTube",
        "theme": "Тема"
    },
    "en": {
        "search": "Search YouTube",
        "clear": "Clear search",
        "label": "Search videos",
        "light": "Light theme",
        "dark": "Dark theme",
        "comments": "Comments",
        "hideComments": "Hide comments",
        "settings": "Settings",
        "close": "Close settings",
        "account": "YouTube account",
        "accountInfo": "Sign in, sign out and switch accounts on the official YouTube and Google pages.",
        "manage": "Manage account",
        "signin": "Sign in",
        "switchAccount": "Switch account",
        "signout": "Sign out",
        "cookies": "YouTube cookies",
        "cookieInfo": "YouTube cookies only. Deleting them may require signing in again.",
        "loading": "Loading…",
        "deleteCookies": "Delete YouTube cookies",
        "confirmCookies": "Delete all YouTube cookies in this profile?",
        "confirm": "Delete",
        "cancel": "Cancel",
        "cookieError": "Could not access cookies. Check the extension permissions.",
        "saveError": "Could not save the setting. Please try again.",
        "cookieCount": "Cookies:",
        "cookieDeleted": "Deleted:",
        "language": "Language",
        "system": "Same as YouTube",
        "theme": "Theme"
    }
};
    let language = null;
    let languageRevision = 0;
    let copy = messages[defaultLanguage];
    let settingsOpen = false;
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
    const hiddenSections = new Set();
    const commentPanelStates = new Map();
    const brandedLinks = new Set();
    // A shadow root isolates the home controls from document-wide CSS.
    const homeStyles = `:host {
    all: initial !important;
    box-sizing: border-box !important;
    position: fixed !important;
    z-index: 2147483647 !important;
    inset: 0 !important;
    isolation: isolate !important;
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
    background-image: none !important;
    box-shadow: none !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: safe center !important;
    min-height: 100svh !important;
    max-height: none !important;
    margin: 0 !important;
    border: 0 !important;
    border-radius: 0 !important;
    transform: none !important;
    filter: none !important;
    padding: 72px 24px 112px !important;
    overflow: auto !important;
    background: var(--myt-bg) !important;
    color: var(--myt-ink) !important;
    font-family: "Roboto", "Arial", sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Theme variables are scoped to the home route and inherit into its flat backdrop. */
:host([data-myt-theme="light"]) {
    color-scheme: only light !important;
    --myt-bg: #f9f9fb;
    --myt-surface: #ffffff;
    --myt-ink: #18181b;
    --myt-muted: #74747d;
    --myt-border: #e5e5ea;
    --myt-soft: #f1f1f4;
    --myt-shadow: none;
}

:host([data-myt-theme="dark"]) {
    color-scheme: only dark !important;
    --myt-bg: #101012;
    --myt-surface: #19191d;
    --myt-ink: #f4f4f5;
    --myt-muted: #92929d;
    --myt-border: #2c2c33;
    --myt-soft: #24242a;
    --myt-shadow: none;
}

*, *::before, *::after {
    box-sizing: border-box;
}

.myt-home__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 36px;
    color: inherit;
    text-decoration: none;
}

:host > * {
    flex-shrink: 0;
}

.myt-home__brand:focus-visible {
    outline: 2px solid var(--myt-accent);
    outline-offset: 6px;
    border-radius: 4px;
}

.myt-home__mark {
    width: 42px;
    height: 32px;
    color: var(--myt-accent);
    flex: none;
}

.myt-home__wordmark {
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -1.1px;
}

.myt-search {
    display: flex;
    align-items: center;
    gap: 14px;
    width: min(100%, 600px);
    min-height: 64px;
    margin: 0;
    padding: 7px 22px;
    border: 1px solid var(--myt-border);
    border-radius: 18px;
    background: var(--myt-surface);
    box-shadow: none;
    transition: border-color 150ms ease;
}

.myt-search:focus-within {
    border-color: var(--myt-muted);
    outline: 2px solid color-mix(in srgb, var(--myt-muted) 20%, transparent);
    outline-offset: 2px;
}

.myt-search__input {
    min-width: 0;
    width: 100%;
    padding: 12px 0;
    border: 0;
    outline: none;
    background: transparent;
    color: var(--myt-ink);
    font: inherit;
    font-size: 16px;
    line-height: 1.3;
    appearance: none;
}

.myt-search__input::placeholder {
    color: var(--myt-muted);
    opacity: 1;
}

.myt-search__input::-webkit-search-decoration,
.myt-search__input::-webkit-search-results-button,
.myt-search__input::-webkit-search-results-decoration {
    -webkit-appearance: none;
    appearance: none;
    display: none;
}

.myt-search__input::-webkit-search-cancel-button {
    appearance: none;
}

.myt-search__clear {
    gap: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    border: 0;
    cursor: pointer;
    font: inherit;
    transition: background 150ms ease, transform 150ms ease;
}

.myt-search__clear {
    width: 32px;
    height: 36px;
    padding: 7px;
    border-radius: 9px;
    background: transparent;
    color: var(--myt-muted);
}

.myt-search__clear[hidden] {
    display: none;
}

.myt-search__clear:hover {
    background: var(--myt-soft);
    color: var(--myt-ink);
}

.myt-search__clear svg {
    display: block;
    width: 22px;
    height: 22px;
}

.myt-search button:focus-visible {
    outline: 2px solid var(--myt-accent);
    outline-offset: 3px;
}

.myt-theme-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-height: 34px;
    margin-top: 18px;
    padding: 7px 12px;
    border: 1px solid transparent;
    border-radius: 999px;
    background: transparent;
    color: var(--myt-muted);
    font: inherit;
    font-size: 12px;
    line-height: 1.5;
    cursor: pointer;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
}

.myt-theme-toggle:hover {
    border-color: var(--myt-border);
    background: var(--myt-surface);
    color: var(--myt-ink);
}

.myt-theme-toggle:focus-visible {
    outline: 2px solid var(--myt-accent);
    outline-offset: 3px;
}

.myt-theme-toggle svg {
    display: block;
    width: 16px;
    height: 16px;
    flex: none;
}

.myt-theme-toggle[data-theme="light"] .myt-theme-toggle__sun,
.myt-theme-toggle[data-theme="dark"] .myt-theme-toggle__moon {
    display: none;
}


:host::before, :host::after, :host::backdrop { content: none !important; display: none !important; }

[hidden] { display: none !important; }
.myt-settings-button {
    position: fixed; right: 24px; top: 24px;
    display: grid; place-items: center; width: 44px; height: 44px;
    border: 1px solid var(--myt-border); border-radius: 14px;
    background: var(--myt-surface); color: var(--myt-muted); cursor: pointer;
}
.myt-settings-button:hover { color: var(--myt-ink); background: var(--myt-soft); }
.myt-settings-button svg { width: 22px; height: 22px; }
.myt-settings-panel {
    position: fixed; right: 24px; top: 80px; z-index: 1;
    width: min(360px, calc(100% - 32px)); max-height: calc(100svh - 104px);
    overflow: auto; overscroll-behavior: contain; padding: 20px;
    border: 1px solid var(--myt-border); border-radius: 18px;
    background: var(--myt-surface); color: var(--myt-ink); text-align: start;
    font: 14px/1.5 "Roboto", "Arial", sans-serif;
}
.myt-settings-panel header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.myt-settings-panel h2 { margin: 0; font-size: 18px; }
.myt-settings-panel section { padding-block: 16px; border-bottom: 1px solid var(--myt-border); }
.myt-settings-panel section:last-of-type { border: 0; padding-bottom: 0; }
.myt-settings-panel h3, .myt-settings-panel label { display: block; font-size: 14px; font-weight: 600; margin: 0 0 8px; }
.myt-settings-panel p { color: var(--myt-muted); font-size: 12px; margin: 8px 0; }
.myt-settings-panel a, .myt-settings-panel button, .myt-settings-panel select {
    font: inherit; border: 1px solid var(--myt-border); border-radius: 9px;
    color: var(--myt-ink); background: var(--myt-soft); padding: 8px 10px;
}
.myt-settings-panel a, .myt-settings-panel button { cursor: pointer; text-decoration: none; }
.myt-settings-panel button:disabled { opacity: .5; cursor: default; }
.myt-settings-panel :is(a, button, select):focus-visible, .myt-settings-button:focus-visible { outline: 2px solid var(--myt-muted); outline-offset: 3px; }
.myt-settings-panel select { width: 100%; }
.myt-settings-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.myt-settings-panel ul { margin: 8px 0; padding: 0; list-style: none; max-height: 120px; overflow: auto; font-size: 12px; overflow-wrap: anywhere; }
.myt-settings-panel li { padding-block: 4px; border-bottom: 1px solid var(--myt-border); }
.myt-settings-panel #myt-settings-error { color: var(--myt-ink); }
@media (max-width: 600px) {
    .myt-settings-button { right: 16px; top: 16px; }
    .myt-settings-panel { right: 16px; top: 72px; max-height: calc(100svh - 88px); }
}

@media (max-width: 600px) {
    :host {
        justify-content: flex-start !important;
        padding: max(80px, 20svh) 20px 40px !important;
    }

    .myt-home__brand {
        margin-bottom: 40px;
    }

    .myt-search {
        gap: 9px;
        min-height: 58px;
        padding: 5px 15px;
        border-radius: 16px;
    }

}
`;
    const brandMarkup = '<svg class="myt-home__mark" viewBox="0 0 44 32" aria-hidden="true"><rect x="1" y="1" width="42" height="30" rx="10" fill="#ff0033"/><path d="m18 9 12 7-12 7Z" fill="white"/></svg><span class="myt-home__wordmark">YouTube</span>';
    const voteSelector = [
        "ytd-segmented-like-dislike-button-renderer", "segmented-like-dislike-button-view-model",
        "yt-segmented-like-dislike-button-view-model", "like-button-view-model", "dislike-button-view-model",
        "ytd-like-button-renderer", "ytd-dislike-button-renderer",
        "[target-id='watch-like']", "[target-id='watch-dislike']",
    ].join(",");

    function applyLanguage(value) {
        language = value === "ru" || value === "en" ? value : null;
        copy = messages[language || defaultLanguage];
        if (home?.isConnected) {
            home.remove();
            home = createHome();
            renderTheme();
        }
        if (settingsReady) syncWatch();
    }

    function saveTheme(value) {
        const previous = theme;
        theme = value;
        const writing = ++themeWrite;
        renderTheme();
        chrome.storage.local.set({ theme }, () => {
            if (chrome.runtime?.lastError && writing === themeWrite) {
                theme = previous;
                renderTheme();
                const error = home?.firstElementChild.shadowRoot.querySelector("#myt-settings-error");
                if (error) error.textContent = copy.saveError;
            }
        });
    }

    function renderTheme() {
        if (enabled) root.dataset.mytTheme = theme || (root.hasAttribute("dark") ? "dark" : "light");
        else delete root.dataset.mytTheme;
        if (home) {
            home.dataset.mytTheme = root.dataset.mytTheme || "";
            home.firstElementChild.dataset.mytTheme = root.dataset.mytTheme || "";
        }
        const themeSelect = home?.firstElementChild.shadowRoot.querySelector("#myt-settings-theme");
        if (themeSelect) themeSelect.value = root.dataset.mytTheme || "light";
        const button = home?.firstElementChild.shadowRoot.querySelector("#myt-theme-toggle");
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

    function syncBrand() {
        if (!enabled) return;
        for (const link of brandedLinks) {
            if (!link.isConnected) {
                link.querySelectorAll(":scope > .myt-masthead-brand").forEach(brand => brand.remove());
                link.removeAttribute("data-myt-logo");
                brandedLinks.delete(link);
            }
        }
        for (const link of document.querySelectorAll("ytd-masthead a#logo, ytd-masthead ytd-topbar-logo-renderer a[href]")) {
            const brands = [...link.querySelectorAll(":scope > .myt-masthead-brand")];
            if (!brands.length) {
                const brand = document.createElement("span");
                brand.className = "myt-masthead-brand";
                brand.innerHTML = brandMarkup;
                link.append(brand);
            } else brands.slice(1).forEach(brand => brand.remove());
            if (!link.hasAttribute("data-myt-logo")) link.setAttribute("data-myt-logo", "");
            brandedLinks.add(link);
        }
    }

    function restoreBrand() {
        for (const brand of document.querySelectorAll("ytd-masthead .myt-masthead-brand")) brand.remove();
        for (const link of brandedLinks) {
            link.querySelectorAll(":scope > .myt-masthead-brand").forEach(brand => brand.remove());
            link.removeAttribute("data-myt-logo");
        }
        document.querySelectorAll("ytd-masthead [data-myt-logo]").forEach(link => link.removeAttribute("data-myt-logo"));
        brandedLinks.clear();
    }

    function syncSections() {
        const wanted = new Set();
        if (enabled) {
            const pages = [root.dataset.mytPage, root.dataset.mytPreviousPage];
            for (const page of new Set(pages)) {
                const selector = page === "search" ? "ytd-search" : page === "channel" ? "ytd-browse[page-subtype='channels']" : null;
                if (!selector) continue;
                for (const scope of document.querySelectorAll(selector)) {
                    for (const shelf of scope.querySelectorAll("ytd-shelf-renderer, grid-shelf-view-model, ytd-rich-section-renderer")) {
                        const heading = shelf.querySelector("#title-container, #header, :scope > #title, :scope > h2, yt-section-header-view-model, .ytShelfHeaderLayoutTitle");
                        const titleNode = heading?.querySelector("#title, h2, h3, .ytSectionHeaderViewModelTitle") || heading;
                        const title = titleNode?.textContent.replace(/\s+/g, " ").trim() || "";
                        const match = page === "search" ?
                            /^(?:новые видео на канале|последние видео (?:на канале|от)|latest(?: videos)? from|new videos from)\s+/iu :
                            /^(?:new uploads|новые (?:видео|загрузки)|последние (?:видео|загрузки))(?=$|\s)/iu;
                        if (match.test(title)) wanted.add(shelf);
                    }
                }
            }
        }
        for (const shelf of hiddenSections) {
            if (!wanted.has(shelf)) {
                shelf.removeAttribute("data-myt-hidden-section");
                hiddenSections.delete(shelf);
            }
        }
        for (const shelf of wanted) {
            if (!shelf.hasAttribute("data-myt-hidden-section")) shelf.setAttribute("data-myt-hidden-section", "latest");
            hiddenSections.add(shelf);
        }
    }

    function syncSearch(scope = document) {
        const attributes = ["data-myt-search-video", "data-myt-search-cell", "data-myt-search-grid"];
        const active = enabled && (root.dataset.mytPage === "search" || root.dataset.mytPreviousPage === "search");
        for (const element of searchVideoCards) {
            if (!active || !element.isConnected || !element.closest("ytd-search")) {
                for (const name of attributes) element.removeAttribute(name);
                searchVideoCards.delete(element);
            }
        }
        if (!active) return;
        const searches = new Set([
            ...(scope instanceof Element && scope.closest("ytd-search") ? [scope.closest("ytd-search")] : []),
            ...scope.querySelectorAll("ytd-search"),
        ]);
        const videoSelector = "ytd-video-renderer, ytd-grid-video-renderer, ytd-compact-video-renderer, yt-lockup-view-model";
        const otherResults = "ytd-channel-renderer, ytd-playlist-renderer, ytd-grid-playlist-renderer, ytd-radio-renderer, ytd-movie-renderer";
        const shelves = "ytd-shelf-renderer, grid-shelf-view-model, ytd-rich-section-renderer, yt-horizontal-list-renderer";
        const listContainers = "ytd-item-section-renderer > #contents, ytd-shelf-renderer > #content, ytd-horizontal-card-list-renderer > #items, grid-shelf-view-model #items, yt-horizontal-list-renderer #items, ytd-rich-grid-renderer > #contents";
        const urlOf = anchor => {
            try { return anchor && new URL(anchor.href, location.href); }
            catch { return null; }
        };
        const isVideoURL = url => url && url.protocol === "https:" &&
            (url.hostname === "youtube.com" || url.hostname.endsWith(".youtube.com")) &&
            url.pathname === "/watch" && Boolean(url.searchParams.get("v"));
        const isVideo = card => {
            if (card.closest(nativeShorts) || card.closest(otherResults) || card.matches("[is-playlist], [content-type='playlist'], [data-content-type='playlist']") ||
                card.querySelector("yt-collection-thumbnail-view-model, yt-collections-stack, yt-collection-thumbnail-overlay-view-model, ytd-thumbnail-overlay-side-panel-renderer, .ytCollectionThumbnailViewModelHost")) return false;
            // A channel avatar can precede the main thumbnail in current lockups.
            // The title or thumbnail identifies the result; incidental links do not.
            const title = card.querySelector("a#video-title[href], a#video-title-link[href], h3 a[href], a.yt-lockup-metadata-view-model__title[href], a.yt-lockup-metadata-view-model-wiz__title[href], a.ytLockupMetadataViewModelTitle[href]");
            const thumbnail = card.querySelector("ytd-thumbnail a[href], a#thumbnail[href], .yt-lockup-view-model__content-image a[href], .yt-lockup-view-model-wiz__content-image a[href], .ytLockupViewModelContentImage a[href], a:has(yt-thumbnail-view-model)[href]");
            const main = title || thumbnail;
            if (main) return isVideoURL(urlOf(main));
            return [...card.querySelectorAll("a[href]")].some(anchor =>
                !anchor.closest("ytd-channel-name, #channel-info, #avatar, .yt-lockup-metadata-view-model__image, .yt-lockup-metadata-view-model-wiz__image, .ytLockupMetadataViewModelImage") && isVideoURL(urlOf(anchor)));
        };
        for (const search of searches) {
            const wanted = new Map();
            const mark = (element, name) => {
                if (!wanted.has(element)) wanted.set(element, new Set());
                wanted.get(element).add(name);
            };
            const videos = [...search.querySelectorAll(videoSelector)].filter(isVideo).filter(card =>
                !card.parentElement.closest(videoSelector) && !card.closest("[data-myt-hidden-section]"));
            const descendantCounts = new Map();
            for (const card of videos) {
                mark(card, "data-myt-search-video");
                mark(card, "data-myt-search-cell");
                for (let parent = card.parentElement; parent && parent !== search; parent = parent.parentElement) {
                    descendantCounts.set(parent, (descendantCounts.get(parent) || 0) + 1);
                }
            }
            for (const container of search.querySelectorAll(listContainers)) {
                if (descendantCounts.has(container)) mark(container, "data-myt-search-grid");
            }
            const wrappers = new Set();
            for (const card of videos) {
                // Keep native nodes in place. A single-video wrapper is a cell;
                // a wrapper containing several videos gets its own nested grid.
                for (let parent = card.parentElement; parent && parent !== search; parent = parent.parentElement) {
                    if (parent.matches("ytd-item-section-renderer > #contents")) break;
                    if (parent.matches(`${videoSelector}, ytd-shelf-renderer, grid-shelf-view-model, ytd-rich-section-renderer, ytd-item-section-renderer, ytd-section-list-renderer`)) continue;
                    wrappers.add(parent);
                }
            }
            for (const parent of wrappers) {
                const count = descendantCounts.get(parent);
                const structuralList = parent.matches(`${listContainers}, yt-horizontal-list-renderer`);
                const mixed = parent.matches(otherResults) || parent.querySelector(`${otherResults}, ${shelves}`);
                if (structuralList || count > 1 || mixed) mark(parent, "data-myt-search-grid");
                else if (count === 1) mark(parent, "data-myt-search-cell");
            }
            for (const element of searchVideoCards) {
                if (!search.contains(element)) continue;
                for (const name of attributes) {
                    if (!wanted.get(element)?.has(name)) element.removeAttribute(name);
                }
                if (!wanted.has(element)) searchVideoCards.delete(element);
            }
            for (const [element, names] of wanted) {
                for (const name of names) {
                    if (!element.hasAttribute(name)) element.setAttribute(name, "");
                }
                searchVideoCards.add(element);
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
        const container = document.createElement("dialog");
        container.id = "myt-home";
        container.className = "myt-home";
        container.setAttribute("aria-label", "YouTube");
        container.lang = language || defaultLanguage;
        const surface = document.createElement("div");
        const view = surface.attachShadow({ mode: "open" });
        container.append(surface);
        view.innerHTML = `<style>${homeStyles}</style>
            <a class="myt-home__brand" href="/" aria-label="YouTube">
                ${brandMarkup}
            </a>
            <form class="myt-search" role="search" action="/results" method="get" accept-charset="UTF-8">
                <input class="myt-search__input" id="myt-query" name="search_query" type="search" autofocus autocomplete="off" aria-label="${copy.label}" placeholder="${copy.search}">
                <button class="myt-search__clear" type="button" aria-label="${copy.clear}" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
            </form>
            <button class="myt-theme-toggle" id="myt-theme-toggle" type="button">
                <svg class="myt-theme-toggle__sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
                <svg class="myt-theme-toggle__moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M20.8 13A9 9 0 0 1 11 3.2 9 9 0 1 0 20.8 13Z"/></svg>
                <span></span>
            </button>
            <button class="myt-settings-button" id="myt-settings-button" type="button" aria-label="${copy.settings}" title="${copy.settings}" aria-expanded="${settingsOpen}" aria-controls="myt-settings-panel">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m9 3-.6 2.3-2 .9L4.3 5.5 2.8 8.1l1.7 1.6-.2 2.3-1.7 1.5 1.5 2.7 2.3-.7 1.9 1.1.6 2.4h3l.6-2.4 1.9-1.1 2.3.7 1.5-2.7-1.7-1.5-.2-2.3 1.7-1.6-1.5-2.6-2.1.7-2-.9L12 3Z" transform="translate(1 1)"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
            <aside class="myt-settings-panel" id="myt-settings-panel" role="region" aria-label="${copy.settings}" ${settingsOpen ? "" : "hidden"}>
                <header><h2>${copy.settings}</h2><button type="button" id="myt-settings-close" aria-label="${copy.close}">×</button></header>
                <section><h3>${copy.account}</h3><p>${copy.accountInfo}</p><div class="myt-settings-actions">
                    <a id="myt-account-manage" href="https://www.youtube.com/account">${copy.manage}</a>
                    <a id="myt-account-signin" href="https://www.youtube.com/signin?next=%2F">${copy.signin}</a>
                    <a id="myt-account-switch" href="https://accounts.google.com/AccountChooser?service=youtube&amp;continue=https%3A%2F%2Fwww.youtube.com%2F">${copy.switchAccount}</a>
                    <a id="myt-account-signout" href="https://www.youtube.com/logout?next=%2F">${copy.signout}</a>
                </div></section>
                <section><h3>${copy.cookies}</h3><p>${copy.cookieInfo}</p><p id="myt-cookie-status" role="status"></p><ul id="myt-cookie-list"></ul>
                    <button type="button" id="myt-cookie-clear" disabled>${copy.deleteCookies}</button>
                    <div id="myt-cookie-confirmation" hidden><p>${copy.confirmCookies}</p><div class="myt-settings-actions"><button type="button" id="myt-cookie-confirm">${copy.confirm}</button><button type="button" id="myt-cookie-cancel">${copy.cancel}</button></div></div>
                </section>
                <section><label for="myt-settings-language">${copy.language}</label><select id="myt-settings-language"><option value="">${copy.system}</option><option value="ru">Русский</option><option value="en">English</option></select></section>
                <section><label for="myt-settings-theme">${copy.theme}</label><select id="myt-settings-theme"><option value="light">${copy.light}</option><option value="dark">${copy.dark}</option></select></section>
                <p id="myt-settings-error" role="alert"></p>
            </aside>`;
        view.querySelector("#myt-theme-toggle").addEventListener("click", () => {
            const dark = theme ? theme === "dark" : root.hasAttribute("dark");
            saveTheme(dark ? "light" : "dark");
        });
        const panel = view.querySelector("#myt-settings-panel");
        const settingsButton = view.querySelector("#myt-settings-button");
        const cookieStatus = view.querySelector("#myt-cookie-status");
        const cookieList = view.querySelector("#myt-cookie-list");
        const clearCookies = view.querySelector("#myt-cookie-clear");
        const confirmation = view.querySelector("#myt-cookie-confirmation");
        const settingsError = view.querySelector("#myt-settings-error");
        const setPanel = open => {
            settingsOpen = open;
            panel.hidden = !open;
            settingsButton.setAttribute("aria-expanded", String(open));
            confirmation.hidden = true;
            if (open) {
                view.querySelector("#myt-settings-close").focus();
                requestCookies("minimal-youtube:get-cookies");
            } else settingsButton.focus();
        };
        const requestCookies = action => {
            cookieStatus.textContent = copy.loading;
            clearCookies.disabled = true;
            view.querySelector("#myt-cookie-confirm").disabled = true;
            const done = response => {
                if (!container.isConnected) return;
                view.querySelector("#myt-cookie-confirm").disabled = false;
                if (chrome.runtime?.lastError || !response?.ok || !Array.isArray(response.cookies)) {
                    cookieStatus.textContent = copy.cookieError;
                    return;
                }
                confirmation.hidden = true;
                cookieList.replaceChildren();
                for (const cookie of response.cookies) {
                    const item = document.createElement("li");
                    item.textContent = `${cookie.name} · ${cookie.domain}`;
                    cookieList.append(item);
                }
                clearCookies.disabled = response.cookies.length === 0;
                cookieStatus.textContent = `${typeof response.removed === "number" ? copy.cookieDeleted + " " + response.removed + ". " : ""}${copy.cookieCount} ${response.cookies.length}`;
            };
            try { chrome.runtime.sendMessage({ action }, done); }
            catch { done(null); }
        };
        settingsButton.addEventListener("click", () => setPanel(panel.hidden));
        view.querySelector("#myt-settings-close").addEventListener("click", () => setPanel(false));
        view.addEventListener("keydown", event => {
            if (event.key === "Escape" && !panel.hidden) {
                event.preventDefault();
                event.stopPropagation();
                setPanel(false);
            }
        });
        clearCookies.addEventListener("click", () => {
            confirmation.hidden = false;
            view.querySelector("#myt-cookie-confirm").focus();
        });
        view.querySelector("#myt-cookie-cancel").addEventListener("click", () => {
            confirmation.hidden = true;
            clearCookies.focus();
        });
        view.querySelector("#myt-cookie-confirm").addEventListener("click", () => requestCookies("minimal-youtube:clear-cookies"));
        view.querySelector("#myt-settings-theme").addEventListener("change", event => saveTheme(event.target.value));
        const languageSelect = view.querySelector("#myt-settings-language");
        languageSelect.value = language || "";
        languageSelect.addEventListener("change", () => {
            const selected = languageSelect.value;
            chrome.storage.local.set({ language: selected }, () => {
                if (chrome.runtime?.lastError) {
                    languageSelect.value = language || "";
                    settingsError.textContent = copy.saveError;
                    return;
                }
                if (language !== (selected || null)) applyLanguage(selected);
                const url = new URL(location.href);
                url.searchParams.set("hl", selected || defaultLanguage);
                url.searchParams.set("persist_hl", "1");
                location.assign(url.href);
            });
        });
        const input = view.querySelector("input");
        const clear = view.querySelector(".myt-search__clear");
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
        view.querySelector("form").addEventListener("submit", event => {
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
        // Body can be transformed, filtered or contained by YouTube/other styles.
        // A fixed child of that body is no longer a viewport overlay. Keep the
        // homepage beside body so its size and color do not inherit those effects.
        root.append(container);
        // A modal dialog is in the browser's top layer, outside native stacking
        // contexts and ancestor transforms/filters. The hidden app stays intact.
        container.addEventListener("cancel", event => event.preventDefault());
        container.showModal();
        if (settingsOpen) setPanel(true);
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
        const nextPage = url.pathname === "/" ? "home" : url.pathname === "/watch" ? "watch" :
            url.pathname === "/results" ? "search" : channelRoute.test(url.pathname) ? "channel" : "other";
        const previous = root.dataset.mytPage;
        if (previous && previous !== nextPage && previous !== "home" && !root.dataset.mytPreviousPage) {
            root.dataset.mytPreviousPage = previous;
        }
        // Incoming styles apply immediately, while outgoing styles remain until
        // the native destination is mounted. Never reveal an unstyled old page.
        if (!pendingNavigation && (url.pathname === "/" ? home?.isConnected : destinationMounted(url.pathname))) {
            delete root.dataset.mytPreviousPage;
        }
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
        root.dataset.mytPage = nextPage;
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
        syncSections();
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
            syncBrand();
            if (!settingsReady) return;
            syncWatch();
            syncSections();
            refreshHidden([...pendingRoots]);
            for (const node of pendingRoots) {
                if (node.isConnected) {
                    scanShorts(node);
                }
            }
            // Added thumbnails/labels can produce many mutation roots in one
            // frame. Reconcile each search once, rather than once per new node.
            if (pendingRoots.size) syncSearch();
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
        syncBrand();
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
            syncBrand();
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
            restoreBrand();
            syncSections();
            syncSearch();
            delete root.dataset.mytTheme;
            currentURL = "";
            pendingNavigation = null;
            redirectingURL = "";
            transitionActive = false;
            delete root.dataset.mytPage;
            delete root.dataset.mytPreviousPage;
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
        const target = event.composedPath()[0];
        if (target instanceof Element && target.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])")) return;
        event.preventDefault();
        home?.firstElementChild.shadowRoot.querySelector("input").focus();
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
        const page = root.dataset.mytPage;
        const mainSelector = page === "watch" ? "ytd-watch-flexy" :
            page === "search" ? "ytd-search" : page === "channel" ? "ytd-browse[page-subtype='channels']" : "ytd-browse";
        const visible = element => !element.closest("[hidden], [aria-hidden='true']") &&
            element.getClientRects().length && getComputedStyle(element).visibility !== "hidden";
        const main = [...document.querySelectorAll(mainSelector)].find(visible) ||
            [...document.querySelectorAll("ytd-page-manager")].find(visible);
        if (!main) return;
        // Channels have a full-width banner but a narrower content rail.
        const rail = page === "channel" ?
            [...main.querySelectorAll("#channel-header-container, :scope > #contents, :scope > #tabs")]
                .find(element => visible(element) && element.clientWidth > 0 && element.clientWidth < innerWidth) || main : main;
        const bounds = rail.getBoundingClientRect();
        let gutter = event.clientX < bounds.left || event.clientX >= bounds.right;
        // Normal content and independent scrollboxes keep their native wheel path.
        // An ancestor such as html may be scrollable even when a gutter overlay
        // blocks its native wheel events, so it must not veto gutter forwarding.
        if (!gutter && main.contains(target) && target !== main) return;
        for (let element = target; element; element = element.parentElement) {
            if (element !== document.scrollingElement && element !== document.body &&
                !element.contains(main) && canScroll(element)) return;
        }
        const inner = [...main.querySelectorAll("*")].filter(element =>
            element.clientHeight >= innerHeight / 2 && element.clientWidth >= main.clientWidth / 2 &&
            canScroll(element) && visible(element) &&
            !element.closest("[role='dialog'], ytd-comments, ytd-player"))
            .sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight)[0];
        if (!gutter && inner) {
            const innerBounds = inner.getBoundingClientRect();
            gutter = event.clientX < innerBounds.left || event.clientX >= innerBounds.right;
        }
        if (!gutter) return;
        let scroller = inner || main;
        while (scroller && !canScroll(scroller)) scroller = scroller.parentElement;
        if (!scroller) return;
        const unit = event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? scroller.clientHeight :
            event.deltaMode === WheelEvent.DOM_DELTA_LINE ? parseFloat(getComputedStyle(scroller).lineHeight) || 16 : 1;
        const before = scroller.scrollTop;
        scroller.scrollBy({ top: event.deltaY * unit, behavior: "instant" });
        if (scroller.scrollTop !== before) {
            event.preventDefault();
            event.stopPropagation();
        }
    }, { passive: false, capture: true });

    chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== "local") return;
        if (Object.hasOwn(changes, "theme")) {
            themeRevision++;
            const value = changes.theme.newValue;
            theme = value === "dark" || value === "light" ? value : null;
            renderTheme();
        }
        if (Object.hasOwn(changes, "language")) {
            languageRevision++;
            applyLanguage(changes.language.newValue);
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
    const initialLanguageRevision = languageRevision;
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
        if (languageRevision === initialLanguageRevision) applyLanguage(data?.language);
        if (storageRevision === initialRevision) {
            setEnabled(typeof data?.enabled === "undefined" ? true : Boolean(data.enabled));
        }
        if (enabled) { updateRoute(true); cleanTitle(); schedule(); }
        renderTheme();
    }
    try {
        chrome.storage.local.get(["enabled", "theme", "language"], settingsLoaded);
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
