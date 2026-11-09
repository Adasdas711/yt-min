"""Channel redirects, metadata, English controls and real section navigation."""
import json
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, MASTHEAD, setup, navigate_spa, assert_stable
from search import video, playlist


def fixture(legacy=False):
    metadata = ('<div id="channel-tagline"><span id="channel-handle">@JoeSpeen</span> · '
                '<span id="subscriber-count">2,24 млн подписчиков</span> · '
                '<span id="videos-count">2,4 тыс. видео</span></div>') if legacy else (
                '<yt-content-metadata-view-model><div class="ytContentMetadataViewModelMetadataRow">'
                '<span>@JoeSpeen</span> · <span>2,24 млн подписчиков</span> · <span>2,4 тыс. видео</span>'
                '</div></yt-content-metadata-view-model>')
    tabs=''.join(f'<yt-tab-shape><div role="tab">{label}</div></yt-tab-shape>'
                 for label in ['Главная','Видео','Трансляции','Плейлисты','Записи','Shorts','Поиск'])
    profile = 'ytd-c4-tabbed-header-renderer' if legacy else 'yt-page-header-view-model'
    return '<style>ytd-browse,yt-page-header-view-model,ytd-c4-tabbed-header-renderer{display:block}#banner{height:120px;background:#386b65}</style><ytd-app>'+MASTHEAD+f'''
      <ytd-page-manager><ytd-browse page-subtype="channels"><div id="page-header"><div id="banner">Banner</div>
      <{profile}><div id="channel-header-container"><h1>Joe Speen — Мой канал</h1>
      <img id="avatar" width="80" height="80" alt="Joe Speen">{metadata}
      <yt-description-preview-view-model><span id="author-description" style="font-family:Arial">Пщщ! Я Joe Speen, а это мой канал.</span><button id="description-more" onclick="window.__more=(window.__more||0)+1">...ещё</button></yt-description-preview-view-model>
      <yt-channel-external-link-view-model><a href="https://t.me/joe_speen_youtube">t.me/joe_speen_youtube и ещё 5 ссылок</a></yt-channel-external-link-view-model>
      <ytd-subscribe-button-renderer><button id="subscribe" aria-label="Подписаться" onclick="this.textContent='Вы подписаны';window.__subscriptions=(window.__subscriptions||0)+1">Подписаться</button></ytd-subscribe-button-renderer>
      </div></{profile}><div id="tabs"><yt-tab-group-shape>{tabs}</yt-tab-group-shape></div></div>
      <div id="contents"><ytd-feed-filter-chip-bar-renderer><button>Новые</button><button>Популярные</button><button>Старые</button></ytd-feed-filter-chip-bar-renderer>
      {video(1)}{playlist(1,count=12)}<ytd-continuation-item-renderer></ytd-continuation-item-renderer></div>
      </ytd-browse></ytd-page-manager></ytd-app>'''


def header(browser,legacy,width,dark):
    page=setup(browser,'/@JoeSpeen/videos',fixture(legacy),width=width,native_dark=dark)
    stats=page.locator('#myt-channel-stats')
    expect(stats).to_be_visible()
    expect(stats.locator('.row')).to_have_text('@JoeSpeen·2.24 M·2.4 K')
    expect(stats.locator('svg')).to_have_count(2)
    expect(stats.locator('[data-kind=subscribers]')).to_have_attribute('aria-label','2.24 M subscribers')
    expect(page.locator('yt-channel-external-link-view-model')).to_be_hidden()
    expect(page.locator('#author-description')).to_have_text('Пщщ! Я Joe Speen, а это мой канал.')
    assert 'Mono' in page.locator('#author-description').evaluate('e=>getComputedStyle(e).fontFamily')
    expect(page.locator('h1')).to_have_text('Joe Speen — Мой канал')
    expect(page.locator('#subscribe')).to_have_text('Subscribe')
    expect(page.locator('#description-more')).to_have_text('More')
    page.locator('#description-more').click()
    assert page.evaluate('__more')==1
    expect(page.get_by_role('button',name='Latest',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Popular',exact=True)).to_be_visible()
    page.locator('#subscribe').click()
    expect(page.locator('#subscribe')).to_have_text('Subscribed')
    assert page.evaluate('__subscriptions')==1
    nav=page.locator('#myt-channel-nav')
    expect(nav.get_by_role('link')).to_have_text(['Videos','Live','Playlists','Posts'])
    expect(nav.get_by_role('button',name='Search',exact=True)).to_be_visible()
    source='#subscriber-count' if legacy else 'yt-content-metadata-view-model'
    for native,expected in [('0 subscribers','0'),('1 subscriber','1'),('525M subscribers','525 M'),('1,23 Mio. Abonnenten','1.23 M'),('123 456 подписчиков','123.46 K')]:
        value=native if legacy else '@JoeSpeen · '+native+' · 2,4 тыс. видео'
        page.locator(source).evaluate('(e,value)=>e.textContent=value',value)
        expect(stats.locator('[data-kind=subscribers]')).to_have_attribute('aria-label',expected+' subscribers')
    page.wait_for_timeout(100)
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(stats).to_have_count(0)
    expect(nav).to_have_count(0)
    expect(page.locator('yt-channel-external-link-view-model')).to_be_visible()
    expect(page.locator('#subscribe')).to_have_text('Вы подписаны')
    page.close()
    print(f'PASS metadata, icons, English controls, original content, updates/restoration: legacy={legacy}, {width}px, dark={dark}',flush=True)


def startup(browser,path,enabled=True):
    page=browser.new_page()
    modules=['ads','watch','playlist','search-data','search','channel','content']
    code='\n'.join((ROOT/'src/content'/f'{module}.js').read_text() for module in modules)
    page.add_init_script(f'({MOCK})({json.dumps({"enabled":enabled})});\n'+code)
    requests=[]
    def route(request):
        requests.append(request.request.url)
        lang='en' if parse_qs(urlparse(request.request.url).query).get('hl')==['en'] else 'ru'
        request.fulfill(content_type='text/html; charset=utf-8',body=f'<!doctype html><html lang="{lang}"><head><style>'+ (ROOT/'src/styles/styles.css').read_text()+'</style></head><body>'+fixture()+'</body></html>')
    page.route('https://www.youtube.com/**',route)
    page.goto('https://www.youtube.com'+path)
    return page,requests


def redirects(browser):
    for base in ('/@JoeSpeen','/channel/UCfixture','/c/Creator','/user/Creator'):
        page,requests=startup(browser,base+'?view=0#profile')
        page.wait_for_url('**/videos?**')
        assert urlparse(page.url).path==base+'/videos',page.url
        assert parse_qs(urlparse(page.url).query)=={'view':['0'],'hl':['en'],'persist_hl':['1']},page.url
        assert urlparse(page.url).fragment=='profile'
        assert len(requests)==2,requests
        page.close()
    page,requests=startup(browser,'/@JoeSpeen/featured')
    page.wait_for_url('**/videos?**');assert len(requests)==2,requests;page.close()
    for section in ('videos','streams','playlists','posts','search'):
        page,requests=startup(browser,'/@JoeSpeen/'+section+'?query=hello')
        page.wait_for_url('**hl=en**')
        assert urlparse(page.url).path=='/@JoeSpeen/'+section,page.url
        assert parse_qs(urlparse(page.url).query)=={'query':['hello'],'hl':['en'],'persist_hl':['1']},page.url
        assert len(requests)==2,requests
        page.close()
    page,requests=startup(browser,'/@JoeSpeen',False)
    page.wait_for_timeout(150)
    assert urlparse(page.url).path=='/@JoeSpeen' and len(requests)==1,requests
    page.close()
    print('PASS single English /videos redirect for all channel URL forms; disabled mode stays native',flush=True)


def navigation(browser):
    page,requests=startup(browser,'/@JoeSpeen/videos?hl=en&persist_hl=1')
    for name,path in [('Live','streams'),('Playlists','playlists'),('Posts','posts'),('Videos','videos')]:
        # Simulate YouTube swallowing native links; our tabs must still navigate.
        page.evaluate('document.addEventListener("click",e=>{e.preventDefault();e.stopImmediatePropagation()},true)')
        page.locator('#myt-channel-nav').get_by_role('link',name=name,exact=True).click()
        page.wait_for_url('**/'+path+'?**')
        assert parse_qs(urlparse(page.url).query)=={'hl':['en'],'persist_hl':['1']},page.url
        expect(page.locator('#myt-channel-nav').get_by_role('link',name=name,exact=True)).to_have_attribute('aria-current','page')
        if path=='posts':expect(page.locator('#myt-search')).to_have_count(0)
    page.locator('#myt-channel-nav').get_by_role('button',name='Search',exact=True).click()
    field=page.get_by_role('searchbox',name='Search this channel')
    field.fill('Поиск & + #')
    field.press('Enter')
    page.wait_for_url('**/search?**')
    assert parse_qs(urlparse(page.url).query)=={'hl':['en'],'persist_hl':['1'],'query':['Поиск & + #']},page.url
    expect(page.get_by_role('searchbox',name='Search this channel')).to_have_value('Поиск & + #')
    # A channel reached through YouTube SPA routing gets the same landing rule.
    navigate_spa(page,'/@JoeSpeen')
    page.wait_for_url('**/videos?**')
    assert len(requests)==7,requests
    page.close()
    print('PASS real section clicks, native interception, Posts, Unicode channel search and SPA landing redirect',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for legacy in (False,True):
            for width,dark in ((1440,True),(390,False)):
                header(browser,legacy,width,dark)
        redirects(browser)
        navigation(browser)
        browser.close()
