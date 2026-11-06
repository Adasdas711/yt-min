"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function main() {
    const handlers = new Map(), attributes = new Map();
    class Response { constructor(data) { this.data = data; } async json() { return this.data; } }
    const context = vm.createContext({
        Response, location: { pathname: "/watch" },
        document: {
            documentElement: { hasAttribute: name => attributes.has(name), setAttribute: (name, value) => attributes.set(name, value) },
            addEventListener: (name, handler) => handlers.set(name, handler),
        },
    });
    context.window = context;
    const originalParse = vm.runInContext("JSON.parse", context), originalResponseJSON = Response.prototype.json;
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/content/data-pruning.js"), "utf8"), context);
    const parse = data => vm.runInContext("JSON.parse", context)(JSON.stringify(data));
    const command = enabled => handlers.get("minimal-youtube:optimization")({ detail: { enabled } });
    const secondary = data => data.contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results;
    const playlist = { playlistPanelRenderer: { contents: [{ playlistPanelVideoRenderer: { videoId: "keep-playlist" } }] } };
    const chat = { liveChatRenderer: { continuations: [{ token: "drop-chat" }] } };
    const primary = { videoPrimaryInfoRenderer: { title: { runs: [{ text: "Keep title" }] } } };
    const watch = { contents: { twoColumnWatchNextResults: {
        results: { results: { contents: [primary] } },
        playlist: { playlist: { playlistId: "keep-active-playlist" } },
        conversationBar: { liveChatRenderer: { continuations: [{ token: 'drop-primary-chat' }] } },
        secondaryResults: { secondaryResults: { results: [
            { compactVideoRenderer: { videoId: "drop-related", cache: new Array(100).fill(1) } },
            { lockupViewModel: { contentId: "drop-related-modern" } }, playlist, chat,
            { continuationItemRenderer: { continuationEndpoint: { token: "drop-related-continuation" } } },
        ] } },
    } }, engagementPanels: [{ transcript: "Keep transcript" }] };
    context.ytInitialData = watch;
    assert.equal(context.ytInitialData, watch, "Pruning must not clone/retain another response");
    assert.deepEqual(secondary(watch), [playlist]);
    assert.equal(watch.contents.twoColumnWatchNextResults.conversationBar, undefined);
    assert.equal(watch.contents.twoColumnWatchNextResults.results.results.contents[0], primary);
    assert.equal(watch.contents.twoColumnWatchNextResults.playlist.playlist.playlistId, "keep-active-playlist");
    assert.equal(watch.engagementPanels[0].transcript, "Keep transcript");
    assert(attributes.has("data-myt-pruned"));

    for (const key of ['liveChatRenderer', 'liveChatReplayRenderer', 'liveChatViewModel']) {
        const replay = parse({ contents: { twoColumnWatchNextResults: {
            conversationBar: { [key]: { continuations: [{ token: 'drop-chat' }] } },
        } }, engagementPanels: [
            { engagementPanelSectionListRenderer: { targetId: 'engagement-panel-live-chat', content: { [key]: {} } } },
            { engagementPanelSectionListRenderer: { targetId: 'engagement-panel-comments', content: { text: 'Keep comments' } } },
            { engagementPanelSectionListRenderer: { targetId: 'engagement-panel-searchable-transcript', content: { text: 'Keep transcript' } } },
        ] });
        assert.equal(replay.contents.twoColumnWatchNextResults.conversationBar, undefined);
        assert.equal(replay.engagementPanels.length, 2);
        assert.equal(replay.engagementPanels[0].engagementPanelSectionListRenderer.content.text, 'Keep comments');
        assert.equal(replay.engagementPanels[1].engagementPanelSectionListRenderer.content.text, 'Keep transcript');
    }
    const chatResponse = await new Response({ continuationContents: { liveChatContinuation: { actions: [{ addChatItemAction: { text: 'Discard message' } }] } } }).json();
    assert.equal(chatResponse.continuationContents.liveChatContinuation, undefined);

    const nested = parse({contents:{twoColumnWatchNextResults:{secondaryResults:{secondaryResults:{results:[
        {itemSectionRenderer:{targetId:"watch-next-feed",contents:[{compactVideoRenderer:{videoId:"nested-drop"}}],continuations:[{nextContinuationData:{token:"drop-paging"}}]}},
        {playlistPanelRenderer:{contents:[{playlistPanelVideoRenderer:{videoId:"keep-active"}},{continuationItemRenderer:{token:"keep-playlist-paging"}}]}},
        {itemSectionRenderer:{targetId:"comments-section",contents:[{commentThreadRenderer:{text:"keep"}}]}},
    ]}}}}});
    assert.equal(secondary(nested)[0].itemSectionRenderer.contents.length,0);
    assert.equal(secondary(nested)[0].itemSectionRenderer.continuations,undefined);
    assert.equal(secondary(nested)[1].playlistPanelRenderer.contents.length,2);
    assert.equal(secondary(nested)[2].itemSectionRenderer.contents[0].commentThreadRenderer.text,"keep");

    const video = { videoRenderer: { videoId: "keep", navigationEndpoint: { watchEndpoint: { videoId: "keep" } }, thumbnail: { url: "keep-static.jpg" }, inlinePlaybackEndpoint: { watchEndpoint: { videoId: "preview" } }, richThumbnail: { movingThumbnailRenderer: { thumbnail: "drop-animated.webp" } } } };
    const search = parse({ contents: { twoColumnSearchResultsRenderer: { contents: [
        video, { reelShelfRenderer: { items: [{ reelItemRenderer: { videoId: "drop" } }] } },
        { richItemRenderer: { content: { shortsLockupViewModel: { entityId: "drop-short" } } } },
        { videoRenderer: { navigationEndpoint: { commandMetadata: { webCommandMetadata: { url: "/shorts/drop" } } } } },
        { richSectionRenderer: { content: { richShelfRenderer: { isShorts: true } } } },
        { playlistRenderer: { playlistId: "keep-search-playlist" } },
    ] } } });
    const items = search.contents.twoColumnSearchResultsRenderer.contents;
    assert.equal(items.length, 2);
    assert.equal(items[0].videoRenderer.navigationEndpoint.watchEndpoint.videoId, "keep");
    assert.equal(items[0].videoRenderer.thumbnail.url, "keep-static.jpg");
    assert(!("inlinePlaybackEndpoint" in items[0].videoRenderer));
    assert(!("richThumbnail" in items[0].videoRenderer));
    assert.equal(items[1].playlistRenderer.playlistId, "keep-search-playlist");

    const next = await new Response({ onResponseReceivedActions: [
        { appendContinuationItemsAction: { targetId: "watch-next-feed", continuationItems: [{ compactVideoRenderer: {} }] } },
        { appendContinuationItemsAction: { targetId: "comments-section", continuationItems: [{ commentThreadRenderer: { text: "Keep comment" } }] } },
        { reloadContinuationItemsCommand: { targetId: "playlist", continuationItems: [{ playlistPanelVideoRenderer: { videoId: "keep" } }] } },
    ] }).json();
    assert.equal(next.onResponseReceivedActions[0].appendContinuationItemsAction.continuationItems.length, 0);
    assert.equal(next.onResponseReceivedActions[1].appendContinuationItemsAction.continuationItems[0].commentThreadRenderer.text, "Keep comment");
    assert.equal(next.onResponseReceivedActions[2].reloadContinuationItemsCommand.continuationItems[0].playlistPanelVideoRenderer.videoId, "keep");
    const player = { streamingData: { adaptiveFormats: [{ url: "https://media.example/video" }] }, playabilityStatus: { status: "OK" }, videoDetails: { videoId: "native" }, contents: { twoColumnSearchResultsRenderer: { contents: [{ reelShelfRenderer: {} }] } } };
    assert.deepEqual(JSON.parse(JSON.stringify(parse(player))), player, "Player data is outside the pruning scope");
    const unrelated = { inlinePlaybackEndpoint: { value: 1 }, text: "Unrelated JSON" };
    assert.deepEqual(JSON.parse(JSON.stringify(parse(unrelated))), unrelated);
    assert.throws(() => vm.runInContext('JSON.parse("not json")', context));
    assert.equal(vm.runInContext('JSON.parse("{\\"value\\":1}", (key,value)=>key==="value"?2:value).value', context), 2);

    context.location.pathname = "/@creator";
    const shelves = parse({ contents: { twoColumnBrowseResultsRenderer: { contents: [
        { shelfRenderer: { title: { simpleText: "New Uploads" }, content: { largeCache: [1] } } },
        { shelfRenderer: { title: { simpleText: "For you" } } },
        { shelfRenderer: { title: { runs: [{ text: "Популярные видео" }] } } },
    ] } } });
    assert.equal(shelves.contents.twoColumnBrowseResultsRenderer.contents.length, 2);
    context.location.pathname = "/results";
    assert.equal(parse({ contents: { twoColumnSearchResultsRenderer: { contents: [
        { shelfRenderer: { title: { simpleText: "Latest from creator" } } },
    ] } } }).contents.twoColumnSearchResultsRenderer.contents.length, 0);

    command(false);
    assert.equal(vm.runInContext("JSON.parse", context), originalParse);
    assert.equal(Response.prototype.json, originalResponseJSON);
    const native = parse({ contents: { twoColumnSearchResultsRenderer: { contents: [{ reelShelfRenderer: {} }] } } });
    assert.equal(native.contents.twoColumnSearchResultsRenderer.contents.length, 1);
    const nativeChat = parse({ contents: { twoColumnWatchNextResults: { conversationBar: chat } } });
    assert.deepEqual(JSON.parse(JSON.stringify(nativeChat.contents.twoColumnWatchNextResults.conversationBar)), chat);
    context.ytInitialData = native;
    command(true);
    assert.equal(native.contents.twoColumnSearchResultsRenderer.contents.length, 0);
    command(false);
    console.log("PASS initial/fetch/parse feed pruning and live/replay chat removal; native player, playlist, comments, transcript, static thumbnails and disabled mode preserved");
}
main().catch(error => { console.error(error); process.exitCode = 1; });
