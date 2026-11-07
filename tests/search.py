"""Search layout, Shorts section cleanup and repeatable native filters."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, assert_stable, navigate_spa
from playlist import cover


def video(i):
    return f'''<ytd-video-renderer id="video-{i}"><div id="dismissible"><ytd-thumbnail><a href="/watch?v=video{i}"><img src="{cover()}"></a></ytd-thumbnail><div id="details"><h3><a id="video-title" href="/watch?v=video{i}">Regular video {i}</a></h3><div id="channel-info"><ytd-channel-name><a href="/@creator">Creator</a></ytd-channel-name></div><div class="metadata-snippet-container">Unwanted description</div><ytd-expandable-metadata-renderer>Transcript excerpt 1:02</ytd-expandable-metadata-renderer></div></div></ytd-video-renderer>'''


def playlist(i,modern=False):
    if modern:
        return f'''<div id="playlist-wrapper"><yt-lockup-view-model id="playlist-{i}" content-type="playlist"><div><a href="/watch?v=first&list=PL{i}"><yt-collection-thumbnail-view-model><img src="{cover()}"><yt-collection-thumbnail-overlay-view-model>64 videos</yt-collection-thumbnail-overlay-view-model></yt-collection-thumbnail-view-model></a><h3><a href="/watch?v=first&list=PL{i}">German playlist {i}</a></h3><div class="ytContentMetadataViewModelMetadataRow"><a href="/@easygerman">Easy German</a></div><div class="ytContentMetadataViewModelMetadataRow">Updated 2 days ago</div></div></yt-lockup-view-model></div>'''
    return f'''<ytd-playlist-renderer id="playlist-{i}"><div><a href="/playlist?list=PL{i}"><ytd-thumbnail><img src="{cover()}"></ytd-thumbnail></a><h3><a id="video-title" href="/playlist?list=PL{i}">German playlist {i}</a></h3><ytd-channel-name><a href="/@easygerman">Easy German</a></ytd-channel-name><span id="video-count-text">64 videos</span><span id="published-time-text">Updated 2 days ago</span></div></ytd-playlist-renderer>'''


def fixture():
    return f'''<style>ytd-search-sub-menu-renderer,tp-yt-iron-collapse,ytd-search-filter-group-renderer,yt-collection-thumbnail-view-model{{display:block}}#filter-button{{min-height:40px}}#collapse{{height:0;overflow:hidden}}ytd-thumbnail img{{width:100%;height:auto}}</style><ytd-app>{MASTHEAD}<ytd-page-manager><ytd-search><ytd-search-sub-menu-renderer><button id="filter-button" aria-label="Search filters" aria-expanded="false" onclick="window.__nativeToggles=(window.__nativeToggles||0)+1;if(__nativeToggles>2)return;document.querySelector('#collapse').hidden=!document.querySelector('#collapse').hidden">Filters</button><tp-yt-iron-collapse id="collapse" hidden><ytd-search-filter-group-renderer><a href="/results?search_query=fixture&sp=videos" onclick="event.preventDefault();window.__filtered=true">Videos</a></ytd-search-filter-group-renderer></tp-yt-iron-collapse></ytd-search-sub-menu-renderer><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents"><ytd-channel-renderer id="channel"><div id="content-section"><div id="avatar-section"><img src="{cover()}"></div><div id="info-section"><a id="main-link" href="/@easygerman">Easy German</a><button>Subscribe</button></div></div></ytd-channel-renderer>{playlist(1)}{video(1)}{video(2)}{playlist(2,True)}{video(3)}<yt-section-header-view-model id="shorts-title"><h2>Shorts</h2></yt-section-header-view-model><ytd-shelf-renderer id="mixed-shelf"><div id="title-container"><h2>Shorts</h2></div><div id="content">{video(4)}<yt-shorts-lockup-view-model id="short"><a href="/shorts/short1">Short video</a></yt-shorts-lockup-view-model></div></ytd-shelf-renderer><ytd-shelf-renderer id="empty-shorts"><div id="title-container"><h2>Shorts</h2></div><div id="content"></div></ytd-shelf-renderer><ytd-continuation-item-renderer>Next page</ytd-continuation-item-renderer></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'''


def check(browser,width,dark):
    page=setup(browser,'/results?search_query=fixture',fixture(),width=width,theme='dark' if dark else 'light',native_dark=not dark)
    channel=page.locator('#channel');a=channel.bounding_box()
    regular=page.locator('#video-1').bounding_box();wide=page.locator('#playlist-1').bounding_box()
    assert abs((a['width']-(regular['width']*1.5+12)) if width>1000 else a['width']-wide['width'])<1,(a,wide,regular)
    if width>1000:
        assert abs(wide['width']-regular['width']*2-24)<1,(wide,regular)
        assert wide['width']>regular['width'],(wide,regular)
    elif width>600:assert abs(wide['width']-regular['width']*2-24)<1,(wide,regular)
    else:assert abs(wide['width']-regular['width'])<1,(wide,regular)
    filters=page.locator('ytd-search-sub-menu-renderer').bounding_box()
    assert a['y']>=filters['y']+filters['height']+15,(a,filters)
    expect(page.locator('#shorts-title')).to_be_hidden();expect(page.locator('#empty-shorts')).to_be_hidden()
    expect(page.locator('#mixed-shelf #title-container')).to_be_hidden();expect(page.locator('#short')).to_be_hidden()
    expect(page.locator('#video-4')).to_be_visible()
    expect(page.locator('#video-1 .metadata-snippet-container')).to_be_hidden()
    expect(page.locator('#video-1 ytd-expandable-metadata-renderer')).to_be_hidden()
    for i in [1,2]:
        card=page.locator(f'#playlist-{i} [data-myt-search-playlist-card]')
        expect(card.locator('.title')).to_have_text(f'German playlist {i}')
        expect(card.locator('.title')).to_have_attribute('href',f'https://www.youtube.com/playlist?list=PL{i}')
        expect(card.locator('.owner')).to_have_text('Easy German')
        expect(card.locator('.count')).to_have_text('64 videos')
        expect(card.locator('.updated')).to_have_text('Updated 2 days ago')
    # Recycled result data updates in place and returns to native video markup.
    page.locator('#playlist-2 .ytContentMetadataViewModelMetadataRow').last.evaluate('e=>e.textContent="Updated yesterday"')
    expect(page.locator('#playlist-2 [data-myt-search-playlist-card] .updated')).to_have_text('Updated yesterday')
    button=page.locator('#filter-button');panel=page.locator('#collapse')
    for _ in range(8):
        button.click();expect(panel).to_be_visible();expect(button).to_have_attribute('aria-expanded','true')
        panel.get_by_role('link',name='Videos',exact=True).click();assert page.evaluate('__filtered')
        button.click();expect(panel).to_be_hidden();expect(button).to_have_attribute('aria-expanded','false')
    assert page.evaluate('window.__nativeToggles||0')==0
    # A new orphan title is removed in the mutation microtask, before painting.
    page.evaluate('''() => document.querySelector('ytd-item-section-renderer > #contents').insertAdjacentHTML('beforeend','<yt-section-header-view-model id="late-shorts"><h2>Shorts</h2></yt-section-header-view-model>')''')
    expect(page.locator('#late-shorts')).to_be_hidden()
    page.locator('#late-shorts h2').evaluate('e=>e.textContent="Videos"')
    expect(page.locator('#late-shorts')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert_stable(page)
    page.evaluate('scrollTo(0,0)');page.screenshot(path=f'/tmp/yt-min-search23-{width}-{dark}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-search-playlist-card],[data-myt-search-playlist-source],[data-myt-search-filters]')).to_have_count(0)
    expect(page.locator('#shorts-title')).to_be_visible();expect(button).to_have_attribute('aria-expanded','false')
    assert panel.get_attribute('hidden') is not None
    page.close()
    print(f'PASS search playlists/Shorts/filter cycles: width={width}, dark={dark}',flush=True)


def covers_and_sections(browser,width,dark):
    badge=f'''<yt-lockup-view-model id="badge-playlist" content-type="playlist"><div><a href="/playlist?list=PLbadge"><yt-collection-thumbnail-view-model><picture><source data-srcset="https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg 320w, https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg 480w"><img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"></picture><yt-thumbnail-overlay-badge-view-model><yt-badge-shape><span class="ytBadgeShapeText">256 видео</span></yt-badge-shape></yt-thumbnail-overlay-badge-view-model></yt-collection-thumbnail-view-model></a><h3><a href="/playlist?list=PLbadge">A real playlist cover</a></h3><a href="/@creator">Creator</a><p id="published-time-text">Updated 2 days ago</p></div></yt-lockup-view-model>'''
    payload='''<yt-lockup-view-model id="payload-playlist" content-type="playlist"><div><a href="/playlist?list=PLpayload"><yt-collection-thumbnail-view-model></yt-collection-thumbnail-view-model></a><h3><a href="/playlist?list=PLpayload">A lazy playlist</a></h3><a href="/@creator">Creator</a></div></yt-lockup-view-model>'''
    def section(content):return '<ytd-item-section-renderer><div id="contents">'+content+'</div></ytd-item-section-renderer>'
    special=section('<yt-section-header-view-model id="for-you-heading"><h2>For you</h2></yt-section-header-view-model>'+''.join(video(i) for i in range(6,10)))
    special=special.replace('<ytd-item-section-renderer>','<ytd-item-section-renderer id="for-you">',1)
    shelf='<ytd-shelf-renderer id="watch-again"><div id="title-container"><h2>Watch again</h2></div><div id="content"><div id="shelf-items"><div class="native-row">'+''.join(video(i) for i in range(10,13))+'</div><div class="native-row">'+video(13)+'</div></div></div></ytd-shelf-renderer>'
    sections=section(video(1)+video(2))+section(badge)+section(video(3)+video(4))+section(payload)+section(video(5))+special+section(shelf)
    html='<style>ytd-item-section-renderer,ytd-shelf-renderer,yt-collection-thumbnail-view-model{display:block}ytd-thumbnail img{width:100%;height:auto}</style><ytd-app>'+MASTHEAD+'<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents">'+sections+'<ytd-continuation-item-renderer id="paging">More</ytd-continuation-item-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
    page=setup(browser,'/results?search_query=playlist',html,width=width,native_dark=dark,enabled=False,prune_data=True)
    page.route('https://i.ytimg.com/**',lambda route:route.fulfill(status=200,content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#596f9c"/><circle cx="320" cy="180" r="80" fill="#ddd"/></svg>'))
    page.evaluate('__setEnabled(true)')
    expect(page.locator('[data-myt-search-playlist-card]')).to_have_count(2)
    # Capture public data while native cover/count widgets are still lazy.
    page.evaluate('''() => {
      window.__parents=new Map([...document.querySelectorAll('ytd-video-renderer,yt-lockup-view-model')].map(node=>[node,node.parentElement]));
      window.ytInitialData={contents:{twoColumnSearchResultsRenderer:{contents:[{playlistRenderer:{playlistId:'PLpayload',videoCount:'64',thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/12345678901/hqdefault.jpg',width:480}]}}}]}}};
    }''')
    for source,count,id in [('badge-playlist','256 videos','abcdefghijk'),('payload-playlist','64 videos','12345678901')]:
        card=page.locator(f'#{source} [data-myt-search-playlist-card]')
        expect(card.locator('.count')).to_have_text(count)
        expect(card.locator('img')).to_have_attribute('src',f'https://i.ytimg.com/vi/{id}/hqdefault.jpg')
        card.locator('img').scroll_into_view_if_needed()
        expect(card.locator('img')).to_be_visible()
        page.wait_for_function('''id=>document.querySelector('#'+id+' [data-myt-search-playlist-card]').shadowRoot.querySelector('img').naturalWidth>1''',arg=source)
    if width>1000:
        boxes={i:page.locator('#video-'+str(i)).bounding_box() for i in range(1,6)}
        a=page.locator('#badge-playlist').bounding_box();b=page.locator('#payload-playlist').bounding_box()
        assert abs(boxes[1]['y']-boxes[3]['y'])<1,(boxes,a)
        assert abs(a['y']-boxes[4]['y'])<1,(boxes,a)
        assert abs(b['y']-boxes[5]['y'])<1,(boxes,b)
    for source,start in [('#for-you',6),('#watch-again',10)]:
        panel=page.locator(source)
        expect(panel).to_have_attribute('data-myt-search-special','')
        expect(panel).to_have_css('background-color','rgb(36, 36, 42)' if dark else 'rgb(241, 241, 244)')
        boxes=[page.locator('#video-'+str(i)).bounding_box() for i in range(start,start+4)]
        if width>600:
            assert abs(boxes[0]['y']-boxes[1]['y'])<1,(source,boxes)
            assert abs(boxes[2]['y']-boxes[3]['y'])<1 and boxes[2]['y']>boxes[0]['y'],(source,boxes)
        assert all(box['x']>=panel.bounding_box()['x'] for box in boxes)
    page.evaluate('''() => window.ytInitialData={contents:{twoColumnSearchResultsRenderer:{contents:[{playlistRenderer:{playlistId:'PLpayload',videoCount:'65',thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/12345678901/hqdefault.jpg',width:480}]}}}]}}}''')
    expect(page.locator('#payload-playlist [data-myt-search-playlist-card] .count')).to_have_text('65 videos')
    assert page.evaluate('[...__parents].every(([node,parent])=>node.parentElement===parent)')
    expect(page.locator('#paging')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert_stable(page)
    page.evaluate('scrollTo(0,0)');page.screenshot(path=f'/tmp/yt-min-search24-{width}-{dark}.png',full_page=True)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-search-flow],[data-myt-search-flat],[data-myt-search-special],[data-myt-search-special-heading],[data-myt-search-balanced]')).to_have_count(0)
    assert page.evaluate('[...__parents].every(([node,parent])=>node.parentElement===parent)')
    page.close()
    print(f'PASS lazy covers/count badges, compact mixed sections and special panels: width={width}, dark={dark}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,900,390]:
            for dark in [True,False]:
                check(browser,width,dark)
                covers_and_sections(browser,width,dark)
        browser.close()


if __name__=='__main__':main()
