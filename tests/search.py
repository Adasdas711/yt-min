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
    assert abs(wide['width']-a['width'])<1,(a,wide)
    if width>1000:
        assert abs(wide['width']-regular['width']*2-24)<1,(wide,regular)
        assert abs(wide['y']-regular['y'])<1 and regular['x']>=wide['x']+wide['width']+23,(wide,regular)
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


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,900,390]:
            for dark in [True,False]:check(browser,width,dark)
        browser.close()


if __name__=='__main__':main()
