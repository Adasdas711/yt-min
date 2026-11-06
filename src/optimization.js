"use strict";

// Persistent browser configuration: the landing page never loads YouTube's app.
(() => {
    const ruleId = 470001;
    const chatRuleId = 470002;
    const scriptId = "minimal-youtube-data-pruning";
    let revision = 0;
    let configuration = Promise.resolve();
    const supported = Boolean(chrome.declarativeNetRequest && chrome.scripting);
    const focusEnabled = value => typeof value === "undefined" || Boolean(value);

    function configure(enabled) {
        const current = ++revision;
        configuration = configuration.catch(() => {}).then(async () => {
            if (!supported || current !== revision) return;
            await chrome.declarativeNetRequest.updateDynamicRules({
                removeRuleIds: [ruleId, chatRuleId],
                addRules: enabled ? [{
                    id: ruleId,
                    priority: 1,
                    action: { type: "redirect", redirect: {
                        regexSubstitution: chrome.runtime.getURL("src/home/index.html") + "\\2",
                    } },
                    condition: {
                        regexFilter: "^https://(www\\.)?youtube\\.com/(\\?.*)?$",
                        resourceTypes: ["main_frame"],
                    },
                }, {
                    id: chatRuleId,
                    priority: 1,
                    action: { type: "block" },
                    condition: {
                        regexFilter: "^https://([a-z0-9-]+\\.)?youtube\\.com/(live_chat(_replay)?([/?].*)?|youtubei/v1/live_chat/.*)$",
                        resourceTypes: ["sub_frame", "xmlhttprequest"],
                        excludedInitiatorDomains: ["music.youtube.com"],
                        excludedRequestDomains: ["music.youtube.com"],
                    },
                }] : [],
            });
            const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [scriptId] });
            if (!enabled) {
                if (registered.length) await chrome.scripting.unregisterContentScripts({ ids: [scriptId] });
                return;
            }
            const script = {
                id: scriptId,
                matches: ["https://*.youtube.com/*"],
                excludeMatches: ["https://music.youtube.com/*"],
                js: ["src/content/data-pruning.js"],
                runAt: "document_start",
                world: "MAIN",
                allFrames: false,
                persistAcrossSessions: true,
            };
            if (registered.length) await chrome.scripting.updateContentScripts([script]);
            else await chrome.scripting.registerContentScripts([script]);
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
