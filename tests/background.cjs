"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function main() {
    let listener;
    let denied = false;
    let oldAPI = false;
    let reads = 0;
    let cookies = [
        { name: "PREF", domain: ".youtube.com", path: "/", value: "private-pref", storeId: "profile", session: true },
        { name: "AUTH", domain: "www.youtube.com", path: "/", value: "private-auth", storeId: "profile", httpOnly: true },
        { name: "PARTITIONED", domain: "m.youtube.com", path: "/", value: "private-partition", storeId: "profile", partitionKey: { topLevelSite: "https://youtube.com" } },
        { name: "OTHER_PROFILE", domain: ".youtube.com", path: "/", value: "private-other", storeId: "other" },
        { name: "GOOGLE", domain: ".google.com", path: "/", value: "private-google", storeId: "profile" },
        { name: "LOOKALIKE", domain: "youtube.com.example", path: "/", value: "private-lookalike", storeId: "profile" },
    ];
    const removals = [];
    const context = {
        URL,
        chrome: {
            runtime: { id: "extension-id", onMessage: { addListener(fn) { listener = fn; } } },
            cookies: {
                async getAllCookieStores() { return [{ id: "profile", tabIds: [7] }, { id: "other", tabIds: [9] }]; },
                async getAll(filter) {
                    reads++;
                    if (denied) throw new Error("Permission denied with internal diagnostic");
                    if (filter.partitionKey && oldAPI) throw new Error("Unexpected property: partitionKey");
                    assert.equal(filter.domain, "youtube.com");
                    assert.equal(filter.storeId, "profile");
                    // Include unrelated domains deliberately: the worker must filter them.
                    return cookies.filter(cookie => cookie.storeId === filter.storeId && (filter.partitionKey ? Boolean(cookie.partitionKey) : !cookie.partitionKey));
                },
                async remove(details) {
                    removals.push(details);
                    assert.equal(new URL(details.url).protocol, "https:");
                    const domain = new URL(details.url).hostname;
                    assert(domain === "youtube.com" || domain.endsWith(".youtube.com"));
                    assert.equal(details.storeId, "profile");
                    const index = cookies.findIndex(cookie => cookie.name === details.name && cookie.storeId === details.storeId);
                    assert(index >= 0);
                    if (cookies[index].partitionKey) assert.deepEqual(details.partitionKey, cookies[index].partitionKey);
                    cookies.splice(index, 1);
                    return { name: details.name };
                },
            },
        },
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../src/background.js"), "utf8"), context);
    const sender = { id: "extension-id", url: "https://www.youtube.com/", tab: { id: 7 } };
    const request = action => new Promise(resolve => {
        assert.equal(listener({ action }, sender, resolve), true);
    });
    for (const untrusted of [
        { ...sender, id: "another-extension" },
        { ...sender, url: "https://youtube.com.example/" },
        { ...sender, url: "http://www.youtube.com/" },
        { ...sender, url: "https://example.com/" },
    ]) assert.equal(listener({ action: "minimal-youtube:clear-cookies" }, untrusted, () => assert.fail("Unexpected response")), false);
    assert.equal(listener({ action: "unknown" }, sender, () => assert.fail("Unexpected response")), false);
    assert.equal(reads, 0);
    const result = await request("minimal-youtube:get-cookies");
    assert.equal(result.ok, true);
    assert.equal(result.cookies.length, 3);
    assert(result.cookies.every(cookie => !("value" in cookie)));
    assert(!JSON.stringify(result).includes("private-"));
    assert.equal(removals.length, 0);
    oldAPI = true;
    const legacy = await request("minimal-youtube:get-cookies");
    assert.equal(legacy.ok, true);
    assert.equal(legacy.cookies.length, 2);
    oldAPI = false;
    const cleared = await request("minimal-youtube:clear-cookies");
    assert.equal(cleared.ok, true);
    assert.equal(cleared.removed, 3);
    assert.equal(cleared.cookies.length, 0);
    assert.equal(cookies.length, 3, "Other profile and non-YouTube cookies must remain");
    denied = true;
    const failure = await request("minimal-youtube:get-cookies");
    assert.equal(failure.ok, false);
    assert.equal(failure.error, "cookies-unavailable");
    const noStore = await new Promise(resolve => listener({ action: "minimal-youtube:clear-cookies" }, { ...sender, tab: { id: 100 } }, resolve));
    assert.equal(noStore.ok, false);
    assert.equal(removals.length, 3);
    console.log("PASS cookie metadata privacy, YouTube/profile scope, partitioned deletion, sender validation and permission errors");
}

main().catch(error => { console.error(error); process.exitCode = 1; });
