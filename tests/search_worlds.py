"""Real Chromium MAIN/ISOLATED worlds: avatars cannot rely on page properties leaking."""
import json
from playwright.sync_api import sync_playwright,expect
from smoke import ROOT,MOCK,document,MASTHEAD
from search import video


def check(browser,prune):
    page=browser.new_page(viewport={'width':1440,'height':960},reduced_motion='reduce')
    body='<ytd-app>'+MASTHEAD+'<ytd-search><ytd-section-list-renderer><ytd-channel-renderer id="channel"><a href="/@creator" onclick="event.preventDefault();window.__channelVisits=(window.__channelVisits||0)+1"><h3>Creator</h3></a><ytd-subscribe-button-renderer><button>Subscribe</button></ytd-subscribe-button-renderer></ytd-channel-renderer>'+video(1)+'</ytd-section-list-renderer></ytd-search></ytd-app>'
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html',body=document(body)))
    page.route('https://yt3.googleusercontent.com/**',lambda route:route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="176" height="176"><circle cx="88" cy="88" r="88" fill="#00bcd4"/></svg>'))
    page.goto('https://www.youtube.com/results?search_query=worlds')
    page.add_style_tag(path=str(ROOT/'src/styles/styles.css'))
    page.add_script_tag(path=str(ROOT/'src/content/search-data.js'))
    if prune:page.add_script_tag(path=str(ROOT/'src/content/data-pruning.js'))
    page.evaluate('''()=>document.querySelector('#channel').data={channelRenderer:{channelId:'UCX6OQ3DkcsbYNE6H8uQQuVA',title:{simpleText:'Creator'},navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@creator'}},thumbnail:{thumbnails:[{url:'https://yt3.googleusercontent.com/main-only-avatar',width:176}]},trackingParams:'PRIVATE-NEVER-COPY',descriptionSnippet:{simpleText:'BIO-NEVER-COPY'}}}''')
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
    for path in ['ads.js','watch.js','playlist.js','search-data.js','search.js','content.js']:
        evaluate((ROOT/'src/content'/path).read_text())
    image=page.locator('#myt-search [data-myt-search-channel-card] .avatar img')
    expect(image).to_have_attribute('src','https://yt3.googleusercontent.com/main-only-avatar')
    expect(image).to_be_visible()
    page.wait_for_function('document.querySelector("#myt-search").shadowRoot.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector("img").naturalWidth===176')
    assert page.evaluate('typeof MinimalYouTubeSearch==="undefined"') is True
    snapshot=page.locator('html').get_attribute('data-myt-search-snapshot')
    assert 'PRIVATE-NEVER-COPY' not in snapshot and 'BIO-NEVER-COPY' not in snapshot
    image.click();assert page.evaluate('__channelVisits')==1
    evaluate('__setEnabled(false)');expect(page.locator('#myt-search')).to_have_count(0)
    evaluate('__setEnabled(true)');expect(image).to_have_attribute('src','https://yt3.googleusercontent.com/main-only-avatar')
    page.close();print(f'PASS actual MAIN/ISOLATED separation, MAIN-only renderer avatar, public snapshot, channel navigation and re-enable: pruning={prune}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for prune in [False,True]:check(browser,prune)
        browser.close()


if __name__=='__main__':main()
