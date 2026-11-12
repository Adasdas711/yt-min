"use strict";

// Persistent scoped ad/chat filters and pruning; the verified local homepage redirect is session-only.
(() => {
    const ruleId = 470001;
    const chatRuleId = 470002;
    const adRuleIds = [470003, 470004];
    // Decorations the owned pages never show: voice search sounds (its button
    // is hidden) and Lottie animations (like/subscribe effects).
    const extrasRuleId = 470005;
    const scriptId = "minimal-youtube-data-pruning";
    const homePath = "src/home/index.html";
    const homeFiles = [homePath, "src/home/home.js", "src/home/home.css", "src/content/content.js", "src/styles/styles.css"];
    async function localHomeAvailable() {
        try {
            const manifest = chrome.runtime.getManifest();
            const exposed = manifest.web_accessible_resources?.some(entry =>
                entry.resources?.includes(homePath) && entry.matches?.includes("<all_urls>"));
            if (!exposed) return false;
            const available = await Promise.all(homeFiles.map(async path => {
                try {
                    const response = await fetch(chrome.runtime.getURL(path), { cache: "no-store" });
                    const ok = response.ok;
                    await response.body?.cancel();
                    return ok;
                } catch { return false; }
            }));
            return available.every(Boolean);
        } catch { return false; }
    }
    let revision = 0;
    let configuration = Promise.resolve();
    const supported = Boolean(chrome.declarativeNetRequest && chrome.scripting);
    const focusEnabled = value => typeof value === "undefined" || Boolean(value);

    function configure(enabled) {
        const current = ++revision;
        configuration = configuration.catch(() => {}).then(async () => {
            if (!supported || current !== revision) return;
            await chrome.declarativeNetRequest.updateDynamicRules({
                removeRuleIds: [ruleId, chatRuleId, ...adRuleIds, extrasRuleId],
                addRules: enabled ? [{
                    id: chatRuleId,
                    priority: 1,
                    action: { type: "block" },
                    condition: {
                        regexFilter: "^https://([a-z0-9-]+\\.)?youtube\\.com/(live_chat(_replay)?([/?].*)?|youtubei/v1/live_chat/.*)$",
                        resourceTypes: ["sub_frame", "xmlhttprequest"],
                        excludedInitiatorDomains: ["music.youtube.com"],
                        excludedRequestDomains: ["music.youtube.com"],
                    },
                }, {
                    id: adRuleIds[0], priority: 1, action: { type: "block" },
                    condition: {
                        regexFilter: "^https://([a-z0-9-]+\\.)*(doubleclick\\.net|googleadservices\\.com|googlesyndication\\.com)/(pagead/|gampad/|pcs/|ddm/|simgad/)",
                        initiatorDomains: ["youtube.com"], excludedInitiatorDomains: ["music.youtube.com"],
                        resourceTypes: ["script", "xmlhttprequest", "sub_frame", "image", "media", "ping"],
                    },
                }, {
                    id: adRuleIds[1], priority: 1, action: { type: "block" },
                    condition: {
                        regexFilter: "^https://([a-z0-9-]+\\.)?youtube\\.com/(pagead/|api/stats/ads([/?]|$)|youtubei/v1/player/ad_break([/?]|$))",
                        initiatorDomains: ["youtube.com"], excludedInitiatorDomains: ["music.youtube.com"],
                        resourceTypes: ["script", "xmlhttprequest", "sub_frame", "image", "media", "ping"],
                    },
                }, {
                    id: extrasRuleId, priority: 1, action: { type: "block" },
                    condition: {
                        regexFilter: "^https://([a-z0-9-]+\\.)?youtube\\.com/(s/search/audio/|youtube/img/lottie/)",
                        initiatorDomains: ["youtube.com"], excludedInitiatorDomains: ["music.youtube.com"],
                        resourceTypes: ["xmlhttprequest", "media", "other"],
                    },
                }] : [],
            });
            // Old releases kept a redirect across updates/restarts, even if its
            // target disappeared. Remove it above before checking any local file.
            const sessionRules = chrome.declarativeNetRequest.updateSessionRules;
            if (sessionRules) await chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [ruleId], addRules: [] });
            const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [scriptId] });
            if (!enabled) {
                if (registered.length) await chrome.scripting.unregisterContentScripts({ ids: [scriptId] });
                return;
            }
            const script = {
                id: scriptId,
                matches: ["https://*.youtube.com/*"],
                excludeMatches: ["https://music.youtube.com/*"],
                js: ["src/content/search-data.js", "src/content/data-pruning.js"],
                runAt: "document_start",
                world: "MAIN",
                allFrames: false,
                persistAcrossSessions: true,
            };
            if (registered.length) await chrome.scripting.updateContentScripts([script]);
            else await chrome.scripting.registerContentScripts([script]);
            if (sessionRules && await localHomeAvailable() && current === revision) {
                await chrome.declarativeNetRequest.updateSessionRules({
                    removeRuleIds: [ruleId],
                    addRules: [{
                        id: ruleId, priority: 1,
                        action: { type: "redirect", redirect: { regexSubstitution: chrome.runtime.getURL(homePath) + "\\2" } },
                        condition: { regexFilter: "^https://(www\\.)?youtube\\.com/(\\?.*)?$", resourceTypes: ["main_frame"] },
                    }],
                });
            }
        });
        return configuration;
    }

    async function refresh() {
        const state = await chrome.storage.local.get("enabled");
        await configure(focusEnabled(state.enabled));
    }
    function start() {
        refresh().catch(() => console.warn("Minimal YouTube: memory optimization configuration failed."));
    }
    async function nativeHome() {
        const state = await chrome.storage.local.get("enabled");
        if (focusEnabled(state.enabled)) return { ok: false, error: "focus-enabled" };
        await configure(false);
        return { ok: true, url: "https://www.youtube.com/" };
    }
    globalThis.MinimalYouTubeOptimization = { configure, nativeHome };
    if (!supported) return;
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area === "local" && changes.enabled) {
            configure(focusEnabled(changes.enabled.newValue)).catch(() =>
                console.warn("Minimal YouTube: memory optimization configuration failed."));
        }
    });
    chrome.runtime.onInstalled.addListener(start);
    chrome.runtime.onStartup.addListener(start);
    start();
})();
