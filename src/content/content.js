(() => {
    "use strict";

    function initialize() {
    const root = document.documentElement;
    const standaloneHome = root.hasAttribute("data-myt-standalone-home");
    const pageLocation = () => standaloneHome ? "https://www.youtube.com/" + location.search : location.href;
    let homeRedirecting = false;
    function openNativeHome() {
        if (homeRedirecting) return;
        homeRedirecting = true;
        chrome.runtime.sendMessage({ action: "minimal-youtube:open-native-home" }, result => {
            if (result?.ok && result.url === "https://www.youtube.com/") location.replace(result.url);
            else { homeRedirecting = false; console.warn("Minimal YouTube: could not open the native homepage."); }
        });
    }
    const hiddenAttribute = "data-myt-hidden";
    const hiddenElements = new Set();
    const pendingRoots = new Set();
    const suspendedChatFrames = new Map();
    const playerAds = globalThis.MinimalYouTubeAds ? new globalThis.MinimalYouTubeAds() : null;
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
        "settingsHint": "Аккаунт, приватность и оформление",
        "showCookies": "Список cookies",
        "appearance": "Оформление",
        "languageInfo": "Для YouTube и расширения",
        "themeInfo": "Оформление главной страницы",
        "lightShort": "Светлая",
        "darkShort": "Тёмная",
        "close": "Закрыть настройки",
        "account": "Аккаунт YouTube",
        "accountInfo": "Вход и управление аккаунтом на YouTube и Google.",
        "manage": "Управление аккаунтом",
        "signin": "Войти",
        "switchAccount": "Сменить аккаунт",
        "signout": "Выйти",
        "cookies": "Cookies YouTube",
        "cookieInfo": "Только cookies YouTube. После удаления может потребоваться вход.",
        "loading": "Загрузка…",
        "deleteCookies": "Удалить cookies",
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
        "settingsHint": "Account, privacy and appearance",
        "showCookies": "View cookies",
        "appearance": "Appearance",
        "languageInfo": "YouTube and extension interface",
        "themeInfo": "Start page appearance",
        "lightShort": "Light",
        "darkShort": "Dark",
        "close": "Close settings",
        "account": "YouTube account",
        "accountInfo": "Sign in and manage your YouTube account.",
        "manage": "Manage account",
        "signin": "Sign in",
        "switchAccount": "Switch account",
        "signout": "Sign out",
        "cookies": "YouTube cookies",
        "cookieInfo": "YouTube cookies only. You may need to sign in again.",
        "loading": "Loading…",
        "deleteCookies": "Clear cookies",
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
    let watchView = null;
    const commentPanelStates = new Map();
    const brandedLinks = new Set();
    const searchDecorations = new Set();
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
    padding: 72px 24px !important;
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


:host([data-myt-theme="light"]) {
    --myt-settings-bg: #ffffff; --myt-settings-control: #f4f4f6;
    --myt-settings-selected: #ffffff; --myt-settings-header: #fcfcfd;
    --myt-settings-accent-bg: #fff0f2; --myt-danger: #bc2b3c;
    --myt-settings-shadow: 0 32px 100px rgba(24, 24, 27, .18);
}
:host([data-myt-theme="dark"]) {
    --myt-settings-bg: #18181b; --myt-settings-control: #232327;
    --myt-settings-selected: #37373d; --myt-settings-header: #1c1c20;
    --myt-settings-accent-bg: #362127; --myt-danger: #ff929e;
    --myt-settings-shadow: 0 32px 100px rgba(0, 0, 0, .48);
}
.myt-settings-button {
    position: fixed; right: 24px; top: 24px; display: grid; place-items: center;
    width: 44px; height: 44px; border: 1px solid var(--myt-border); border-radius: 14px;
    background: var(--myt-surface); color: var(--myt-muted); cursor: pointer;
    transition: color 150ms ease, background-color 150ms ease;
}
.myt-settings-button:hover { color: var(--myt-ink); background: var(--myt-soft); }
.myt-settings-button svg { width: 22px; height: 22px; }
:host([data-settings-open]) :is(.myt-home__brand, .myt-search, .myt-theme-toggle) { visibility: hidden; pointer-events: none; }
.myt-settings-backdrop { position: fixed; inset: 0; z-index: 2; background: rgba(0,0,0,.48); backdrop-filter: blur(10px); }
.myt-settings-panel {
    position: fixed; left: 50%; top: 50%; z-index: 3; transform: translate(-50%,-50%);
    width: min(600px,calc(100% - 32px)); max-height: calc(100svh - 40px);
    overflow: auto; overscroll-behavior: contain; padding: 0; scrollbar-width: thin;
    border: 1px solid var(--myt-border); border-radius: 24px;
    background: var(--myt-settings-bg); color: var(--myt-ink); box-shadow: var(--myt-settings-shadow);
    text-align: start; font: 14px/1.5 "Roboto","Arial",sans-serif;
}
.myt-settings-panel:not([hidden]) { animation: myt-settings-enter 160ms ease-out; }
@keyframes myt-settings-enter { from { opacity: 0; } to { opacity: 1; } }
.myt-settings-panel > header {
    position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between;
    gap: 20px; padding: 28px 32px; border-bottom: 1px solid var(--myt-border); background: var(--myt-settings-header);
}
.myt-settings-heading { display: flex; align-items: center; gap: 16px; min-width: 0; }
.myt-settings-heading > span {
    display: grid; place-items: center; flex: none; width: 46px; height: 46px;
    border-radius: 15px; background: var(--myt-settings-accent-bg); color: var(--myt-accent);
}
.myt-settings-panel svg { width: 18px; height: 18px; flex: none; }
.myt-settings-heading > span svg { width: 23px; height: 23px; }
.myt-settings-panel h2 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -.7px; line-height: 1.2; }
.myt-settings-panel p { margin: 8px 0 0; color: var(--myt-muted); font-size: 13px; line-height: 1.6; }
.myt-settings-heading p { margin-top: 5px; font-size: 13px; }
.myt-settings-body { padding: 0 32px 28px; }
.myt-settings-panel section { min-width: 0; padding: 26px 0; border-bottom: 1px solid var(--myt-border); }
.myt-settings-panel section:last-of-type { border-bottom: 0; padding-bottom: 0; }
.myt-section-heading { display: flex; align-items: center; gap: 12px; min-width: 0; }
.myt-section-icon { display: grid; place-items: center; flex: none; width: 36px; height: 36px; color: var(--myt-muted); }
.myt-section-heading h3 { margin: 0; font-size: 16px; font-weight: 600; }
.myt-account-overview { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.myt-account-overview .myt-section-heading { flex: 1 1 auto; }
.myt-account-overview .myt-section-icon { width: 46px; height: 46px; border-radius: 50%; background: var(--myt-settings-control); }
.myt-account-overview p { max-width: 250px; margin-top: 5px; }
.myt-settings-panel a, .myt-settings-panel button, .myt-settings-panel select {
    box-sizing: border-box; font: inherit; border: 1px solid transparent; border-radius: 12px;
    padding: 10px 13px; color: var(--myt-ink); background: var(--myt-settings-control);
    transition: color 150ms ease, background-color 150ms ease, border-color 150ms ease;
}
.myt-settings-panel :is(a,button) { cursor: pointer; text-decoration: none; }
.myt-settings-panel :is(a,button):hover:not(:disabled) { background: var(--myt-soft); }
.myt-settings-panel button:disabled { opacity: .45; cursor: default; }
.myt-settings-panel :is(a,button,select):focus-visible, .myt-settings-button:focus-visible { outline: 2px solid var(--myt-accent); outline-offset: 3px; }
.myt-settings-panel #myt-settings-close { display: grid; place-items: center; width: 36px; height: 36px; padding: 9px; border-radius: 50%; color: var(--myt-muted); background: transparent; }
.myt-settings-panel #myt-settings-close:hover { color: var(--myt-ink); background: var(--myt-settings-control); }
.myt-settings-panel #myt-account-manage { display: inline-flex; align-items: center; justify-content: center; gap: 12px; flex: none; min-height: 44px; font-size: 13px; font-weight: 600; border: 1px solid var(--myt-border); background: var(--myt-settings-bg); }
.myt-settings-panel #myt-account-manage:hover { border-color: var(--myt-muted); }
.myt-settings-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.myt-account-actions { margin-top: 22px; gap: 4px; padding: 4px; border-radius: 14px; background: var(--myt-settings-control); }
.myt-account-actions a { flex: 1 1 auto; text-align: center; white-space: nowrap; font-size: 13px; background: transparent; padding: 9px 12px; }
.myt-account-actions a:hover { background: var(--myt-settings-selected) !important; }
.myt-cookie-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.myt-settings-panel #myt-cookie-status { margin: 0; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-variant-numeric: tabular-nums; background: var(--myt-settings-control); }
.myt-settings-panel #myt-cookie-status:is(.is-error,.is-notice) { flex-basis: 100%; padding: 0; background: transparent; }
.myt-settings-panel #myt-cookie-status.is-error { color: var(--myt-danger); }
.myt-cookie-tools { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.myt-settings-panel #myt-cookie-toggle { display: inline-flex; align-items: center; gap: 8px; padding: 9px 0; background: transparent; font-size: 13px; }
.myt-settings-panel #myt-cookie-toggle:hover:not(:disabled) { color: var(--myt-muted); }
.myt-settings-panel #myt-cookie-toggle[aria-expanded="true"] svg { transform: rotate(180deg); }
.myt-settings-panel #myt-cookie-clear { display: inline-flex; align-items: center; justify-content: center; gap: 8px; width: auto; padding: 9px 12px; color: var(--myt-danger); background: transparent; font-size: 13px; }
.myt-settings-panel #myt-cookie-clear:hover:not(:disabled) { background: var(--myt-settings-accent-bg); }
.myt-cookie-details { margin-top: 12px; padding: 6px 14px; border-radius: 14px; background: var(--myt-settings-control); }
.myt-settings-panel ul { margin: 0; padding: 0; list-style: none; max-height: 150px; overflow: auto; scrollbar-width: thin; font-size: 12px; overflow-wrap: anywhere; }
.myt-settings-panel li { padding: 9px 0; border-bottom: 1px solid var(--myt-border); }
.myt-settings-panel li:last-child { border: 0; }
.myt-cookie-name { font-family: ui-monospace,monospace; }
.myt-cookie-domain { color: var(--myt-muted); }
.myt-settings-panel #myt-cookie-confirmation { margin-top: 16px; padding: 16px; border: 1px solid var(--myt-danger); border-radius: 14px; }
.myt-settings-panel #myt-cookie-confirmation p { margin: 0 0 14px; color: var(--myt-ink); }
.myt-settings-panel #myt-cookie-confirm { background: var(--myt-danger); color: var(--myt-settings-bg); }
.myt-preferences { margin-top: 20px; }
.myt-preference-row { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 16px 0; }
.myt-preference-row + .myt-preference-row { border-top: 1px solid var(--myt-border); }
.myt-preference-row:last-child { padding-bottom: 0; }
.myt-settings-panel label, .myt-preference-label { display: block; margin: 0; font-size: 14px; font-weight: 500; }
.myt-preference-row p { margin-top: 4px; font-size: 12px; }
.myt-settings-panel select { width: 230px; max-width: 100%; min-height: 44px; font-size: 13px; padding: 10px 12px; }
.myt-theme-switch { display: flex; gap: 4px; padding: 4px; width: 230px; flex: none; border-radius: 14px; background: var(--myt-settings-control); }
.myt-settings-panel .myt-theme-choice { display: inline-flex; align-items: center; justify-content: center; gap: 8px; flex: 1 1 0; padding: 8px 9px; background: transparent; color: var(--myt-muted); font-size: 13px; }
.myt-settings-panel .myt-theme-choice[aria-pressed="true"] { background: var(--myt-settings-selected); color: var(--myt-ink); box-shadow: 0 1px 4px rgba(0,0,0,.1); }
.myt-settings-panel .myt-theme-choice svg { width: 16px; height: 16px; }
.myt-settings-panel #myt-settings-error { margin: 18px 0 0; color: var(--myt-danger); font-size: 13px; }
.myt-settings-panel #myt-settings-error:empty { display: none; }
@media (max-width: 600px) {
    .myt-settings-button { right: 16px; top: 16px; }
    .myt-settings-panel { border-radius: 20px; max-height: calc(100svh - 24px); }
    .myt-settings-panel > header { padding: 24px; gap: 12px; }
    .myt-settings-body { padding: 0 24px 24px; }
    .myt-settings-heading { gap: 12px; }
    .myt-settings-panel h2 { font-size: 24px; }
    .myt-account-overview { align-items: stretch; flex-direction: column; gap: 18px; }
    .myt-account-overview p { max-width: none; }
}
@media (max-width: 440px) {
    .myt-settings-heading > span { width: 40px; height: 40px; border-radius: 13px; }
    .myt-settings-heading p { font-size: 12px; }
    .myt-settings-panel > header { padding: 22px; }
    .myt-settings-body { padding-inline: 22px; }
    .myt-account-actions a { padding-inline: 9px; font-size: 12px; }
    .myt-preference-row { flex-direction: column; align-items: stretch; gap: 12px; }
    .myt-settings-panel select, .myt-theme-switch { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
    .myt-settings-panel:not([hidden]) { animation: none; }
    .myt-settings-panel :is(a,button,select), .myt-settings-button { transition: none; }
}

@media (max-width: 600px) {
    :host {
        justify-content: safe center !important;
        padding: 72px 20px !important;
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
        const value = theme || (root.hasAttribute("dark") ? "dark" : "light");
        if (enabled && root.dataset.mytTheme !== value) root.dataset.mytTheme = value;
        else if (!enabled) delete root.dataset.mytTheme;
        if (home) {
            if (home.dataset.mytTheme !== value) home.dataset.mytTheme = value;
            if (home.firstElementChild.dataset.mytTheme !== value) home.firstElementChild.dataset.mytTheme = value;
        }
        for (const choice of home?.firstElementChild.shadowRoot.querySelectorAll("[data-myt-theme-choice]") || []) {
            const pressed = String(choice.dataset.mytThemeChoice === root.dataset.mytTheme);
            if (choice.getAttribute("aria-pressed") !== pressed) choice.setAttribute("aria-pressed", pressed);
        }
        const button = home?.firstElementChild.shadowRoot.querySelector("#myt-theme-toggle");
        if (!button) return;
        const dark = theme ? theme === "dark" : root.hasAttribute("dark");
        const buttonTheme = dark ? "dark" : "light";
        if (button.dataset.theme !== buttonTheme) button.dataset.theme = buttonTheme;
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

    function syncSearchDecorations() {
        for (const icon of searchDecorations) {
            if (!enabled || !icon.isConnected || !icon.closest("ytd-masthead")) {
                icon.removeAttribute("data-myt-search-decoration");
                searchDecorations.delete(icon);
            }
        }
        if (!enabled) return;
        for (const input of document.querySelectorAll("ytd-masthead input:not([type='hidden'])")) {
            const scope = input.closest("ytd-searchbox, yt-searchbox, .ytSearchboxComponentHost") || input.closest("form");
            if (!scope) continue;
            const field = input.getBoundingClientRect();
            if (!field.width || !field.height) continue;
            // Native focus icons can have unnamed wrappers. Remove leading
            // graphics by their position, leaving clear/keyboard controls at right
            // and suggestion-row icons below the input untouched.
            for (const icon of scope.querySelectorAll("svg, yt-icon, [role='img']")) {
                const bounds = icon.getBoundingClientRect();
                if (!bounds.width || !bounds.height || bounds.bottom <= field.top || bounds.top >= field.bottom ||
                    bounds.left > field.left + 32 || bounds.right < scope.getBoundingClientRect().left) continue;
                const decoration = icon.closest("yt-icon") || icon;
                decoration.setAttribute("data-myt-search-decoration", "");
                searchDecorations.add(decoration);
            }
        }
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
        syncSearchDecorations();
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
        const attributes = ["data-myt-search-video", "data-myt-search-cell", "data-myt-search-grid", "data-myt-search-channel", "data-myt-search-channel-cell", "data-myt-search-video-start"];
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
            try { return anchor && new URL(anchor.href, pageLocation()); }
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
            const channels = [...search.querySelectorAll("ytd-channel-renderer")].filter(card => !card.closest("[data-myt-hidden-section]"));
            const cells = [...videos, ...channels];
            const descendantCounts = new Map();
            for (const card of cells) {
                if (channels.includes(card)) {
                    mark(card, "data-myt-search-channel");
                    mark(card, "data-myt-search-channel-cell");
                } else {
                    mark(card, "data-myt-search-video");
                    mark(card, "data-myt-search-cell");
                }
                for (let parent = card.parentElement; parent && parent !== search; parent = parent.parentElement) {
                    descendantCounts.set(parent, (descendantCounts.get(parent) || 0) + 1);
                }
            }
            for (const container of search.querySelectorAll(listContainers)) {
                if (descendantCounts.has(container)) mark(container, "data-myt-search-grid");
            }
            const wrappers = new Set();
            for (const card of cells) {
                // Keep native nodes in place. A single-video wrapper is a cell;
                // a wrapper containing several videos gets its own nested grid.
                for (let parent = card.parentElement; parent && parent !== search; parent = parent.parentElement) {
                    if (parent.matches("ytd-item-section-renderer > #contents")) break;
                    if (parent.matches(`${videoSelector}, ${otherResults}, ytd-shelf-renderer, grid-shelf-view-model, ytd-rich-section-renderer, ytd-item-section-renderer, ytd-section-list-renderer`)) continue;
                    wrappers.add(parent);
                }
            }
            for (const parent of wrappers) {
                const count = descendantCounts.get(parent);
                const structuralList = parent.matches(`${listContainers}, yt-horizontal-list-renderer`);
                const mixed = parent.matches(otherResults) || parent.querySelector(`${otherResults}, ${shelves}`);
                if (!structuralList && count === 1 && parent.querySelector("ytd-channel-renderer") && !parent.querySelector(shelves)) mark(parent, "data-myt-search-channel-cell");
                else if (structuralList || count > 1 || mixed) mark(parent, "data-myt-search-grid");
                else if (count === 1) mark(parent, "data-myt-search-cell");
            }
            const grids = new Set(search.querySelectorAll("ytd-item-section-renderer > #contents"));
            for (const [element, names] of wanted) {
                if (names.has("data-myt-search-grid")) grids.add(element);
            }
            for (const grid of grids) {
                const children = [...grid.children];
                if (!children.some(child => wanted.get(child)?.has("data-myt-search-channel-cell"))) continue;
                const firstVideo = children.find(child => wanted.get(child)?.has("data-myt-search-cell"));
                if (firstVideo) mark(firstVideo, "data-myt-search-video-start");
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

    function syncChatFrames() {
        for (const [frame, source] of suspendedChatFrames) {
            if (!frame.isConnected) suspendedChatFrames.delete(frame);
            else if (!enabled) {
                if (frame.getAttribute("src") === "about:blank") frame.setAttribute("src", source);
                suspendedChatFrames.delete(frame);
            }
        }
        if (!enabled) return;
        for (const frame of document.querySelectorAll("ytd-live-chat-frame iframe, iframe#chatframe, iframe[src*='/live_chat']")) {
            const source = frame.getAttribute("src");
            if (!source || source === "about:blank") continue;
            try {
                const url = new URL(source, pageLocation());
                if (url.protocol !== "https:" || !(url.hostname === "youtube.com" || url.hostname.endsWith(".youtube.com")) ||
                    !/^\/live_chat(?:_replay)?(?:\/|$)/.test(url.pathname)) continue;
                suspendedChatFrames.set(frame, source);
                frame.setAttribute("src", "about:blank");
            } catch { /* Unrelated embeds are not chat. */ }
        }
    }

    function syncWatchDetails() {
        syncChatFrames();
        const active = enabled && (root.dataset.mytPage === "watch" || root.dataset.mytPreviousPage === "watch");
        const watch = active && [...document.querySelectorAll("ytd-watch-flexy:not([hidden])")].find(node =>
            !node.closest("[hidden], [aria-hidden='true']") && node.querySelector("video, ytd-player"));
        playerAds?.bind(watch ? (watch.querySelector("#movie_player, .html5-video-player") || watch.querySelector("ytd-player")) : null);
        if (watchView && (!watch || watchView.native !== watch)) {
            watchView.destroy();
            watchView = null;
        }
        if (!watch || !globalThis.MinimalYouTubeWatch || !watch.querySelector("ytd-watch-metadata, ytd-video-primary-info-renderer, ytd-video-secondary-info-renderer")) return;
        if (!watchView) watchView = new globalThis.MinimalYouTubeWatch({ native: watch });
        watchView.sync({
            native: watch, language: language || defaultLanguage,
            dark: root.hasAttribute("dark"), video: new URL(pageLocation()).searchParams.get("v") || "",
            commentsButton, commentsOpen,
        });
    }

    function syncWatch() {
        if (!enabled || root.dataset.mytPage !== "watch") {
            if (commentsButton || watchVideo !== null) resetWatch();
            return;
        }
        const video = new URL(pageLocation()).searchParams.get("v") || "";
        if (watchVideo !== video) {
            watchVideo = video;
            setCommentsOpen(false);
        }
        const active = element => !element.closest("[hidden], [aria-hidden='true']") && (watchView || getComputedStyle(element).display !== "none");
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
                syncWatchDetails();
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
        if (!watchView && (commentsButton.parentElement !== row || (slot && commentsButton.nextElementSibling !== slot))) {
            row.insertBefore(commentsButton, slot || row.firstChild);
        }
    }

    function shortsDestination(value) {
        let url;
        try { url = new URL(value, pageLocation()); } catch { return null; }
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
            try { return /^\/(watch|playlist)$/.test(new URL(anchor.href, pageLocation()).pathname); }
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

    function settingsIcon(name) {
        const paths = {
            settings: '<path d="M4 7h8m6 0h2M4 17h2m6 0h8"/><circle cx="15" cy="7" r="3"/><circle cx="9" cy="17" r="3"/>',
            account: '<circle cx="12" cy="8" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
            cookies: '<path d="M21 12a4 4 0 0 1-4-4 4 4 0 0 1-5-5 9 9 0 1 0 9 9Z"/><circle cx="8" cy="10" r=".8"/><circle cx="10" cy="16" r=".8"/><circle cx="15" cy="13" r=".8"/>',
            arrow: '<path d="m7 17 10-10M7 7h10v10"/>',
            chevron: '<path d="m6 9 6 6 6-6"/>',
            close: '<path d="m6 6 12 12M18 6 6 18"/>',
            trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
            language: '<path d="M3 5h12M9 3v2M5 5c0 5 4 9 8 11M13 5c-1 5-4 9-10 12M14 21l4-10 4 10M15.5 17h5"/>',
            theme: '<circle cx="12" cy="12" r="8"/><path d="M12 4v16a8 8 0 0 0 0-16Z" fill="currentColor"/>',
            sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
            moon: '<path d="M20.8 13A9 9 0 0 1 11 3.2 9 9 0 1 0 20.8 13Z"/>',
        };
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
    }

    function pauseHiddenPreview(video) {
        if (!enabled || root.dataset.mytPage !== "home" || !home?.isConnected ||
            !(video instanceof HTMLVideoElement) || video.paused || document.pictureInPictureElement === video ||
            video.closest("ytd-miniplayer") || !video.closest("ytd-video-preview, #video-preview, ytd-rich-grid-renderer, ytd-browse[page-subtype='home']")) return;
        video.pause();
    }
    document.addEventListener("play", event => pauseHiddenPreview(event.target), true);

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
            <div class="myt-settings-backdrop" id="myt-settings-backdrop" ${settingsOpen ? "" : "hidden"}></div>
            <aside class="myt-settings-panel" id="myt-settings-panel" role="dialog" aria-modal="true" aria-labelledby="myt-settings-title" ${settingsOpen ? "" : "hidden"}>
                <header><div class="myt-settings-heading"><span>${settingsIcon("settings")}</span><div><h2 id="myt-settings-title">${copy.settings}</h2><p>${copy.settingsHint}</p></div></div><button type="button" id="myt-settings-close" aria-label="${copy.close}">${settingsIcon("close")}</button></header>
                <div class="myt-settings-body">
                    <section>
                        <div class="myt-account-overview"><div class="myt-section-heading"><span class="myt-section-icon">${settingsIcon("account")}</span><div><h3>${copy.account}</h3><p>${copy.accountInfo}</p></div></div>
                            <a id="myt-account-manage" href="https://www.youtube.com/account">${copy.manage}${settingsIcon("arrow")}</a>
                        </div>
                        <div class="myt-settings-actions myt-account-actions">
                            <a id="myt-account-signin" href="https://www.youtube.com/signin?next=%2F">${copy.signin}</a>
                            <a id="myt-account-switch" href="https://accounts.google.com/AccountChooser?service=youtube&amp;continue=https%3A%2F%2Fwww.youtube.com%2F">${copy.switchAccount}</a>
                            <a id="myt-account-signout" href="https://www.youtube.com/logout?next=%2F">${copy.signout}</a>
                        </div>
                    </section>
                    <section>
                        <div class="myt-cookie-heading"><div class="myt-section-heading"><span class="myt-section-icon">${settingsIcon("cookies")}</span><h3>${copy.cookies}</h3></div><p id="myt-cookie-status" role="status"></p></div><p>${copy.cookieInfo}</p>
                        <div class="myt-cookie-tools"><button type="button" id="myt-cookie-toggle" aria-expanded="false" aria-controls="myt-cookie-details" disabled>${copy.showCookies}${settingsIcon("chevron")}</button><button type="button" id="myt-cookie-clear" disabled>${settingsIcon("trash")}${copy.deleteCookies}</button></div>
                        <div id="myt-cookie-details" class="myt-cookie-details" hidden><ul id="myt-cookie-list"></ul></div>
                        <div id="myt-cookie-confirmation" hidden><p>${copy.confirmCookies}</p><div class="myt-settings-actions"><button type="button" id="myt-cookie-confirm">${copy.confirm}</button><button type="button" id="myt-cookie-cancel">${copy.cancel}</button></div></div>
                    </section>
                    <section>
                        <div class="myt-section-heading"><span class="myt-section-icon">${settingsIcon("theme")}</span><h3>${copy.appearance}</h3></div>
                        <div class="myt-preferences">
                            <div class="myt-preference-row"><div><label for="myt-settings-language">${copy.language}</label><p>${copy.languageInfo}</p></div><select id="myt-settings-language"><option value="">${copy.system}</option><option value="ru">Русский</option><option value="en">English</option></select></div>
                            <div class="myt-preference-row"><div><span class="myt-preference-label">${copy.theme}</span><p>${copy.themeInfo}</p></div><div class="myt-theme-switch" id="myt-settings-theme" role="group" aria-label="${copy.theme}"><button type="button" class="myt-theme-choice" id="myt-theme-light" data-myt-theme-choice="light" aria-label="${copy.light}" aria-pressed="false">${settingsIcon("sun")}${copy.lightShort}</button><button type="button" class="myt-theme-choice" id="myt-theme-dark" data-myt-theme-choice="dark" aria-label="${copy.dark}" aria-pressed="false">${settingsIcon("moon")}${copy.darkShort}</button></div></div>
                        </div>
                    </section>
                    <p id="myt-settings-error" role="alert"></p>
                </div>
            </aside>`;
        if (standaloneHome) {
            view.querySelector("form").action = "https://www.youtube.com/results";
            view.querySelector(".myt-home__brand").href = chrome.runtime.getURL("src/home/index.html") + location.search;
        }
        view.querySelector("#myt-theme-toggle").addEventListener("click", () => {
            const dark = theme ? theme === "dark" : root.hasAttribute("dark");
            saveTheme(dark ? "light" : "dark");
        });
        const panel = view.querySelector("#myt-settings-panel");
        const settingsButton = view.querySelector("#myt-settings-button");
        const cookieStatus = view.querySelector("#myt-cookie-status");
        const cookieList = view.querySelector("#myt-cookie-list");
        const clearCookies = view.querySelector("#myt-cookie-clear");
        const cookieToggle = view.querySelector("#myt-cookie-toggle");
        const cookieDetails = view.querySelector("#myt-cookie-details");
        const confirmation = view.querySelector("#myt-cookie-confirmation");
        const settingsError = view.querySelector("#myt-settings-error");
        const setPanel = open => {
            settingsOpen = open;
            panel.hidden = !open;
            view.querySelector("#myt-settings-backdrop").hidden = !open;
            surface.toggleAttribute("data-settings-open", open);
            for (const element of view.querySelectorAll(".myt-home__brand, .myt-search, .myt-theme-toggle")) element.inert = open;
            settingsButton.setAttribute("aria-expanded", String(open));
            confirmation.hidden = true;
            if (open) {
                view.querySelector("#myt-settings-close").focus();
                requestCookies("minimal-youtube:get-cookies");
            } else settingsButton.focus();
        };
        const requestCookies = action => {
            cookieStatus.textContent = copy.loading;
            cookieDetails.hidden = true;
            cookieToggle.disabled = true;
            cookieToggle.setAttribute("aria-expanded", "false");
            cookieStatus.classList.remove("is-error", "is-notice");
            clearCookies.disabled = true;
            view.querySelector("#myt-cookie-confirm").disabled = true;
            const done = response => {
                if (!container.isConnected) return;
                view.querySelector("#myt-cookie-confirm").disabled = false;
                if (chrome.runtime?.lastError || !response?.ok || !Array.isArray(response.cookies)) {
                    cookieStatus.classList.add("is-error");
                    cookieStatus.textContent = copy.cookieError;
                    return;
                }
                confirmation.hidden = true;
                cookieList.replaceChildren();
                for (const cookie of response.cookies) {
                    const item = document.createElement("li");
                    const name = document.createElement("span");
                    name.className = "myt-cookie-name";
                    name.textContent = cookie.name;
                    const domain = document.createElement("span");
                    domain.className = "myt-cookie-domain";
                    domain.textContent = ` · ${cookie.domain}`;
                    item.append(name, domain);
                    cookieList.append(item);
                }
                cookieToggle.disabled = response.cookies.length === 0;
                cookieStatus.classList.toggle("is-notice", typeof response.removed === "number");
                clearCookies.disabled = response.cookies.length === 0;
                cookieStatus.textContent = `${typeof response.removed === "number" ? copy.cookieDeleted + " " + response.removed + ". " : ""}${copy.cookieCount} ${response.cookies.length}`;
            };
            try {
                if (standaloneHome && chrome.tabs?.getCurrent) {
                    chrome.tabs.getCurrent(tab => chrome.runtime.sendMessage({ action, tabId: tab?.id }, done));
                } else chrome.runtime.sendMessage({ action }, done);
            } catch { done(null); }
        };
        settingsButton.addEventListener("click", () => setPanel(panel.hidden));
        view.querySelector("#myt-settings-close").addEventListener("click", () => setPanel(false));
        view.querySelector("#myt-settings-backdrop").addEventListener("click", () => setPanel(false));
        view.addEventListener("keydown", event => {
            if (event.key === "Tab" && !panel.hidden) {
                const controls = [...panel.querySelectorAll("a[href], button:not(:disabled), select:not(:disabled)")]
                    .filter(element => element.getClientRects().length && !element.closest("[hidden]"));
                const first = controls[0], last = controls[controls.length - 1];
                if ((event.shiftKey && view.activeElement === first) || (!event.shiftKey && view.activeElement === last)) {
                    event.preventDefault();
                    (event.shiftKey ? last : first)?.focus();
                }
            }
            if (event.key === "Escape" && !panel.hidden) {
                event.preventDefault();
                event.stopPropagation();
                setPanel(false);
            }
        });
        cookieToggle.addEventListener("click", () => {
            const open = cookieDetails.hidden;
            cookieDetails.hidden = !open;
            cookieToggle.setAttribute("aria-expanded", String(open));
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
        for (const choice of view.querySelectorAll("[data-myt-theme-choice]")) {
            choice.addEventListener("click", () => saveTheme(choice.dataset.mytThemeChoice));
        }
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
                const url = new URL(pageLocation());
                url.searchParams.set("hl", selected || defaultLanguage);
                url.searchParams.set("persist_hl", "1");
                location.assign(standaloneHome ? chrome.runtime.getURL("src/home/index.html") + url.search : url.href);
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
            if (standaloneHome && language) {
                for (const [name, value] of [["hl", language], ["persist_hl", "1"]]) {
                    let setting = view.querySelector(`input[name="${name}"]`);
                    if (!setting) { setting = document.createElement("input"); setting.type = "hidden"; setting.name = name; view.querySelector("form").append(setting); }
                    setting.value = value;
                }
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
        if (pendingNavigation && pageLocation() !== navigationSource) pendingNavigation = null;
        const url = new URL(pendingNavigation || pageLocation());
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
        // A verified browser rule may open the lightweight local home. Native
        // and SPA arrivals always have this own UI as a fallback: never blindly
        // navigate to an extension file that could be missing after an update.
        if (path === "/") {
            if (!home?.isConnected) {
                home = createHome();
                document.querySelectorAll("video").forEach(pauseHiddenPreview);
            }
        } else if (home && !keepHome) {
            home.remove();
            home = null;
        }
        renderTheme();
        syncWatch();
        syncWatchDetails();
        syncSections();
        if ((urlChanged || force) && nextPage !== "home") {
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
            if (root.dataset.mytPage === "home" && home?.isConnected && !pendingNavigation && !transitionActive) {
                pendingRoots.clear();
                cleanTitle();
                return;
            }
            if (!watchView) {
                syncBrand();
                syncSearchDecorations();
            }
            if (!settingsReady) return;
            syncWatch();
            syncWatchDetails();
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
        if (enabled && (pageLocation() !== (pendingNavigation ? navigationSource : currentURL) ||
            (home?.isConnected && root.dataset.mytPage !== "home") ||
            (root.dataset.mytPage === "home" && document.body && !home?.isConnected))) {
            updateRoute();
        }
        const stableHome = root.dataset.mytPage === "home" && home?.isConnected && !pendingNavigation && !transitionActive;
        const relevant = records.filter(record => {
            const target = record.target instanceof Element ? record.target : record.target.parentElement;
            if (!target) return false;
            if (target.closest("title")) { cleanTitle(); return false; }
            if (stableHome) return record.target === root && record.attributeName === "dark";
            if (target.closest("#myt-watch, #myt-home")) return false;
            // Player clocks, captions, progress aria labels and popup animations
            // do not change our metadata UI. React only to media-node replacement.
            if (watchView && target.closest("ytd-player, #movie_player, .html5-video-player")) {
                return record.type === "childList" && [...record.addedNodes, ...record.removedNodes].some(node =>
                    node instanceof Element && (node.matches("video, ytd-player") || node.querySelector("video, ytd-player")));
            }
            if (watchView && target.closest("ytd-popup-container, ytd-comments")) return false;
            return true;
        });
        if (!relevant.length) return;
        for (const record of relevant) {
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
        playerAds?.setEnabled(Boolean(value));
        document.dispatchEvent(new CustomEvent("minimal-youtube:optimization", { detail: { enabled: Boolean(value) } }));
        if (!value && standaloneHome) { openNativeHome(); return; }
        if (enabled === value) return;
        enabled = value;
        root.classList.toggle("minimal-youtube", enabled);
        if (enabled) {
            classObserver.observe(root, { attributes: true, attributeFilter: ["class"] });
            observer.observe(document.documentElement, {
                subtree: true, childList: true, characterData: true,
                attributes: true, attributeFilter: ["href", "aria-label", "aria-hidden", "visibility", "is-shorts", "dark", "hidden", "theater", "fullscreen", "collapsed", "src", "srcset", "data-src", "expanded", "is-expanded", "aria-pressed", "subscribed", "is-subscribed", "disabled", "aria-disabled", "aria-busy", "aria-valuetext", "data-value", "value", "content"],
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
            syncWatchDetails();
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
                const incoming = new URL(value, pageLocation());
                if (incoming.origin === location.origin) {
                    pendingNavigation = incoming.href;
                    navigationSource = pageLocation();
                    transitionActive = true;
                    if (incoming.pathname !== "/watch" || incoming.searchParams.get("v") !== new URL(pageLocation()).searchParams.get("v")) {
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
        transitionActive = Boolean(home?.isConnected && new URL(pageLocation()).pathname !== "/");
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
    document.addEventListener("focusin", () => { if (enabled) schedule(); });
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
        if (watchView && (event.composedPath().includes(watchView.host) || event.target.closest?.("[data-myt-watch-island]"))) return;
        if (!enabled || root.dataset.mytPage === "home" ||
            event.ctrlKey || !event.deltaY || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
        const target = event.target instanceof Element ? event.target : event.target.parentElement;
        if (!target || target.closest("input, textarea, select, [contenteditable], dialog, [role='menu'], [role='dialog'], [role='listbox'], tp-yt-paper-dialog, ytd-popup-container, ytd-player, video, iframe, #movie_player, .html5-video-player, .ytp-popup")) return;
        const canScroll = element => {
            if (element.scrollHeight <= element.clientHeight + 1) return false;
            const overflow = getComputedStyle(element).overflowY;
            return /auto|scroll/.test(overflow) ||
                (element === document.scrollingElement && !/clip/.test(overflow));
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
        // An empty area can be inside the full-width renderer, not just outside
        // its bounding box. Treat that background as part of the page scrollport.
        const background = !target.closest("a, button, [role='button'], ytd-video-renderer, ytd-grid-video-renderer, ytd-rich-item-renderer, yt-lockup-view-model, ytd-channel-renderer, ytd-playlist-renderer");
        if ((!gutter && !background) || (event.defaultPrevented && !background)) return;
        const inner = [...main.querySelectorAll("*")].filter(element =>
            element.clientHeight >= innerHeight / 2 && element.clientWidth >= main.clientWidth / 2 &&
            canScroll(element) && visible(element) &&
            !element.closest("[role='dialog'], ytd-comments, ytd-player"))
            .sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight)[0];
        if (!gutter && inner) {
            const innerBounds = inner.getBoundingClientRect();
            gutter = event.clientX < innerBounds.left || event.clientX >= innerBounds.right;
        }
        if (!gutter && !background) return;
        let scroller = inner || main;
        while (scroller && !canScroll(scroller)) scroller = scroller.parentElement;
        if (!scroller) return;
        for (let element = target; element; element = element.parentElement) {
            if (element !== scroller && element !== document.scrollingElement && element !== document.body &&
                !element.contains(main) && canScroll(element)) return;
        }
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
