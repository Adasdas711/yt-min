"""Channel layout, native controls, sticky tabs and incremental cards."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, navigate_spa
from search import video, playlist


def fixture():
    tabs=''.join(f'<yt-tab-shape role="tab"><a href="/@creator/{path}">{label}</a></yt-tab-shape>' for path,label in [('featured','Home'),('videos','Videos'),('streams','Live'),('playlists','Playlists'),('community','Posts'),('shorts','Shorts'),('about','About'),('search','Search')])
    return '<style>ytd-browse,yt-page-header-view-model{display:block}#banner{height:120px}#tabs{height:48px}yt-tab-shape{display:inline-block;padding:10px}</style><ytd-app>'+MASTHEAD+'<ytd-page-manager><ytd-browse page-subtype="channels"><div id="header"><div id="banner">Banner</div><yt-page-header-view-model><h1>Название канала</h1><img id="avatar" width="80" height="80"><div id="description-container">Channel description</div><button id="subscribe" onclick="this.textContent=\'Subscribed\'">Subscribe</button></yt-page-header-view-model></div><div id="tabs"><yt-tab-group-shape>'+tabs+'</yt-tab-group-shape></div><div id="contents"><ytd-rich-grid-renderer><div id="contents">'+video(1)+playlist(1,count=12)+''.join(video(i) for i in range(2,18))+'<ytd-continuation-item-renderer id="continuation"></ytd-continuation-item-renderer></div></ytd-rich-grid-renderer></div></ytd-browse></ytd-page-manager></ytd-app>'

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width,nested in ((1440,False),(900,False),(390,False),(1440,True)):
        page=setup(browser,path='/@creator/videos',body=fixture().replace('</div><div id="tabs">','<div id="tabs">').replace('</yt-tab-group-shape></div><div id="contents">','</yt-tab-group-shape></div></div><div id="contents">') if nested else fixture(),width=width)
        expect(page.locator('#myt-search .media')).to_have_count(18)
        for label in ('Home','About','Shorts'):
            expect(page.get_by_role('tab').filter(has_text=label)).to_be_hidden()
        expect(page.get_by_role('tab').filter(has_text='Videos')).to_be_visible()
        page.locator('#subscribe').click()
        expect(page.locator('#subscribe')).to_have_text('Subscribed')
        assert page.locator('h1').evaluate("e=>getComputedStyle(e).fontStyle")=='italic'
        assert 'Mono' in page.locator('#description-container').evaluate("e=>getComputedStyle(e).fontFamily")
        result=page.locator('#myt-search').evaluate('''host=>{const q=s=>host.shadowRoot.querySelector(s),a=q('.video').getBoundingClientRect(),b=q('.playlist').getBoundingClientRect();return {video:a.width,playlist:b.width,display:getComputedStyle(q('.playlist')).display,width:host.getBoundingClientRect().width}}''')
        assert abs(result['video']-result['playlist'])<2,result
        assert result['display']=='flex',result
        page.evaluate('window.scrollTo(0,500)')
        page.wait_for_timeout(100)
        assert abs(page.locator('ytd-browse #tabs').bounding_box()['y']-56)<3, page.evaluate("()=>({position:getComputedStyle(document.querySelector('ytd-browse #tabs')).position,scroll:scrollY,tabs:document.querySelector('ytd-browse #tabs').getBoundingClientRect().toJSON(),parents:[...document.querySelectorAll('ytd-app,ytd-page-manager,ytd-browse')].map(e=>[e.tagName,getComputedStyle(e).overflow,getComputedStyle(e).height])})")
        page.locator('ytd-rich-grid-renderer > #contents').evaluate('(e,html)=>e.insertAdjacentHTML("beforeend",html)',video(99))
        expect(page.locator('#myt-search .media')).to_have_count(19)
        page.evaluate('window.__setEnabled(false)')
        expect(page.locator('#myt-search')).to_have_count(0)
        expect(page.get_by_role('tab').filter(has_text='Home')).to_be_visible()
        page.close()
        print(f'PASS nested={nested} channel identity, tabs, sticky navigation, equal playlist/video cells, updates and disable at {width}px')
    page=setup(browser,path='/@creator/community',body=fixture())
    expect(page.locator('#myt-search')).to_have_count(0)
    expect(page.locator('#subscribe')).to_be_visible()
    navigate_spa(page,'/@creator/videos')
    expect(page.locator('#myt-search .media')).to_have_count(18)
    navigate_spa(page,'/@creator/community')
    expect(page.locator('#myt-search')).to_have_count(0)
    expect(page.locator('#subscribe')).to_be_visible()
    page.close()
    print('PASS native posts and SPA transitions between posts and video grid')
    browser.close()
