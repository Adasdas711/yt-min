"use strict";
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({URL});vm.runInContext(fs.readFileSync('src/content/search-data.js','utf8'),context);
const model=context.MinimalYouTubeSearchData,plain=value=>JSON.parse(JSON.stringify(value));
const channel={channelId:'UCX6OQ3DkcsbYNE6H8uQQuVA',title:{simpleText:'MrBeast'},navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@MrBeast'}},avatar:{decoratedAvatarViewModel:{avatar:{avatarViewModel:{image:{sources:[{url:'https://yt3.googleusercontent.com/small',width:88},{url:'https://yt3.googleusercontent.com/large',width:176}]}}}}},descriptionSnippet:{simpleText:'Never copy this'},trackingParams:'Never copy this either'};
const result=plain(model.record(channel,'channel'));
assert.equal(result.image,'https://yt3.googleusercontent.com/large');assert.equal(result.href,'https://www.youtube.com/@MrBeast');assert.equal(result.title,'MrBeast');assert(!JSON.stringify(result).includes('Never copy'));
const modern={lockupViewModel:{contentId:'abcdefghijk',contentType:'LOCKUP_CONTENT_TYPE_VIDEO',contentImage:{thumbnailViewModel:{image:{sources:[{url:'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',width:480}]}}},metadata:{lockupMetadataViewModel:{title:{content:'Пользовательский заголовок'},metadata:{contentMetadataViewModel:{metadataRows:[{metadataParts:[{text:{content:'User channel',commandRuns:[{onTap:{innertubeCommand:{browseEndpoint:{canonicalBaseUrl:'/@creator'}}}}]}}]}]}}}}}};
const video=plain(model.record(modern));assert.equal(video.title,'Пользовательский заголовок');assert.equal(video.kind,'video');assert.equal(video.href,'https://www.youtube.com/watch?v=abcdefghijk');assert.deepEqual(video.channel,{name:'User channel',href:'https://www.youtube.com/@creator'});
const snapshot=model.collect({contents:[{channelRenderer:channel},modern,{searchFilterRenderer:{label:{simpleText:'Плейлист'},navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=x&sp=EgIQAw%3D%3D'}}}}}]});
assert(snapshot.records.some(item=>item.kind==='channel'));assert.equal(snapshot.filters[0].label,'Плейлист');assert(snapshot.filters[0].href.includes('sp='));
assert.equal(model.youtube('https://example.com/watch?v=x'),'');assert.equal(model.url('javascript:alert(1)'),'');assert.equal(model.channelURL('/watch?v=abcdefghijk'),'');
for(const [value,count]of [[{videoCount:0},'0'],[{videoCount:1},'1'],[{videoCountText:{runs:[{text:'1 234 видео'}]}},'1 234'],[{videoCountShortText:{simpleText:'50+ videos'}},'50+'],[{contentImage:{collectionThumbnailViewModel:{primaryThumbnail:{thumbnailViewModel:{overlays:[{thumbnailBottomOverlayViewModel:{badges:[{thumbnailBadgeViewModel:{text:'128 videos'}}]}}]}}}}},'128']]){
    const item=model.record({lockupViewModel:{contentId:'PLcounts',contentType:'LOCKUP_CONTENT_TYPE_PLAYLIST',...value}});
    assert.equal(item.count,count);
}
const notACount={metadata:{lockupMetadataViewModel:{
    title:{content:'200 videos I like'},
    metadata:{contentMetadataViewModel:{metadataRows:[{metadataParts:[{text:{content:'3,000 views'}}]}]}},
}}};
assert.equal(model.playlistCount(notACount),'');
const modernChannel=plain(model.record({lockupViewModel:{contentId:'UCmodern',contentType:'LOCKUP_CONTENT_TYPE_CHANNEL',metadata:{lockupMetadataViewModel:{title:{content:'Joe Speen'},metadata:{contentMetadataViewModel:{metadataRows:[{metadataParts:[{text:{content:'@JoeSpeen'}},{text:{content:'2.24M subscribers'}}]}]}}}}}}));
assert(modernChannel.metadata.includes('2.24M subscribers'));assert.equal(modernChannel.handle,'@JoeSpeen');
// Courses are playlists with their own lockup type and a lesson count.
const course=plain(model.record({lockupViewModel:{contentId:'PLcourse01',contentType:'LOCKUP_CONTENT_TYPE_COURSE',contentImage:{collectionThumbnailViewModel:{primaryThumbnail:{thumbnailViewModel:{overlays:[{thumbnailOverlayBadgeViewModel:{thumbnailBadges:[{thumbnailBadgeViewModel:{text:'33 lessons',icon:{sources:[{clientResource:{imageName:'SCHOOL'}}]}}}]}}]}}}},metadata:{lockupMetadataViewModel:{title:{content:'Немецкий язык A2'}}}}}));
assert.equal(course.kind,'playlist');assert.equal(course.count,'33');assert.equal(course.course,true);assert.equal(course.href,'https://www.youtube.com/playlist?list=PLcourse01');
const lessons=plain(model.record({lockupViewModel:{contentId:'PLcourse02',contentType:'LOCKUP_CONTENT_TYPE_PLAYLIST',contentImage:{collectionThumbnailViewModel:{primaryThumbnail:{thumbnailViewModel:{overlays:[{thumbnailBadgeViewModel:{text:'94 урока'}}]}}}}}}));
assert.equal(lessons.count,'94');assert.equal(lessons.course,true);
assert.equal(plain(model.record({lockupViewModel:{contentId:'PLplain',contentType:'LOCKUP_CONTENT_TYPE_PLAYLIST',videoCountText:{simpleText:'19 videos'}}})).course,undefined);
console.log('PASS legacy and modern public search records, nested avatars, channel endpoints, native filters and unchanged user text');
