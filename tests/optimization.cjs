"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function main() {
    const state = { enabled: true }, rules = new Map([[470001, { action: { type: 'redirect', redirect: { url: 'chrome-extension://old-id/missing.html' } } }]]), sessionRules = new Map(), registered = new Map(), events = {};
    const homeFiles = ['src/home/index.html', 'src/home/home.js', 'src/home/home.css', 'src/content/content.js', 'src/styles/styles.css'];
    const missing = new Set(), rejected = new Set(), probes = [], sessionChanges = [];
    let publicHome = true, probeGate = null;
    let storageListener, messageListener;
    const chrome = {
        runtime: {
            id: "extension-id", getURL: resource => "chrome-extension://extension-id/" + resource,
            getManifest: () => ({ web_accessible_resources: publicHome ? [{ resources: ['src/home/index.html'], matches: ['<all_urls>'] }] : [] }),
            onInstalled: { addListener: fn => events.installed = fn }, onStartup: { addListener: fn => events.startup = fn },
            onMessage: { addListener: fn => messageListener = fn },
        },
        storage: { local: { async get() { return { ...state }; } }, onChanged: { addListener: fn => storageListener = fn } },
        declarativeNetRequest: {
            async updateDynamicRules({ removeRuleIds, addRules }) {
                for (const id of removeRuleIds) rules.delete(id);for (const rule of addRules) rules.set(rule.id, rule);
            },
            async updateSessionRules({ removeRuleIds, addRules }) {
                sessionChanges.push(addRules.length);
                for (const id of removeRuleIds) sessionRules.delete(id);for (const rule of addRules) sessionRules.set(rule.id, rule);
            },
        },
        scripting: {
            async getRegisteredContentScripts() { return [...registered.values()]; },
            async registerContentScripts(scripts) { for (const script of scripts) registered.set(script.id, script); },
            async updateContentScripts(scripts) { for (const script of scripts) registered.set(script.id, script); },
            async unregisterContentScripts({ ids }) { for (const id of ids) registered.delete(id); },
        },
        cookies: {
            async getAllCookieStores() { return [{ id: "current", tabIds: [7] }]; },
            async getAll(filter) { assert.equal(filter.storeId, "current");return []; },
        },
    };
    const context = vm.createContext({ chrome, URL, console, fetch: async (url, options) => {
        assert(url.startsWith(chrome.runtime.getURL('')), 'Probe only this extension');
        const file = url.slice(chrome.runtime.getURL('').length);
        assert(homeFiles.includes(file), file);assert.equal(options.cache, 'no-store');probes.push(file);
        if (probeGate) await probeGate;
        if (rejected.has(file)) throw new Error('ERR_FILE_NOT_FOUND');
        return { ok: !missing.has(file), body: { async cancel() {} } };
    } });
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/optimization.js"), "utf8"), context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/background.js"), "utf8"), context);
    await new Promise(setImmediate);
    assert.equal(rules.size, 4);assert.equal(sessionRules.size, 1);assert.equal(registered.size, 1);
    assert(!rules.has(470001), 'A legacy persistent homepage redirect must be removed');
    assert.deepEqual([...probes].sort(), [...homeFiles].sort());
    const rule = [...sessionRules.values()][0], script = [...registered.values()][0];
    assert.equal(script.world, "MAIN");assert.equal(script.runAt, "document_start");assert.equal(script.persistAcrossSessions, true);
    assert.deepEqual([...script.excludeMatches], ["https://music.youtube.com/*"]);
    assert.deepEqual([...rule.condition.resourceTypes], ["main_frame"]);
    const redirect = url => {
        const match = url.match(new RegExp(rule.condition.regexFilter));
        return match && rule.action.redirect.regexSubstitution.replace(/\\(\d)/g, (_, index) => match[Number(index)] || "");
    };
    assert.equal(redirect("https://www.youtube.com/"), chrome.runtime.getURL("src/home/index.html"));
    assert.equal(redirect("https://youtube.com/?hl=ru&persist_hl=1"), chrome.runtime.getURL("src/home/index.html") + "?hl=ru&persist_hl=1");
    for (const url of ["https://www.youtube.com/watch?v=keep", "https://www.youtube.com/results?search_query=keep", "https://www.youtube.com/@channel", "https://www.youtube.com/signin", "https://www.youtube.com/account", "https://www.youtube.com/logout", "https://music.youtube.com/", "https://youtube.com.example/"]) assert.equal(redirect(url), null, url);
    const chatRule = [...rules.values()].find(rule => rule.action.type === 'block');
    assert.deepEqual([...chatRule.condition.resourceTypes], ['sub_frame', 'xmlhttprequest']);
    assert.deepEqual([...chatRule.condition.excludedInitiatorDomains], ['music.youtube.com']);
    assert.deepEqual([...chatRule.condition.excludedRequestDomains], ['music.youtube.com']);
    const chatURL = new RegExp(chatRule.condition.regexFilter);
    for (const path of ['/live_chat?v=live', '/live_chat_replay?continuation=replay', '/youtubei/v1/live_chat/get_live_chat?key=live', '/youtubei/v1/live_chat/get_live_chat_replay?key=replay']) {
        assert(chatURL.test('https://www.youtube.com' + path), path);
        assert(chatURL.test('https://youtube.com' + path), path);
    }
    for (const url of ['https://www.youtube.com/watch?v=keep', 'https://www.youtube.com/youtubei/v1/player', 'https://www.youtube.com/youtubei/v1/next', 'https://www.youtube.com/live/keep', 'https://www.youtube.com/live_chat_settings', 'https://youtube.com.example/live_chat', 'https://media.example/video']) assert(!chatURL.test(url), url);
    const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '../manifest.json'), 'utf8'));
    for (const domain of ['doubleclick.net','googleadservices.com','googlesyndication.com']) assert(manifest.host_permissions.includes('https://*.'+domain+'/*'));
    const extras = rules.get(470005), blocksExtra = url => new RegExp(extras.condition.regexFilter).test(url);
    assert.equal(extras.action.type, 'block');assert.deepEqual([...extras.condition.initiatorDomains], ['youtube.com']);
    assert(!extras.condition.resourceTypes.includes('main_frame') && !extras.condition.resourceTypes.includes('script'));
    for (const url of ['https://www.youtube.com/s/search/audio/open.mp3', 'https://www.youtube.com/s/search/audio/no_input.mp3']) assert(blocksExtra(url), url);
    // Lottie animations stay allowed: YouTube retries a blocked one without end.
    for (const url of ['https://www.youtube.com/youtube/img/lottie/custom_animated_like_icon/animated_like_learning_dark_v2.json', 'https://www.gstatic.com/youtube/img/lottie/animated_like_icon/like_dark.json', 'https://www.gstatic.com/youtube/img/lottie/subscribe_action/subscribe.json']) assert(!blocksExtra(url), url);
    assert(!manifest.host_permissions.includes('https://www.gstatic.com/*'), 'No gstatic host access is needed');
    for (const url of ['https://www.youtube.com/s/player/a5c2aafe/player_es6.vflset/ru_RU/base.js', 'https://www.youtube.com/s/desktop/cb518cf3/jsbin/scheduler.vflset/scheduler.js', 'https://www.youtube.com/youtubei/v1/search', 'https://www.youtube.com/api/stats/watchtime', 'https://www.youtube.com/s/search/audio']) assert(!blocksExtra(url), url);
    const adRules = [rules.get(470003), rules.get(470004)];
    for (const ad of adRules) {
        assert.equal(ad.action.type, 'block');
        assert.deepEqual([...ad.condition.initiatorDomains], ['youtube.com']);
        assert.deepEqual([...ad.condition.excludedInitiatorDomains], ['music.youtube.com']);
        assert(!ad.condition.resourceTypes.includes('main_frame'));
    }
    const blocksAdURL = url => adRules.some(rule => new RegExp(rule.condition.regexFilter).test(url));
    for (const url of ['https://googleads.g.doubleclick.net/pagead/ads?slot=1', 'https://pubads.g.doubleclick.net/gampad/ads', 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js', 'https://www.googleadservices.com/pagead/conversion', 'https://www.youtube.com/pagead/adview', 'https://www.youtube.com/api/stats/ads?ver=2', 'https://www.youtube.com/youtubei/v1/player/ad_break?prettyPrint=false']) assert(blocksAdURL(url), url);
    for (const url of ['https://rr1---sn.example.googlevideo.com/videoplayback?sig=keep&ad=word', 'https://www.youtube.com/youtubei/v1/player?videoId=keep', 'https://www.youtube.com/youtubei/v1/next', 'https://www.youtube.com/api/stats/watchtime', 'https://www.youtube.com/watch?v=ad123', 'https://i.ytimg.com/vi/video/default.jpg', 'https://static.doubleclick.net/instream/ad_status.js', 'https://www.youtube.com/s/player/native/base.js', 'https://doubleclick.net.example/pagead/ads']) assert(!blocksAdURL(url), url);
    const home = { id: chrome.runtime.id, url: chrome.runtime.getURL("src/home/index.html") + "?hl=ru", frameId: 0 };
    const request = (action, sender = home, extra = {}) => new Promise(resolve => {
        assert.equal(messageListener({ action, ...extra }, sender, resolve), true);
    });
    assert.equal((await request("minimal-youtube:open-native-home")).error, "focus-enabled");
    assert.deepEqual(JSON.parse(JSON.stringify(await request("minimal-youtube:get-cookies", home, { tabId: 7 }))), { ok: true, cookies: [] });
    const missingTab = await request("minimal-youtube:get-cookies", { id: chrome.runtime.id, url: "https://www.youtube.com/" }, { tabId: 7 });
    assert.equal(missingTab.ok, false, "Website messages must not choose a cookie store");
    for (const url of ["chrome-extension://another-id/src/home/index.html", "chrome-extension://extension-id/src/home/index.html.evil", "https://example.com/src/home/index.html"]) {
        assert.equal(messageListener({ action: "minimal-youtube:get-cookies" }, { ...home, url }, () => assert.fail("Untrusted response")), false);
    }
    assert.equal(messageListener({ action: "minimal-youtube:get-cookies" }, { ...home, frameId: 2 }, () => assert.fail("Subframe response")), false);
    state.enabled = false;storageListener({ enabled: { newValue: false } }, "local");
    const native = await request("minimal-youtube:open-native-home");
    assert.equal(native.url, "https://www.youtube.com/");assert.equal(rules.size, 0);assert.equal(sessionRules.size, 0);assert.equal(registered.size, 0);
    state.enabled = true;storageListener({ enabled: { newValue: true } }, "local");
    await new Promise(setImmediate);assert.equal(rules.size, 4);assert.equal(sessionRules.size, 1);assert.equal(registered.size, 1);
    await Promise.all([context.MinimalYouTubeOptimization.configure(false), context.MinimalYouTubeOptimization.configure(true), context.MinimalYouTubeOptimization.configure(false)]);
    assert.equal(rules.size, 0);assert.equal(sessionRules.size, 0);assert.equal(registered.size, 0);
    state.enabled = true;events.startup();await new Promise(setImmediate);
    assert.equal(rules.size, 4);assert.equal(sessionRules.size, 1);assert.equal(registered.size, 1);
    // Missing HTML or any of its dependencies must never enable a broken redirect.
    for (const file of homeFiles) {
        missing.add(file);await context.MinimalYouTubeOptimization.configure(true);
        assert.equal(sessionRules.size, 0, file);assert.equal(rules.size, 4);assert.equal(registered.size, 1);
        missing.clear();
    }
    rejected.add(homeFiles[0]);await context.MinimalYouTubeOptimization.configure(true);
    assert.equal(sessionRules.size, 0);rejected.clear();
    publicHome = false;await context.MinimalYouTubeOptimization.configure(true);
    assert.equal(sessionRules.size, 0);publicHome = true;
    const sessionAPI = chrome.declarativeNetRequest.updateSessionRules;
    delete chrome.declarativeNetRequest.updateSessionRules;
    rules.set(470001, { action: { type: 'redirect' } });
    await context.MinimalYouTubeOptimization.configure(true);
    assert(!rules.has(470001));assert.equal(registered.size, 1);
    chrome.declarativeNetRequest.updateSessionRules = sessionAPI;
    let releaseProbe;
    probeGate = new Promise(resolve => releaseProbe = resolve);
    const addsBefore = sessionChanges.filter(Boolean).length;
    const pending = context.MinimalYouTubeOptimization.configure(true);
    await new Promise(setImmediate);
    const stopped = context.MinimalYouTubeOptimization.configure(false);
    releaseProbe();probeGate = null;await Promise.all([pending, stopped]);
    assert.equal(sessionChanges.filter(Boolean).length, addsBefore, 'A late probe must not re-enable a disabled redirect');
    assert.equal(sessionRules.size, 0);assert.equal(rules.size, 0);assert.equal(registered.size, 0);
    await context.MinimalYouTubeOptimization.configure(true);
    assert.equal(sessionRules.size, 1);assert.equal(rules.size, 4);assert.equal(registered.size, 1);
    console.log("PASS verified session-only home redirect, old-rule migration, missing/rejected files, WAR/API fallback, racing disable, scoped ad request filters that preserve video CDN/player requests, persistent chat/pruning and sender/cookie scope");
}
main().catch(error => { console.error(error); process.exitCode = 1; });
