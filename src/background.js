"use strict";

if (typeof importScripts === "function") importScripts("optimization.js");

const youtubeDomain = domain => domain === "youtube.com" || domain.endsWith(".youtube.com");

async function cookieStore(sender) {
    if (typeof sender.tab?.id !== "number") throw new Error("Missing tab");
    const stores = await chrome.cookies.getAllCookieStores();
    const store = stores.find(store => store.tabIds.includes(sender.tab.id));
    if (!store) throw new Error("Missing cookie store");
    return store.id;
}

async function youtubeCookies(sender) {
    const storeId = await cookieStore(sender);
    const filter = { domain: "youtube.com", storeId };
    const cookies = await chrome.cookies.getAll(filter);
    // An empty partition-key filter includes partitioned cookies on newer
    // Chromium versions. Older versions reject this optional API field.
    try { cookies.push(...await chrome.cookies.getAll({ ...filter, partitionKey: {} })); }
    catch (error) {
        if (!/Unexpected property|Invalid value|No matching signature/i.test(error.message || "")) throw error;
    }
    const unique = new Map();
    for (const cookie of cookies) {
        if (!youtubeDomain(cookie.domain.replace(/^\./, ""))) continue;
        const key = JSON.stringify([cookie.storeId, cookie.name, cookie.domain, cookie.path, cookie.partitionKey || null]);
        unique.set(key, cookie);
    }
    return [...unique.values()];
}

function cookieMetadata(cookies) {
    // Cookie values and authentication material never leave the background worker.
    return cookies.map(({ name, domain, path, session, expirationDate }) => ({ name, domain, path, session, expirationDate }));
}

async function handleCookieRequest(message, sender) {
    // Extension pages can lack sender.tab. Their own tabs.getCurrent() supplies
    // the tab ID; ordinary website senders cannot select another cookie store.
    if (!sender.tab && chrome.runtime.getURL && Number.isInteger(message.tabId)) {
        const home = new URL(chrome.runtime.getURL("src/home/index.html"));
        const source = new URL(sender.url);
        if (source.protocol === home.protocol && source.host === home.host && source.pathname === home.pathname) {
            sender = { ...sender, tab: { id: message.tabId } };
        }
    }
    const cookies = await youtubeCookies(sender);
    if (message.action === "minimal-youtube:get-cookies") {
        return { ok: true, cookies: cookieMetadata(cookies) };
    }
    let removed = 0;
    for (const cookie of cookies) {
        const details = {
            url: `https://${cookie.domain.replace(/^\./, "")}${cookie.path}`,
            name: cookie.name,
            storeId: cookie.storeId,
        };
        if (cookie.partitionKey) details.partitionKey = cookie.partitionKey;
        if (await chrome.cookies.remove(details)) removed++;
    }
    const remaining = await youtubeCookies(sender);
    return { ok: true, removed, cookies: cookieMetadata(remaining) };
}

function trustedSender(sender) {
    if (sender.id !== chrome.runtime.id || (typeof sender.frameId === "number" && sender.frameId !== 0)) return false;
    try {
        const url = new URL(sender.url || "");
        if (url.protocol === "https:" && youtubeDomain(url.hostname)) return true;
        if (chrome.runtime.getURL) {
            const home = new URL(chrome.runtime.getURL("src/home/index.html"));
            return url.protocol === home.protocol && url.host === home.host && url.pathname === home.pathname;
        }
    } catch { /* Only exact extension/YouTube origins can access these actions. */ }
    return false;
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
    if (!trustedSender(sender)) return false;
    if (message?.action === "minimal-youtube:open-native-home") {
        if (!globalThis.MinimalYouTubeOptimization) { respond({ ok: false }); return false; }
        globalThis.MinimalYouTubeOptimization.nativeHome().then(respond, () => respond({ ok: false }));
        return true;
    }
    if (!["minimal-youtube:get-cookies", "minimal-youtube:clear-cookies"].includes(message?.action)) return false;
    handleCookieRequest(message, sender).then(respond, () => respond({ ok: false, error: "cookies-unavailable" }));
    return true;
});
