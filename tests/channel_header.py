"""Channel redirects, metadata, English controls and real section navigation."""
import json
import re
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, MASTHEAD, setup, navigate_spa, assert_stable
from search import video, playlist


def fixture(legacy=False,contents=None):
    if contents is None:contents=video(1)+playlist(1,count=12)+'<ytd-continuation-item-renderer></ytd-continuation-item-renderer>'
    metadata = ('<div id="channel-tagline"><span id="channel-handle">@JoeSpeen</span> · '
                '<span id="subscriber-count">2,24 млн подписчиков</span> · '
                '<span id="videos-count">2,4 тыс. видео</span></div>') if legacy else (
                '<yt-content-metadata-view-model><div class="ytContentMetadataViewModelMetadataRow">'
                '<span>@JoeSpeen</span> · <span>2,24 млн подписчиков</span> · <span>2,4 тыс. видео</span>'
                '</div></yt-content-metadata-view-model>')
    tabs=''.join(f'<yt-tab-shape><div role="tab">{label}</div></yt-tab-shape>'
                 for label in ['Главная','Видео','Трансляции','Плейлисты','Записи','Shorts','Поиск'])
    profile = 'ytd-c4-tabbed-header-renderer' if legacy else 'yt-page-header-view-model'
    return '''<style>ytd-browse,yt-page-header-view-model,ytd-c4-tabbed-header-renderer{display:block}#banner{height:120px;background:#386b65}
      yt-description-preview-view-model{display:block;position:relative}
      .ytDescriptionPreviewViewModelTruncatedText{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:1;overflow:hidden}
      .ytDescriptionPreviewViewModelMoreButton{position:absolute;right:0;bottom:0;transform:translateY(-8px);font:500 14px/20px Arial}
      </style><ytd-app>'''+MASTHEAD+f'''
      <ytd-page-manager><ytd-browse page-subtype="channels"><div id="page-header"><div id="banner">Banner</div>
      <{profile}><div id="channel-header-container"><h1>Joe Speen — Мой канал</h1>
      <img id="avatar" width="80" height="80" alt="Joe Speen" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Ccircle cx='40' cy='40' r='40' fill='%23e44'/%3E%3C/svg%3E">{metadata}
      <yt-description-preview-view-model><yt-attributed-string class="ytDescriptionPreviewViewModelTruncatedText"><span id="author-description" style="font-family:Arial">Пщщ! Я Joe Speen, а это мой канал.</span></yt-attributed-string><button id="description-more" class="ytDescriptionPreviewViewModelMoreButton" onclick="window.__more=(window.__more||0)+1"><span id="more-label">...ещё</span></button></yt-description-preview-view-model>
      <yt-channel-external-link-view-model><a href="https://t.me/joe_speen_youtube">t.me/joe_speen_youtube и ещё 5 ссылок</a></yt-channel-external-link-view-model>
      <ytd-subscribe-button-renderer><button id="subscribe" aria-label="Подписаться" onclick="this.textContent='Вы подписаны';window.__subscriptions=(window.__subscriptions||0)+1">Подписаться</button></ytd-subscribe-button-renderer>
      </div></{profile}><div id="tabs"><yt-tab-group-shape>{tabs}</yt-tab-group-shape></div></div>
      <div id="contents"><ytd-feed-filter-chip-bar-renderer><button>Новые</button><button>Популярные</button><button>Старые</button></ytd-feed-filter-chip-bar-renderer>
      {contents}</div>
      </ytd-browse></ytd-page-manager></ytd-app>'''


def tabbed_fixture():
    # Live YouTube (measured): the profile and the tabs live in a fixed
    # tp-yt-app-header inside ytd-tabbed-page-header; the tabs are inside
    # tp-yt-paper-tabs #tabsContent.
    avatar="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2780%27 height=%2780%27%3E%3Ccircle cx=%2740%27 cy=%2740%27 r=%2740%27 fill=%27%23e44%27/%3E%3C/svg%3E"
    tabs=''.join(f'<yt-tab-shape role="tab"><a href="/@JoeSpeen/{path}">{label}</a></yt-tab-shape>' for path,label in [('featured','Home'),('videos','Videos'),('streams','Live'),('playlists','Playlists'),('posts','Posts')])
    return f'''<style>ytd-browse,ytd-tabbed-page-header,tp-yt-app-header-layout,tp-yt-app-header,tp-yt-app-toolbar,tp-yt-paper-tabs,yt-page-header-renderer,yt-page-header-view-model{{display:block}}
      tp-yt-app-header{{background:#0f0f0f}}#tabsContainer{{position:relative;overflow:hidden;height:48px}}#tabsContent{{display:flex;position:absolute;left:0;top:0}}
      ytd-tabbed-page-header #page-header{{max-width:1284px;margin:0 auto;padding:0 24px}}</style><ytd-app>{MASTHEAD}<ytd-page-manager><ytd-browse page-subtype="channels">
      <div id="header"><ytd-tabbed-page-header><tp-yt-app-header-layout><div id="wrapper"><tp-yt-app-header id="header" style="position:fixed;top:56px;left:0;right:0;z-index:2;transform:translateY(0)"><div id="contentContainer">
        <div id="page-header-container"><div id="page-header-banner"><img alt="" src="{avatar}" style="width:100%;height:120px"></div>
          <div id="page-header"><yt-page-header-renderer><yt-page-header-view-model><yt-image-banner-view-model><img alt="" src="{avatar}" style="width:100%;height:150px"></yt-image-banner-view-model>
            <div class="yt-page-header-view-model__page-header-headline"><yt-decorated-avatar-view-model><img alt="" src="{avatar}" style="width:160px;height:160px"></yt-decorated-avatar-view-model>
            <div class="yt-page-header-view-model__page-header-headline-info"><h1>Joe Speen</h1><yt-content-metadata-view-model>@JoeSpeen · 2.24M subscribers · 2.4K videos</yt-content-metadata-view-model><yt-description-preview-view-model><span class="ytDescriptionPreviewViewModelTruncatedText">Пщщ! Я Joe Speen, а это мой канал.</span></yt-description-preview-view-model>
            <yt-flexible-actions-view-model><yt-subscribe-button-view-model><button id="subscribe">Subscribe</button></yt-subscribe-button-view-model></yt-flexible-actions-view-model></div></div>
          </yt-page-header-view-model></yt-page-header-renderer></div></div>
        <tp-yt-app-toolbar><div id="tabs-container"><tp-yt-paper-tabs><div id="tabsContainer"><div id="tabsContent">{tabs}</div></div></tp-yt-paper-tabs></div></tp-yt-app-toolbar>
      </div></tp-yt-app-header><div id="contentContainer" style="padding-top:420px"></div></div></tp-yt-app-header-layout></ytd-tabbed-page-header></div>
      <div id="contents" style="min-height:3000px"><ytd-rich-grid-renderer><div id="contents">{video(1)}</div></ytd-rich-grid-renderer></div></ytd-browse></ytd-page-manager></ytd-app>'''


def tabbed_header(browser,width):
    page=setup(browser,'/@JoeSpeen/videos',tabbed_fixture(),width=width)
    own=page.locator('#myt-channel-header')
    expect(own.locator('h1')).to_have_text('Joe Speen')
    # The owned header takes the native profile's place inside YouTube's
    # header, so no empty native header band remains above it.
    assert page.evaluate("document.querySelector('#myt-channel-header').closest('tp-yt-app-header')!==null")
    assert abs(own.bounding_box()['y']-56)<1,own.bounding_box()
    # Banner across the whole window; a larger avatar overlaps its bottom; the
    # name, stats and description form one column right of the avatar.
    banner=own.locator('.myt-ch-banner').bounding_box();avatar=own.locator('.myt-ch-avatar').bounding_box()
    title=own.locator('h1').bounding_box();description=page.locator('#myt-channel-description').bounding_box()
    assert banner['x']==0 and abs(banner['width']-width)<1,banner
    assert abs(avatar['width']-(300 if width>600 else 120))<1,avatar
    assert avatar['y']<banner['y']+banner['height']<avatar['y']+avatar['height']/2,(banner,avatar)
    assert title['x']>=avatar['x']+avatar['width'] and title['y']>=banner['y']+banner['height'],(avatar,title)
    assert abs(description['x']-title['x'])<1,(title,description)
    if width>900:
        # The text column keeps the same distance from both window edges.
        right=page.locator('#myt-channel-description').evaluate('e=>innerWidth-e.getBoundingClientRect().right')
        assert abs(right-title['x'])<2,(title,right)
    # YouTube's fixed, script-positioned app header becomes part of the page:
    # it scrolls with the document (no lag) and its reserved space is gone.
    assert page.evaluate("getComputedStyle(document.querySelector('tp-yt-app-header')).position")!='fixed'
    top=own.bounding_box()['y'];page.evaluate('window.scrollTo(0,200)')
    assert abs(own.bounding_box()['y']-(top-200))<1,own.bounding_box()
    page.evaluate('window.scrollTo(0,2000)');page.wait_for_timeout(100)
    # The navigation still stays pinned below the masthead.
    nav=page.locator('#myt-channel-nav')
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_be_in_viewport()
    assert abs(nav.bounding_box()['y']-56)<1,nav.bounding_box()
    # Pinned by CSS alone: it holds its place on every scroll position.
    assert page.evaluate('''async()=>{const nav=document.querySelector('#myt-channel-nav');let max=0;
      for(let y=1000;y<=2600;y+=37){scrollTo(0,y);max=Math.max(max,Math.abs(nav.getBoundingClientRect().top-56));}
      return max<1&&getComputedStyle(nav).position==='sticky'&&!document.querySelector('[data-myt-channel-sticky-header]');}''')
    # The navigation row is centered in the window.
    links=page.evaluate('''()=>{const nav=document.querySelector('#myt-channel-nav').shadowRoot,items=[...nav.querySelectorAll('nav a,.channel-search > button')].filter(e=>e.getClientRects().length).map(e=>e.getBoundingClientRect());
      return {left:Math.min(...items.map(r=>r.left)),right:Math.max(...items.map(r=>r.right))};}''')
    assert abs((links['left']+links['right'])/2-width/2)<=2,(links,width)
    page.evaluate('window.scrollTo(0,0)')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # The owned navigation sits right below the header, the native toolbar is gone.
    nav=page.locator('#myt-channel-nav')
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_be_visible()
    assert nav.bounding_box()['y']>=own.bounding_box()['y']+own.bounding_box()['height']-1
    expect(own.locator('.myt-ch-actions #subscribe')).to_be_visible()
    page.close()
    print(f'PASS live tabbed header: owned header in the native profile slot, centered navigation pinned by CSS: {width}px',flush=True)


def click_more(page):
    page.locator('#myt-channel-description .more').click()
    dialog=page.locator('#myt-channel-description .full')
    expect(dialog).to_be_visible()
    expect(dialog.locator('.full-text')).not_to_be_empty()
    dialog.locator('.close').click()


def header(browser,legacy,width,dark):
    page=setup(browser,'/@JoeSpeen/videos',fixture(legacy),width=width,native_dark=dark)
    stats=page.locator('#myt-channel-stats')
    expect(stats).to_be_visible()
    expect(stats.locator('.row')).to_have_text('@JoeSpeen·2.24 M·2.4 K')
    expect(stats.locator('svg')).to_have_count(2)
    expect(stats.locator('[data-kind=subscribers]')).to_have_attribute('aria-label','2.24 M subscribers')
    expect(page.locator('yt-channel-external-link-view-model')).to_be_hidden()
    expect(page.locator('#author-description')).to_have_text('Пщщ! Я Joe Speen, а это мой канал.')
    assert 'Mono' in page.locator('#myt-channel-description .summary').evaluate('e=>getComputedStyle(e).fontFamily')
    expect(page.locator('#myt-channel-header h1')).to_have_text('Joe Speen — Мой канал')
    # The owned header shows the name and avatar; the native profile is hidden
    # and YouTube's subscribe control is the only native part, in its slot.
    expect(page.locator('#channel-header-container')).to_be_hidden()
    expect(page.locator('#myt-channel-header .myt-ch-actions #subscribe')).to_be_visible()
    expect(page.locator('#subscribe')).to_have_text('Subscribe')
    expect(page.locator('#description-more')).to_have_text('More')
    # Subscribe sits on the title row, right of the channel name, and the
    # avatar is one and a half times its native size.
    title=page.locator('#myt-channel-header h1').bounding_box();button=page.locator('#subscribe').bounding_box()
    assert button['x']>=title['x']+title['width']-1 and abs(button['y']+button['height']/2-title['y']-title['height']/2)<title['height']/2,(title,button)
    avatar=page.locator('#myt-channel-header .myt-ch-avatar').bounding_box()
    assert abs(avatar['width']-(300 if width>600 else 120))<1,avatar
    click_more(page)
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


def links_and_more(browser):
    variants=[
        '<yt-attribution-view-model class="ytAttributionViewModelHost">{link}</yt-attribution-view-model>',
        '<div class="yt-attribution-view-model-wiz__host">{link}</div>',
        '<div class="native-link-row">{link}</div>',
    ]
    link='<a id="external-link" href="https://www.youtube.com/redirect?event=channel_header&amp;q=https%3A%2F%2Ft.me%2Fjoe_speen_youtube">t.me/joe_speen_youtube</a><button id="more-links">and 5 more links</button>'
    for width in (1440,900,390):
        for wrapper in variants:
            body=fixture().replace('<yt-channel-external-link-view-model><a href="https://t.me/joe_speen_youtube">t.me/joe_speen_youtube и ещё 5 ссылок</a></yt-channel-external-link-view-model>',wrapper.format(link=link))
            page=setup(browser,'/@JoeSpeen/videos',body,width=width,native_dark=True)
            expect(page.locator('#external-link')).to_be_hidden()
            expect(page.locator('#more-links')).to_be_hidden()
            more=page.locator('#myt-channel-description .more')
            expect(more).to_be_visible()
            author=page.locator('#myt-channel-description .summary').bounding_box()
            label=page.locator('#myt-channel-description .more').bounding_box()
            assert 3<=label['y']-author['y']-author['height']<=5,(width,author,label)
            assert more.bounding_box()['x']+more.bounding_box()['width']<=width+1
            click_more(page)
            assert page.evaluate('__more')==1
            expect(page.locator('#subscribe')).to_be_visible()
            page.locator('#external-link').evaluate('e=>{const row=e.parentElement,copy=row.cloneNode(true);copy.removeAttribute("data-myt-channel-source");row.replaceWith(copy)}')
            expect(page.locator('#external-link')).to_be_hidden()
            page.evaluate('__setEnabled(false)')
            expect(page.locator('#external-link')).to_be_visible()
            expect(page.locator('#more-links')).to_be_visible()
            page.locator('#description-more').click()
            assert page.evaluate('__more')==2
            page.close()
        print(f'PASS external-link wrappers hidden, More separated below description/clickable, native restoration: {width}px',flush=True)


def assert_owned_description(page,width):
    host=page.locator('#myt-channel-description')
    expect(host).to_be_visible()
    summary=host.locator('.summary')
    button=host.locator('.more')
    expect(summary).to_be_visible()
    expect(button).to_be_visible()
    result=summary.evaluate("""e=>{
        const range=document.createRange();range.selectNodeContents(e);
        const rects=[...range.getClientRects()],clipped=[];
        for(let parent=e;parent;parent=parent.parentElement||parent.getRootNode().host){
            const style=getComputedStyle(parent),box=parent.getBoundingClientRect();
            if(/hidden|clip/.test(style.overflowY)&&rects.some(r=>r.top<box.top-1||r.bottom>box.bottom+1))clipped.push(parent.tagName);
        }
        return {clipped,mask:getComputedStyle(e).maskImage,background:getComputedStyle(e).backgroundImage};
    }""")
    assert not result['clipped'],result
    assert result['mask']=='none' and result['background']=='none',result
    text_box=summary.bounding_box();button_box=button.bounding_box();box=host.bounding_box()
    assert 3<=button_box['y']-text_box['y']-text_box['height']<=5,(text_box,button_box)
    assert box['x']>=-1 and box['x']+box['width']<=width+1,box
    assert button_box['y']+button_box['height']<=box['y']+box['height'],(box,button_box)


def preview_descenders(browser):
    for width in (1440,900,390):
        for text_class in ('ytDescriptionPreviewViewModelTruncatedText','yt-description-preview-view-model-wiz__truncated-text'):
            body=fixture().replace('ytDescriptionPreviewViewModelTruncatedText',text_class)
            body+=f'<style>.{text_class}{{height:16px;max-height:16px;line-height:16px}}</style>'
            page=setup(browser,'/@JoeSpeen/videos',body,width=width,native_dark=True)
            page.locator('#author-description').evaluate('e=>e.textContent="SUBSCRIBE FOR A COOKIE! gypqj_ уфру"')
            assert_owned_description(page,width)
            expect(page.locator('.'+text_class)).to_be_hidden()
            click_more(page)
            assert page.evaluate('__more')==1
            page.close()
        print(f'PASS native preview height cannot clip letter descenders; More remains functional: {width}px',flush=True)


def nested_preview(browser):
    preview='''<div class="native-preview-shell" style="width:calc(100% - 48px);height:22px;max-height:22px;overflow:hidden">
      <yt-description-preview-view-model style="overflow:hidden;mask-image:linear-gradient(to right,black 60%,transparent)">
      <div class="native-preview-inner" style="height:22px;max-height:22px;overflow:clip">
      <div class="native-preview-line">
        <yt-attributed-string class="ytDescriptionPreviewViewModelTruncatedText" style="height:16px;max-height:16px;overflow:hidden;mask-image:linear-gradient(to right,black,transparent)"><span id="author-description">SUBSCRIBE FOR A COOKIE! gypq_</span></yt-attributed-string>
        <span class="native-more-shell" style="display:block;height:18px;max-height:18px;overflow:hidden"><button id="description-more" class="ytDescriptionPreviewViewModelMoreButton" style="height:18px;max-height:18px;overflow:hidden;background-image:linear-gradient(to right,transparent,#111)" onclick="window.__more=(window.__more||0)+1"><span id="more-label" style="mask-image:linear-gradient(to right,black,transparent)">...more</span></button></span>
      </div></div></yt-description-preview-view-model></div>'''
    body=fixture()
    start=body.index('<yt-description-preview-view-model>')
    end=body.index('</yt-description-preview-view-model>',start)+len('</yt-description-preview-view-model>')
    body=body[:start]+preview+body[end:]
    body+='''<style>
      .ytDescriptionPreviewViewModelMoreButton::before{content:"";position:absolute;inset:0;background:linear-gradient(to right,transparent,#111)}
      .ytDescriptionPreviewViewModelTruncatedText::after{content:"";position:absolute;inset:0;background:linear-gradient(to right,transparent,#111)}
      .native-preview-shell::after{content:"";position:absolute;inset:0;background:linear-gradient(to right,transparent,#111);pointer-events:none}
      </style>'''
    for width in (1440,900,390):
        page=setup(browser,'/@JoeSpeen/videos',body,width=width,native_dark=True)
        assert_owned_description(page,width)
        expect(page.locator('.native-preview-shell')).to_be_hidden()
        # Native masks and clipping remain on hidden source nodes, so the new
        # block proves it does not depend on patching the old view model.
        assert page.locator('yt-description-preview-view-model').evaluate('e=>getComputedStyle(e).maskImage')!='none'
        click_more(page)
        assert page.evaluate('__more')==1
        page.wait_for_timeout(100)
        assert_stable(page)
        page.screenshot(path=f'/tmp/yt-min-preview-{width}.png')
        page.evaluate('__setEnabled(false)')
        assert page.locator('yt-description-preview-view-model').evaluate('e=>getComputedStyle(e).maskImage')!='none'
        page.close()
        print(f'PASS independent description bypasses nested native clamps/masks and opens native More: {width}px',flush=True)


def more_text_spacing(browser):
    for width in (1440,900,390):
        body=re.sub(r'<button id="description-more".*?</button>', '<span id="description-more" class="ytDescriptionPreviewViewModelMoreText"><span id="more-label">...more</span></span>',fixture())
        body=body.replace('<yt-description-preview-view-model>', '<yt-description-preview-view-model role="button" onclick="window.__more=(window.__more||0)+1">')
        page=setup(browser,'/@JoeSpeen/videos',body,width=width,native_dark=True)
        author=page.locator('#myt-channel-description .summary').bounding_box()
        more=page.locator('#myt-channel-description .more').bounding_box()
        assert 3<=more['y']-author['y']-author['height']<=5,(width,author,more)
        click_more(page)
        assert page.evaluate('__more')==1
        page.close()
    print('PASS explicit description/More spacing for delegated More text controls at desktop/tablet/mobile widths',flush=True)


def description_updates(browser):
    for width,dark in ((1440,False),(390,True)):
        page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=dark)
        host=page.locator('#myt-channel-description')
        expect(host).to_have_count(1)
        expect(page.locator('yt-description-preview-view-model')).to_be_hidden()
        text='Текст автора 😀 сохраняется. '+('Длинное описание должно переноситься без обрезания букв. '*12)
        page.locator('#author-description').evaluate('(e,text)=>e.textContent=text',text)
        expect(host.locator('.summary')).to_contain_text('Текст автора 😀 сохраняется.')
        shown=host.locator('.summary').inner_text()
        assert shown==text.strip(),shown
        assert host.locator('.summary').evaluate('e=>getComputedStyle(e).textOverflow==="ellipsis"&&getComputedStyle(e).whiteSpace==="nowrap"&&e.scrollWidth>e.clientWidth&&e.getBoundingClientRect().height<=parseFloat(getComputedStyle(e).lineHeight)+1')
        assert_owned_description(page,width)
        click_more(page)
        assert page.evaluate('__more')==1
        # The visible component must use the latest native opener after restamps.
        for i in range(3):
            page.locator('yt-description-preview-view-model').evaluate('''e=>{
                const copy=e.cloneNode(true);copy.removeAttribute('data-myt-channel-description-source');
                copy.querySelector('button').setAttribute('onclick','window.__more=(window.__more||0)+10');e.replaceWith(copy);
            }''')
            expect(host).to_have_count(1)
            click_more(page)
            assert page.evaluate('__more')==1+(i+1)*10
        page.locator('yt-description-preview-view-model').evaluate('e=>{window.__sourceDescription=e;e.remove()}')
        expect(host).to_have_count(0)
        page.locator('#channel-header-container').evaluate('e=>e.append(window.__sourceDescription)')
        expect(host).to_have_count(1)
        page.wait_for_timeout(100)
        assert_stable(page)
        page.evaluate('__setEnabled(false)')
        expect(host).to_have_count(0)
        expect(page.locator('yt-description-preview-view-model')).to_be_visible()
        page.evaluate('__setEnabled(true)')
        expect(host).to_have_count(1)
        expect(page.locator('yt-description-preview-view-model')).to_be_hidden()
        page.close()
    print('PASS isolated description updates, Unicode excerpt, native opener restamps, removal and enable/disable restoration',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for legacy in (False,True):
            for width,dark in ((1440,True),(390,False)):
                header(browser,legacy,width,dark)
        redirects(browser)
        navigation(browser)
        links_and_more(browser)
        preview_descenders(browser)
        nested_preview(browser)
        more_text_spacing(browser)
        description_updates(browser)
        for width in (1440,390):
            tabbed_header(browser,width)
        browser.close()
