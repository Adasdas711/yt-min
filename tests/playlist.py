"""Standalone playlist page layout, native action and continuation regressions."""
import base64
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, assert_stable, navigate_spa


def cover(title='MEIN NAME IST CARI'):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#49744e"/><path d="M0 245 640 100v260H0Z" fill="#243d2a"/><circle cx="495" cy="160" r="95" fill="#c4b195"/><text x="28" y="90" fill="white" font-size="38" font-family="sans-serif" font-weight="bold">{title}</text><text x="28" y="302" fill="#ddd" font-size="24" font-family="sans-serif">EASY GERMAN</text></svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()


def row(number):
    return f'''<ytd-playlist-video-renderer data-row="{number}"><div id="container"><div id="index-container">{number+1}</div><div id="content"><a id="thumbnail" href="/watch?v=video{number}&list=PLfixture" onclick="event.preventDefault();window.__visit=this.href"><ytd-thumbnail><img src="{cover()}"></ytd-thumbnail></a><div id="meta"><h3><a id="video-title" href="/watch?v=video{number}&list=PLfixture" onclick="event.preventDefault();window.__visit=this.href">{['Introduce Yourself in Slow German (for Absolute Beginners)','Learn Basic German Greetings and Farewells in Slow German','Top 50 Everyday Objects in Slow German','Our Morning Routine in Slow German'][number%4]}</a></h3><div id="byline-container"><a href="/@easygerman" onclick="event.preventDefault();window.__channel=true">Easy German</a></div><div id="video-info">3.2m · 24 July 2024</div></div></div></div><div id="menu"><button aria-label="Video actions" onclick="window.__menu=(window.__menu||0)+1">⋯</button></div></ytd-playlist-video-renderer>'''


def body(legacy=False, count=12):
    summary=f'''<div class="immersive-header-background" style="position:absolute;inset:0;background:linear-gradient(#658938,#071a0a)"></div><div id="content" class="page-header-sidebar" style="position:fixed;left:240px;top:80px;width:360px;height:calc(100vh - 80px);background:linear-gradient(#658938,#071a0a);color:white"><ytd-thumbnail id="hero-image"><img src="{cover()}"></ytd-thumbnail><h1 id="title">German A1 | For Absolute Beginners</h1><div id="byline"><a href="/@easygerman" onclick="event.preventDefault();window.__channel=true">Easy German</a></div><p id="stats">64 videos · 10,377,110 views</p><p id="description">New at learning German? Start here! A collection of useful conversations, stories and everyday language.</p><div id="action-buttons"><button onclick="window.__play=true">Play all</button><button onclick="window.__shuffle=true">Shuffle</button><button aria-label="Playlist actions" onclick="window.__playlistMenu=true">⋯</button></div></div>'''
    list_html='<ytd-playlist-video-list-renderer><div id="contents">'+''.join(row(n) for n in range(count))+'''<ytd-continuation-item-renderer><button id="load-more" onclick="window.__continued=true">Load more</button></ytd-continuation-item-renderer></div></ytd-playlist-video-list-renderer>'''
    if legacy:
        tree=f'<div id="contents"><ytd-two-column-browse-results-renderer><div id="primary"><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer>{list_html}</ytd-item-section-renderer></div></ytd-section-list-renderer></div><div id="secondary"><ytd-playlist-sidebar-renderer>{summary}</ytd-playlist-sidebar-renderer></div></ytd-two-column-browse-results-renderer></div>'
    else:
        tree=f'<div id="header"><ytd-playlist-header-renderer>{summary}</ytd-playlist-header-renderer></div><div id="contents" style="margin-left:400px;width:calc(100% - 400px)"><ytd-two-column-browse-results-renderer><div id="primary"><ytd-section-list-renderer><ytd-item-section-renderer>{list_html}</ytd-item-section-renderer></ytd-section-list-renderer></div></ytd-two-column-browse-results-renderer></div>'
    return '''<style>
      ytd-browse,ytd-playlist-header-renderer,ytd-playlist-sidebar-renderer,ytd-playlist-video-list-renderer,ytd-playlist-video-renderer,ytd-two-column-browse-results-renderer {display:block;font-family:Arial,sans-serif}
      ytd-playlist-header-renderer,ytd-playlist-sidebar-renderer {min-height:100vh;background:linear-gradient(#658938,#071a0a)}
      ytd-playlist-video-renderer {padding:8px}ytd-playlist-video-renderer #container,ytd-playlist-video-renderer #content {display:flex}ytd-playlist-video-renderer #menu {float:right}
      ytd-playlist-video-renderer a#thumbnail {width:160px;flex:none}ytd-playlist-video-renderer img {width:160px;height:90px}
      a {color:inherit;text-decoration:none}button {font:inherit}#hero-image img {width:360px}
    </style><ytd-app>'''+MASTHEAD+'<ytd-page-manager><ytd-browse page-subtype="playlist">'+tree+'</ytd-browse></ytd-page-manager></ytd-app>'


def check(browser, legacy, width, dark):
    page=setup(browser,'/playlist?list=PLfixture',body(legacy),width=width,native_dark=not dark,theme='dark' if dark else 'light')
    expect(page.locator('html')).to_have_attribute('data-myt-page','playlist')
    expect(page.locator('[data-myt-playlist-layout]')).to_have_count(1)
    summary=page.locator('[data-myt-playlist-summary]')
    playlist=page.locator('[data-myt-playlist-list]')
    a,b=summary.bounding_box(),playlist.bounding_box()
    assert a and b,(a,b)
    rail=page.locator('[data-myt-playlist-layout]').bounding_box()
    assert abs(rail['x']*2+rail['width']-width)<1,rail
    assert (a['x']+a['width']<=b['x']-12) if width>900 else (a['y']+a['height']<=b['y']-12),(a,b)
    if width>900:assert abs(a['y']-b['y'])<1,(a,b)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,a,b)
    neutral=summary.evaluate('''e=>{const s=getComputedStyle(e);return {color:s.backgroundColor,image:s.backgroundImage,height:e.getBoundingClientRect().height};}''')
    assert neutral['image']=='none' and neutral['color']==('rgb(36, 36, 42)' if dark else 'rgb(241, 241, 244)'),neutral
    assert neutral['height']<700,neutral
    for row_node in page.locator('ytd-playlist-video-renderer').all():
        rect=row_node.bounding_box()
        assert rect and rect['x']>=b['x']-1 and rect['x']+rect['width']<=b['x']+b['width']+1,rect
        thumb=row_node.locator('a#thumbnail').bounding_box();title=row_node.locator('#meta').bounding_box()
        assert thumb['x']+thumb['width']<=title['x'],(thumb,title)
    summary.get_by_role('button',name='Play all',exact=True).click()
    assert page.evaluate('__play')
    summary.get_by_role('button',name='Shuffle',exact=True).click()
    assert page.evaluate('__shuffle')
    summary.get_by_role('button',name='Playlist actions').click()
    assert page.evaluate('__playlistMenu')
    # Preserve source nodes/parents, playlist-context URLs, menus and pagination.
    page.evaluate('''() => {window.__sourceRow=document.querySelector('ytd-playlist-video-renderer');window.__sourceParent=__sourceRow.parentElement;}''')
    playlist.locator('#video-title').first.click()
    assert 'v=video0' in page.evaluate('__visit') and 'list=PLfixture' in page.evaluate('__visit')
    playlist.get_by_role('button',name='Video actions').first.click()
    assert page.evaluate('__menu')==1
    page.locator('#load-more').click()
    assert page.evaluate('__continued')
    playlist.locator('#contents').evaluate('(e,html)=>e.insertAdjacentHTML("beforeend",html)',row(12))
    expect(playlist.locator('ytd-playlist-video-renderer')).to_have_count(13)
    assert page.evaluate('__sourceRow===document.querySelector("ytd-playlist-video-renderer")&&__sourceParent===__sourceRow.parentElement')
    # A creator-color update must not reintroduce a tinted panel or gradient.
    summary.evaluate("e=>{e.style.background='linear-gradient(red,blue)';e.querySelector('.page-header-sidebar').style.background='linear-gradient(magenta,green)';}")
    expect(summary).to_have_css('background-color',neutral['color'])
    expect(summary).to_have_css('background-image','none')
    assert_stable(page)
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=f'/tmp/yt-min-playlist-page-{legacy}-{width}-{dark}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-playlist-layout],[data-myt-playlist-summary],[data-myt-playlist-wrapper]')).to_have_count(0)
    assert 'linear-gradient' in page.locator('ytd-playlist-header-renderer,ytd-playlist-sidebar-renderer').evaluate('e=>getComputedStyle(e).backgroundImage')
    page.evaluate('__setEnabled(true)')
    expect(page.locator('[data-myt-playlist-layout]')).to_have_count(1)
    navigate_spa(page,'/@easygerman/videos')
    # Retain outgoing styles until the actual channel DOM is mounted.
    expect(page.locator('[data-myt-playlist-layout]')).to_have_count(1)
    page.evaluate('''() => {document.querySelector('ytd-browse').hidden=true;document.querySelector('ytd-page-manager').insertAdjacentHTML('beforeend','<ytd-browse page-subtype="channels"><div id="contents">Channel videos</div></ytd-browse>');}''')
    expect(page.locator('[data-myt-playlist-layout]')).to_have_count(0)
    page.close()
    print(f'PASS standalone playlist: legacy={legacy}, width={width}, dark={dark}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for legacy in [False,True]:
            for width in [2016,1440,900,390]:
                check(browser,legacy,width,True)
        for legacy in [False,True]:
            check(browser,legacy,1440,False)
        empty=body().replace('<ytd-playlist-video-list-renderer>','<ytd-playlist-video-list-renderer hidden>')
        empty=empty.replace('</ytd-playlist-video-list-renderer>','</ytd-playlist-video-list-renderer><ytd-message-renderer id="empty-playlist">No videos yet</ytd-message-renderer>')
        page=setup(browser,'/playlist?list=empty',empty,native_dark=True)
        expect(page.locator('#empty-playlist')).to_have_attribute('data-myt-playlist-list','')
        expect(page.locator('#empty-playlist')).to_be_visible()
        page.locator('ytd-playlist-video-list-renderer').evaluate('e=>{e.hidden=false;document.querySelector("#empty-playlist").remove();}')
        expect(page.locator('ytd-playlist-video-list-renderer')).to_have_attribute('data-myt-playlist-list','')
        assert_stable(page)
        page.close()
        page=setup(browser,'/', '<ytd-app><ytd-page-manager></ytd-page-manager></ytd-app>')
        expect(page.locator('#myt-home')).to_be_visible()
        navigate_spa(page,'/playlist?list=unavailable')
        page.locator('ytd-page-manager').evaluate('e=>e.innerHTML=\'<ytd-browse page-subtype="playlist"><ytd-message-renderer>Playlist unavailable</ytd-message-renderer></ytd-browse>\'')
        expect(page.locator('#myt-home')).to_have_count(0)
        expect(page.locator('ytd-message-renderer')).to_be_visible()
        page.close()
        print('PASS empty/late-loaded playlists and unavailable-playlist SPA destination',flush=True)
        direct=body(count=300).replace('<div id="header"><ytd-playlist-header-renderer>','<ytd-playlist-header-renderer>').replace('</ytd-playlist-header-renderer></div>','</ytd-playlist-header-renderer>')
        page=setup(browser,'/playlist?list=long',direct,native_dark=True)
        page.evaluate('''() => {
          window.__fullScans=0;const query=Element.prototype.querySelectorAll;
          Element.prototype.querySelectorAll=function(selector){if(selector==='*')__fullScans++;return query.call(this,selector);};
        }''')
        page.mouse.move(8,400);page.mouse.wheel(0,300)
        page.wait_for_function('scrollY>=300')
        assert page.evaluate('__fullScans')==0
        assert abs(page.locator('[data-myt-playlist-summary-slot]').bounding_box()['y']-84)<1
        page.set_viewport_size({'width':1440,'height':500})
        page.evaluate('window.scrollTo(0,0)')
        summary=page.locator('[data-myt-playlist-summary-slot]')
        page.mouse.move(summary.bounding_box()['x']+80,250);page.mouse.wheel(0,100)
        page.wait_for_function('document.querySelector("[data-myt-playlist-summary-slot]").scrollTop>0')
        assert page.evaluate('scrollY')==0
        assert_stable(page)
        page.close()
        print('PASS long-playlist gutter scrolling avoids full-tree scans; short-window summary scrolls independently',flush=True)
        browser.close()


if __name__=='__main__':
    main()
