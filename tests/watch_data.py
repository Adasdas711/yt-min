"""Watch page from YouTube's page data: text, links, chapters, stats, votes and the playlist panel."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, watch_details_fixture

RESPONSE = """
const run=(text,url)=>url?{text,navigationEndpoint:{commandMetadata:{webCommandMetadata:{url}}}}:{text};
const panel=(id,title,index,selected)=>({playlistPanelVideoRenderer:{videoId:id,title:{simpleText:title},shortBylineText:{runs:[run('Panel creator')]},
  lengthText:{simpleText:'4:0'+index},indexText:{simpleText:String(index)},selected,thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/mqdefault.jpg',width:320}]},
  navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id+'&list=PLwatch&index='+index}},watchEndpoint:{videoId:id,playlistId:'PLwatch',index:index-1}}}});
const description='Intro at 1:05 and more at example.com plus #music';
document.querySelector('ytd-watch-flexy').data={
  currentVideoEndpoint:{watchEndpoint:{videoId:'details'}},
  contents:{twoColumnWatchNextResults:{
    results:{results:{contents:[
      {videoPrimaryInfoRenderer:{title:{runs:[{text:'Data title from the page'}]},viewCount:{videoViewCountRenderer:{viewCount:{simpleText:'1,234,567 views'}}},dateText:{simpleText:'Mar 5, 2024'}}},
      {videoSecondaryInfoRenderer:{owner:{videoOwnerRenderer:{title:{runs:[run('Data Owner','/@dataowner')]},thumbnail:{thumbnails:[{url:'https://yt3.ggpht.com/owner=s88',width:88}]}}},
        attributedDescription:{content:description,commandRuns:[
          {startIndex:9,length:4,onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'/watch?v=details&t=65s'}},watchEndpoint:{videoId:'details',startTimeSeconds:65}}}},
          {startIndex:26,length:11,onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'https://www.youtube.com/redirect?event=video_description&q=https%3A%2F%2Fexample.com%2F'}},urlEndpoint:{url:'https://www.youtube.com/redirect?event=video_description&q=https%3A%2F%2Fexample.com%2F'}}}},
          {startIndex:43,length:6,onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'/hashtag/music'}},browseEndpoint:{browseId:'FEhashtag'}}}}]}}}]}},
    playlist:{playlist:{title:{simpleText:'Watch playlist'},playlistId:'PLwatch',ownerName:{simpleText:'Playlist owner'},totalVideos:3,localCurrentIndex:1,
      contents:[panel('aaaaaaaaaaa','First in list',1,false),panel('details','Data title from the page',2,true),panel('ccccccccccc','Third in list',3,false)]}}}},
  engagementPanels:[{engagementPanelSectionListRenderer:{content:{macroMarkersListRenderer:{contents:[
    {macroMarkersListItemRenderer:{title:{simpleText:'Opening'},timeDescription:{simpleText:'0:00'},onTap:{watchEndpoint:{videoId:'details',startTimeSeconds:0}}}},
    {macroMarkersListItemRenderer:{title:{simpleText:'Data chapter'},timeDescription:{simpleText:'1:05'},onTap:{watchEndpoint:{videoId:'details',startTimeSeconds:65}}}}]}}}}]};
document.dispatchEvent(new Event('yt-page-data-updated'));
document.querySelector('ytd-watch-metadata,ytd-video-secondary-info-renderer').setAttribute('data-refresh','1');
"""


def check(browser, width):
    page = setup(browser, '/watch?v=details&list=PLwatch', watch_details_fixture(), width=width)
    expect(page.locator('#myt-watch')).to_be_visible()
    page.evaluate(RESPONSE)
    root = page.locator('#myt-watch')
    # Text comes from the page data, not the native DOM.
    expect(root.locator('#watch-title')).to_have_text('Data title from the page')
    expect(root.locator('.stats')).to_contain_text('5 March 2024')
    # Without a native owner, the page data names the channel.
    expect(root.locator('.owner .owner-name')).to_have_text('Data Owner')
    expect(root.locator('.owner .owner-name')).to_have_attribute('href', 'https://www.youtube.com/@dataowner')
    # Description links: a timestamp seeks the player, an external link opens
    # its target directly, a hashtag routes as usual.
    prose = root.locator('.prose')
    expect(prose).to_contain_text('Intro at 1:05 and more at example.com plus #music')
    expect(prose.locator('a[data-seconds="65"]')).to_have_text('1:05')
    external = prose.get_by_role('link', name='example.com')
    expect(external).to_have_attribute('href', 'https://example.com/')
    expect(external).to_have_attribute('target', '_blank')
    expect(prose.get_by_role('link', name='#music')).to_have_attribute('href', 'https://www.youtube.com/hashtag/music')
    prose.locator('a[data-seconds="65"]').click()
    assert page.evaluate("document.querySelector('video').currentTime") == 65
    # Chapters from the page data seek too.
    chapters = root.locator('.chapter')
    expect(chapters.locator('.chapter-title')).to_have_text(['Opening', 'Data chapter'])
    chapters.first.click()
    assert page.evaluate("document.querySelector('video').currentTime") == 0
    # Votes: owned buttons mirror YouTube's like state and count and press them.
    page.evaluate('''()=>{const meta=document.querySelector('ytd-watch-metadata');meta.insertAdjacentHTML('beforeend','<div id="actions"><div id="top-level-buttons-computed"><segmented-like-dislike-button-view-model><like-button-view-model><button aria-pressed="true" aria-label="like this video along with 12,345 other people" onclick="window.__like=(window.__like||0)+1;this.setAttribute(\\'aria-pressed\\',String(this.getAttribute(\\'aria-pressed\\')!==\\'true\\'))">12K</button></like-button-view-model><dislike-button-view-model><button aria-pressed="false" aria-label="Dislike this video" onclick="window.__dislike=true">Dislike</button></dislike-button-view-model></segmented-like-dislike-button-view-model><button aria-label="Save to playlist" onclick="window.__save=true">Save</button></div></div>');}''')
    like = root.get_by_role('button', name='Like', exact=True)
    expect(like).to_have_attribute('aria-pressed', 'true')
    expect(like).to_have_text('12K')
    like.click()
    assert page.evaluate('window.__like') == 1
    expect(like).to_have_attribute('aria-pressed', 'false')
    root.get_by_role('button', name='Dislike', exact=True).click()
    assert page.evaluate('window.__dislike') is True
    root.locator('.actions').get_by_role('button', name='Save', exact=True).click()
    assert page.evaluate('window.__save') is True
    # The owned playlist panel: rows from data, the current video marked.
    panel = root.locator('.own-playlist')
    expect(panel.locator('.own-playlist-title')).to_have_text('Watch playlist')
    expect(panel.locator('.own-playlist-meta')).to_have_text('Playlist owner · 2 / 3')
    expect(panel.locator('.own-playlist-name')).to_have_text(['First in list', 'Data title from the page', 'Third in list'])
    expect(panel.locator('[aria-current="true"] .own-playlist-name')).to_have_text('Data title from the page')
    expect(panel.locator('.own-playlist-link').nth(2)).to_have_attribute('href', 'https://www.youtube.com/watch?v=ccccccccccc&list=PLwatch&index=3')
    assert page.evaluate("!document.querySelector('[data-myt-watch-island=\"sidecar\"]')")
    # Closing hides the panel and offers the playlist button; it reopens.
    panel.locator('.own-playlist-close').click()
    expect(root.locator('.sidecar')).to_be_hidden()
    toggle = root.locator('.playlist-toggle')
    expect(toggle).to_be_visible()
    toggle.click()
    expect(root.locator('.sidecar')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.close()
    print(f'PASS watch page text, links, chapters, stats and playlist panel from page data: {width}px', flush=True)


def other_video(browser):
    # Data for a different video (a page in transition) is never used.
    page = setup(browser, '/watch?v=details', watch_details_fixture())
    page.evaluate(RESPONSE.replace("currentVideoEndpoint:{watchEndpoint:{videoId:'details'}}", "currentVideoEndpoint:{watchEndpoint:{videoId:'otherVideo1'}}"))
    expect(page.locator('#myt-watch #watch-title')).to_have_text('Music, life and the stories behind it')
    expect(page.locator('#myt-watch .own-playlist')).to_have_count(0)
    page.close()
    print('PASS watch data for another video is ignored', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in (1440, 390):
            check(browser, width)
        other_video(browser)
        browser.close()
