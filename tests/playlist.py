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
    neutral=summary.locator('.panel').evaluate('''e=>{const s=getComputedStyle(e);return {color:s.backgroundColor,image:s.backgroundImage,height:e.getBoundingClientRect().height};}''')
    assert neutral['image']=='none' and neutral['color']==('rgb(36, 36, 42)' if dark else 'rgb(241, 241, 244)'),neutral
    assert neutral['height']<=max(700,page.viewport_size['height']-120),neutral
    for row_node in page.locator('ytd-playlist-video-renderer').all():
        rect=row_node.bounding_box()
        assert rect and rect['x']>=b['x']-1 and rect['x']+rect['width']<=b['x']+b['width']+1,rect
        owned=row_node.locator('[data-myt-owned-playlist-card=video]')
        thumb=owned.locator('a.cover').bounding_box();title=owned.locator('.meta').bounding_box()
        assert thumb['x']+thumb['width']<=title['x'],(thumb,title)
    summary.get_by_role('button',name='Play all',exact=True).click()
    assert page.evaluate('__play')
    summary.get_by_role('button',name='Shuffle',exact=True).click()
    assert page.evaluate('__shuffle')
    summary.get_by_role('button',name='Playlist actions').click()
    assert page.evaluate('__playlistMenu')
    # Preserve source nodes/parents, playlist-context URLs, menus and pagination.
    page.evaluate('''() => {window.__sourceRow=document.querySelector('ytd-playlist-video-renderer');window.__sourceParent=__sourceRow.parentElement;}''')
    playlist.locator('[data-myt-owned-playlist-card=video] a.title').first.click()
    assert 'v=video0' in page.evaluate('__visit') and 'list=PLfixture' in page.evaluate('__visit')
    playlist.get_by_role('button',name='Video actions').first.click()
    assert page.evaluate('__menu')==1
    page.locator('#load-more').click()
    assert page.evaluate('__continued')
    playlist.locator('#contents').evaluate('(e,html)=>e.insertAdjacentHTML("beforeend",html)',row(12))
    expect(playlist.locator('ytd-playlist-video-renderer')).to_have_count(13)
    assert page.evaluate('__sourceRow===document.querySelector("ytd-playlist-video-renderer")&&__sourceParent===__sourceRow.parentElement')
    # A creator-color update must not reintroduce a tinted panel or gradient.
    page.locator('ytd-playlist-header-renderer,ytd-playlist-sidebar-renderer').evaluate("e=>{e.style.background='linear-gradient(red,blue)';e.querySelector('.page-header-sidebar').style.background='linear-gradient(magenta,green)';}")
    expect(summary.locator('.panel')).to_have_css('background-color',neutral['color'])
    expect(summary.locator('.panel')).to_have_css('background-image','none')
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


def mixed_markup(browser, width=1440, modern_rows=False):
    html=body().replace('ytd-playlist-header-renderer','yt-page-header-renderer')
    legacy=body(True).split('<ytd-playlist-sidebar-renderer>',1)[1].split('</ytd-playlist-sidebar-renderer>',1)[0]
    html=html.replace('</ytd-browse>', '<ytd-playlist-sidebar-renderer class="inactive-legacy">'+legacy+'</ytd-playlist-sidebar-renderer></ytd-browse>')
    html+='<style>yt-page-header-renderer{display:block}.inactive-legacy{display:none}img{width:100vw!important;height:70vh!important;max-width:none} .page-header-sidebar{position:fixed!important;width:100vw!important;height:100vh!important;background:linear-gradient(green,black)!important}</style>'
    if modern_rows:
        html=html.replace('<ytd-playlist-video-list-renderer>','<div id="modern-list">').replace('</ytd-playlist-video-list-renderer>','</div>').replace('ytd-playlist-video-renderer','yt-lockup-view-model')
    page=setup(browser,'/playlist?list=PLfixture',html,width=width,native_dark=True)
    summary=page.locator('#myt-playlist-summary')
    expect(summary).to_have_count(1)
    expect(summary.locator('h1')).to_have_text('German A1 | For Absolute Beginners')
    expect(page.locator('.inactive-legacy')).to_be_hidden()
    expect(page.locator('[data-myt-owned-playlist-card=video]')).to_have_count(12)
    expect(summary.locator('.panel')).to_have_css('background-color','rgb(36, 36, 42)')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for img in page.locator('img').all():
        if img.is_visible():assert img.bounding_box()['width']<=max(340,width-32),img.bounding_box()
    cards=page.locator('[data-myt-owned-playlist-card=video]')
    previous=-1
    for card in cards.all():
        rect=card.bounding_box();assert rect['y']>previous;previous=rect['y']
    summary.get_by_role('button',name='Play all',exact=True).click()
    assert page.evaluate('__play')
    cards.first.locator('a.title').click()
    assert 'v=video0' in page.evaluate('__visit')
    # Native menu commands use an invisible top-layer anchor at the owned button.
    page.locator('yt-page-header-renderer button[aria-label="Playlist actions"]').evaluate('e=>e.onclick=function(){window.__menuBox={x:this.getBoundingClientRect().x,y:this.getBoundingClientRect().y};}')
    menu=summary.get_by_role('button',name='Playlist actions');menu.click()
    expected=menu.bounding_box();actual=page.evaluate('__menuBox')
    assert abs(actual['x']-expected['x'])<1 and abs(actual['y']-expected['y'])<1,(actual,expected)
    assert_stable(page)
    page.screenshot(path=f'/tmp/yt-min-owned-playlist-mixed-{width}-{modern_rows}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-owned-playlist-card],[data-myt-playlist-row],[data-myt-playlist-native-row-part],[data-myt-playlist-action-anchor]')).to_have_count(0)
    expect(page.locator('.inactive-legacy')).to_be_hidden()
    page.close()
    print(f'PASS mixed native versions and hostile styles: width={width}, modern_rows={modern_rows}',flush=True)


def lifecycle(browser):
    page=setup(browser,'/playlist?list=PLfixture',body(),native_dark=True)
    expect(page.locator('[data-myt-owned-playlist-card=video]')).to_have_count(12)
    # Native header restamping must update data without recreating owned cards.
    page.evaluate('''() => {
      window.__summary=document.querySelector('#myt-playlist-summary');
      window.__first=document.querySelector('[data-myt-owned-playlist-card=video]');
      const header=document.querySelector('ytd-playlist-header-renderer'),next=header.cloneNode(true);
      next.querySelector('h1').textContent='Updated playlist';header.replaceWith(next);
    }''')
    expect(page.locator('#myt-playlist-summary h1')).to_have_text('Updated playlist')
    assert page.evaluate('__summary===document.querySelector("#myt-playlist-summary")&&__first===document.querySelector("[data-myt-owned-playlist-card=video]")')
    # Native row rerenders preserve the owned row and reconnect action sources.
    page.evaluate('''() => {
      const container=document.querySelector('ytd-playlist-video-renderer #container'),next=container.cloneNode(true);
      next.querySelector('#video-title').textContent='Updated video';container.replaceWith(next);
    }''')
    expect(page.locator('[data-myt-owned-playlist-card=video] a.title').first).to_have_text('Updated video')
    assert page.evaluate('__first===document.querySelector("[data-myt-owned-playlist-card=video]")')
    page.locator('[data-myt-owned-playlist-card=video] a.title').first.click()
    assert 'v=video0' in page.evaluate('__visit')
    # Keep the native continuation in flow for its original intersection observer.
    page.evaluate('''html => {
      const continuation=document.querySelector('ytd-continuation-item-renderer');
      window.__continuedByIntersection=0;
      window.__continuationObserver=new IntersectionObserver(entries=>{
        if(entries.some(entry=>entry.isIntersecting)){
          __continuedByIntersection++;continuation.insertAdjacentHTML('beforebegin',html);
          __continuationObserver.disconnect();
        }
      });
      __continuationObserver.observe(continuation);
    }''',row(12))
    page.locator('ytd-continuation-item-renderer').scroll_into_view_if_needed()
    expect(page.locator('[data-myt-owned-playlist-card=video]')).to_have_count(13)
    assert page.evaluate('__continuedByIntersection')==1
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-owned-playlist-card],[data-myt-playlist-native-row-part]')).to_have_count(0)
    expect(page.locator('ytd-playlist-header-renderer h1')).to_be_visible()
    page.close()
    print('PASS header/row restamping preserves owned cards; native intersection pagination remains active',flush=True)


def menu_position(browser,width,dark):
    # Native metadata can contain a channel byline as well as a separate author
    # link. Preserve real counts/dates while removing both author appearances.
    html=body().replace('<div id="video-info">3.2m · 24 July 2024</div>','<div id="video-info"><a href="/@easygerman">Easy German</a> · 3.2m · 24 July 2024</div>')
    html+='<style>[data-myt-owned-playlist-card="summary"]{background:transparent!important;border:0!important}</style>'
    page=setup(browser,'/playlist?list=PLfixture',html,width=width,theme='dark' if dark else 'light',native_dark=not dark)
    summary=page.locator('#myt-playlist-summary')
    expect(summary.locator('.panel')).to_have_css('background-color','rgb(36, 36, 42)' if dark else 'rgb(241, 241, 244)')
    expect(summary.locator('.owner a')).to_have_text('Easy German')
    cards=page.locator('[data-myt-owned-playlist-card=video]')
    expect(cards.locator('.owner')).to_have_count(0)
    expect(cards.first.locator('.metadata')).to_have_text('3.2m · 24 July 2024')
    page.locator('ytd-playlist-video-renderer #video-info').first.evaluate('e=>e.textContent="Easy German"')
    expect(cards.first.locator('.metadata')).to_be_hidden()
    page.evaluate('''() => {
      const popups=document.createElement('ytd-popup-container');document.body.append(popups);
      window.__openNativeMenu=() => {
        setTimeout(()=>{
          popups.innerHTML='<tp-yt-iron-dropdown style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:280px"><ytd-menu-popup-renderer role="menu" style="display:block;padding:16px;border-radius:16px;background:#24242a;color:white"><button role="menuitem" onclick="window.__menuCommand=true;this.closest(\\\'tp-yt-iron-dropdown\\\').hidden=true">Shuffle</button><p>Playlist actions</p></ytd-menu-popup-renderer></tp-yt-iron-dropdown>';
          document.querySelector('tp-yt-iron-dropdown').dataset.originalStyle=document.querySelector('tp-yt-iron-dropdown').getAttribute('style');
        },10);
      };
      document.querySelector('ytd-playlist-header-renderer button[aria-label="Playlist actions"]').onclick=__openNativeMenu;
      document.querySelector('ytd-playlist-video-renderer #menu button').onclick=__openNativeMenu;
      document.addEventListener('keydown',event=>{if(event.key==='Escape')document.querySelector('tp-yt-iron-dropdown')?.setAttribute('hidden','');});
    }''')
    for control in [summary.get_by_role('button',name='Playlist actions'),cards.first.get_by_role('button',name='Video actions')]:
        control.click()
        popup=page.locator('tp-yt-iron-dropdown')
        expect(popup).to_be_visible()
        expect(control).to_have_attribute('aria-expanded','true')
        button,menu=control.bounding_box(),popup.bounding_box()
        assert menu['x']>=8 and menu['x']+menu['width']<=width-8,(button,menu)
        assert abs(menu['y']-button['y']-button['height']-8)<1 or abs(menu['y']+menu['height']-button['y']+8)<1,(button,menu)
        # Late Polymer layout updates must not move the menu back to the center.
        popup.evaluate('e=>{e.style.left="50%";e.style.top="50%";e.style.transform="translate(-50%,-50%)";}')
        page.wait_for_function('getComputedStyle(document.querySelector("tp-yt-iron-dropdown")).transform==="none"')
        page.screenshot(path=f'/tmp/yt-min-playlist22-menu-{width}-{dark}.png')
        popup.get_by_role('menuitem',name='Shuffle').click()
        assert page.evaluate('__menuCommand')
        expect(popup).to_be_hidden()
        expect(control).to_have_attribute('aria-expanded','false')
        assert popup.evaluate('e=>{const original=document.createElement("div");original.style.cssText=e.dataset.originalStyle;return [...original.style].every(name=>original.style.getPropertyValue(name)===e.style.getPropertyValue(name));}')
    summary.get_by_role('button',name='Playlist actions').click()
    expect(page.locator('tp-yt-iron-dropdown')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('tp-yt-iron-dropdown')).to_be_hidden()
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-owned-playlist-card]')).to_have_count(0)
    page.close()
    print(f'PASS playlist author removal and anchored native menus: width={width}, dark={dark}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for legacy in [False,True]:
            for width in [2016,1440,900,390]:
                check(browser,legacy,width,True)
        for legacy in [False,True]:
            check(browser,legacy,1440,False)
        for modern_rows in [False,True]:
            for width in [1440,390]:
                mixed_markup(browser,width,modern_rows)
        lifecycle(browser)
        for width in [1440,390]:
            for dark in [True,False]:
                menu_position(browser,width,dark)
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
