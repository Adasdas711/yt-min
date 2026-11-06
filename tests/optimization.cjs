"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function main() {
    const state = { enabled: true }, rules = new Map(), registered = new Map(), events = {};
    let storageListener, messageListener;
    const chrome = {
        runtime: {
            id: "extension-id", getURL: resource => "chrome-extension://extension-id/" + resource,
            onInstalled: { addListener: fn => events.installed = fn }, onStartup: { addListener: fn => events.startup = fn },
            onMessage: { addListener: fn => messageListener = fn },
        },
        storage: { local: { async get() { return { ...state }; } }, onChanged: { addListener: fn => storageListener = fn } },
        declarativeNetRequest: { async updateDynamicRules({ removeRuleIds, addRules }) {
            for (const id of removeRuleIds) rules.delete(id);for (const rule of addRules) rules.set(rule.id, rule);
        } },
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
    const context = vm.createContext({ chrome, URL, console });
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/optimization.js"), "utf8"), context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/background.js"), "utf8"), context);
    await new Promise(setImmediate);
    assert.equal(rules.size, 2);assert.equal(registered.size, 1);
    const rule = [...rules.values()].find(rule => rule.action.type === 'redirect'), script = [...registered.values()][0];
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
    assert.equal(native.url, "https://www.youtube.com/");assert.equal(rules.size, 0);assert.equal(registered.size, 0);
    state.enabled = true;storageListener({ enabled: { newValue: true } }, "local");
    await new Promise(setImmediate);assert.equal(rules.size, 2);assert.equal(registered.size, 1);
    await Promise.all([context.MinimalYouTubeOptimization.configure(false), context.MinimalYouTubeOptimization.configure(true), context.MinimalYouTubeOptimization.configure(false)]);
    assert.equal(rules.size, 0);assert.equal(registered.size, 0);
    state.enabled = true;events.startup();await new Promise(setImmediate);
    assert.equal(rules.size, 2);assert.equal(registered.size, 1);
    console.log("PASS homepage redirect, live/replay chat network blocking with Music/player exceptions, persistent MAIN script, disabled/racing settings and exact sender/cookie-profile scope");
}
main().catch(error => { console.error(error); process.exitCode = 1; });
