"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

async function main() {
    const handlers = new Map(), attributes = new Map(), resizes = [];
    let playerAPI = { setSize: (...size) => resizes.push(size) };
    class Response { constructor(data) { this.data = data; } async json() { return this.data; } }
    const context = vm.createContext({
        Response, location: { pathname: "/watch" },
        document: {
            documentElement: { hasAttribute: name => attributes.has(name), setAttribute: (name, value) => attributes.set(name, value),removeAttribute:name=>attributes.delete(name) },
            addEventListener: (name, handler) => handlers.set(name, handler),
            querySelector: () => playerAPI,
        },
    });
    context.window = context;
    const originalParse = vm.runInContext("JSON.parse", context), originalResponseJSON = Response.prototype.json;
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/content/data-pruning.js"), "utf8"), context);
    const resize = (detail,target) => handlers.get('minimal-youtube:player-resize')({ detail,target });
    resize({ width: 1920.4, height: 1080.1 });assert.deepEqual(resizes.pop(), [1920, 1080]);
    playerAPI = { closest: () => ({ getApiInterface: () => ({ setSize: (...size) => resizes.push(size) }) }) };
    resize({ width: 390, height: 600 });assert.deepEqual(resizes.pop(), [390, 600]);
    resize({width:1280,height:720},{matches:()=>true,querySelector:()=>({setSize:(...size)=>resizes.push(size)})});assert.deepEqual(resizes.pop(),[1280,720]);
    for (const detail of [{width:0,height:100},{width:1e9,height:100},{width:NaN,height:100},{width:'1920',height:1080},{width:100,height:Infinity}]) resize(detail);
    assert.equal(resizes.length,0);
    playerAPI = { setSize: () => { throw new Error('Native API variant'); } };
    assert.doesNotThrow(() => resize({width:1920,height:1080}));
    playerAPI = { setSize: (...size) => resizes.push(size) };
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

    context.location.pathname='/results';
    const cards=parse({contents:{twoColumnSearchResultsRenderer:{contents:[
        {playlistRenderer:{playlistId:'PLlegacy',videoCount:'256',thumbnails:[{url:'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',width:480}],privateTracking:'never-copy'}},
        {lockupViewModel:{
            contentId:'PLmodern',contentType:'LOCKUP_CONTENT_TYPE_PLAYLIST',
            contentImage:{collectionThumbnailViewModel:{primaryThumbnail:{thumbnailViewModel:{
                image:{sources:[{url:'https://i.ytimg.com/vi/12345678901/mqdefault.jpg',width:320},{url:'https://i.ytimg.com/vi/12345678901/hqdefault.jpg',width:480}]},
                overlays:[{thumbnailBottomOverlayViewModel:{badges:[{thumbnailBadgeViewModel:{text:'64 videos'}}]}}],
            }}}},
            metadata:{lockupMetadataViewModel:{title:{content:'Do not copy title'},metadata:{contentMetadataViewModel:{metadataRows:[]}}}},
        }},
    ]}}});
    const summaries=JSON.parse(attributes.get('data-myt-search-playlists')).sort((a,b)=>a.id.localeCompare(b.id));
    assert.deepEqual(summaries,[{id:'PLlegacy',image:'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',count:'256'},{id:'PLmodern',image:'https://i.ytimg.com/vi/12345678901/hqdefault.jpg',count:'64'}]);
    assert.equal(cards.contents.twoColumnSearchResultsRenderer.contents[0].playlistRenderer.privateTracking,'never-copy');
    await new Response({onResponseReceivedActions:[{appendContinuationItemsAction:{continuationItems:[{playlistRenderer:{playlistId:'PLlegacy',videoCount:'257'}}]}}]}).json();
    assert.equal(JSON.parse(attributes.get('data-myt-search-playlists')).find(item=>item.id==='PLlegacy').count,'257');
    parse({contents:{twoColumnSearchResultsRenderer:{contents:Array.from({length:205},(_,i)=>({playlistRenderer:{playlistId:'PLlimit'+i,videoCount:String(i)}}))}}});
    assert.equal(JSON.parse(attributes.get('data-myt-search-playlists')).length,200);
    context.location.pathname='/watch';

    const headed = parse({contents:{twoColumnSearchResultsRenderer:{contents:[
        {sectionHeaderRenderer:{title:{simpleText:'Shorts'}}},
        {sectionHeaderViewModel:{title:{content:'Shorts'}}},
        {sectionHeaderRenderer:{title:{runs:[{text:'Videos'}]}}},
        {videoRenderer:{videoId:'keep-title',title:{simpleText:'Shorts'}}},
    ]}}});
    const headedItems=headed.contents.twoColumnSearchResultsRenderer.contents;
    assert.equal(headedItems.length,2);
    assert.equal(headedItems[0].sectionHeaderRenderer.title.runs[0].text,'Videos');
    assert.equal(headedItems[1].videoRenderer.videoId,'keep-title');
    const latest=parse({contents:{twoColumnSearchResultsRenderer:{contents:[
        {shelfRenderer:{title:{simpleText:'Latest Shorts from MrBeast'},content:{horizontalListRenderer:{items:[{videoRenderer:{videoId:'vertical-with-watch-endpoint'}}]}}}},
        {sectionHeaderRenderer:{title:{simpleText:'Latest Shorts from Creator'}}},
        {shortsLockupViewModelV3:{entityId:'new-version'}},
        {lockupViewModel:{contentId:'short',rendererContext:{commandContext:{onTap:{innertubeCommand:{reelWatchEndpoint:{videoId:'short'}}}}}}},
        {videoRenderer:{videoId:'keep-long',title:{simpleText:'Latest Shorts from my channel explained'}}},
    ]}}});
    assert.equal(latest.contents.twoColumnSearchResultsRenderer.contents.length,1);
    assert.equal(latest.contents.twoColumnSearchResultsRenderer.contents[0].videoRenderer.videoId,'keep-long');

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
    const adPlayer = {
        playabilityStatus: { status: 'OK' }, videoDetails: { videoId: 'native-ad-free' },
        streamingData: { adaptiveFormats: [{ url: 'https://rr1.googlevideo.com/videoplayback?sig=private', signatureCipher: 'unchanged' }], serverAbrStreamingUrl: 'https://rr1.googlevideo.com/sabr?token=keep' },
        responseContext: { visitorData: 'keep' }, captions: { tracks: ['keep'] },
        playerAds: [{ id: 'drop-client-ad' }], adPlacements: [{ slot: 'drop-pre-roll' }], adSlots: [{ slot: 'drop-mid-roll' }],
    };
    const stream = adPlayer.streamingData;
    context.ytInitialPlayerResponse = adPlayer;
    assert.equal(context.ytInitialPlayerResponse, adPlayer);
    assert.equal(adPlayer.streamingData, stream);
    assert.equal(adPlayer.responseContext.visitorData, 'keep');
    for (const key of ['playerAds', 'adPlacements', 'adSlots']) assert(!(key in adPlayer), key);
    for (const response of [parse({ ...adPlayer, playerAds: [1], adPlacements: [2], adSlots: [3] }), await new Response({ ...adPlayer, playerAds: [1], adPlacements: [2] }).json()]) {
        assert(!response.playerAds && !response.adPlacements && !response.adSlots);
        assert.deepEqual(JSON.parse(JSON.stringify(response.streamingData)), stream);
        assert.equal(response.playabilityStatus.status, 'OK');
    }
    const prefetched = parse({ playerResponse: { ...adPlayer, adSlots: [1] } });
    assert(!prefetched.playerResponse.adSlots);
    const adOnly = parse({ responseContext: { visitorData: 'keep' }, adSlots: [1], adPlacements: [2], tracking: 'keep' });
    assert(!adOnly.adSlots && !adOnly.adPlacements);assert.equal(adOnly.responseContext.visitorData, 'keep');assert.equal(adOnly.tracking, 'keep');
    const lookalike = { adPlacements: ['keep-unrelated-json'], value: 'not player data' };
    assert.deepEqual(JSON.parse(JSON.stringify(parse(lookalike))), lookalike);
    // A reviver is allowed to freeze a value; ad filtering must not break parsing.
    context.frozenText = JSON.stringify({ ...adPlayer, playerAds: [1] });
    assert.doesNotThrow(() => vm.runInContext('JSON.parse(frozenText, (key,value)=>key===""?Object.freeze(value):value)', context));
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
    resize({width:1920,height:1080});assert.equal(resizes.length,0,'Disabled mode must not resize native controls');
    assert.equal(vm.runInContext("JSON.parse", context), originalParse);
    assert.equal(Response.prototype.json, originalResponseJSON);
    const playerDescriptor = Object.getOwnPropertyDescriptor(context, 'ytInitialPlayerResponse');
    assert.equal(playerDescriptor.get, undefined);assert.equal(playerDescriptor.value, adPlayer);
    context.ytInitialPlayerResponse = { ...adPlayer, playerAds: [1] };
    assert.deepEqual(context.ytInitialPlayerResponse.playerAds, [1]);
    const native = parse({ contents: { twoColumnSearchResultsRenderer: { contents: [{ reelShelfRenderer: {} }] } } });
    assert.equal(native.contents.twoColumnSearchResultsRenderer.contents.length, 1);
    const nativeChat = parse({ contents: { twoColumnWatchNextResults: { conversationBar: chat } } });
    assert.deepEqual(JSON.parse(JSON.stringify(nativeChat.contents.twoColumnWatchNextResults.conversationBar)), chat);
    context.ytInitialData = native;
    command(true);
    assert(!context.ytInitialPlayerResponse.playerAds);
    assert.equal(native.contents.twoColumnSearchResultsRenderer.contents.length, 0);
    command(false);
    console.log("PASS initial/fetch/parse feed pruning and live/replay chat removal; explicit player ad placements stripped; native streams/playability/captions, playlist, comments, transcript and disabled parsers/globals preserved");
}
main().catch(error => { console.error(error); process.exitCode = 1; });
