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
    # Votes are not offered: no like/dislike buttons or counts. Save presses YouTube's own.
    page.evaluate('''()=>{const meta=document.querySelector('ytd-watch-metadata');meta.insertAdjacentHTML('beforeend','<div id="actions"><div id="top-level-buttons-computed"><segmented-like-dislike-button-view-model><like-button-view-model><button aria-pressed="true" aria-label="like this video along with 12,345 other people">12K</button></like-button-view-model><dislike-button-view-model><button aria-pressed="false" aria-label="Dislike this video">Dislike</button></dislike-button-view-model></segmented-like-dislike-button-view-model><button aria-label="Save to playlist" onclick="window.__save=true">Save</button></div></div>');}''')
    save = root.locator('.actions').get_by_role('button', name='Save', exact=True)
    expect(save).to_be_visible()
    expect(root.get_by_role('button', name='Like', exact=True)).to_have_count(0)
    expect(root.get_by_role('button', name='Dislike', exact=True)).to_have_count(0)
    expect(root.locator('.actions')).not_to_contain_text('12K')
    assert page.locator('like-button-view-model button').evaluate('e=>!e.checkVisibility()')
    save.click()
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
    # The playlist title opens the playlist itself.
    title = panel.locator('.own-playlist-title a')
    expect(title).to_have_text('Watch playlist')
    expect(title).to_have_attribute('href', 'https://www.youtube.com/playlist?list=PLwatch')
    page.evaluate('''()=>navigation.addEventListener('navigate',event=>{if(new URL(event.destination.url).pathname==='/playlist'){event.preventDefault();window.__playlistOpened=event.destination.url;}})''')
    title.click()
    page.wait_for_function('window.__playlistOpened')
    assert page.evaluate('__playlistOpened') == 'https://www.youtube.com/playlist?list=PLwatch'
    page.close()
    print(f'PASS watch page text, links, chapters, stats and playlist panel from page data: {width}px', flush=True)



def theater_scroll(browser):
    """In theater mode the playlist sits beside the details; a long playlist
    keeps a bounded panel and scrolls inside it."""
    page = setup(browser, '/watch?v=details&list=PLwatch', watch_details_fixture(), width=1440)
    expect(page.locator('#myt-watch')).to_be_visible()
    long_list = "contents:[" + ",".join(f"panel('vid{n:08d}','Item {n}',{n},false)" for n in range(1, 60)) + ",panel('details','Data title from the page',60,true)]"
    response = RESPONSE.replace("contents:[panel('aaaaaaaaaaa','First in list',1,false),panel('details','Data title from the page',2,true),panel('ccccccccccc','Third in list',3,false)]", long_list)
    assert response != RESPONSE
    long_text = ''.join(f'\\nParagraph {n}: a longer line of the description that wraps across the column.' for n in range(1, 40))
    response = response.replace("const description='Intro at 1:05 and more at example.com plus #music';", "const description='Intro at 1:05 and more at example.com plus #music"+long_text+"';")
    page.evaluate("document.querySelector('ytd-watch-flexy').setAttribute('theater','')")
    page.evaluate(response)
    root = page.locator('#myt-watch')
    expect(root.locator('.own-playlist-name')).to_have_count(60)
    page.wait_for_function("[...document.querySelectorAll('[theater]')].some(node=>node.localName!=='ytd-watch-flexy')")
    page.wait_for_timeout(300)
    sidecar, details = root.locator('.sidecar'), root.locator('.details')
    collapsed = sidecar.bounding_box()
    assert collapsed['height'] < 2000, collapsed
    # The panel follows the details: as tall as they are, never taller.
    assert abs(collapsed['height'] - details.bounding_box()['height']) < 4 or collapsed['height'] <= 400, (collapsed, details.bounding_box())
    scrollable = root.locator('.own-playlist-items').evaluate('e=>e.scrollHeight>e.clientHeight+100')
    assert scrollable, 'playlist items do not scroll inside the panel'
    # Opening the description makes the panel taller; closing it shortens it again.
    expand = root.locator('.expand')
    expand.click()
    expect(expand).to_have_attribute('aria-expanded', 'true')
    page.wait_for_timeout(300)
    opened = sidecar.bounding_box()
    assert opened['height'] > collapsed['height'] + 20, (collapsed, opened)
    assert abs(opened['height'] - details.bounding_box()['height']) < 4, (opened, details.bounding_box())
    expand.click()
    expect(expand).to_have_attribute('aria-expanded', 'false')
    page.wait_for_timeout(300)
    assert abs(sidecar.bounding_box()['height'] - collapsed['height']) < 4, (collapsed, sidecar.bounding_box())
    page.close()
    print('PASS theater mode: the playlist panel follows the description height and scrolls', flush=True)

def wheel_listeners(page):
    cdp = page.context.new_cdp_session(page)
    window = cdp.send('Runtime.evaluate', {'expression': 'window'})['result']['objectId']
    listeners = cdp.send('DOMDebugger.getEventListeners', {'objectId': window})['listeners']
    return [item for item in listeners if item['type'] == 'wheel' and not item['passive']]


def scroll_path(browser):
    # Scrolling the owned page never waits for the main thread: a blocking
    # wheel listener exists only while the pointer is over a native layer.
    page = setup(browser, '/watch?v=details', watch_details_fixture())
    expect(page.locator('#myt-watch')).to_be_visible()
    title = page.locator('#watch-title').bounding_box()
    page.mouse.move(title['x'] + 5, title['y'] + 5)
    assert not wheel_listeners(page), wheel_listeners(page)
    page.locator('#player').evaluate("e=>e.dispatchEvent(new PointerEvent('pointerover',{bubbles:true,composed:true}))")
    assert len(wheel_listeners(page)) == 1
    page.mouse.move(title['x'] + 5, title['y'] + 5)
    page.locator('#watch-title').evaluate("e=>e.dispatchEvent(new PointerEvent('pointerover',{bubbles:true,composed:true}))")
    assert not wheel_listeners(page)
    page.close()
    print('PASS the owned watch page scrolls without a blocking wheel listener', flush=True)


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
        scroll_path(browser)
        theater_scroll(browser)
        browser.close()
