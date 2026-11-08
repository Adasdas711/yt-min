"""Real Chromium MAIN/ISOLATED worlds: avatars cannot rely on page properties leaking."""
import json
from playwright.sync_api import sync_playwright,expect
from smoke import ROOT,MOCK,document,MASTHEAD
from search import video,playlist
from native_search_filters import filters,NATIVE_STYLE


def check(browser,prune,adapter=True):
    page=browser.new_page(viewport={'width':1440,'height':960},reduced_motion='reduce',has_touch=True)
    toolbar,_=filters()
    body=NATIVE_STYLE+'<ytd-app>'+MASTHEAD+'<ytd-search>'+toolbar+'<ytd-section-list-renderer><ytd-channel-renderer id="channel"><a href="/@creator" onclick="event.preventDefault();window.__channelVisits=(window.__channelVisits||0)+1"><h3>Creator</h3></a><ytd-subscribe-button-renderer><button>Subscribe</button></ytd-subscribe-button-renderer></ytd-channel-renderer>'+video(1)+'</ytd-section-list-renderer></ytd-search></ytd-app>'
    body=body.replace('<ytd-search>','<div id="cached-pane" style="display:none"><ytd-search id="cached-search">Stale SPA page</ytd-search></div><section id="active-pane"><ytd-search>',1).replace('</ytd-search></ytd-app>','</ytd-search></section></ytd-app>')
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html',body=document(body)))
    page.route('https://yt3.googleusercontent.com/**',lambda route:route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="176" height="176"><circle cx="88" cy="88" r="88" fill="#00bcd4"/></svg>'))
    page.goto('https://www.youtube.com/results?search_query=worlds')
    page.add_style_tag(path=str(ROOT/'src/styles/styles.css'))
    page.add_script_tag(path=str(ROOT/'src/content/search-data.js'))
    if prune:page.add_script_tag(path=str(ROOT/'src/content/data-pruning.js'))
    page.evaluate('''()=>document.querySelector('#channel').data={channelRenderer:{channelId:'UCX6OQ3DkcsbYNE6H8uQQuVA',title:{simpleText:'Creator'},navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@creator'}},thumbnail:{thumbnails:[{url:'https://yt3.googleusercontent.com/main-only-avatar',width:176}]},trackingParams:'PRIVATE-NEVER-COPY',descriptionSnippet:{simpleText:'BIO-NEVER-COPY'}}}''')
    page.evaluate('''()=>{
      const filters=sp=>({searchFilterRenderer:{label:{simpleText:'Видео'},navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=worlds&sp='+sp}}}}});
      document.querySelector('#cached-search').data=filters('inactive');document.querySelector('#active-pane ytd-search').data=filters('active');
    }''')
    session=page.context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    isolated=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'extension-search-test'})['executionContextId']

    def evaluate(expression):
        result=session.send('Runtime.evaluate',{'expression':expression,'contextId':isolated,'returnByValue':True})
        assert not result.get('exceptionDetails'),result.get('exceptionDetails')
        return result.get('result',{}).get('value')

    evaluate('('+MOCK+')({enabled:true})')
    evaluate('chrome.runtime.id="extension-search-test"')
    assert evaluate('document.querySelector("#channel").data===undefined') is True
    scripts=['ads.js','watch.js','playlist.js']+(['search-data.js'] if adapter else [])+['search.js','content.js']
    for path in scripts:
        evaluate((ROOT/'src/content'/path).read_text())
    root=page.locator('#myt-search')
    expect(root.locator('.media')).to_have_count(1)
    expect(page.locator('#active-pane #myt-search')).to_be_visible()
    expect(page.locator('#cached-pane #myt-search')).to_have_count(0)
    expect(page.locator('ytd-video-renderer')).to_be_hidden()
    expect(page.locator('#myt-search-native-style')).to_have_count(1)
    # A cached manifest may omit search-data.js in ISOLATED while MAIN already
    # has it. Previously that stopped rendering immediately after the channel.
    if not adapter:assert evaluate('typeof MinimalYouTubeSearchData==="undefined"') is True
    image=page.locator('#myt-search [data-myt-search-channel-card] .avatar img')
    expect(image).to_have_attribute('src','https://yt3.googleusercontent.com/main-only-avatar')
    expect(image).to_be_visible()
    page.wait_for_function('document.querySelector("#myt-search").shadowRoot.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector("img").naturalWidth===176')
    assert page.evaluate('typeof MinimalYouTubeSearch==="undefined"') is True
    snapshot=page.locator('html').get_attribute('data-myt-search-snapshot')
    assert 'PRIVATE-NEVER-COPY' not in snapshot and 'BIO-NEVER-COPY' not in snapshot
    # Native roots mount after the first frame, without any extension markers.
    # Their contents must not paint before the queued extraction pass either.
    modern='<yt-lockup-view-model><a class="ytLockupViewModelContentImage" href="/watch?v=abcdefghijk"><img src="'+video(2).split('src="',1)[1].split('"',1)[0]+'"></a><h3 class="ytLockupMetadataViewModelTitle"><a href="/watch?v=abcdefghijk">Modern nested video title</a></h3><a href="/@creator">Creator</a></yt-lockup-view-model>'
    late='<section id="late-native"><ytd-shelf-renderer><div id="title-container"><h2>Новые видео на канале Creator</h2></div>'+modern+playlist(3,True)+video(4)+'</ytd-shelf-renderer></section>'
    hidden_before_update=page.evaluate('''html=>{
      document.querySelector('#active-pane ytd-search').insertAdjacentHTML('beforeend',html);
      document.querySelector('#late-native yt-lockup-view-model[content-type="playlist"]').data={contentId:'PL3',contentType:'LOCKUP_CONTENT_TYPE_PLAYLIST',contentImage:{collectionThumbnailViewModel:{primaryThumbnail:{thumbnailViewModel:{overlays:[{thumbnailBottomOverlayViewModel:{badges:[{thumbnailBadgeViewModel:{text:'72 videos'}}]}}]}}}}};
      const source=document.querySelector('#late-native'),style=getComputedStyle(source);
      return style.opacity==='0'&&source.getBoundingClientRect().height===0;
    }''',late)
    assert hidden_before_update, 'Unmarked native results painted before rendering'
    expect(root.locator('.media')).to_have_count(4)
    expect(root.locator('.playlist-badge')).to_have_text('72 videos')
    expect(root.locator('.group h2')).to_have_text('Latest from Creator')
    expect(root.locator('.media-title',has_text='Modern nested video title')).to_have_count(1)
    expect(root.locator('.media-channel',has_text='Creator')).to_have_count(4)
    native_button=page.locator('#native-filters-toggle');panel=page.locator('#native-filters')
    native_button.click();expect(panel).to_be_visible();assert page.evaluate('__filterButtonTrusted')
    page.screenshot(path=f'/workspace/yt-min-qa/search-original-filters-{prune}-{adapter}.png',full_page=True)
    page.locator('#native-filters-close').click()
    native_button.focus();native_button.press('Space');expect(panel).to_be_visible()
    panel.locator('a',has_text='Video').first.click();expect(panel).to_be_hidden();assert page.evaluate('__filterOptionTrusted')
    native_button.tap();expect(panel).to_be_visible()
    page.locator('#native-filters-close').tap();expect(panel).to_be_hidden()
    page.locator('#native-toolbar').evaluate('node=>node.remove()')
    expect(page.locator('[data-myt-search-toolbar]')).to_have_count(0)
    page.locator('#active-pane ytd-search').evaluate('(node,html)=>node.insertAdjacentHTML("afterbegin",html)',toolbar)
    expect(native_button).to_have_text('Filters')
    native_button.click();expect(panel).to_be_visible();assert page.evaluate('__filterButtonTrusted')
    page.locator('#native-filters-close').click()
    if not adapter:
        evaluate((ROOT/'src/content/search-data.js').read_text())
        evaluate('document.dispatchEvent(new Event("yt-page-data-updated"))')
        expect(root.locator('.media')).to_have_count(4)
        expect(page.locator('#myt-search-native-style')).to_have_count(1)
    # A SPA cache can switch by ancestor style without replacing its nodes.
    page.evaluate('document.querySelector("#active-pane").style.display="none";document.querySelector("#cached-pane").style.display="block"')
    expect(page.locator('#cached-pane #myt-search')).to_be_visible()
    page.evaluate('document.querySelector("#active-pane").style.display="block";document.querySelector("#cached-pane").style.display="none"')
    expect(page.locator('#active-pane #myt-search')).to_be_visible()
    expect(root.locator('.media')).to_have_count(4)
    page.evaluate('''navigation.addEventListener('navigate',event=>{if(new URL(event.destination.url).pathname==='/@creator'){event.preventDefault();window.__channelDestination=event.destination.url;}})''')
    page.evaluate('''navigation.addEventListener('navigate',event=>{if(event.sourceElement){event.preventDefault();window.__nativeLinkCancelled=true;}})''')
    image.click();assert page.evaluate('__channelDestination')=='https://www.youtube.com/@creator'
    assert page.evaluate('!window.__nativeLinkCancelled')
    evaluate('__setEnabled(false)');expect(page.locator('#myt-search')).to_have_count(0)
    evaluate('__setEnabled(true)');expect(image).to_have_attribute('src','https://yt3.googleusercontent.com/main-only-avatar')
    expect(root.locator('.media')).to_have_count(4)
    page.screenshot(path=f'/workspace/yt-min-qa/search-upgrade-{prune}-{adapter}.png',full_page=True)
    page.close();print(f'PASS MAIN/ISOLATED separation, old/new manifest, delayed native containers, nested titles, filters and re-enable: pruning={prune}, adapter={adapter}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for prune in [False,True]:
            for adapter in [False,True]:check(browser,prune,adapter)
        browser.close()


if __name__=='__main__':main()
