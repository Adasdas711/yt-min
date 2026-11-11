"""Browser regression checks using local YouTube DOM fixtures and mock storage.

Run: python tests/smoke.py (requires installed Playwright and Chromium).
No live YouTube requests or unpacked-extension installation are performed.
"""
import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = """<style>
* { box-sizing: border-box; } body { margin: 0; }
[hidden] { display: none !important; }
ytd-engagement-panel-section-list-renderer[visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN"] { display: none !important; }
ytd-app, ytd-page-manager, ytd-browse, ytd-rich-grid-renderer,
ytd-watch-flexy, ytd-reel-shelf-renderer, ytd-rich-item-renderer,
ytd-video-renderer, ytd-playlist-panel-renderer, ytd-playlist-panel-video-renderer,
ytd-comments, yt-tab-shape, tp-yt-paper-tab { display: block; }
ytd-masthead, ytd-watch-metadata, segmented-like-dislike-button-view-model,
ytd-segmented-like-dislike-button-renderer,
ytd-engagement-panel-section-list-renderer, ytd-video-primary-info-renderer,
ytd-video-secondary-info-renderer, ytd-search, ytd-section-list-renderer,
ytd-item-section-renderer, ytd-thumbnail, ytd-channel-renderer,
ytd-playlist-renderer, ytd-continuation-item-renderer,
yt-lockup-view-model { display: block; }
ytd-c4-tabbed-header-renderer, yt-image-banner-view-model,
ytd-banner-header-renderer, tp-yt-paper-tabs { display: block; }
ytd-page-manager { margin-left: 72px; }
#header, #contents, #primary, #secondary { min-height: 30px; }
video { width: 640px; height: 360px; object-fit: contain; }
ytd-masthead { height: 56px; font-family: Arial, sans-serif; }
html[dark] body { background: #0f0f0f; color: #f1f1f1; }
ytd-masthead > #container { height: 56px; display: flex; align-items: center; justify-content: space-between; }
ytd-masthead #start { display: flex; flex: 0 0 240px; width: 240px; }
ytd-masthead #logo { display: block; width: 100px; height: 24px; }
ytd-masthead #center { display: flex; flex: 0 1 640px; width: 640px; }
ytd-masthead #end { width: 240px; }
ytd-searchbox { display: block; width: 100%; }
ytd-searchbox #search-form { display: flex; width: 100%; }
ytd-searchbox #container { flex: 1; min-width: 0; }
ytd-searchbox #container, ytd-searchbox #search-input { display: flex; align-items: center; height: 100%; }
ytd-searchbox #search-input { width: 100%; }
ytd-searchbox input#search { width: 100%; min-width: 0; }
ytd-masthead input { border: 0; outline: none; background: transparent; font: inherit; }
ytd-masthead #logo { color: inherit; text-decoration: none; }
ytd-topbar-logo-renderer { display: block; width: 129px; padding: 16px; }
ytd-masthead #logo { width: 129px; padding: 16px; }
ytd-masthead #logo-icon { display: inline-block; width: 90px; height: 20px; }
yt-searchbox { display: block; width: 100%; }
.ytSearchboxComponentHost, .ytSearchboxComponentSearchForm { display: flex; width: 100%; }
.ytSearchboxComponentInputBox { display: flex; align-items: center; flex: 1; min-width: 0; }
.ytSearchboxComponentInput { width: 100%; min-width: 0; }
</style>"""

MASTHEAD = '''<ytd-masthead><div id="container"><div id="start"><ytd-topbar-logo-renderer><a id="logo" href="/" aria-label="YouTube"><span id="logo-icon"><svg viewBox="0 0 90 20" aria-hidden="true"><rect x="0" y="1" width="27" height="18" rx="5" fill="#ff0033"/><path d="m11 5 9 5-9 5z" fill="white"/><text x="31" y="16" font-family="Arial" font-weight="bold" font-size="15" fill="currentColor">YouTube</text></svg></span></a></ytd-topbar-logo-renderer></div>
  <div id="center"><ytd-searchbox><form id="search-form" action="/results" method="get"><div id="container"><div id="search-input"><input id="search" name="search_query" aria-label="Search"></div></div><button id="search-icon-legacy" type="submit" aria-label="Search"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="m15 15 5 5"/></svg></button></form></ytd-searchbox></div>
  <div id="end"><div id="buttons"><button id="create">Create</button><button id="avatar-btn">Account</button></div></div>
  <button id="voice-search-button">Voice</button></div></ytd-masthead>'''


def document(body="", title="(12) YouTube"):
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>{BASE}</head><body>{body}</body></html>'


MOCK = """(initial) => {
  window.__stored = initial;
  window.__storageListeners = [];
  window.chrome = {runtime: {}, storage: {
    local: {
      get: (key, cb) => cb(window.__stored),
      set: (value, cb) => {
        const old = {...window.__stored};
        Object.assign(window.__stored, value);
        const changes = Object.fromEntries(Object.entries(value).map(([key, newValue]) =>
          [key, {oldValue: old[key], newValue}]));
        for (const fn of window.__storageListeners)
          fn(changes, 'local');
        if (cb) cb();
      }
    },
    onChanged: {addListener: fn => window.__storageListeners.push(fn)}
  }};
  window.__setEnabled = enabled => chrome.storage.local.set({enabled});
}"""


def setup(browser, path="/", body="", enabled=None, width=1440, theme=None, native_dark=False, language="en", watch_ui=True, prune_data=False, runtime_id=None):
    page = browser.new_page(viewport={"width": width, "height": 960}, reduced_motion="reduce")
    if prune_data:
        page.add_init_script(path=str(ROOT / "src/content/search-data.js"))
        page.add_init_script(path=str(ROOT / "src/content/data-pruning.js"))
    page.route("https://www.youtube.com/**", lambda route: route.fulfill(
        status=200, content_type="text/html", body=document(body)))
    page.goto("https://www.youtube.com" + path)
    initial = {} if enabled is None else {"enabled": enabled}
    if theme is not None:
        initial["theme"] = theme
    page.evaluate(MOCK, initial)
    if runtime_id:
        page.evaluate("id=>{chrome.runtime.id=id;chrome.runtime.getURL=path=>'chrome-extension://'+id+'/'+path;}",runtime_id)
    page.evaluate("language => document.documentElement.lang = language", language)
    if native_dark:
        page.evaluate("document.documentElement.setAttribute('dark', '')")
    page.add_style_tag(path=str(ROOT / "src/styles/styles.css"))
    page.add_script_tag(path=str(ROOT / "src/content/ads.js"))
    if watch_ui:
        page.add_script_tag(path=str(ROOT / "src/content/watch.js"))
    page.add_script_tag(path=str(ROOT / "src/content/playlist.js"))
    page.add_script_tag(path=str(ROOT / "src/content/search-data.js"))
    page.add_script_tag(path=str(ROOT / "src/content/search.js"))
    page.add_script_tag(path=str(ROOT / "src/content/channel.js"))
    page.add_script_tag(path=str(ROOT / "src/content/channel-main.js"))
    page.add_script_tag(path=str(ROOT / "src/content/page-data-main.js"))
    page.add_script_tag(path=str(ROOT / "src/content/channel-navigation-main.js"))
    page.add_script_tag(path=str(ROOT / "src/content/content.js"))
    return page


def select_home_theme(page, value):
    page.locator('#myt-settings-button').click()
    page.locator('#myt-theme-'+value).click()
    page.locator('#myt-settings-close').click()


def centered(page, selector, tolerance=3):
    bounds = page.locator(selector).bounding_box()
    assert bounds and bounds["width"] > 0, f"Missing layout box: {selector}"
    viewport = page.viewport_size["width"]
    assert abs(bounds["x"] * 2 + bounds["width"] - viewport) < tolerance, (selector, bounds, viewport)
    assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= viewport + 1, bounds


def centered_header(page):
    brand = page.locator("#myt-masthead .myt-masthead-brand")
    logo = brand.bounding_box() if brand.count() else page.locator("#logo-icon svg").bounding_box()
    search = page.locator("#myt-masthead .myt-masthead-search").bounding_box()
    assert logo and search, (logo, search)
    left = min(logo["x"], search["x"])
    right = max(logo["x"] + logo["width"], search["x"] + search["width"])
    assert abs(left + right - page.viewport_size["width"]) < 3, (logo, search)
    assert abs(logo['y'] + logo['height']/2 - search['y'] - search['height']/2) < 1, (logo, search)


def navigate_spa(page, path):
    page.evaluate("""path => {
      history.pushState({}, '', path);
      document.dispatchEvent(new Event('yt-navigate-finish'));
    }""", path)


def assert_stable(page):
    mutations = page.evaluate("""async () => {
      const frames = async count => {
        for (let n = 0; n < count; n++) await new Promise(requestAnimationFrame);
      };
      await frames(3);
      let count = 0;
      const observer = new MutationObserver(records => count += records.length);
      observer.observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
      await frames(5);
      observer.disconnect();
      return count;
    }""")
    assert mutations == 0, f"Watch UI keeps mutating after stabilization: {mutations}"


def setup_at_document_start(browser, path, enabled=True, defer_settings=False):
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    code = (ROOT / "src/content/watch.js").read_text() + "\n" + (ROOT / "src/content/playlist.js").read_text() + "\n" + (ROOT / "src/content/search.js").read_text() + "\n" + (ROOT / "src/content/channel.js").read_text() + "\n" + (ROOT / "src/content/content.js").read_text()
    initial = json.dumps({"enabled": enabled})
    script = f"({MOCK})({initial});\n"
    if defer_settings:
        script += "chrome.storage.local.get = (keys, cb) => { window.__resolveSettings = () => cb(window.__stored); };\n"
    page.add_init_script(script=script + code)
    html = document('<ytd-app id="early-app"><ytd-page-manager class="ytd-app"><p id="early-native">Native app</p></ytd-page-manager></ytd-app>')
    probe = "<script>window.__earlyStartup = {enabled: document.documentElement.classList.contains('minimal-youtube'), page: document.documentElement.dataset.mytPage, bodyExists: !!document.body};</script>"
    html = html.replace("</head>", f"<style>{(ROOT / 'src/styles/styles.css').read_text()}</style>{probe}</head>")
    page.route("https://www.youtube.com/**", lambda route: route.fulfill(content_type="text/html", body=html))
    page.goto("https://www.youtube.com" + path)
    return page


def assert_uniform_full_page(page):
    png = page.screenshot(full_page=True, animations="disabled")
    result = page.evaluate("""async encoded => {
      const image = await createImageBitmap(await (await fetch('data:image/png;base64,' + encoded)).blob());
      const canvas = new OffscreenCanvas(image.width, image.height);
      const context = canvas.getContext('2d');
      context.drawImage(image, 0, 0);
      const points = [[0,0],[image.width-1,0],[0,image.height-1],[image.width-1,image.height-1]];
      for(let y=0;y<image.height;y+=120) points.push([4,y],[image.width-5,y]);
      const colors = points.map(([x,y])=>[...context.getImageData(x,y,1,1).data].join(','));
      return {width:image.width,height:image.height,colors:[...new Set(colors)]};
    }""", base64.b64encode(png).decode())
    assert len(result["colors"]) == 1, f"Full-page screenshot contains horizontal background bands: {result}"
    assert result["height"] == page.viewport_size["height"], f"Hidden native content still expands home page: {result}"



def check_home_isolation(browser, theme):
    page = setup(browser, theme=theme)
    page.add_style_tag(content="""
      form::before { content: ''; position: fixed; inset: 26vh 0 45vh;
                     background: rgba(0,0,0,.15); z-index: 2147483647; }
      input, div { filter: brightness(.4) !important; }
    """)
    # A separate document layer cannot be fixed by resetting main::before.
    page.evaluate("""() => {
      const overlay = document.createElement('div');
      overlay.id = 'native-overlay';
      overlay.style.cssText = 'position:fixed;inset:0 0 74vh;background:rgba(0,0,0,.15);z-index:2147483647;pointer-events:none';
      document.documentElement.append(overlay);
    }""")
    assert_uniform_full_page(page)
    page.add_style_tag(content='html { filter: brightness(.85); transform: translateY(40px); }')
    for size in [{"width":2016,"height":1240}, {"width":390,"height":844}]:
        page.set_viewport_size(size)
        assert_uniform_full_page(page)
        expected = '16,16,18,255' if theme == 'dark' else '249,249,251,255'
        # Check the rendered pixel, not merely a computed CSS color.
        png = page.screenshot(animations='disabled')
        pixel = page.evaluate("""async encoded => {
          const image = await createImageBitmap(await (await fetch('data:image/png;base64,' + encoded)).blob());
          const context = new OffscreenCanvas(image.width,image.height).getContext('2d');
          context.drawImage(image,0,0);
          return [...context.getImageData(4,4,1,1).data].join(',');
        }""", base64.b64encode(png).decode())
        assert pixel == expected, (pixel, expected)
    assert page.locator('#myt-query').evaluate('element => getComputedStyle(element).filter') == 'none'
    page.locator('#myt-query').fill('a')
    page.locator('#myt-query').press('/')
    expect(page.locator('#myt-query')).to_have_value('a/')
    page.locator('#myt-query').press('Escape')
    expect(page.locator('#myt-query')).to_have_value('')
    expect(page.locator('#myt-home')).to_be_visible()
    select_home_theme(page, 'light' if theme=='dark' else 'dark')
    assert_uniform_full_page(page)
    navigate_spa(page, '/results?search_query=restored')
    expect(page.locator('#myt-home')).to_have_count(0)
    assert page.locator('html').evaluate('element => element.inert') is False
    # Removal of a modal must restore interaction with the native page.
    page.evaluate("document.body.innerHTML='<button id=native-button onclick=\"this.textContent=123\">Native</button>'")
    page.locator('#native-button').click()
    expect(page.locator('#native-button')).to_have_text('123')
    page.close()



def check_search_icon_variants(browser, variant, width, path):
    if variant == 'legacy':
        header = MASTHEAD.replace('name="search_query"', 'type="search" name="search_query"')
    else:
        start = MASTHEAD.index('<ytd-searchbox>')
        end = MASTHEAD.index('</ytd-searchbox>') + len('</ytd-searchbox>')
        header = MASTHEAD[:start] + '''<yt-searchbox><form class="ytSearchboxComponentSearchForm" action="/results">
          <div class="ytSearchboxComponentInputBox"><input id="search" type="search" name="search_query"></div>
          </form></yt-searchbox>''' + MASTHEAD[end:]
    page = setup(browser, path, '<ytd-app>' + header + '</ytd-app>', width=width)
    # The owned header replaces YouTube's searchbox in every native variant.
    own = page.locator('#myt-masthead .myt-masthead-query')
    expect(own).to_be_visible()
    expect(page.locator('#search')).to_be_hidden()
    assert own.evaluate("element => getComputedStyle(element).appearance") == 'none'
    assert own.evaluate("element => getComputedStyle(element, '::-webkit-search-decoration').appearance") == 'none'
    own.fill('mr beast')
    clear = page.locator('#myt-masthead .myt-masthead-clear')
    expect(clear).to_be_visible()
    clear.click()
    expect(own).to_have_value('')
    expect(clear).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-masthead')).to_have_count(0)
    expect(page.locator('#search')).to_be_visible()
    page.evaluate('__setEnabled(true)')
    expect(own).to_be_visible()
    own.fill('mr beast & C++')
    own.press('Enter')
    page.wait_for_url('**/results?**')
    assert parse_qs(urlparse(page.url).query)['search_query'] == ['mr beast & C++']
    page.close()



def check_gutter_document_scroll(browser, path, renderer):
    fixture = f'''<ytd-app><ytd-page-manager><{renderer} page-subtype="channels" style="min-height:3200px">
      <div id="contents" style="height:3000px;max-width:1200px;margin-inline:auto">Page content</div></{renderer}></ytd-page-manager></ytd-app>
      <div id="left-gutter" style="position:fixed;left:0;top:0;width:80px;height:100vh;overflow:hidden;overscroll-behavior:contain"></div>
      <div id="right-gutter" style="position:fixed;right:0;top:0;width:80px;height:100vh;overflow:hidden;overscroll-behavior:contain"></div>'''
    page = setup(browser, path, fixture, width=2016)
    expect(page.locator(renderer)).to_have_css('visibility','visible')
    page.evaluate("""() => {
      for (const id of ['left-gutter', 'right-gutter']) {
        document.getElementById(id).addEventListener('wheel', event => event.preventDefault(), {passive:false});
      }
    }""")
    for x in [20, 1996]:
        page.evaluate('window.scrollTo(0,0)')
        page.mouse.move(x,400)
        page.mouse.wheel(0,300)
        page.wait_for_function('window.scrollY >= 250')
        # Capture forwarding must consume the native default, not double the delta.
        page.wait_for_timeout(100)
        assert 250 <= page.evaluate('scrollY') <= 350
        page.mouse.wheel(0,-150)
        page.wait_for_function('window.scrollY < 250')
    page.evaluate('__setEnabled(false); window.scrollTo(0,0)')
    page.mouse.wheel(0,300)
    page.wait_for_timeout(100)
    assert page.evaluate('scrollY') == 0
    page.close()



def check_latest_search_shelf(browser, title, renderer):
    fixture = f'''<ytd-app><ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">
      <ytd-channel-renderer id="matching-channel"><a href="/@creator">Creator</a><button id="subscribe">Subscribe</button></ytd-channel-renderer>
      <{renderer} id="latest"><div id="header"><h2>{title}</h2></div><div id="content">
      <ytd-video-renderer><a id="video-title" href="/watch?v=latest">Latest video</a></ytd-video-renderer><button>+8 more</button></div></{renderer}>
      <ytd-video-renderer id="ordinary-video"><h3><a id="video-title" href="/watch?v=ordinary">{title}</a></h3></ytd-video-renderer>
      <ytd-shelf-renderer id="ordinary-shelf"><div id="header"><h2>Popular videos</h2></div><div id="content"><ytd-video-renderer><a id="video-title" href="/watch?v=popular">Popular</a></ytd-video-renderer></div></ytd-shelf-renderer>
      </div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'''
    page = setup(browser, '/results?search_query=creator', fixture)
    expect(page.locator('#latest')).to_be_hidden()
    for selector in ['#matching-channel', '#matching-channel [data-myt-search-channel-card] .subscribe', '#ordinary-video', '#ordinary-shelf']:
        expect(page.locator(selector)).to_be_visible()
    page.locator('#latest #header h2').evaluate("element => element.textContent='Popular videos'")
    expect(page.locator('#latest')).to_be_visible()
    page.locator('#latest #header h2').evaluate('(element, title) => element.textContent=title',title)
    expect(page.locator('#latest')).to_be_hidden()
    page.locator('#latest').evaluate("element => { const copy=element.cloneNode(true); copy.id='dynamic-latest'; element.after(copy); }")
    expect(page.locator('#dynamic-latest')).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#latest')).to_be_visible()
    expect(page.locator('#dynamic-latest')).to_be_visible()
    page.evaluate('__setEnabled(true)')
    expect(page.locator('#latest')).to_be_hidden()
    page.evaluate("document.querySelector('ytd-page-manager').insertAdjacentHTML('beforeend','<ytd-browse page-subtype=channels>Channel</ytd-browse>')")
    navigate_spa(page, '/@creator/videos')
    expect(page.locator('#latest')).to_be_visible()
    page.close()



def check_channel_sections(browser, width):
    cards = ''.join(f'<ytd-grid-video-renderer id="popular-{i}"><ytd-thumbnail><a href="/watch?v={i}">Preview</a></ytd-thumbnail><a href="/watch?v={i}">Title</a></ytd-grid-video-renderer>' for i in range(5))
    fixture = f'''<ytd-app><ytd-page-manager><ytd-browse page-subtype="channels"><div id="contents">
      <ytd-shelf-renderer id="uploads"><div id="title-container"><h2>New Uploads</h2><button>Play all</button></div><div style="height:300px">Uploads</div></ytd-shelf-renderer>
      <ytd-shelf-renderer id="for-you"><div id="title-container"><h2>For you</h2></div><ytd-horizontal-list-renderer><div style="overflow-x:auto"><div id="items" style="display:flex;width:max-content">{cards.replace('popular-', 'for-you-')}</div></div></ytd-horizontal-list-renderer></ytd-shelf-renderer>
      <ytd-shelf-renderer id="popular"><div id="title-container"><h2>Popular videos</h2></div><ytd-horizontal-list-renderer><div id="carousel-scroll" style="overflow-x:auto"><div id="items" style="display:flex;width:max-content">{cards}</div></div></ytd-horizontal-list-renderer></ytd-shelf-renderer>
      </div></ytd-browse></ytd-page-manager></ytd-app>'''
    page = setup(browser, '/@creator/videos', fixture, width=width)
    expect(page.locator('#uploads')).to_be_hidden()
    expect(page.locator('#myt-search .media')).to_have_count(10)
    expect(page.locator('#myt-search .group')).to_have_count(2)
    sizes=page.locator('#myt-search').evaluate("""host=>[...host.shadowRoot.querySelectorAll('.media .cover')].map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height}})""")
    assert all(abs(size['width']-sizes[0]['width'])<1 for size in sizes),sizes
    assert all(abs(size['height']-size['width']*9/16)<1 for size in sizes),sizes
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#uploads')).to_be_visible()
    page.close()


def check_navigation_style_retention(browser):
    fixture = '''<ytd-app><ytd-page-manager><ytd-watch-flexy id="old-watch"><div id="secondary">Native recommendations</div><ytd-comments>Native comments</ytd-comments></ytd-watch-flexy></ytd-page-manager></ytd-app>'''
    page = setup(browser, '/watch?v=source', fixture)
    expect(page.locator('#secondary')).to_be_hidden()
    state = page.evaluate("""() => {
      document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail:{url:'/results?search_query=target'}}));
      return {page:document.documentElement.dataset.mytPage, hidden:getComputedStyle(document.querySelector('#secondary')).display==='none'};
    }""")
    assert state == {'page':'search','hidden':True}, state
    page.evaluate("history.pushState({},'', '/results?search_query=target')")
    frames = page.evaluate("""async () => {
      const states=[];
      for(let n=0;n<8;n++) { await new Promise(requestAnimationFrame); states.push(getComputedStyle(document.querySelector('#secondary')).display); }
      return states;
    }""")
    assert set(frames) == {'none'}, frames
    page.evaluate("""() => {
      document.querySelector('#old-watch').hidden=true;
      document.querySelector('ytd-page-manager').insertAdjacentHTML('beforeend','<ytd-search><ytd-video-renderer><a id=video-title href=/watch?v=next>Next</a></ytd-video-renderer></ytd-search>');
      document.dispatchEvent(new Event('yt-navigate-finish'));
    }""")
    expect(page.locator('html')).not_to_have_attribute('data-myt-previous-page')
    expect(page.locator('#myt-search .media[data-kind="video"]')).to_have_count(1)
    page.evaluate("document.dispatchEvent(new CustomEvent('yt-navigate-start',{detail:{url:'/@creator'}})); document.dispatchEvent(new Event('yt-navigate-cancel'))")
    expect(page.locator('html')).to_have_attribute('data-myt-page','search')
    expect(page.locator('html')).not_to_have_attribute('data-myt-previous-page')
    page.close()



def check_home_settings(browser, width):
    page = setup(browser, theme='dark', width=width)
    page.evaluate("""() => {
      window.__cookieRequests=[];
      window.__testCookies=[{name:'PREF',domain:'.youtube.com'}];
      chrome.runtime.sendMessage=(message, callback) => {
        __cookieRequests.push(message.action);
        if(message.action==='minimal-youtube:clear-cookies') {
          const removed=__testCookies.length; __testCookies=[];
          callback({ok:true, removed, cookies:[]});
        } else callback({ok:true,cookies:__testCookies});
      };
    }""")
    expect(page.locator('#myt-settings-panel')).to_be_hidden()
    brand=page.locator('#myt-home .myt-home__brand').bounding_box()
    theme=page.locator('#myt-home .myt-search').bounding_box()
    assert abs((brand['y']+theme['y']+theme['height'])/2-page.viewport_size['height']/2)<1, (brand,theme)
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-settings-panel')).to_be_visible()
    panel=page.locator('#myt-settings-panel').bounding_box()
    assert abs(panel['x']+panel['width']/2-width/2)<1, panel
    assert abs(panel['y']+panel['height']/2-page.viewport_size['height']/2)<1, panel
    expect(page.locator('#myt-home .myt-home__brand')).to_be_hidden()
    expect(page.locator('#myt-query')).to_be_hidden()
    assert page.locator('#myt-query').evaluate('element=>element.closest("form").inert')
    page.locator('#myt-settings-close').press('Shift+Tab')
    expect(page.locator('#myt-theme-dark')).to_be_focused()
    page.locator('#myt-theme-dark').press('Tab')
    expect(page.locator('#myt-settings-close')).to_be_focused()
    expect(page.locator('#myt-cookie-list')).to_contain_text('PREF · .youtube.com')
    expect(page.locator('#myt-cookie-list')).to_be_hidden()
    page.locator('#myt-cookie-toggle').click()
    expect(page.locator('#myt-cookie-toggle')).to_have_attribute('aria-expanded','true')
    expect(page.locator('#myt-cookie-list')).to_be_visible()
    page.locator('#myt-cookie-toggle').press('Enter')
    expect(page.locator('#myt-cookie-toggle')).to_have_attribute('aria-expanded','false')
    expect(page.locator('#myt-cookie-list')).to_be_hidden()
    assert page.locator('#myt-account-manage').get_attribute('href') == 'https://www.youtube.com/account'
    assert page.locator('#myt-account-signin').get_attribute('href').startswith('https://www.youtube.com/signin?')
    assert page.locator('#myt-account-switch').get_attribute('href').startswith('https://accounts.google.com/AccountChooser?')
    assert page.locator('#myt-account-signout').get_attribute('href').startswith('https://www.youtube.com/logout?')
    page.locator('#myt-cookie-clear').click()
    expect(page.locator('#myt-cookie-confirmation')).to_be_visible()
    assert page.evaluate('__cookieRequests').count('minimal-youtube:clear-cookies') == 0
    page.locator('#myt-cookie-cancel').click()
    expect(page.locator('#myt-cookie-confirmation')).to_be_hidden()
    assert page.evaluate('__cookieRequests').count('minimal-youtube:clear-cookies') == 0
    page.locator('#myt-cookie-clear').click()
    page.locator('#myt-cookie-confirm').click()
    expect(page.locator('#myt-cookie-status')).to_have_text('Deleted: 1. Cookies: 0')
    expect(page.locator('#myt-cookie-clear')).to_be_disabled()
    assert page.evaluate('__cookieRequests').count('minimal-youtube:clear-cookies') == 1
    page.locator('#myt-theme-light').click()
    expect(page.locator('#myt-theme-light')).to_have_attribute('aria-pressed','true')
    expect(page.locator('#myt-theme-dark')).to_have_attribute('aria-pressed','false')
    expect(page.locator('html')).to_have_attribute('data-myt-theme','light')
    assert page.evaluate('__stored.theme') == 'light'
    page.locator('#myt-settings-close').click()
    select_home_theme(page, 'dark')
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-theme-dark')).to_have_attribute('aria-pressed','true')
    page.evaluate("chrome.storage.local.set({language:'ru'})")
    expect(page.locator('#myt-settings-panel h2')).to_have_text('Settings')
    expect(page.locator('#myt-settings-language')).to_have_count(0)
    expect(page.locator('#myt-query')).to_have_attribute('placeholder','Search YouTube')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#myt-settings-close').click()
    expect(page.locator('#myt-settings-panel')).to_be_hidden()
    expect(page.locator('#myt-query')).to_be_visible()
    assert not page.locator('#myt-query').evaluate('element=>element.closest("form").inert')
    expect(page.locator('#myt-settings-button')).to_be_focused()
    page.locator('#myt-settings-button').click()
    page.locator('#myt-settings-close').press('Escape')
    expect(page.locator('#myt-settings-panel')).to_be_hidden()
    expect(page.locator('#myt-home')).to_be_visible()
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-settings-language')).to_have_count(0)
    expect(page.locator('#myt-settings-panel h2')).to_have_text('Settings')
    page.close()


def check_settings_failures(browser):
    page = setup(browser, theme='dark')
    page.evaluate("""() => {
      chrome.runtime.sendMessage=(message,cb)=>cb({ok:false,error:'cookies-unavailable'});
      chrome.storage.local.set=(value,cb)=> {
        chrome.runtime.lastError={message:'Fixture write failure'};
        cb(); delete chrome.runtime.lastError;
      };
    }""")
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-cookie-status')).to_contain_text('Could not access cookies')
    expect(page.locator('#myt-cookie-clear')).to_be_disabled()
    page.locator('#myt-theme-light').click()
    expect(page.locator('html')).to_have_attribute('data-myt-theme','dark')
    expect(page.locator('#myt-theme-dark')).to_have_attribute('aria-pressed','true')
    expect(page.locator('#myt-settings-error')).to_contain_text('Could not save')
    expect(page.locator('#myt-settings-language')).to_have_count(0)
    assert page.url == 'https://www.youtube.com/'
    page.close()



def check_header_alignment_and_anonymous_icons(browser, width):
    legacy = MASTHEAD[MASTHEAD.index('<ytd-searchbox>'):MASTHEAD.index('</ytd-searchbox>')+len('</ytd-searchbox>')]
    modern = '''<yt-searchbox style="height:40px;margin-top:5px"><div class="ytSearchboxComponentHost" style="height:40px"><form class="ytSearchboxComponentSearchForm" style="position:relative;height:40px;margin-top:4px" action="/results">
      <div class="ytSearchboxComponentInputBox"><input id="search" type="search" name="search_query"></div>
      </form></div></yt-searchbox>'''
    header = MASTHEAD.replace(legacy,modern).replace('<div id="center">','<div id="center" style="height:40px;align-items:flex-start">')
    page = setup(browser,'/results?search_query=alignment','<ytd-app>'+header+'</ytd-app>',width=width)
    own = page.locator('#myt-masthead .myt-masthead-query')
    # The field shows the current query; native offsets cannot move it.
    expect(own).to_have_value('alignment')
    own.fill('mr beast')
    centered_header(page)
    field = page.locator('#myt-masthead .myt-masthead-search').bounding_box()
    text = own.bounding_box()
    assert abs(field['y'] + field['height']/2 - text['y'] - text['height']/2) < 1, (field,text)
    assert abs(field['height'] - 44) < 1, field
    png=page.screenshot(animations='disabled')
    ink=page.evaluate("""async data => {
      const image=await createImageBitmap(await (await fetch('data:image/png;base64,'+data.png)).blob());
      const ctx=new OffscreenCanvas(image.width,image.height).getContext('2d'); ctx.drawImage(image,0,0);
      const r=data.field, text=data.text, ys=[];
      for(let y=Math.ceil(r.y+3);y<r.y+r.height-3;y++) {
        for(let x=Math.ceil(text.x+3);x<Math.min(text.x+120,text.x+text.width-3);x++) {
          const p=ctx.getImageData(x,y,1,1).data;
          if(p[0]<110 && p[1]<110 && p[2]<110) { ys.push(y);break; }
        }
      }
      return {min:Math.min(...ys),max:Math.max(...ys)};
    }""",{'png':base64.b64encode(png).decode(),'field':field,'text':text})
    assert abs((ink['min']+ink['max'])/2-field['y']-field['height']/2)<3, (field,ink)
    # YouTube's own searchbox and any icon it mounts stay hidden.
    page.locator('.ytSearchboxComponentSearchForm').evaluate("""form => {
      form.insertAdjacentHTML('afterbegin','<span data-anonymous-icon style="position:absolute;left:14px;top:10px"><svg width="24" height="24"><circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/></svg></span>');
    }""")
    expect(page.locator('[data-anonymous-icon] svg')).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-anonymous-icon] svg')).to_be_visible()
    page.evaluate('__setEnabled(true)')
    expect(page.locator('[data-anonymous-icon] svg')).to_be_hidden()
    expect(own).to_have_value('alignment')
    own.fill('mr beast')
    own.press('Enter')
    page.wait_for_url('**/results?**')
    assert parse_qs(urlparse(page.url).query)['search_query']==['mr beast']
    page.close()


def check_search_channels_and_row_gaps(browser, width):
    def channel(i):
        return f'''<div class="channel-wrapper"><ytd-channel-renderer id="channel-{i}"><div id="content-section"><div id="avatar-section"><img alt="" style="width:160px;height:160px"></div><div id="info-section"><a id="main-link" href="/@creator{i}">Channel {i}</a><button id="subscribe-{i}">Subscribe</button></div></div></ytd-channel-renderer></div>'''
    def video(i):
        return f'<ytd-video-renderer id="video-{i}"><ytd-thumbnail><a href="/watch?v={i}"><div style="height:100px">Preview</div></a></ytd-thumbnail><h3><a id="video-title" href="/watch?v={i}">Video {i}</a></h3></ytd-video-renderer>'
    fixture = '<ytd-app><ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents">'
    fixture += '<ytd-item-section-renderer><div id="contents">'+''.join(channel(i) for i in range(4))+'</div></ytd-item-section-renderer>'
    fixture += '<ytd-item-section-renderer><div id="contents">'+''.join(video(i) for i in range(6))+'</div></ytd-item-section-renderer>'
    fixture += '<ytd-item-section-renderer><div id="contents">'+''.join(video(i) for i in range(6,9))+'</div></ytd-item-section-renderer>'
    fixture += '</div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
    page = setup(browser,'/results?search_query=channels',fixture,width=width)
    a,b,c = [page.locator('#channel-'+str(i)).bounding_box() for i in range(3)]
    assert (abs(a['y']-b['y'])<1 and b['x']>a['x']+a['width']) if width>1000 else (abs(a['x']-b['x'])<1 and b['y']>=a['y']+a['height']+15),(a,b)
    boxes=[page.locator('#video-'+str(i)).bounding_box() for i in range(9)]
    assert len({(round(box['x']),round(box['y'])) for box in boxes})==9,boxes
    rail=page.locator('[data-myt-search-flow]').first.bounding_box()
    assert all(box['x']>=rail['x'] and box['x']+box['width']<=rail['x']+rail['width']+1 for box in boxes),boxes
    if width>1000:assert abs(a['width']-(rail['width']-24)/2)<1,(a,rail)
    for i in range(4):
        expect(page.locator('#channel-'+str(i)+' [data-myt-search-channel-card] .subscribe')).to_be_visible()
        expect(page.locator('#channel-'+str(i)+' #main-link')).to_have_attribute('href','/@creator'+str(i))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('__setEnabled(false)')
    assert page.locator('[data-myt-search-channel-cell]').count()==0
    page.close()



def check_channel_row_gaps(browser):
    fixture = '''<ytd-app><ytd-page-manager><ytd-browse page-subtype="channels"><div id="contents"><ytd-rich-grid-renderer>
      <div id="contents"><ytd-rich-grid-row style="display:block;margin:0"><div id="row-1" style="height:180px">First row</div></ytd-rich-grid-row><ytd-rich-grid-row style="display:block;margin:0"><div id="row-2" style="height:180px">Second row</div></ytd-rich-grid-row></div>
      </ytd-rich-grid-renderer></div></ytd-browse></ytd-page-manager></ytd-app>'''
    page = setup(browser,'/@creator/videos',fixture)
    a=page.locator('#row-1').bounding_box();b=page.locator('#row-2').bounding_box()
    assert abs(b['y']-a['y']-a['height']-32)<1, (a,b)
    page.evaluate('__setEnabled(false)')
    a=page.locator('#row-1').bounding_box();b=page.locator('#row-2').bounding_box()
    assert abs(b['y']-a['y']-a['height'])<1, (a,b)
    page.close()



def check_full_width_background_scroll(browser):
    fixture = '''<ytd-app><ytd-page-manager><ytd-search style="max-width:none!important;padding:0;position:relative">
      <div id="contents" style="max-width:1000px;margin-inline:auto;height:3600px">Native content
        <div id="independent-scroll" style="width:240px;height:120px;overflow:auto"><div style="height:1000px">Nested scrolling</div></div>
      </div><div id="empty-left" style="position:fixed;left:0;top:80px;width:200px;height:80vh"></div><div id="empty-right" style="position:fixed;right:0;top:80px;width:200px;height:80vh"></div>
      </ytd-search></ytd-page-manager></ytd-app>'''
    fixture=fixture.replace('ytd-search','ytd-browse').replace('<ytd-browse style=','<ytd-browse page-subtype="channels" style=')
    # Independent native controls belong outside the replaced video results.
    fixture=fixture.replace('<div id="contents" style=', '<div id="header" style=')
    page=setup(browser,'/@creator/videos',fixture,width=2016)
    expect(page.locator('#independent-scroll')).to_have_css('visibility','visible')
    page.evaluate("document.documentElement.style.overflow='hidden'; for (const id of ['empty-left','empty-right']) document.getElementById(id).addEventListener('wheel',event=>event.preventDefault(),{passive:false})")
    for x in [26,1990]:
        page.evaluate('window.scrollTo(0,0)')
        page.mouse.move(x,400)
        page.mouse.wheel(0,300)
        page.wait_for_function('scrollY>=250')
        page.wait_for_timeout(100)
        assert page.evaluate('scrollY')<=350
    page.evaluate('window.scrollTo(0,0)')
    page.locator('#independent-scroll').hover()
    page.mouse.wheel(0,100)
    page.wait_for_function("document.querySelector('#independent-scroll').scrollTop>0")
    assert page.evaluate('scrollY')==0
    page.evaluate('__setEnabled(false)')
    page.mouse.move(1990,400)
    page.mouse.wheel(0,300)
    page.wait_for_timeout(100)
    assert page.evaluate('scrollY')==0
    page.close()



def check_channel_first_within_sections(browser):
    def video(i):
        return f'<ytd-video-renderer id="video-order-{i}"><h3><a id="video-title" href="/watch?v={i}">Video {i}</a></h3></ytd-video-renderer>'
    def channel(i):
        return f'<div><ytd-channel-renderer id="channel-order-{i}"><a href="/@creator{i}">Channel {i}</a></ytd-channel-renderer></div>'
    fixture='<ytd-app><ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents">'
    fixture+='<ytd-item-section-renderer><div id="contents">'+video(0)+'</div></ytd-item-section-renderer>'
    fixture+='<ytd-item-section-renderer><div id="contents" id="mixed">'+video(1)+channel(1)+video(2)+channel(2)+video(3)+'</div></ytd-item-section-renderer>'
    fixture+='<ytd-item-section-renderer><div id="contents">'+channel(3)+'</div></ytd-item-section-renderer>'
    fixture+='</div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
    page=setup(browser,'/results?search_query=mixed-order',fixture)
    first=page.locator('#video-order-0').bounding_box()
    c1=page.locator('#channel-order-1').bounding_box();c2=page.locator('#channel-order-2').bounding_box()
    v1=page.locator('#video-order-1').bounding_box();v2=page.locator('#video-order-2').bounding_box()
    last=page.locator('#channel-order-3').bounding_box()
    assert first['y']>=c1['y']+c1['height']+15, (first,c1)
    assert abs(c2['y']-c1['y'])<1 and c2['x']>c1['x'], (c1,c2)
    assert v1['y']>=c1['y']+c1['height']+15, (c1,c2,v1)
    assert v2['y']>=v1['y'], (v1,v2)
    assert last['y']>=c2['y'], (last,c2)
    assert page.locator('#video-order-1').evaluate("element => Boolean(element.compareDocumentPosition(document.querySelector('#channel-order-1')) & Node.DOCUMENT_POSITION_FOLLOWING)")
    page.locator('#channel-order-2').evaluate('element=>element.parentElement.remove()')
    expect(page.locator('#channel-order-2')).to_have_count(0)
    v1=page.locator('#video-order-1').bounding_box();c1=page.locator('#channel-order-1').bounding_box()
    assert v1['y']>=c1['y']+c1['height']+15, (c1,v1)
    page.evaluate('__setEnabled(false)')
    assert page.locator('[data-myt-search-video-start]').count()==0
    page.close()



def check_native_hover_surface(browser, dark):
    fixture = '''<ytd-app><ytd-page-manager><ytd-search><ytd-item-section-renderer><div id="contents">
      <ytd-video-renderer id="native-hover-video"><ytd-thumbnail><a href="/watch?v=hover"><div style="height:160px">Preview</div></a></ytd-thumbnail><h3><a id="video-title" href="/watch?v=hover">Video</a></h3></ytd-video-renderer>
      <ytd-channel-renderer id="native-hover-channel"><a href="/@creator">Channel</a><button>Subscribe</button></ytd-channel-renderer>
      <yt-lockup-view-model id="native-hover-modern"><a href="/watch?v=modern"><div style="height:160px">Modern preview</div></a><h3><a href="/watch?v=modern">Modern video</a></h3></yt-lockup-view-model>
      </div></ytd-item-section-renderer></ytd-search></ytd-page-manager></ytd-app>'''
    page=setup(browser,'/results?search_query=hover',fixture,native_dark=dark)
    # Native preview styles can arrive after the extension and clear backgrounds.
    page.add_style_tag(content="""
      ytd-video-renderer:has(ytd-thumbnail:hover), ytd-channel-renderer:hover, yt-lockup-view-model:has(a:hover),
      ytd-video-renderer:focus-within, ytd-channel-renderer:focus-within, yt-lockup-view-model:focus-within {
        background: transparent !important;
      }
    """)
    for selector,hover_target in [('#native-hover-video','#native-hover-video ytd-thumbnail'),('#native-hover-channel','#native-hover-channel .channel-subscribe'),('#native-hover-modern','#native-hover-modern a')]:
        surface=page.locator(selector+' .channel-card' if selector=='#native-hover-channel' else selector)
        page.mouse.move(1,1)
        before=surface.evaluate('element=>getComputedStyle(element).backgroundColor')
        page.locator(hover_target+':visible').first.hover(position={'x':12,'y':12})
        color=surface.evaluate('element=>getComputedStyle(element).backgroundColor')
        assert color not in ['transparent','rgba(0, 0, 0, 0)'], (selector,before,color)
        assert color!=before, (selector,before,color)
        page.mouse.move(1,1)
        page.locator(selector+' a:visible').first.focus()
        color=surface.evaluate('element=>getComputedStyle(element).backgroundColor')
        assert color not in ['transparent','rgba(0, 0, 0, 0)'], (selector,color)
        page.evaluate('()=>{let active=document.activeElement;while(active?.shadowRoot?.activeElement)active=active.shadowRoot.activeElement;active?.blur();}')
    page.evaluate("""() => document.body.insertAdjacentHTML('beforeend', '<ytd-video-preview id=floating-preview style="display:none;width:360px"><div id=wrapper><div style="height:150px;background:black">Player</div><div id=details>Metadata</div></div></ytd-video-preview>')""")
    expect(page.locator('#floating-preview')).to_be_hidden()
    page.locator('#floating-preview').evaluate("element=>element.style.display='block'")
    expected='rgb(37, 37, 43)' if dark else 'rgb(247, 247, 249)'
    for selector in ['#floating-preview','#floating-preview #wrapper','#floating-preview #details']:
        assert page.locator(selector).evaluate('element=>getComputedStyle(element).backgroundColor')==expected
    page.evaluate('__setEnabled(false)')
    page.locator('#native-hover-video ytd-thumbnail').hover()
    assert page.locator('#native-hover-video').evaluate('element=>getComputedStyle(element).backgroundColor')=='rgba(0, 0, 0, 0)'
    page.close()



def check_channel_hover_surface(browser, dark):
    def card(tag,identifier):
        return f'<{tag} id="{identifier}" style="display:block;width:360px"><ytd-thumbnail><a href="/watch?v={identifier}"><div style="height:140px">Preview</div></a></ytd-thumbnail><h3><a href="/watch?v={identifier}">Video</a></h3></{tag}>'
    fixture='<ytd-app><ytd-page-manager><ytd-browse page-subtype="channels"><div id="contents">'
    fixture+=card('ytd-rich-item-renderer','rich-hover')+card('ytd-grid-video-renderer','grid-hover')+card('yt-lockup-view-model','lockup-hover')
    fixture+='</div></ytd-browse></ytd-page-manager></ytd-app>'
    page=setup(browser,'/@creator/videos',fixture,native_dark=dark)
    page.add_style_tag(content=':is(ytd-rich-item-renderer,ytd-grid-video-renderer,yt-lockup-view-model):is(:hover,:focus-within) { background:transparent !important; }')
    expect(page.locator('#myt-search .media')).to_have_count(3)
    for surface in page.locator('#myt-search .media').all():
        surface.hover()
        assert surface.evaluate('element=>getComputedStyle(element).backgroundColor')!='rgba(0, 0, 0, 0)'
    page.close()



def check_settings_short_viewport(browser):
    page=setup(browser,theme='light',width=390)
    page.set_viewport_size({'width':390,'height':420})
    page.evaluate("() => { chrome.runtime.sendMessage=(message,cb)=>cb({ok:true,cookies:[{name:'PREF',domain:'.youtube.com'}]}); }")
    page.locator('#myt-settings-button').click()
    box=page.locator('#myt-settings-panel').bounding_box()
    assert box['y']>=11 and box['y']+box['height']<=409, box
    page.locator('#myt-theme-dark').scroll_into_view_if_needed()
    expect(page.locator('#myt-settings-close')).to_be_in_viewport()
    expect(page.locator('#myt-theme-dark')).to_be_in_viewport()
    assert page.locator('#myt-settings-panel').evaluate('element=>element.scrollTop')>0
    page.locator('#myt-theme-dark').focus()
    page.locator('#myt-theme-dark').press('Escape')
    expect(page.locator('#myt-settings-panel')).to_be_hidden()
    expect(page.locator('#myt-query')).to_be_visible()
    page.close()


def assert_card_surface(page, selector, channel=False):
    card = page.locator(selector)
    color = "element => getComputedStyle(element).backgroundColor.match(/[\\d.]+/g).map(Number)"
    page.evaluate("()=>{let active=document.activeElement;while(active?.shadowRoot?.activeElement)active=active.shadowRoot.activeElement;active?.blur();}")
    page.mouse.move(1, 1)
    base = card.evaluate(color)
    assert len(base) == 3 or base[3] > .95, (selector, base)
    assert max(base[:3]) - min(base[:3]) < 16, (selector, base)
    assert card.evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
    if channel:
        # A result without a native subscription exposes its channel link,
        # whose own background supplies hover/focus feedback (as on watch).
        expect(card.locator('.channel-subscribe')).to_be_hidden()
        name=card.locator('.owner-name');name.hover()
        assert name.evaluate(color)[3]>0
        name.focus();assert name.evaluate(color)[3]>0
        return
    card.hover()
    hover = card.evaluate(color)
    assert sum(hover[:3]) > sum(base[:3]), (selector, base, hover)
    page.mouse.move(1, 1)
    card.locator('a[href]:visible').first.focus()
    focused = card.evaluate(color)
    assert sum(focused[:3]) > sum(base[:3]), (selector, base, focused)
    page.evaluate("()=>{let active=document.activeElement;while(active?.shadowRoot?.activeElement)active=active.shadowRoot.activeElement;active?.blur();}")


def watch_details_fixture(legacy=False):
    image = 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#414450"/><circle cx="160" cy="72" r="35" fill="#9b9dab"/><path d="M95 180q0-85 65-85t65 85" fill="#7b7d8a"/></svg>').decode()
    description = f'''
      <div id="description" class="ytd-watch-metadata">
        <div id="description-inner"><div id="info-container">906,359 views · Mar 8, 2025</div>
        <div id="snippet">A conversation about music, life and creativity.</div>
        <button id="expand" onclick="document.querySelector('#expanded').hidden=false;document.querySelector('#snippet').hidden=true;this.hidden=true">Show more</button>
        <div id="expanded" hidden>
          <p>A conversation about music, life and creativity. Discover the stories behind the songs and the people who inspired them. We explore the early performances, important collaborations, creative decisions and memorable conversations that shaped the artist’s career, with chapters and a complete transcript below.</p>
          <p>Follow the show: <a id="plain-link" href="https://example.com/show">https://example.com/show</a><br>
          <a id="inline-social" class="yt-core-attributed-string__link" href="https://example.com/profile"><yt-icon><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg></yt-icon><span>Instagram</span></a><br>
          Jump to <a id="time-link" href="/watch?v=details&amp;t=165">2:45</a> for the next story.</p>
          <ytd-structured-description-content-renderer><ytd-video-description-section-renderer><div id="structured-description">
            <ytd-video-description-chapters-section-renderer id="chapters"><h2>Эпизоды</h2>
              <ytd-horizontal-card-list-renderer><div id="items">
                <ytd-macro-markers-list-item-renderer><a id="chapter-link" href="/watch?v=details&amp;t=0" onclick="event.preventDefault();window.__chapter=0"><img src="{image}"><div id="time">0:00</div><h3 id="title">Introduction</h3></a></ytd-macro-markers-list-item-renderer>
                <ytd-macro-markers-list-item-renderer><a id="chapter-two" href="/watch?v=details&amp;t=165" onclick="event.preventDefault();window.__chapter=165"><img src="{image}"><div id="time">2:45</div><h3 id="title">The story behind the music</h3></a></ytd-macro-markers-list-item-renderer>
              </div></ytd-horizontal-card-list-renderer>
            </ytd-video-description-chapters-section-renderer>
            <ytd-video-description-infocards-section-renderer id="people"><h2>Упомянутые люди</h2><div id="subtitle">2 people</div>
              <ytd-horizontal-card-list-renderer><div id="items">
                <ytd-info-card-contents-renderer><a id="person-link" href="/results?search_query=Nelly" onclick="event.preventDefault();window.__person=true"><img src="{image}"><h3 id="title">Nelly</h3></a></ytd-info-card-contents-renderer>
                <ytd-info-card-contents-renderer><a href="/results?search_query=KRS-One"><img src="{image}"><h3 id="title">KRS-One</h3></a></ytd-info-card-contents-renderer>
              </div></ytd-horizontal-card-list-renderer>
            </ytd-video-description-infocards-section-renderer>
            <ytd-video-description-transcript-section-renderer id="transcript"><h2>Расшифровка видео</h2>
              <p>Find the information you need in this video.</p>
              <ytd-button-renderer><button id="open-transcript" onclick="document.querySelector('#transcript-panel').setAttribute('visibility','ENGAGEMENT_PANEL_VISIBILITY_EXPANDED')">Show transcript</button></ytd-button-renderer>
            </ytd-video-description-transcript-section-renderer>
            <ytd-video-description-channel-section-renderer id="creator"><h2>REVOLT</h2><p id="subtitle">3.33M subscribers</p>
              <yt-button-shape><a id="social-link" class="yt-spec-button-shape-next" href="https://example.com/social" onclick="event.preventDefault();window.__social=true">Instagram ↗</a></yt-button-shape>
              <yt-button-shape><button id="about-channel">About channel</button></yt-button-shape>
            </ytd-video-description-channel-section-renderer>
          </div></ytd-video-description-section-renderer></ytd-structured-description-content-renderer>
          <button id="collapse" onclick="document.querySelector('#expanded').hidden=true;document.querySelector('#snippet').hidden=false;document.querySelector('#expand').hidden=false">Show less</button>
        </div></div>
      </div>'''
    metadata = 'ytd-video-secondary-info-renderer' if legacy else 'ytd-watch-metadata'
    body = '<ytd-app>' + MASTHEAD + f'''
      <style>
        body {{ background:#090909; }} ytd-app {{ background:#0e0e0e; }}
        ytd-page-manager {{ background:#131313; }} ytd-watch-flexy {{ background:#0a0a0a; }}
        #columns {{ background:#101010; }} #primary {{ background:#151515; }} #below {{ background:#080808; }}
        ytd-watch-metadata, ytd-video-secondary-info-renderer {{ background:#131313; }}
        body::before, ytd-watch-flexy::after {{ content:'';position:fixed;inset:28vh 0 40vh;
          background:rgba(0,0,0,.25);box-shadow:0 200px 0 100px rgba(0,0,0,.15);pointer-events:none;z-index:9999; }}
        #cinematics {{ position:fixed;inset:0;background:linear-gradient(#293b4b,transparent);pointer-events:none; }}
        #player {{ background:#000; }} video {{ width:100%;height:auto;aspect-ratio:16/9; }}
        #description.ytd-watch-metadata {{ padding:12px;border-radius:12px;background:#272727; }}
        #description.ytd-watch-metadata:hover {{ background:#333; }}
        #description h2 {{ font:700 24px/1.5 Arial; }}
        #description #title {{ font:700 22px/1.5 Arial; }}
        #description p {{ margin-block:16px; }}
        #description ytd-horizontal-card-list-renderer {{ display:block;max-width:100%;overflow:hidden; }}
        #description #items {{ display:flex;overflow:auto; }}
        #people #items {{ flex-wrap:wrap; }}
        #description ytd-info-card-contents-renderer {{ display:block; }}
        #description ytd-info-card-contents-renderer img {{ width:240px;height:240px;object-fit:cover; }}
        #description ytd-macro-markers-list-item-renderer {{ display:block;flex-shrink:0; }}
        #description a {{ color:#3ea6ff; }}
        #description .yt-spec-button-shape-next {{ display:inline-flex;align-items:center; }}
      </style>
      <ytd-page-manager class="ytd-app"><ytd-watch-flexy>
        <div id="cinematics"></div><div id="columns"><div id="primary"><div id="player"><video></video></div>
        <div id="below"><{metadata}><h1>Music, life and the stories behind it</h1>{description}</{metadata}></div></div>
        <div id="secondary"><div id="secondary-inner"><div id="related">Recommendations</div>
          <ytd-engagement-panel-section-list-renderer id="transcript-panel" target-id="engagement-panel-searchable-transcript" visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN">
            <button id="close-transcript" onclick="document.querySelector('#transcript-panel').setAttribute('visibility','ENGAGEMENT_PANEL_VISIBILITY_HIDDEN')">Close transcript</button>
            <ytd-transcript-renderer><ytd-transcript-segment-list-renderer><ytd-transcript-segment-renderer>0:00 Introduction</ytd-transcript-segment-renderer></ytd-transcript-segment-list-renderer></ytd-transcript-renderer>
          </ytd-engagement-panel-section-list-renderer>
        </div></div></div>
      </ytd-watch-flexy></ytd-page-manager></ytd-app>'''
    return body

def native_watch_fixture(theater=False):
    avatar = 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect width="48" height="48" rx="24" fill="#ee4433"/><text x="11" y="30" fill="white" font-size="19">R</text></svg>').decode()
    player = '''<div id="player-container-outer"><div id="player-container-inner"><div id="player"><ytd-player id="ytd-player"><div id="container"><div id="movie_player" class="html5-video-player"><video class="html5-main-video" muted playsinline></video><span id="clock" class="ytp-time-current">0:00</span><button id="native-play" onclick="let v=document.querySelector('video');v.paused?v.play():v.pause()">YouTube play/pause</button><button id="native-fullscreen" class="ytp-fullscreen-button" onclick="document.fullscreenElement?document.exitFullscreen():this.closest('ytd-player').requestFullscreen().catch(error=>window.__fullscreenError=error.message)">Full screen</button></div></div></ytd-player></div></div></div>'''
    return '<ytd-app>'+MASTHEAD+f'''
      <style>
      ytd-player,#movie_player {{ display:block;position:relative;width:100%;height:100%; }}
      #player-container-outer,#player-container-inner,#player {{ height:360px; }}
      #ytd-player > #container {{ width:100%;height:100%; }}
      video.html5-main-video {{ position:absolute;inset:0;width:100%;height:100%;object-fit:contain; }}
      #native-play {{ position:absolute;bottom:8px;left:8px;z-index:5; }}
      #native-fullscreen {{ position:absolute;bottom:8px;right:8px;z-index:5; }}
      </style><ytd-page-manager class="ytd-app"><ytd-watch-flexy {'theater' if theater else ''}>
      <div id="full-bleed-container"><div id="cinematics-container">{player if theater else '<div id=ambient-layer></div>'}</div></div>
      <div id="columns"><div id="primary">{'' if theater else player}<div id="below"><ytd-watch-metadata>
      <h1>Native YouTube player regression</h1>
      <div id="owner"><img class="badge" src="https://www.youtube.com/invalid-badge"><a id="avatar" href="/@revolt"><yt-img-shadow><img src="{avatar}"></yt-img-shadow></a><ytd-channel-name><yt-formatted-string id="text"><a href="/@revolt">REVOLT</a><tp-yt-paper-tooltip>REVOLT</tp-yt-paper-tooltip></yt-formatted-string></ytd-channel-name><span id="owner-sub-count">3.33M subscribers</span><div id="subscribe-button"><button>Subscribe</button></div></div>
      <div id="actions"><div id="top-level-buttons-computed"><button id="share">Share</button></div></div>
      <div id="description" role="button"><span id="info-container">906,359 views</span><ytd-text-inline-expander id="description-inline-expander"><yt-attributed-string id="attributed-snippet-text">The real video description is available here.</yt-attributed-string><yt-attributed-string id="attributed-description-text"></yt-attributed-string><button id="expand" onclick="document.querySelector('#attributed-description-text').innerHTML='Full video description with native markup, links and paragraphs. &lt;a href=&quot;https://example.com/description&quot;&gt;Official website&lt;/a&gt;';window.__descriptionLoaded=true">Show more</button></ytd-text-inline-expander></div>
      </ytd-watch-metadata></div></div><div id="secondary"><div id="secondary-inner"></div></div></div>
      </ytd-watch-flexy></ytd-page-manager></ytd-app>'''


VIDEO_STREAM = """async () => {
  const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;
  const context=canvas.getContext('2d');context.fillStyle='rgb(24,180,96)';context.fillRect(0,0,640,360);
  window.__stream=canvas.captureStream(15);
  window.__frames=setInterval(()=>context.fillRect(0,0,640,360),50);
  const video=document.querySelector('video');window.__nativeVideo=video;window.__nativeVideoParent=video.parentElement;
  video.srcObject=window.__stream;video.muted=true;await video.play();
  await Promise.race([new Promise(resolve=>video.requestVideoFrameCallback(resolve)),new Promise((_,reject)=>setTimeout(()=>reject(new Error('No decoded video frame')),3000))]);
  return {width:video.videoWidth,height:video.videoHeight};
}"""


def rendered_pixel(page, x, y):
    png = page.screenshot(animations='disabled')
    return page.evaluate("""async ({encoded,x,y}) => {
      const image=await createImageBitmap(await(await fetch('data:image/png;base64,'+encoded)).blob());
      const context=new OffscreenCanvas(image.width,image.height).getContext('2d');context.drawImage(image,0,0);
      return [...context.getImageData(Math.floor(x),Math.floor(y),1,1).data];
    }""", {'encoded':base64.b64encode(png).decode(),'x':x,'y':y})


def check_native_watch(browser, theater=False, width=1440):
    page=setup(browser,'/watch?v=native',native_watch_fixture(theater),native_dark=True,width=width,prune_data=True)
    if width < 600: page.set_viewport_size({'width':width,'height':600})
    expect(page.locator('#ytd-player')).to_be_visible()
    assert page.locator('#ytd-player').evaluate("e=>e.matches(':popover-open')&&e.parentElement.id==='player'")
    assert page.locator('ytd-watch-flexy').get_attribute('popover') is None
    decoded=page.evaluate(VIDEO_STREAM)
    assert decoded=={'width':640,'height':360}
    box=page.locator('#myt-watch .media').bounding_box()
    video=page.locator('video').bounding_box()
    assert all(abs(video[key]-box[key])<2 for key in ['x','y','width','height']), (video,box)
    pixel=rendered_pixel(page,box['x']+box['width']/2,box['y']+box['height']/2)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])), f'Video is decoded but its visible surface is covered: {pixel}'
    # Native media is a separate top-layer element; wheel events must be
    # forwarded to the own page while native popup scrolling stays independent.
    page.mouse.move(box['x']+box['width']/2,box['y']+min(box['height']/2,300))
    page.mouse.wheel(0,280)
    page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.viewport').scrollTop>0")
    page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop=0')
    page.add_style_tag(content='ytd-player { transition:top .7s ease,left .7s ease; }')
    for selector in ['video','#watch-title']:
        page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop=0')
        direct=page.locator(selector).evaluate('''async e=>{
          const ui=document.querySelector('#myt-watch').firstElementChild.shadowRoot,viewport=ui.querySelector('.viewport');
          const event=new WheelEvent('wheel',{deltaY:120,bubbles:true,cancelable:true,composed:true});
          e.dispatchEvent(event);await new Promise(requestAnimationFrame);
          return {cancelled:event.defaultPrevented,scroll:viewport.scrollTop,maxScroll:viewport.scrollHeight-viewport.clientHeight,playerY:document.querySelector('#ytd-player').getBoundingClientRect().y,slotY:ui.querySelector('.media').getBoundingClientRect().y,transition:getComputedStyle(document.querySelector('#ytd-player')).transitionDuration};
        }''')
        expected_scroll=min(120,direct['maxScroll'])
        assert direct['cancelled'] and direct['scroll']==expected_scroll,direct
        assert abs(direct['playerY']-direct['slotY'])<1 and direct['transition']=='0s',direct
        page.wait_for_timeout(100)
        assert page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')==expected_scroll
    page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop=0')
    page.locator('#movie_player').evaluate("e=>{const menu=document.createElement('div');menu.id='test-player-menu';menu.className='ytp-settings-menu';menu.style.cssText='position:absolute;right:20px;top:20px;width:120px;height:100px;overflow:auto;background:white';const content=document.createElement('div');content.style.height='400px';content.textContent='Native menu';menu.append(content);e.append(menu);}")
    page.locator('#test-player-menu').hover()
    page.mouse.wheel(0,80)
    page.wait_for_function("document.querySelector('#test-player-menu').scrollTop>0")
    assert page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')==0
    page.locator('#test-player-menu').evaluate('e=>e.remove()')
    page.locator('#native-play').click()
    assert page.locator('video').evaluate('v=>v.paused') is True
    page.locator('#native-play').click()
    page.wait_for_function('document.querySelector("video").currentTime>.2')
    expect(page.locator('.owner-name')).to_have_text('REVOLT')
    expect(page.locator('.owner small')).to_have_count(0)
    expect(page.locator('.owner img')).to_be_visible()
    page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.owner img').naturalWidth===48")
    assert 'invalid-badge' not in page.locator('.owner img').get_attribute('src')
    # Lazy native text is fetched before deciding whether an expander is needed.
    expect(page.locator('#watch-description')).to_contain_text('Full video description with native markup')
    expect(page.locator('#watch-description a')).to_have_attribute('href','https://example.com/description')
    assert page.evaluate('window.__descriptionLoaded') is True
    page.locator('#below').evaluate("e=>e.insertAdjacentHTML('beforeend','<meta itemprop=datePublished content=2025-03-08>')")
    page.locator('#info-container').evaluate("e=>{const counter=document.createElement('yt-animated-rolling-number');counter.setAttribute('aria-label','326,412,890 views');counter.textContent='123456789012345678901234567890';const date=document.createElement('span');date.textContent='1 month ago';const products=document.createElement('button');products.textContent='3 products';e.replaceChildren(counter,date,products);}")
    expect(page.locator('#myt-watch .stats')).to_have_text('326.41m · 8 March 2025')
    page.locator('yt-animated-rolling-number').evaluate("e=>e.setAttribute('aria-label','326,412,891 views')")
    expect(page.locator('#myt-watch .stats')).to_have_text('326.41m · 8 March 2025')
    page.locator('#below').evaluate("e=>e.insertAdjacentHTML('beforeend','<meta itemprop=interactionCount content=987654321>')")
    page.locator('yt-animated-rolling-number').evaluate("e=>e.removeAttribute('aria-label')")
    expect(page.locator('#myt-watch .stats')).to_have_text('987.65m · 8 March 2025')

    # Enough chapters to overflow on desktop and mobile: exactly one scroll row.
    page.locator('#below').evaluate("e=>{for(let i=0;i<12;i++)e.insertAdjacentHTML('beforeend',`<ytd-macro-markers-list-item-renderer><button><span id=time>${i}:00</span><span id=title>Episode ${i}: a longer chapter title</span></button></ytd-macro-markers-list-item-renderer>`);}")
    expect(page.locator('.chapter')).to_have_count(12)
    page.locator('.chapter-list').scroll_into_view_if_needed()
    geometry=page.locator('.chapter-list').evaluate('e=>({width:e.clientWidth,scrollWidth:e.scrollWidth,ys:[...e.children].map(c=>c.offsetTop)})')
    assert geometry['scrollWidth']>geometry['width'] and len(set(geometry['ys']))==1, geometry
    page.locator('.chapter-list').hover()
    page.mouse.wheel(0,400)
    page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.chapter-list').scrollLeft>0")
    assert page.locator('#myt-watch .viewport').evaluate('e=>e.scrollWidth<=e.clientWidth')
    first_chapter=page.locator('.chapter').first.element_handle()
    chapter_scroll=page.locator('.chapter-list').evaluate('e=>e.scrollLeft')
    page.locator('yt-animated-rolling-number').evaluate("e=>e.setAttribute('aria-label','987,654,322 views')")
    expect(page.locator('#myt-watch .stats')).to_have_text('987.65m · 8 March 2025')
    assert first_chapter.evaluate('e=>e.isConnected'), 'View updates rebuild chapter cards'
    assert abs(page.locator('.chapter-list').evaluate('e=>e.scrollLeft')-chapter_scroll)<2
    page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop=0')
    page.locator('#native-fullscreen').click()
    page.wait_for_function("document.fullscreenElement?.id==='movie_player'")
    expect(page.locator('#myt-watch')).to_be_hidden()
    assert page.locator('#movie_player').bounding_box()=={'x':0,'y':0,'width':width,'height':page.viewport_size['height']}
    assert page.evaluate('window.__fullscreenError||null') is None
    pixel=rendered_pixel(page,width/2,page.viewport_size['height']/2)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_visible()
    assert page.locator('#ytd-player').evaluate("e=>e.matches(':popover-open')")
    # Native F shortcut must also release the shown wrapper before requesting fullscreen.
    page.evaluate("document.addEventListener('keydown',event=>{if(event.key==='f'){if(document.fullscreenElement)document.exitFullscreen();else document.querySelector('ytd-player').requestFullscreen().catch(error=>window.__fullscreenError=error.message);}});document.querySelector('video').tabIndex=0")
    page.locator('video').focus()
    page.keyboard.press('f')
    page.wait_for_function("document.fullscreenElement?.id==='movie_player'")
    page.keyboard.press('f')
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_visible()
    if not theater and width==1440:
        page.locator('#movie_player').evaluate("e=>e.ondblclick=()=>e.closest('ytd-player').requestFullscreen().catch(error=>window.__fullscreenError=error.message)")
        page.locator('video').dblclick(position={'x':30,'y':30})
        page.wait_for_function("document.fullscreenElement?.id==='movie_player'")
        expect(page.locator('#myt-watch')).to_be_hidden()
        page.locator('#native-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        # A denied/ignored native fullscreen request must restore the player.
        page.locator('#movie_player').evaluate("e=>{window.__fullscreenRequest=e.requestFullscreen;e.requestFullscreen=()=>Promise.reject(new DOMException('Denied','NotAllowedError'));}")
        page.locator('#native-fullscreen').click()
        page.wait_for_function("document.querySelector('#ytd-player').matches(':popover-open')")
        assert page.evaluate('!document.fullscreenElement')
        expect(page.locator('video')).to_be_visible()
        page.locator('#movie_player').evaluate('e=>e.requestFullscreen=window.__fullscreenRequest')
    page.locator('#movie_player').evaluate('e=>e.requestFullscreen()')
    assert page.evaluate('document.fullscreenElement.id')=='movie_player'
    before_scroll=page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')
    page.mouse.move(width/2,300)
    page.mouse.wheel(0,150)
    assert page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')==before_scroll

    pixel=rendered_pixel(page,width/2,page.viewport_size['height']/2)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])), pixel
    page.evaluate('document.exitFullscreen()')
    expect(page.locator('#myt-watch')).to_be_visible()
    assert page.locator('#ytd-player').evaluate("e=>e.matches(':popover-open')")
    assert page.evaluate('window.__nativeVideo===document.querySelector("video")&&window.__nativeVideoParent===document.querySelector("video").parentElement')
    page.evaluate('__setEnabled(false)')
    assert page.locator('#ytd-player').get_attribute('popover') is None
    assert page.locator('video').get_attribute('style') is None
    assert page.evaluate('window.__nativeVideo===document.querySelector("video")&&!document.querySelector("video").paused')
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_fullscreen_cached_layout(browser,target,theater=False,width=1440):
    page=setup(browser,'/watch?v=fullscreen-layout',native_watch_fixture(theater),native_dark=True,width=width)
    if width<600:page.set_viewport_size({'width':width,'height':600})
    page.evaluate(VIDEO_STREAM)
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.evaluate("""target=>{
        window.__fullscreenVideo=document.querySelector('video');
        window.__fullscreenParent=window.__fullscreenVideo.parentElement;
        const wrappers=[document.querySelector('#ytd-player > #container'),document.querySelector('#movie_player'),window.__fullscreenVideo];
        const saved=wrappers.map(node=>[node,node.getAttribute('style')]);
        document.querySelector('#native-fullscreen').onclick=()=>document.fullscreenElement?document.exitFullscreen():document.querySelector(target).requestFullscreen().catch(error=>window.__fullscreenError=error.message);
        document.addEventListener('fullscreenchange',()=>{
            for(const[node,original]of saved){
                if(document.fullscreenElement)node.style.cssText='position:absolute;left:0;top:0;width:0px;height:0px;overflow:hidden';
                else if(original===null)node.removeAttribute('style');else node.setAttribute('style',original);
            }
        });
    }""",target)
    page.evaluate('selector=>{const node=document.querySelector(selector);node.closest("[popover]")?.hidePopover();node.requestFullscreen();}',target)
    page.wait_for_function('!!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_hidden()
    dimensions=page.locator('video').bounding_box()
    assert dimensions=={'x':0,'y':0,'width':width,'height':page.viewport_size['height']},dimensions
    assert page.locator('video').evaluate("e=>e.style.width==='0px'&&e.videoWidth===640&&e.videoHeight===360&&!e.paused")
    # Sample the decoded picture across its contained aspect ratio, not just one
    # center pixel that could pass with a small video inside a black fullscreen.
    height=page.viewport_size['height'];picture_w=min(width,height*16/9);picture_h=picture_w*9/16
    for px,py in [(x,y) for x in [.15,.5,.85] for y in [.15,.5,.85]]:
        pixel=rendered_pixel(page,(width-picture_w)/2+px*picture_w,(height-picture_h)/2+py*picture_h)
        assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),(target,px,py,pixel)
    assert page.evaluate('window.__fullscreenVideo===document.querySelector("video")&&window.__fullscreenParent===document.querySelector("video").parentElement')
    # Native controls must remain clickable after the dimensions are repaired.
    page.locator('#native-play').click()
    assert page.locator('video').evaluate('v=>v.paused')
    page.locator('#native-play').click()
    assert not page.locator('video').evaluate('v=>v.paused')
    if target=='#ytd-player':
        # Re-enabling while already fullscreen must keep the own canvas hidden.
        page.evaluate('__setEnabled(false);__setEnabled(true)')
        expect(page.locator('#myt-watch')).to_be_hidden()
        page.evaluate("""async()=>{
          const old=document.querySelector('video'),fresh=old.cloneNode(false);
          fresh.removeAttribute('data-myt-fullscreen-part');fresh.removeAttribute('style');fresh.srcObject=old.srcObject;
          old.replaceWith(fresh);await fresh.play();
          await new Promise(resolve=>fresh.requestVideoFrameCallback(resolve));
        }""")
        expect(page.locator('video')).to_have_attribute('data-myt-fullscreen-part','video')
        pixel=rendered_pixel(page,width/2,height/2)
        assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_visible()
    expect(page.locator('[data-myt-fullscreen-part]')).to_have_count(0)
    assert page.locator('#ytd-player').evaluate("e=>e.matches(':popover-open')")
    assert page.locator('video').bounding_box()==page.locator('#myt-watch .media').bounding_box()
    assert not errors,errors
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-fullscreen-part]')).to_have_count(0)
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_native_home_fallback(browser):
    fixture='<ytd-app><ytd-page-manager><div id="native-feed">Native home feed</div></ytd-page-manager></ytd-app>'
    page=setup(browser,'/',fixture,runtime_id='dofmohajpfnbbpdkmcpmahkpedpingmn')
    expect(page.locator('#myt-home')).to_be_visible()
    assert page.url=='https://www.youtube.com/'
    expect(page.locator('#native-feed')).to_have_count(1)
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-settings-panel')).to_be_visible()
    page.keyboard.press('Escape')
    page.locator('#myt-query').fill('fallback home')
    page.locator('#myt-query').press('Enter')
    page.wait_for_url('**/results?search_query=fallback+home')
    page.close()
    page=setup(browser,'/results?search_query=home',fixture,runtime_id='dofmohajpfnbbpdkmcpmahkpedpingmn')
    navigate_spa(page,'/')
    expect(page.locator('#myt-home')).to_be_visible()
    assert page.url=='https://www.youtube.com/'
    assert_stable(page)
    page.close()


def check_short_watch_scroll(browser,width):
    page=setup(browser,'/watch?v=short-description',native_watch_fixture(),native_dark=True,width=width)
    if width<600:page.set_viewport_size({'width':width,'height':600})
    # A native fixed video layer must follow its own player rectangle, too.
    page.add_style_tag(content='#movie_player { position:fixed!important;inset:0!important;width:100%!important;height:100%!important; }')
    page.evaluate(VIDEO_STREAM)
    viewport=page.locator('#myt-watch .viewport')
    video=page.locator('video')
    initial=video.bounding_box()
    assert initial==page.locator('#myt-watch .media').bounding_box()
    page.mouse.move(initial['x']+initial['width']/2,initial['y']+initial['height']/2)
    page.mouse.wheel(0,150)
    page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.viewport').scrollTop>=150")
    after=video.bounding_box()
    assert after==page.locator('#myt-watch .media').bounding_box() and after['y']<=initial['y']-149,(initial,after)
    viewport.evaluate("e=>e.scrollTo({top:e.scrollHeight,behavior:'instant'})")
    page.wait_for_function("document.querySelector('video').getBoundingClientRect().bottom<=document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.header').getBoundingClientRect().bottom")
    expect(page.locator('#myt-watch .description')).to_be_visible()
    viewport.evaluate("e=>e.scrollTo({top:0,behavior:'instant'})")
    page.wait_for_function("document.querySelector('video').getBoundingClientRect().y===document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.media').getBoundingClientRect().y")
    assert video.bounding_box()==initial
    pixel=rendered_pixel(page,initial['x']+initial['width']/2,initial['y']+initial['height']/2)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    assert page.locator('#ytd-player').evaluate("e=>getComputedStyle(e).contain")=='none'
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_fast_fullscreen(browser):
    page=setup(browser,'/watch?v=instant-fullscreen',native_watch_fixture(),native_dark=True)
    page.evaluate(VIDEO_STREAM)
    page.evaluate("""() => {
      window.__delayedNativeCalls=0;
      document.querySelector('#native-fullscreen').onclick=()=>{__delayedNativeCalls++;setTimeout(()=>document.querySelector('ytd-player').requestFullscreen(),1000);};
      window.__fullscreenStart=performance.now();
    }""")
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!!document.fullscreenElement')
    assert page.evaluate('document.fullscreenElement.id')=='movie_player'
    assert page.evaluate('__delayedNativeCalls')==0
    assert page.locator('video').bounding_box()=={'x':0,'y':0,'width':1440,'height':960}
    pixel=rendered_pixel(page,720,480)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('[data-myt-fullscreen-pending],[data-myt-fullscreen-part]')).to_have_count(0)
    expect(page.locator('#myt-watch')).to_be_visible()
    assert page.evaluate('window.__nativeVideo===document.querySelector("video")&&window.__nativeVideoParent===document.querySelector("video").parentElement')
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_player_ad_data(browser):
    player={'playabilityStatus':{'status':'OK'},'videoDetails':{'videoId':'native'},'streamingData':{'formats':[{'url':'https://media.example/content?signature=keep'}]},'playerAds':[{'id':'ad'}],'adPlacements':[{'slot':'preroll'}],'adSlots':[{'slot':'midroll'}]}
    script='<script>var ytInitialPlayerResponse='+json.dumps(player)+';window.__bootAds=[ytInitialPlayerResponse.playerAds,ytInitialPlayerResponse.adPlacements,ytInitialPlayerResponse.adSlots].filter(Boolean).length;</script>'
    page=setup(browser,'/watch?v=native',script+native_watch_fixture(),prune_data=True)
    assert page.evaluate('window.__bootAds')==0
    assert page.evaluate('ytInitialPlayerResponse.streamingData.formats[0].url')==player['streamingData']['formats'][0]['url']
    actual=page.evaluate("""async player=>{
      const data=await new Response(JSON.stringify(player)).json();
      return {ads:[data.playerAds,data.adPlacements,data.adSlots].filter(Boolean).length,status:data.playabilityStatus.status,url:data.streamingData.formats[0].url};
    }""",player)
    assert actual=={'ads':0,'status':'OK','url':player['streamingData']['formats'][0]['url']},actual
    page.evaluate('__setEnabled(false)')
    assert page.evaluate('(player=>JSON.parse(JSON.stringify(player)).playerAds.length)',player)==1
    assert page.evaluate("Object.getOwnPropertyDescriptor(window,'ytInitialPlayerResponse').get===undefined")
    page.close()


def check_player_ad_controls(browser):
    page=setup(browser,'/watch?v=ad-controls',native_watch_fixture(),native_dark=True)
    page.evaluate(VIDEO_STREAM)
    page.evaluate("""() => {
      window.__skips=0;const player=document.querySelector('#movie_player');
      const button=document.createElement('button');button.id='native-ad-skip';button.className='ytp-ad-skip-button-modern';button.textContent='Skip ads';button.disabled=true;
      button.onclick=()=>window.__skips++;const container=document.createElement('div');container.className='ytp-ad-skip-button-container';container.append(button);player.append(container);
      const overlay=document.createElement('div');overlay.className='ytp-ad-overlay-container';overlay.textContent='Ad banner';player.append(overlay);
      const video=player.querySelector('video');window.__originalMedia={video,parent:video.parentElement,muted:video.muted,volume:video.volume,rate:video.playbackRate,time:video.currentTime};
    }""")
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==0
    page.locator('#movie_player').evaluate("e=>e.classList.add('ad-showing')")
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==0,'A disabled skip button was clicked'
    page.locator('.ytp-ad-skip-button-container').evaluate("e=>e.style.opacity='0'")
    page.locator('#native-ad-skip').evaluate('e=>e.disabled=false')
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==0,'A transparent/pre-countdown control was clicked'
    page.locator('.ytp-ad-skip-button-container').evaluate("e=>e.style.opacity='1'")
    page.wait_for_function('window.__skips===1')
    page.locator('#native-ad-skip').evaluate("e=>e.style.color='white'")
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==1,'The same ad control was spammed'
    page.locator('video').evaluate("e=>e.dispatchEvent(new Event('loadedmetadata'))")
    page.wait_for_function('window.__skips===2')
    expect(page.locator('.ytp-ad-overlay-container')).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    page.locator('#native-ad-skip').evaluate('e=>{e.disabled=true;e.disabled=false;}')
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==2
    page.evaluate('__setEnabled(true)')
    page.wait_for_function('window.__skips===3')
    page.locator('#movie_player').evaluate("e=>e.classList.remove('ad-showing')")
    page.wait_for_timeout(40)
    page.locator('#native-ad-skip').evaluate('e=>e.hidden=true')
    page.locator('#movie_player').evaluate("e=>e.classList.add('ad-showing')")
    page.wait_for_timeout(60)
    assert page.evaluate('window.__skips')==3,'A hidden skip button was clicked'
    page.locator('#native-ad-skip').evaluate('e=>e.hidden=false')
    page.wait_for_function('window.__skips===4')
    page.locator('#movie_player').evaluate("e=>e.classList.remove('ad-showing')")
    assert page.evaluate("""()=>{
      const original=window.__originalMedia,video=document.querySelector('video');
      return video===original.video&&video.parentElement===original.parent&&video.muted===original.muted&&video.volume===original.volume&&video.playbackRate===original.rate&&video.currentTime>=original.time;
    }""")
    box=page.locator('#myt-watch .media').bounding_box()
    pixel=rendered_pixel(page,box['x']+box['width']/2,box['y']+box['height']/2)
    assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    assert_stable(page)
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_fullscreen_timeline(browser,width,api):
    page=setup(browser,'/watch?v=timeline',native_watch_fixture(),native_dark=True,width=width,prune_data=True)
    if width<600:page.set_viewport_size({'width':width,'height':600})
    encoded=base64.b64encode((ROOT/'tests/fixtures/seek.webm').read_bytes()).decode()
    page.evaluate("""async encoded=>{
      const video=document.querySelector('video');window.__timelineVideo=video;
      video.src='data:video/webm;base64,'+encoded;video.muted=true;video.load();
      await new Promise(resolve=>video.addEventListener('loadeddata',resolve,{once:true}));
    }""",encoded)
    page.evaluate("""api=>{
      const player=document.querySelector('#movie_player');
      const chrome=document.createElement('div');chrome.className='ytp-chrome-bottom';chrome.style.cssText='position:absolute;left:12px;bottom:0;height:48px;width:140px;z-index:2';
      chrome.innerHTML='<div class="ytp-progress-bar-container" style="position:absolute;top:0;height:14px;width:140px"><div class="ytp-progress-bar" role="slider" tabindex="0" aria-label="Seek" style="position:relative;height:14px;width:140px"><div class="ytp-chapters-container" style="display:flex;height:7px;width:140px"></div></div></div>';
      player.append(chrome);const bar=chrome.querySelector('.ytp-progress-bar'),chapters=chrome.querySelector('.ytp-chapters-container');
      if(api)for(const ratio of [1,2,1]){const segment=document.createElement('div');segment.className='ytp-chapter-hover-container';segment.dataset.ratio=ratio;segment.style.cssText='height:7px;background:red;width:'+35*ratio+'px';chapters.append(segment);}
      const resize=(width,height)=>{
        window.__timelineResize=[width,height];
        const inset=document.fullscreenElement? (width<=600?12:24):12,available=width-2*inset;
        chrome.style.width=available+'px';
        for(const child of chrome.querySelectorAll('.ytp-progress-bar-container,.ytp-progress-bar,.ytp-chapters-container'))child.style.width=available+'px';
        for(const segment of chapters.children)segment.style.width=available*Number(segment.dataset.ratio)/4+'px';
      };
      if(api==='direct')player.setSize=resize;
      if(api==='wrapper')player.closest('ytd-player').getApiInterface=()=>({setSize:resize});
      let down=false;
      const seek=event=>{const box=bar.getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(event.clientX-box.x)/box.width));document.querySelector('video').currentTime=fraction*document.querySelector('video').duration;};
      bar.addEventListener('pointerdown',event=>{down=true;bar.setPointerCapture(event.pointerId);seek(event);});
      bar.addEventListener('pointermove',event=>{if(down)seek(event);});bar.addEventListener('pointerup',()=>down=false);
      bar.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'){event.preventDefault();const video=document.querySelector('video');video.currentTime=Math.max(0,video.currentTime-.4);}});
      window.__nativeSeek=bar;
    }""",api)
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!!document.fullscreenElement')
    height=page.viewport_size['height'];inset=12 if width<=600 else 24;expected=width-2*inset
    page.wait_for_function("width=>Math.abs(document.querySelector('.ytp-progress-bar').getBoundingClientRect().width-width)<2",arg=expected)
    bar=page.locator('.ytp-progress-bar');box=bar.bounding_box()
    assert abs(box['x']-inset)<1 and abs(box['width']-expected)<1,(box,expected)
    if api:
        page.wait_for_function("width=>window.__timelineResize?.[0]===width",arg=width)
        segments=page.locator('.ytp-chapter-hover-container').all()
        for segment,ratio in zip(segments,[1,2,1]):assert abs(segment.bounding_box()['width']-expected*ratio/4)<1
    for fraction,color in [(.125,[200,30,30,255]),(.5,[30,60,200,255]),(.875,[230,190,24,255])]:
        page.mouse.click(box['x']+box['width']*fraction,box['y']+box['height']/2)
        page.wait_for_function("fraction=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-v.duration*fraction)<.08;}",arg=fraction)
        page.wait_for_timeout(60)
        pixel=rendered_pixel(page,width/2,height/2)
        assert all(abs(a-b)<=10 for a,b in zip(pixel,color)),(fraction,pixel,color)
    page.mouse.move(box['x']+box['width']*.25,box['y']+box['height']/2)
    page.mouse.down();page.mouse.move(box['x']+box['width']*.75,box['y']+box['height']/2,steps=8);page.mouse.up()
    page.wait_for_function("()=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-v.duration*.75)<.08;}")
    bar.focus();page.keyboard.press('ArrowLeft')
    page.wait_for_function("()=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-(v.duration*.75-.4))<.08;}")
    assert page.evaluate("window.__nativeSeek===document.querySelector('.ytp-progress-bar')&&window.__timelineVideo===document.querySelector('video')")
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_visible()
    expect(page.locator('[data-myt-fullscreen-part]')).to_have_count(0)
    if api:
        page.wait_for_function("()=>document.querySelector('.ytp-progress-bar').getBoundingClientRect().width<document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.media').getBoundingClientRect().width")
    assert_stable(page)
    page.close()


def check_theater_edges(browser,width,source_height):
    page=setup(browser,'/watch?v=theater-edges',native_watch_fixture(True),native_dark=True,width=width,prune_data=True)
    if width<600:page.set_viewport_size({'width':width,'height':600})
    stream=VIDEO_STREAM.replace('canvas.height=360','canvas.height='+str(source_height)).replace('640,360','640,'+str(source_height))
    page.evaluate(stream)
    page.wait_for_function("height=>Math.abs(document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.media').getBoundingClientRect().height-document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.viewport').clientWidth*height/640)<1",arg=source_height)
    media=page.locator('#myt-watch .media').bounding_box();video=page.locator('video').bounding_box()
    geometry=page.locator('#myt-watch .header').bounding_box()
    content_width=page.locator('#myt-watch .viewport').evaluate('e=>e.clientWidth')
    assert media['x']==0 and media['width']==content_width and media['y']==geometry['y']+geometry['height'],media
    assert video==media,(video,media)
    assert page.locator('#ytd-player').evaluate('e=>getComputedStyle(e).borderRadius')=='0px'
    for x in [1,content_width-2]:
        pixel=rendered_pixel(page,x,media['y']+min(160,media['height']/2))
        assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),(x,pixel)
    # A native playlist goes below the full-width theater player.
    page.locator('#secondary-inner').evaluate("e=>e.insertAdjacentHTML('beforeend','<ytd-playlist-panel-renderer id=playlist><ytd-playlist-panel-video-renderer>Playlist</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer>')")
    expect(page.locator('#myt-watch .sidecar')).to_be_visible()
    assert page.locator('#myt-watch .media').bounding_box()['width']==content_width
    sidecar=page.locator('#myt-watch .sidecar').bounding_box()
    assert sidecar['y']>=media['y']+media['height'],(sidecar,media)
    page.locator('#playlist').evaluate('e=>e.remove()')
    page.locator('ytd-watch-flexy').evaluate("e=>e.removeAttribute('theater')")
    page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.media').getBoundingClientRect().x>0")
    assert page.locator('#myt-watch .details').evaluate('e=>e.getBoundingClientRect().x>0')
    assert_stable(page)
    page.evaluate('clearInterval(window.__frames);window.__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def playlist_panel_fixture():
    rows=''.join(f'''<ytd-playlist-panel-video-renderer><a href="/watch?v=playlist-{i}" onclick="event.preventDefault();window.__playlistVisit={i}"><span class="playlist-preview">{i+1}</span><span>Playlist video {i+1}: a conversation about life and music</span></a></ytd-playlist-panel-video-renderer>''' for i in range(50))
    return '''<style>
      #playlist { color:#eee;background:#19191d;font:15px/1.4 Arial; }
      #playlist #header { height:88px;padding:16px; }
      #playlist #header button { float:right; }
      #playlist #items { overflow:auto; }
      #playlist ytd-playlist-panel-video-renderer { height:86px;min-height:86px; }
      #playlist ytd-playlist-panel-video-renderer a { display:flex;align-items:center;gap:12px;height:100%;padding:10px;color:inherit;text-decoration:none; }
      #playlist .playlist-preview { display:grid;place-items:center;flex:none;width:96px;height:54px;background:#38495e;border-radius:8px; }
    </style><ytd-playlist-panel-renderer id="playlist"><div id="container"><div id="header"><button onclick="document.querySelector('#playlist').hidden=true">Close playlist</button><strong>Playlist</strong><br>50 videos</div><div id="items">'''+rows+'</div></div></ytd-playlist-panel-renderer>'


def check_playlist_layout(browser, theater=False, width=1440):
    body=native_watch_fixture(theater)
    body=body.replace('<div id="secondary-inner"></div>','<div id="secondary-inner">'+playlist_panel_fixture()+'</div>')
    page=setup(browser,'/watch?v=native&list=fixture',body,native_dark=True,width=width)
    page.evaluate(VIDEO_STREAM)
    page.evaluate("document.querySelector('#expand').onclick=()=>{}")
    page.wait_for_function('''() => {
      const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,placeholder=root.querySelector('.sidecar').getBoundingClientRect(),native=document.querySelector('#playlist').getBoundingClientRect();
      return placeholder.width>0&&Math.abs(placeholder.width-native.width)<1&&Math.abs(placeholder.height-native.height)<1&&Math.abs(placeholder.y-native.y)<1;
    }''')
    bounds=page.evaluate('''() => {
      const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,box=s=>{const b=root.querySelector(s).getBoundingClientRect();return{x:b.x,y:b.y,width:b.width,height:b.height,right:b.right,bottom:b.bottom};};
      return {media:box('.media'),details:box('.details'),playlist:box('.sidecar'),header:box('.header'),width:root.querySelector('.viewport').clientWidth};
    }''')
    media,details,playlist,header=[bounds[key] for key in ['media','details','playlist','header']]
    if width>900:
        assert abs(playlist['right']-bounds['width'])<1,bounds
        assert abs(details['x']+details['width']/2-(playlist['x']/2 if theater else bounds['width']/2))<1,bounds
        if theater:
            assert media['x']==0 and media['width']==bounds['width'],bounds
            assert abs(media['y']-header['bottom'])<1,bounds
            assert playlist['y']>=media['bottom'] and abs(playlist['y']-details['y'])<1,bounds
            assert playlist['height']>=details['height']-1,bounds
            description=page.locator('.description').bounding_box()
            minimum_height=page.locator('.sidecar').evaluate('e=>parseFloat(getComputedStyle(e).minHeight)')
            assert abs(playlist['bottom']-max(description['y']+description['height'],playlist['y']+minimum_height))<1,(bounds,description)
            assert details['height']<600,bounds
        else:
            assert abs(playlist['y']-media['y'])<1,bounds
            assert abs(media['x']+media['width']/2-playlist['x']/2)<1,bounds
            assert abs(playlist['height']-media['height'])<1,bounds
    else:
        assert playlist['y']>=details['bottom']-1,bounds
        assert abs(playlist['x']*2+playlist['width']-bounds['width'])<1,bounds
    minimum=page.locator('#playlist').evaluate('''e=>{
      const rows=e.querySelectorAll('ytd-playlist-panel-video-renderer');return e.querySelector('#header').getBoundingClientRect().height+rows[0].getBoundingClientRect().height+rows[1].getBoundingClientRect().height;
    }''')
    assert playlist['height']>=minimum-1,(playlist,minimum)
    assert page.locator('#playlist').evaluate("e=>e.matches(':popover-open')&&e.parentElement.id==='secondary-inner'")
    if width>900:
        for resized_width in [1024,1440,width]:
            page.set_viewport_size({'width':resized_width,'height':960})
            page.wait_for_function('''() => {
              const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,panel=root.querySelector('.sidecar').getBoundingClientRect(),native=document.querySelector('#playlist').getBoundingClientRect();return Math.abs(panel.right-root.querySelector('.viewport').clientWidth)<1&&Math.abs(native.width-panel.width)<1&&Math.abs(native.x-panel.x)<1;
            }''')
            assert_stable(page)
    if width==1440:
        page.locator('#native-fullscreen').click()
        page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('video').bounding_box()=={'x':0,'y':0,'width':1440,'height':960}
        page.locator('#native-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        page.wait_for_function('''() => {
          const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,a=root.querySelector('.sidecar').getBoundingClientRect(),b=document.querySelector('#playlist').getBoundingClientRect();return a.width>0&&Math.abs(a.width-b.width)<1&&Math.abs(a.y-b.y)<1;
        }''')
        assert_stable(page)
    # Theater follows the current description height; normal mode stays tied to the video.
    page.locator('#attributed-description-text').evaluate("e=>e.innerHTML=Array.from({length:14},(_,i)=>'<p>Paragraph '+i+': '+('A longer description with useful video information. '.repeat(5))+'</p>').join('')")
    page.locator('.expand').click()
    if theater and width>900:
        page.wait_for_function('''() => {
          const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,a=root.querySelector('.sidecar').getBoundingClientRect(),b=root.querySelector('.details').getBoundingClientRect(),native=document.querySelector('#playlist').getBoundingClientRect();return a.height>=b.height-1&&a.height>1000&&Math.abs(native.height-a.height)<1;
        }''')
    page.locator('.expand').click()
    if width>900:
        page.wait_for_function('''theater => {
          const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,panel=root.querySelector('.sidecar').getBoundingClientRect(),target=root.querySelector(theater?'.description':'.media').getBoundingClientRect(),native=document.querySelector('#playlist').getBoundingClientRect();
          return (theater?Math.abs(panel.bottom-target.bottom)<1:Math.abs(panel.height-target.height)<1)&&Math.abs(native.height-panel.height)<1;
        }''',arg=theater)
    # Native list retains independent wheel scrolling and its original handlers.
    page.locator('.viewport').evaluate('''e=>{const panel=e.getRootNode().querySelector('.sidecar'),y=panel.getBoundingClientRect().top;window.__playlistTargetY=Math.min(100,y+e.scrollTop);e.scrollTop+=y-__playlistTargetY;}''')
    page.wait_for_function('''() => Math.abs(document.querySelector('#playlist').getBoundingClientRect().y-document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.sidecar').getBoundingClientRect().y)<1''')
    before=page.locator('.viewport').evaluate('e=>e.scrollTop')
    items=page.locator('#playlist #items');box=items.bounding_box()
    page.mouse.move(box['x']+box['width']/2,max(140,box['y']+30));page.mouse.wheel(0,260)
    page.wait_for_function("document.querySelector('#playlist #items').scrollTop>0")
    assert abs(page.locator('.viewport').evaluate('e=>e.scrollTop')-before)<1
    items.evaluate('e=>e.scrollTop=0')
    page.locator('#playlist ytd-playlist-panel-video-renderer a').first.click()
    assert page.evaluate('__playlistVisit')==0
    assert page.locator('#playlist').evaluate("e=>e.parentElement.id==='secondary-inner'")
    assert_stable(page)
    if width>900:
        page.screenshot(path='/tmp/yt-min-playlist-'+('theater' if theater else 'normal')+'.png')
    page.locator('#playlist .myt-playlist-close').click()
    expect(page.locator('.sidecar')).to_be_hidden()
    expect(page.locator('main')).not_to_have_class('has-sidecar')
    expect(page.locator('#playlist')).to_be_hidden()
    # Legacy hidden panels may have no native expand control in their header.
    page.locator('.playlist-toggle').click()
    expect(page.locator('.sidecar')).to_be_visible()
    assert page.evaluate('document.querySelector("video")===__nativeVideo&&!document.querySelector("video").paused')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-watch-island]')).to_have_count(0)
    assert page.locator('#playlist').evaluate("e=>!e.hasAttribute('popover')&&e.parentElement.id==='secondary-inner'")
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_collapsed_playlist(browser,theater=False,width=1440,state='collapsed'):
    body=native_watch_fixture(theater).replace('<div id="secondary-inner"></div>','<div id="secondary-inner">'+playlist_panel_fixture()+'</div>')
    page=setup(browser,'/watch?v=native&list=fixture',body,native_dark=True,width=width,language='ru')
    page.evaluate(VIDEO_STREAM)
    page.evaluate('''state=>{
      const panel=document.querySelector('#playlist'),items=panel.querySelector('#items'),button=panel.querySelector('#header button');
      window.__originalPlaylist=panel;window.__playlistToggleCalls=0;window.__playlistState=state;
      button.id='expand-collapse-button';button.setAttribute('aria-label','Hide playlist');
      button.onclick=()=>{
        window.__playlistToggleCalls++;
        const collapsed=state==='collapsed'?panel.hasAttribute('collapsed'):state==='class'?panel.classList.contains('is-collapsed'):panel.hidden;
        if(state==='collapsed'){panel.toggleAttribute('collapsed',!collapsed);items.hidden=!collapsed;}
        else if(state==='class'){panel.classList.toggle('is-collapsed',!collapsed);items.style.display=collapsed?'block':'none';}
        else panel.hidden=!collapsed;
        button.setAttribute('aria-label',collapsed?'Hide playlist':'Open playlist');
      };
    }''',state)
    expect(page.locator('.sidecar')).to_be_visible()
    expect(page.locator('.playlist-toggle')).to_be_hidden()
    page.locator('#playlist .myt-playlist-close').click()
    expect(page.locator('.sidecar')).to_be_hidden()
    expect(page.locator('main')).not_to_have_class('has-sidecar')
    opener=page.locator('.playlist-toggle')
    expect(opener).to_be_visible();expect(opener).to_have_text('Playlist')
    expect(opener).to_have_attribute('aria-expanded','false')
    page.wait_for_function('''() => {
      const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,view=root.querySelector('.viewport'),info=root.querySelector('.details').getBoundingClientRect(),media=root.querySelector('.media').getBoundingClientRect();
      return Math.abs(info.left*2+info.width-view.clientWidth)<1&&Math.abs(media.left*2+media.width-view.clientWidth)<1;
    }''')
    # Collapsed playlists keep the same compact action location in both modes.
    page.locator('ytd-watch-flexy').evaluate('e=>e.toggleAttribute("theater")')
    expect(opener).to_be_visible();expect(page.locator('.sidecar')).to_be_hidden()
    page.wait_for_function('''() => {
      const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,b=root.querySelector('.details').getBoundingClientRect();return Math.abs(b.left*2+b.width-root.querySelector('.viewport').clientWidth)<1;
    }''')
    opener.scroll_into_view_if_needed()
    actions=page.locator('.actions').bounding_box();info=page.locator('.details').bounding_box();box=opener.bounding_box()
    assert box['x']>=info['x'] and box['x']+box['width']<=info['x']+info['width']+1,(box,info)
    assert abs(box['y']-actions['y'])<1,(box,actions)
    if width>900:
        more=page.locator('.more-toggle').bounding_box()
        assert box['x']+box['width']<=more['x']+1,(box,more)
        page.locator('.meta-row').screenshot(path='/tmp/yt-min-collapsed-playlist-action.png')
    assert_stable(page)
    opener.click()
    expect(page.locator('.sidecar')).to_be_visible();expect(opener).to_be_hidden()
    assert page.evaluate('__playlistToggleCalls')==2
    assert page.evaluate('document.querySelector("#playlist")===__originalPlaylist&&document.querySelector("video")===__nativeVideo&&document.querySelector("video").parentElement===__nativeVideoParent&&!document.querySelector("video").paused')
    # Reopening again continues using the same native state and media.
    page.locator('.viewport').evaluate('''e=>{const panel=e.getRootNode().querySelector('.sidecar');e.scrollTop+=panel.getBoundingClientRect().top-100;}''')
    page.wait_for_function('''() => Math.abs(document.querySelector('#playlist').getBoundingClientRect().y-document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.sidecar').getBoundingClientRect().y)<1''')
    page.locator('#playlist .myt-playlist-close').click()
    expect(opener).to_be_visible();expect(page.locator('.sidecar')).to_be_hidden()
    opener.focus();opener.press('Enter')
    expect(page.locator('.sidecar')).to_be_visible()
    assert page.evaluate('__playlistToggleCalls')==4
    page.locator('.viewport').evaluate('''e=>{const panel=e.getRootNode().querySelector('.sidecar');e.scrollTop+=panel.getBoundingClientRect().top-100;}''')
    page.wait_for_function('''() => Math.abs(document.querySelector('#playlist').getBoundingClientRect().y-document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.sidecar').getBoundingClientRect().y)<1''')
    page.locator('#playlist .myt-playlist-close').click()
    expect(opener).to_be_visible()
    navigate_spa(page,'/watch?v=other-video')
    expect(opener).to_be_hidden()
    expect(page.locator('.sidecar')).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-watch')).to_have_count(0)
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
    page.close()


def check_description_link_styles(browser,width=1440):
    page=setup(browser,'/watch?v=native',native_watch_fixture(),native_dark=True,width=width)
    long_url='https://example.com/'+'long-link-'*40
    html=f'''<p>Telegram: <a href="https://t.me/maksklg" onclick="event.preventDefault();window.__descriptionVisit=this.href">t.me/maksklg</a> и <a href="{long_url}" onclick="event.preventDefault();window.__descriptionVisit=this.href">{long_url}</a></p><p><a href="/watch?v=native&t=42" onclick="event.preventDefault()">0:42</a></p>'''
    page.locator('#attributed-description-text').evaluate('(e,html)=>e.innerHTML=html',html)
    page.evaluate('document.querySelector("#expand").onclick=()=>{}')
    page.locator('.expand').click()
    links=page.locator('.prose a')
    expect(links).to_have_count(3)
    expect(links.first).to_have_text('t.me/maksklg')
    expect(links.locator('.link-symbol')).to_have_count(3)
    for link in links.all():
        expect(link).to_have_css('font-weight','700')
        expect(link.locator('.link-symbol')).to_have_attribute('aria-hidden','true')
    expect(page.locator('.prose button')).to_have_count(0)
    links.first.locator('.link-symbol').click()
    assert page.evaluate('__descriptionVisit')=='https://t.me/maksklg'
    links.nth(2).click()
    assert page.locator('video').evaluate('e=>e.currentTime')==42
    assert page.locator('.viewport').evaluate('e=>e.scrollWidth===e.clientWidth')
    if width==1440:page.locator('.description').screenshot(path='/tmp/yt-min-description-links.png')
    assert_stable(page)
    page.close()


def check_theater_responsive_width(browser):
    page=setup(browser,'/watch?v=native',native_watch_fixture(theater=True),native_dark=True,prune_data=True)
    page.evaluate(VIDEO_STREAM)
    page.locator('#attributed-description-text').evaluate("e=>e.textContent='W'.repeat(5000)")
    # YouTube can retain very wide inline sizes from its previous layout.
    page.locator('#movie_player').evaluate("e=>{e.style.width='5000px';e.style.minWidth='5000px';e.querySelector('video').style.width='5000px';}")
    for width in [1920,1280,768,390,1440]:
        page.set_viewport_size({'width':width,'height':700})
        page.wait_for_function('''() => {
          const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot,media=root.querySelector('.media').getBoundingClientRect(),video=document.querySelector('video').getBoundingClientRect(),view=root.querySelector('.viewport');
          return media.x===0&&Math.abs(media.width-view.clientWidth)<1&&Math.abs(video.width-media.width)<1&&Math.abs(video.x-media.x)<1&&media.width<=innerWidth&&view.scrollWidth===view.clientWidth;
        }''')
        assert page.locator('.media').bounding_box()['width']<=width
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
    assert_stable(page)
    page.close()


def check_background_work(browser):
    results={}
    probe="""async () => {
      const clock=document.querySelector('#clock');let queries=0,syncs=0;const methods=[];
      for(const proto of [Document.prototype,Element.prototype])for(const name of ['querySelector','querySelectorAll']){
        const original=proto[name];methods.push([proto,name,original]);proto[name]=function(...args){queries++;return original.apply(this,args);};
      }
      const original=MinimalYouTubeWatch.prototype.sync;
      MinimalYouTubeWatch.prototype.sync=function(...args){syncs++;return original.apply(this,args);};
      try {
        for(let i=0;i<40;i++){clock.textContent=String(i);clock.setAttribute('aria-label','Playback '+i);await new Promise(requestAnimationFrame);}
        await new Promise(requestAnimationFrame);return{queries,syncs};
      } finally {for(const[proto,name,method]of methods)proto[name]=method;MinimalYouTubeWatch.prototype.sync=original;}
    }"""
    for path,body in [('/', '<ytd-app><div id="clock">0</div></ytd-app>'),('/watch?v=native',native_watch_fixture())]:
        page=setup(browser,path,body,native_dark=True)
        page.wait_for_timeout(100)
        result=page.evaluate(probe)
        assert result['syncs']==0 and result['queries']<10, (path,result)
        results[path]=result
        if path=='/':
            page.evaluate("document.documentElement.removeAttribute('dark')")
            expect(page.locator('#myt-home')).to_have_attribute('data-myt-theme','light')
            page.evaluate("document.documentElement.setAttribute('dark','')")
            expect(page.locator('#myt-home')).to_have_attribute('data-myt-theme','dark')
        else:
            page.locator('ytd-watch-metadata h1').evaluate("e=>e.textContent='Actual metadata change'")
            expect(page.locator('#watch-title')).to_have_text('Actual metadata change')
        page.close()
    print('Background mutation profile:',results)
    page=setup(browser,'/', '<ytd-app><ytd-browse page-subtype="home"><video muted></video></ytd-browse></ytd-app>')
    paused=page.evaluate("""async()=>{
      const canvas=document.createElement('canvas');canvas.width=2;canvas.height=2;
      const video=document.querySelector('video');const stream=canvas.captureStream(10);video.srcObject=stream;video.muted=true;
      video.play().catch(()=>{});canvas.getContext('2d').fillRect(0,0,2,2);
      await new Promise(resolve=>setTimeout(resolve,100));const paused=video.paused;stream.getTracks().forEach(track=>track.stop());return paused;
    }""")
    assert paused is True, 'Hidden homepage preview keeps decoding in the background'
    page.close()


def open_watch_item(page,name):
    page.locator('.more-toggle').click()
    if name=='Comments':page.locator('.more-popup #myt-comments-toggle').click()
    else:page.locator('.more-popup').get_by_role('menuitem',name=name,exact=True).click()


def check_watch_details(browser, dark, width=1440, legacy=False):
    fixture = watch_details_fixture(legacy)
    actions = '''<div id="top-row"><div id="owner"><a href="/@revolt"><img alt="" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4="><span id="channel-name">REVOLT</span></a><div id="subscribe-button"><button onclick="window.__subscribe=true">Subscribe</button></div></div><div id="actions"><div id="top-level-buttons-computed"><segmented-like-dislike-button-view-model id="video-votes"><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model><button id="share" onclick="window.__share=true;document.querySelector('#share-dialog').hidden=false">Share</button><button id="save" onclick="window.__save=true">Save</button><button id="more" onclick="window.__other=true;document.querySelector('#native-more-dialog').hidden=false">More</button></div></div></div>'''
    fixture = fixture.replace('<div id="description" class=', actions + '<div id="description" class=',1)
    fixture = fixture.replace('</div></div>\n        <div id="secondary">', '<ytd-comments id="comments"><input id="reply-draft" aria-label="Reply"></ytd-comments></div></div>\n        <div id="secondary">',1)
    fixture += '<ytd-popup-container><div id="share-dialog" role="dialog" hidden style="position:fixed;inset:100px auto auto 100px;padding:30px;background:white;color:black"><button onclick="this.parentElement.hidden=true">Close share dialog</button></div><div id="native-more-dialog" role="menu" hidden style="position:fixed;inset:100px auto auto 100px;padding:30px;background:white;color:black"><button onclick="this.parentElement.hidden=true">Close native menu</button></div></ytd-popup-container>'
    page = setup(browser, '/watch?v=details', fixture, native_dark=dark, width=width)
    expect(page.locator('#myt-watch')).to_be_visible()
    expect(page.locator('#watch-title')).to_have_text('Music, life and the stories behind it')
    assert page.locator('#myt-watch').evaluate("e => e.matches(':popover-open')")
    assert page.locator('ytd-watch-flexy').evaluate("e => !e.matches(':popover-open') && e.parentElement.matches('ytd-page-manager')")
    assert page.locator('#player').evaluate("e=>e.matches(':popover-open')")
    page.evaluate("window.__originalWatch=document.querySelector('ytd-watch-flexy');window.__originalVideo=document.querySelector('video');window.__playerParent=document.querySelector('video').parentElement")
    assert page.locator('#myt-watch').bounding_box() == {'x':0,'y':0,'width':width,'height':960}
    assert page.locator('#watch-description').evaluate('e => !e.querySelector("[style],script,yt-formatted-string,ytd-structured-description-content-renderer")')
    expect(page.locator('#watch-description')).to_have_css('font-size','16px' if width <= 600 else '17px')
    page.locator('.expand').click()
    expect(page.locator('.expand')).to_have_attribute('aria-expanded','true')
    expect(page.locator('#expanded')).to_be_hidden()  # Native UI remains covered.
    expect(page.locator('#watch-description')).to_contain_text('Discover the stories')
    expect(page.locator('#watch-chapters .chapter')).to_have_count(2)
    expect(page.locator('#watch-chapters img')).to_have_count(0)
    cards = page.locator('.chapter').all()
    first, second = [card.bounding_box() for card in cards]
    assert second['x'] >= first['x']+first['width']+11 and abs(second['y']-first['y']) < 1
    assert cards[0].evaluate('e=>getComputedStyle(e).backgroundColor') != page.locator('#myt-watch .viewport').evaluate('e=>getComputedStyle(e).backgroundColor')
    cards[1].click()
    assert page.evaluate('window.__chapter') == 165
    page.locator('.person').first.click()
    assert page.evaluate('window.__person') is True
    page.locator('.socials a').click()
    assert page.evaluate('window.__social') is True
    expect(page.locator('#watch-description a').first).to_have_attribute('href','https://example.com/show')
    expect(page.locator('#watch-transcript')).to_be_hidden()
    expect(page.locator('.actions > #myt-comments-toggle')).to_have_count(0)
    open_watch_item(page,'Video transcript')
    expect(page.locator('.transcript-toggle')).to_have_attribute('aria-expanded','true')
    expect(page.locator('.more-popup')).to_be_hidden()
    expect(page.locator('.segment')).to_have_count(1)
    expect(page.locator('.segment')).to_contain_text('Introduction')
    page.locator('.transcript-search').fill('missing phrase')
    expect(page.locator('.segment')).to_have_count(0)
    expect(page.locator('.transcript-status')).to_have_text('No matches')
    page.locator('.transcript-search').fill('Intro')
    expect(page.locator('.segment')).to_have_count(1)
    page.locator('.transcript-toggle').click()
    expect(page.locator('#watch-transcript-content')).to_be_hidden()
    expect(page.locator('#transcript-panel')).to_have_attribute('visibility','ENGAGEMENT_PANEL_VISIBILITY_HIDDEN')
    if dark and width == 1440 and not legacy:
        # Real YouTube can create the panel only after the first request.
        page.locator('#transcript-panel').evaluate('e=>e.remove()')
        page.locator('#open-transcript').evaluate("e=>e.onclick=()=>document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend','<ytd-engagement-panel-section-list-renderer id=transcript-panel target-id=engagement-panel-searchable-transcript visibility=ENGAGEMENT_PANEL_VISIBILITY_EXPANDED><ytd-transcript-renderer><ytd-transcript-segment-renderer>2:45 Introduction after late loading</ytd-transcript-segment-renderer></ytd-transcript-renderer></ytd-engagement-panel-section-list-renderer>')")
        open_watch_item(page,'Video transcript')
        expect(page.locator('.segment')).to_contain_text('Introduction after late loading')
        page.locator('.transcript-toggle').click()
        expect(page.locator('#transcript-panel')).to_have_attribute('visibility','ENGAGEMENT_PANEL_VISIBILITY_HIDDEN')
    toggle = page.locator('#myt-comments-toggle')
    if not legacy:
        open_watch_item(page,'Comments')
        expect(page.locator('#comments')).to_be_visible()
        page.locator('#reply-draft').fill('Keep this native reply')
        open_watch_item(page,'Comments')
        expect(page.locator('#comments')).to_be_hidden()
        open_watch_item(page,'Comments')
        expect(page.locator('#reply-draft')).to_have_value('Keep this native reply')
        open_watch_item(page,'Comments')
        subscription=page.locator('.channel-subscribe')
        box=subscription.bounding_box()
        subscription.click(position={'x':box['width']-12,'y':box['height']/2})
        assert page.evaluate('window.__subscribe') is True
        expect(page.locator('.actions > button').filter(has_text='Share')).to_have_count(0)
        expect(page.locator('.more-popup')).to_be_hidden()
        page.locator('.more-toggle').click()
        expect(page.locator('.more-toggle')).to_have_attribute('aria-expanded','true')
        expect(page.locator('.more-popup button').first).to_be_focused()
        popup=page.locator('.more-popup').bounding_box()
        assert 0 <= popup['x'] and popup['x']+popup['width'] <= width
        assert 0 <= popup['y'] and popup['y']+popup['height'] <= 960
        page.locator('.more-popup').get_by_role('menuitem',name='Share',exact=True).click()
        expect(page.locator('.more-popup')).to_be_hidden()
        assert page.evaluate('window.__share') is True
        expect(page.locator('#share-dialog')).to_be_visible()
        page.get_by_role('button',name='Close share dialog').click()
        # Save is an owned control that presses YouTube's own; votes are not offered.
        actions_row = page.locator('#myt-watch .actions')
        expect(actions_row.get_by_role('button',name='Like',exact=True)).to_have_count(0)
        expect(actions_row.get_by_role('button',name='Dislike',exact=True)).to_have_count(0)
        actions_row.get_by_role('button',name='Save',exact=True).click()
        assert page.evaluate('window.__save') is True
        # Keyboard navigation and light dismissal must retain native More actions.
        page.locator('.more-toggle').press('Enter')
        expect(page.locator('.more-popup button').first).to_be_focused()
        page.locator('.more-popup button').first.press('ArrowUp')
        expect(page.locator('.more-popup button').last).to_be_focused()
        page.locator('.more-popup button').last.press('Enter')
        assert page.evaluate('window.__other') is True
        expect(page.locator('#native-more-dialog')).to_be_visible()
        page.get_by_role('button',name='Close native menu').click()
        page.locator('.more-toggle').click()
        page.locator('.more-popup button').first.press('Escape')
        expect(page.locator('.more-popup')).to_be_hidden()
        expect(page.locator('.more-toggle')).to_be_focused()
        page.locator('.more-toggle').click()
        page.locator('#watch-title').click()
        expect(page.locator('.more-popup')).to_be_hidden()
    # Dynamic native data refreshes only the own view; original components stay put.
    page.locator('ytd-watch-flexy h1').evaluate("e=>e.textContent='Updated video title'")
    expect(page.locator('#watch-title')).to_have_text('Updated video title')
    assert page.evaluate('window.__originalVideo===document.querySelector("video") && window.__playerParent===document.querySelector("video").parentElement')
    if dark and width == 1440 and not legacy:
        page.locator('video').evaluate('e=>e.requestFullscreen()')
        assert page.evaluate('document.fullscreenElement.localName') == 'video'
        assert page.locator('video').bounding_box() == {'x':0,'y':0,'width':width,'height':960}
        page.evaluate('document.exitFullscreen()')
        expect(page.locator('#myt-watch')).to_be_visible()
        assert page.locator('#player').evaluate("e=>e.matches(':popover-open')")
        page.locator('ytd-watch-flexy').evaluate("e=>e.setAttribute('theater','')")
        expect(page.locator('#myt-watch > div')).to_have_attribute('theater','')
        page.locator('ytd-watch-flexy').evaluate("e=>e.removeAttribute('theater')")
        page.locator('#secondary-inner').evaluate("e=>e.insertAdjacentHTML('beforeend','<ytd-playlist-panel-renderer id=playlist><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer>')")
        expect(page.locator('#myt-watch .sidecar')).to_be_visible()
        expect(page.locator('#playlist')).to_be_visible()
        assert page.locator('#playlist').evaluate("e=>e.matches(':popover-open')&&e.parentElement.id==='secondary-inner'")
        page.locator('#playlist').evaluate('e=>e.remove()')
        expect(page.locator('#myt-watch .sidecar')).to_be_hidden()
    # Adversarial native styling reproduces the backdrop/ancestor problem that
    # plain recoloring failed to fix. The own top layer must remain unaffected.
    page.add_style_tag(content='''body { transform:translateY(80px);filter:brightness(.5);min-height:3200px;background:linear-gradient(red,blue)!important; } div { filter:brightness(.4)!important; }''')
    page.evaluate("""() => {const band=document.createElement('div');band.id='external-band';band.style.cssText='position:fixed;inset:20vh 0 30vh;background:#000;z-index:2147483647;pointer-events:none';document.documentElement.append(band);} """)
    expected = '16,16,18,255' if dark else '249,249,251,255'
    for offset in [0,450,1100,2200,6000]:
        page.locator('#myt-watch .viewport').evaluate('(e,y)=>e.scrollTop=y',offset)
        png=page.screenshot(animations='disabled')
        pixels=page.evaluate("""async encoded => {
          const image=await createImageBitmap(await(await fetch('data:image/png;base64,'+encoded)).blob());
          const context=new OffscreenCanvas(image.width,image.height).getContext('2d');context.drawImage(image,0,0);
          const pixels=[];for(let y=0;y<image.height;y+=60) for(const x of [2,document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.viewport').clientWidth-2]) pixels.push([...context.getImageData(x,y,1,1).data].join(','));
          return [...new Set(pixels)];
        }""",base64.b64encode(png).decode())
        assert pixels == [expected], (width,offset,pixels)
    assert page.locator('#myt-watch .viewport').evaluate('e=>e.scrollWidth<=e.clientWidth'), 'Own buttons or cards cause horizontal overflow'
    assert page.locator('#myt-watch button').evaluate_all("nodes=>nodes.filter(e=>e.getClientRects().length).every(e=>e.getBoundingClientRect().height>=(e.matches('.owner .primary')?35.5:43.5) && e.clientWidth>=e.scrollWidth-1)"), 'Own button text clips or the touch target is too short'

    if width==1440 and not legacy:
        page.locator('#watch-chapters').scroll_into_view_if_needed()
        page.screenshot(path=f'/tmp/yt-min-own-watch-{"dark" if dark else "light"}.png')
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-watch,[data-myt-watch-island]')).to_have_count(0)
    assert page.evaluate('window.__originalWatch===document.querySelector("ytd-watch-flexy") && window.__originalVideo===document.querySelector("video")')
    assert page.locator('ytd-watch-flexy').get_attribute('popover') is None
    assert page.locator('ytd-watch-flexy').get_attribute('style') is None
    page.evaluate('__setEnabled(true)')
    expect(page.locator('#myt-watch')).to_be_visible()
    navigate_spa(page,'/watch?v=another')
    expect(page.locator('#myt-watch')).to_have_count(1)
    if not legacy: expect(page.locator('#myt-comments-toggle')).to_have_attribute('aria-expanded','false')
    page.evaluate("document.querySelector('ytd-watch-flexy').hidden=true;document.querySelector('ytd-page-manager').insertAdjacentHTML('beforeend','<ytd-search>Results</ytd-search>')")
    navigate_spa(page,'/results?search_query=details')
    expect(page.locator('#myt-watch,[data-myt-watch-island]')).to_have_count(0)
    page.close()



def check_subscription_card(browser, dark, width, modern=False, search=False):
    avatar='data:image/svg+xml;base64,'+base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="46" height="46"><rect width="46" height="46" rx="23" fill="#ef493c"/></svg>').decode()
    renderer='yt-subscribe-button-view-model' if modern else 'ytd-subscribe-button-renderer'
    state=' aria-pressed="true"' if modern else ''
    owner=f'''<div id="owner"><a id="avatar" href="/@revolt"><img src="{avatar}"></a><ytd-channel-name><a href="/@revolt">REVOLT</a></ytd-channel-name><span id="subscriber-count">3.33M subscribers</span><{renderer} id="subscribe-button"><button id="native-subscribe"{state}>{'Subscribed' if modern else 'Subscribe'}</button></{renderer}></div>'''
    body=watch_details_fixture().replace('<div id="description" class=',owner+'<div id="description" class=',1)+'<ytd-popup-container></ytd-popup-container>'
    if search:body='<ytd-app>'+MASTHEAD+'<ytd-search><ytd-section-list-renderer><div id="contents"><ytd-channel-renderer>'+owner+'</ytd-channel-renderer></div></ytd-section-list-renderer></ytd-search></ytd-app><ytd-popup-container></ytd-popup-container>'
    page=setup(browser,'/results?search_query=revolt' if search else '/watch?v=details',body,native_dark=dark,width=width,language='ru')
    page.evaluate('''() => {
      window.__subscribeCalls=0;window.__channelVisits=0;
      for(const a of document.querySelectorAll('#owner a'))a.onclick=e=>{e.preventDefault();window.__channelVisits++;};
      window.__setSubscribed=value=>{
        const source=document.querySelector('#native-subscribe');
        if(source.hasAttribute('aria-pressed'))source.setAttribute('aria-pressed',String(value));
        else source.parentElement.toggleAttribute('subscribed',value);
        source.textContent=value?'Subscribed':'Subscribe';
      };
      document.querySelector('#native-subscribe').onclick=()=>{
        window.__subscribeCalls++;
        const source=document.querySelector('#native-subscribe'),popups=document.querySelector('ytd-popup-container');
        const subscribed=source.getAttribute('aria-pressed')==='true'||source.parentElement.hasAttribute('subscribed');
        if(window.__signInRequired){popups.innerHTML='<div role="dialog" id="sign-in-dialog">Sign in to subscribe<button id="confirm-button" onclick="window.__wrongConfirm=true">Sign in</button></div>';return;}
        if(subscribed&&window.__useUnsubMenu){
          setTimeout(()=>{
            popups.innerHTML='<ytd-menu-service-item-renderer role="menuitem" data-test-unsubscribe-ui>Unsubscribe</ytd-menu-service-item-renderer>';
            popups.firstElementChild.onclick=()=>{
              window.__unsubscribeMenu=true;
              popups.innerHTML='<yt-confirm-dialog-renderer role="dialog" style="display:block;position:fixed;inset:180px auto auto 80px;padding:30px;background:white;color:black;opacity:1;transition:opacity .25s"><div id="confirm-button"><button>Unsubscribe</button></div></yt-confirm-dialog-renderer>';
              popups.querySelector('button').onclick=()=>{
                window.__unsubscribeConfirm=true;
                if(window.__slowUnsubscribe){
                  popups.firstElementChild.dataset.testUnsubscribeUi='';
                  const backdrop=document.createElement('tp-yt-iron-overlay-backdrop');backdrop.setAttribute('opened','');backdrop.dataset.testUnsubscribeUi='';backdrop.style.cssText='position:fixed;inset:0;background:#0009;opacity:1;transition:opacity .25s;';document.body.append(backdrop);
                  setTimeout(()=>{window.__setSubscribed(false);setTimeout(()=>{popups.replaceChildren();backdrop.remove();},350);},120);
                }else{window.__setSubscribed(false);popups.replaceChildren();}
              };
            };
          },0);
        }else window.__setSubscribed(!subscribed);
      };
    }''')
    card=page.locator('.channel-card');button=page.locator('.channel-subscribe')

    def click_background():
        box=button.bounding_box()
        button.click(position={'x':box['width']-12,'y':box['height']/2})

    expect(button).to_have_attribute('aria-pressed',str(modern).lower())
    expect(card.locator('.stats')).to_have_text('3.33M subscribers' if search else '906.35k · 8 March 2025')
    if not search:
        expect(page.locator('#watch-chapters h2')).to_have_count(0)
        expect(page.locator('#watch-chapters')).to_have_attribute('aria-label','Chapters')
    assert card.evaluate('e=>getComputedStyle(e).backgroundColor')!=page.locator('html' if search else '.viewport').evaluate('e=>getComputedStyle(e).backgroundColor')
    page.evaluate('__setSubscribed(false)')
    expect(button).to_have_attribute('aria-pressed','false')
    card.scroll_into_view_if_needed()
    page.mouse.move(0,0)
    original_color=card.evaluate('e=>getComputedStyle(e).backgroundColor')
    expect(card.locator('.subscription-state svg')).to_have_count(0)
    box=card.bounding_box()
    card.click(position={'x':box['width']-12,'y':box['height']/2})
    expect(button).to_have_attribute('aria-pressed','true')
    expect(button).to_be_enabled()
    page.mouse.move(0,0)
    assert card.evaluate('e=>getComputedStyle(e).backgroundColor')!=original_color
    assert page.evaluate('__subscribeCalls')==1
    for selector in ['.owner-name','.owner img']:
        page.locator(selector).click()
    assert page.evaluate('__channelVisits')==2 and page.evaluate('__subscribeCalls')==1
    button.focus();button.press('Enter')
    expect(button).to_have_attribute('aria-pressed','false')
    expect(button).to_be_focused()
    page.mouse.move(0,0)
    assert card.evaluate('e=>getComputedStyle(e).backgroundColor')==original_color
    if not dark and width==390:card.screenshot(path='/tmp/yt-min-channel-card-light.png')
    button.press('Space')
    expect(button).to_have_attribute('aria-pressed','true')
    if dark and width==1440:card.screenshot(path='/tmp/yt-min-channel-card-subscribed.png')
    page.evaluate('''() => {
      window.__useUnsubMenu=true;window.__slowUnsubscribe=true;window.__unsubscribePainted=[];
      const end=performance.now()+750;
      const frame=()=>{
        for(const node of document.querySelectorAll('[data-test-unsubscribe-ui]')){
          let visible=Boolean(node.getClientRects().length);
          for(let parent=node;parent&&visible;parent=parent.parentElement){const style=getComputedStyle(parent);if(style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0)visible=false;}
          if(visible)window.__unsubscribePainted.push(node.localName);
        }
        if(performance.now()<end)requestAnimationFrame(frame);else window.__unsubscribeCaptureDone=true;
      };requestAnimationFrame(frame);
    }''')
    click_background()
    expect(button).to_have_attribute('aria-pressed','false')
    assert page.evaluate('__unsubscribeMenu&&__unsubscribeConfirm')
    rapid=modern and width==390
    if rapid:
        button.focus();button.press('Space')
        expect(button).to_have_attribute('aria-pressed','true')
    assert page.evaluate('__subscribeCalls')==(5 if rapid else 4)
    page.wait_for_function('window.__unsubscribeCaptureDone')
    assert page.evaluate('__unsubscribePainted')==[], 'Native unsubscribe confirmation or backdrop flashed while opening/closing'
    expect(page.locator('[data-myt-subscription-transient]')).to_have_count(0)
    # An attribute-only native update must also change the card.
    if rapid:
        page.evaluate('__setSubscribed(false)')
        expect(button).to_have_attribute('aria-pressed','false')
    if modern:page.locator('#native-subscribe').evaluate('e=>e.setAttribute("aria-pressed","true")')
    else:page.locator('#subscribe-button').evaluate('e=>e.setAttribute("subscribed","")')
    expect(button).to_have_attribute('aria-pressed','true')
    page.evaluate('__setSubscribed(false);window.__signInRequired=true')
    expect(button).to_have_attribute('aria-pressed','false')
    page.clock.install()
    click_background()
    expect(button).to_have_attribute('aria-busy','true')
    expect(card).to_have_attribute('data-subscribed','false')
    expect(page.locator('#sign-in-dialog')).to_be_visible()
    assert page.locator('#sign-in-dialog').evaluate('e=>!e.closest("[data-myt-subscription-transient]")')
    assert page.evaluate('!window.__wrongConfirm')
    page.clock.fast_forward(6100)
    expect(button).to_have_attribute('aria-busy','false')
    expect(button).to_have_attribute('aria-pressed','false')
    page.locator('#native-subscribe').evaluate('e=>e.disabled=true')
    expect(button).to_be_disabled()
    assert page.locator('html' if search else '.viewport').evaluate('e=>e.scrollWidth<=e.clientWidth')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-search-channel-card]' if search else '#myt-watch')).to_have_count(0)
    page.close()


def check_unsubscribe_staged_dialog(browser, modern=False, width=1440):
    owner='<div id="owner"><a href="/@revolt"><span id="channel-name">REVOLT</span></a><ytd-subscribe-button-renderer id="subscribe-button" subscribed><button id="native-subscribe">Subscribed</button></ytd-subscribe-button-renderer></div>'
    body=watch_details_fixture().replace('<div id="description" class=',owner+'<div id="description" class=',1)+'<ytd-popup-container></ytd-popup-container>'
    page=setup(browser,'/watch?v=details',body,width=width)
    page.evaluate('''modern => {
      window.__stagedPainted=[];
      document.querySelector('#native-subscribe').onclick=()=>{
        const popups=document.querySelector('ytd-popup-container');
        const outer=document.createElement('tp-yt-paper-dialog');outer.setAttribute('role','dialog');outer.dataset.testUnsubStage='';
        outer.style.cssText='display:block;position:fixed;left:60px;top:140px;width:260px;min-height:120px;padding:24px;background:white;color:black;opacity:1;transition:opacity .25s';
        const panel=document.createElement(modern?'yt-confirm-dialog-view-model':'yt-confirm-dialog-renderer');outer.append(panel);popups.append(outer);
        const backdrop=document.createElement('tp-yt-iron-overlay-backdrop');backdrop.setAttribute('opened','');backdrop.dataset.testUnsubStage='';backdrop.style.cssText='position:fixed;inset:0;background:#0009;opacity:1;transition:opacity .25s';document.body.append(backdrop);
        setTimeout(()=>panel.innerHTML='<h2>Вы хотите отписаться от канала?</h2>',50);
        setTimeout(()=>{
          panel.insertAdjacentHTML('beforeend',modern?'<button>Отписаться</button>':'<div id="confirm-button"><button>Unsubscribe</button></div>');
          panel.querySelector('button').onclick=()=>{
            window.__stagedConfirmed=true;
            document.querySelector('#subscribe-button').removeAttribute('subscribed');document.querySelector('#native-subscribe').textContent='Subscribe';
            setTimeout(()=>{outer.remove();backdrop.remove();},300);
          };
        },110);
        const end=performance.now()+750;
        const frame=()=>{
          for(const node of document.querySelectorAll('[data-test-unsub-stage]')){
            let visible=Boolean(node.getClientRects().length);
            for(let parent=node;parent&&visible;parent=parent.parentElement){const style=getComputedStyle(parent);if(style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0)visible=false;}
            if(visible)window.__stagedPainted.push(node.localName);
          }
          if(performance.now()<end)requestAnimationFrame(frame);else window.__stagedCaptureDone=true;
        };requestAnimationFrame(frame);
      };
    }''',modern)
    button=page.locator('.channel-subscribe')
    expect(button).to_have_attribute('aria-pressed','true')
    box=button.bounding_box()
    button.click(position={'x':box['width']-12,'y':box['height']/2})
    expect(button).to_have_attribute('aria-pressed','false',timeout=2000)
    page.wait_for_function('window.__stagedCaptureDone')
    assert page.evaluate('__stagedConfirmed')
    assert page.evaluate('__stagedPainted')==[], 'Partially rendered unsubscribe panel or its outer window painted before the buttons mounted'
    expect(page.locator('[data-myt-subscription-transient]')).to_have_count(0)
    page.close()


def check_collaboration_card(browser, width, attributed=False):
    avatar=lambda color:'data:image/svg+xml;base64,'+base64.b64encode(f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect width="48" height="48" rx="24" fill="{color}"/></svg>'.encode()).decode()
    first,second=avatar('#df493c'),avatar('#527bd6')
    if attributed:
        owner=f'''<yt-video-owner-view-model><yt-avatar-stack-view-model><button id="native-authors-avatars"><img src="{first}"><img src="{second}"></button></yt-avatar-stack-view-model><button id="native-authors"><yt-attributed-string>Первый канал и Второй канал</yt-attributed-string></button><div id="subscribe-button"><button id="native-collab-subscribe" aria-pressed="false">Subscribe</button></div></yt-video-owner-view-model>'''
    else:
        owner=f'''<div id="owner"><yt-avatar-stack-view-model><a href="/@first"><img src="{first}"></a><a href="/channel/second"><img src="{second}"></a></yt-avatar-stack-view-model><yt-attributed-string><a href="/@first">Первый канал</a> и <a href="/channel/second">Второй канал</a></yt-attributed-string><div id="subscribe-button"><button id="native-collab-subscribe" aria-pressed="false">Subscribe</button></div></div>'''
    page=setup(browser,'/watch?v=native',native_watch_fixture(),width=width,language='ru')
    if attributed:owner='<div id=owner hidden><a href="/@old">Устаревший канал</a></div>'+owner
    page.locator('#owner').evaluate('(e,html)=>e.outerHTML=html',owner)
    page.evaluate('''() => {
      window.__authorVisits=[];window.__authorsOpened=0;window.__collabSubscriptions=0;
      for(const link of document.querySelectorAll('ytd-watch-metadata a[href^="/@"],ytd-watch-metadata a[href^="/channel/"]'))link.onclick=event=>{event.preventDefault();__authorVisits.push(new URL(link.href).pathname);};
      for(const button of document.querySelectorAll('#native-authors,#native-authors-avatars'))button.onclick=()=>__authorsOpened++;
      document.querySelector('#native-collab-subscribe').onclick=function(){__collabSubscriptions++;const subscribed=this.getAttribute('aria-pressed')==='true';this.setAttribute('aria-pressed',String(!subscribed));this.textContent=subscribed?'Subscribe':'Subscribed';};
    }''')
    names=page.locator('.owner-name')
    expect(names).to_have_count(1 if attributed else 2)
    expect(page.locator('.channel-card')).to_contain_text('Первый канал')
    expect(page.locator('.channel-card')).to_contain_text('Второй канал')
    expect(page.locator('.channel-card')).not_to_contain_text('Устаревший канал')
    expect(page.locator('.owner img')).to_have_count(2)
    expect(page.locator('.channel-card')).to_have_attribute('data-collaborative','')
    expect(page.locator('.channel-card .stats')).to_have_text('906.35k')
    for name in names.all():name.click()
    for avatar_link in page.locator('.owner .avatar-link').all():avatar_link.click()
    if attributed:assert page.evaluate('__authorsOpened')==3
    else:assert page.evaluate('__authorVisits')==['/@first','/channel/second','/@first','/channel/second']
    assert page.evaluate('__collabSubscriptions')==0
    button=page.locator('.channel-subscribe');box=button.bounding_box();button.click(position={'x':box['width']-10,'y':box['height']/2})
    expect(button).to_have_attribute('aria-pressed','true')
    assert page.evaluate('__collabSubscriptions')==1
    card=page.locator('.channel-card').bounding_box();assert card['x']>=0 and card['x']+card['width']<=width+1,card
    assert page.locator('.viewport').evaluate('e=>e.scrollWidth<=e.clientWidth')
    if width==1440:page.locator('.channel-card').screenshot(path='/tmp/yt-min-collaboration-'+str(attributed)+'.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-watch')).to_have_count(0)
    page.close()


def check_local_title_fonts(browser):
    page=setup(browser,'/watch?v=details',watch_details_fixture(),native_dark=True,watch_ui=False)
    requests=[]

    def font_resource(route):
        name=route.request.url.rsplit('/',1)[-1]
        assert name in ['BarlowCondensed-BlackItalic.ttf','MinimalCondensed-BlackItalic.ttf']
        requests.append(name)
        route.fulfill(status=200,content_type='font/ttf',body=(ROOT/'src/assets/fonts'/name).read_bytes())

    page.route('https://www.youtube.com/__minimal_fonts__/*',font_resource)
    page.evaluate('''() => {
      chrome.runtime.getURL=path=>'https://www.youtube.com/__minimal_fonts__/'+path.split('/').pop();
      const policy=document.createElement('meta');policy.httpEquiv='Content-Security-Policy';policy.content="font-src 'none'";document.head.append(policy);
    }''')
    page.add_script_tag(path=str(ROOT/'src/content/watch.js'))
    page.evaluate("document.dispatchEvent(new Event('yt-navigate-finish'))")
    expect(page.locator('#myt-watch')).to_be_visible()
    page.wait_for_function("[...document.fonts].some(f=>f.family.includes('Barlow')&&f.status==='loaded')")
    assert requests==['BarlowCondensed-BlackItalic.ttf'], 'The Cyrillic fallback should load only when a title needs it'
    session=page.context.new_cdp_session(page)
    session.send('DOM.enable');session.send('CSS.enable')

    def title_fonts():
        page.evaluate('async()=>{await document.fonts.ready;await new Promise(requestAnimationFrame);}')
        session.send('DOM.getDocument',{'depth':-1,'pierce':True})
        obj=session.send('Runtime.evaluate',{'expression':'document.querySelector("#myt-watch").firstElementChild.shadowRoot.querySelector("#watch-title .title-outline")'})['result']['objectId']
        node=session.send('DOM.requestNode',{'objectId':obj})['nodeId']
        return session.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']

    assert any('Barlow' in f['familyName'] and f['isCustomFont'] for f in title_fonts())
    def capture_title(name):
        page.locator('#watch-title').evaluate('e=>{const view=e.getRootNode().querySelector(".viewport");view.scrollTop+=e.getBoundingClientRect().top-140;}')
        page.evaluate('async()=>{await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);}')
        box=page.locator('#watch-title').bounding_box()
        page.screenshot(path='/tmp/yt-min-title-'+name+'.png',clip={'x':box['x']-16,'y':box['y']-24,'width':box['width']+32,'height':box['height']+64})

    page.locator('ytd-watch-metadata h1').evaluate('e=>e.textContent="Nelly On KRS-One Beef, Iconic Band-Aid, Super Bowl Nipplegate, Industry Drama And The Stories Behind The Music | Drink Champs"')
    expect(page.locator('#watch-title')).to_contain_text('Nelly On KRS-One')
    full_title=page.locator('#watch-title').text_content()
    first_line=page.locator('#watch-title .title-outline').text_content()
    assert first_line and len(first_line)<len(full_title)
    page.set_viewport_size({'width':390,'height':960})
    page.wait_for_function('''length=>document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.title-outline').textContent.length<length''',arg=len(first_line))
    assert page.locator('#watch-title').text_content()==full_title
    page.set_viewport_size({'width':1440,'height':960})
    expect(page.locator('#watch-title .title-outline')).to_have_text(first_line)
    capture_title('barlow')
    page.locator('ytd-watch-metadata h1').evaluate('e=>e.textContent="Ледяной бастион! Восстание 2 ютуберов против 50 корейцев в Раст / RUST — история музыки и людей"')
    expect(page.locator('#watch-title')).to_contain_text('Ледяной бастион')
    page.wait_for_function("[...document.fonts].some(f=>f.family.includes('Cyrillic')&&f.status==='loaded')")
    assert any('Minimal Condensed' in f['familyName'] and f['isCustomFont'] for f in title_fonts())
    capture_title('cyrillic')
    assert requests==['BarlowCondensed-BlackItalic.ttf','MinimalCondensed-BlackItalic.ttf']
    page.locator('ytd-watch-metadata h1').evaluate('e=>e.textContent="A different video title"')
    expect(page.locator('#watch-title')).to_have_text('A different video title')
    assert len(requests)==2, 'Metadata rerenders must reuse loaded title fonts'
    page.close()


def check_watch_language_change(browser, legacy=False):
    page=setup(browser,'/watch?v=details',watch_details_fixture(legacy),language='ru')
    stats=page.locator('#myt-watch .stats')
    page.evaluate('window.__originalVideo=document.querySelector("video")')
    expect(stats).to_have_text('906.35k · 8 March 2025')
    page.evaluate("chrome.storage.local.set({language:'en'})")
    expect(stats).to_have_text('906.35k · 8 March 2025')
    page.evaluate("chrome.storage.local.set({language:'ru'})")
    expect(stats).to_have_text('906.35k · 8 March 2025')
    page.locator('#info-container').evaluate('e=>e.textContent="3,33 млн просмотров · 8 марта 2025 г."')
    expect(stats).to_have_text('3.33m · 8 March 2025')
    page.evaluate("chrome.storage.local.set({language:'en'})")
    expect(stats).to_have_text('3.33m · 8 March 2025')
    page.evaluate("chrome.storage.local.set({language:''})")
    expect(stats).to_have_text('3.33m · 8 March 2025')
    assert page.evaluate('__originalVideo===document.querySelector("video")')
    page.close()


def check_watch_stats(browser, language):
    page=setup(browser,'/watch?v=details',watch_details_fixture(),language=language)
    stats=page.locator('#myt-watch .stats')
    ru=False  # Raw source may be Russian; the extension interface is English.
    date=lambda ru_value,en_value:ru_value if ru else en_value
    expect(stats).to_have_text(('906 тыс.' if ru else '906.35k')+' · '+date('8 марта 2025 г.','8 March 2025'))
    for raw,compact in [('1234 views','1,23 тыс.' if ru else '1.23k'),('3,33 млн просмотров','3,33 млн.' if ru else '3.33m'),('1.2K views','1,2 тыс.' if ru else '1.20k'),('999999 views','1 млн.' if ru else '999.99k'),('1000 views','1.00k'),('1000000 views','1.00m'),('1000000000 views','1.00b'),('1009999 views','1.00m'),('1010000 views','1.01m'),('1100000 views','1.10m'),('1009999K views','1.00b'),('1010000K views','1.01b'),('999 views','999'),('No views','0')]:
        page.locator('#info-container').evaluate('(e,value)=>e.textContent=value+" · Jul 4, 2026"',raw)
        expect(stats).to_have_text(compact+' · '+date('4 июля 2026 г.','4 July 2026'))
    page.locator('#info-container').evaluate('e=>e.textContent="853 views · 1 month ago"')
    expect(stats).to_have_text('853')  # A relative label cannot establish a day.
    page.locator('ytd-watch-metadata').evaluate('e=>e.insertAdjacentHTML("beforeend",\'<meta itemprop="uploadDate" content="2024-03-01"><meta itemprop="datePublished" content="2024-02-29T23:45:00-08:00">\')')
    expect(stats).to_have_text('853 · '+date('29 февраля 2024 г.','29 February 2024'))
    page.locator('meta[itemprop=datePublished]').evaluate('e=>e.content="2025-02-29"')
    expect(stats).to_have_text('853 · '+date('1 марта 2024 г.','1 March 2024'))  # Invalid publication day falls back to valid upload metadata.
    page.locator('meta[itemprop=uploadDate]').evaluate('e=>e.remove()')
    expect(stats).to_have_text('853')
    page.locator('meta[itemprop=datePublished]').evaluate('e=>e.remove()')
    page.evaluate('''() => {
      document.head.insertAdjacentHTML('beforeend','<link rel="canonical" href="https://www.youtube.com/watch?v=previous"><meta itemprop="datePublished" content="2025-01-02">');
    }''')
    expect(stats).to_have_text('853')
    page.locator('link[rel=canonical]').evaluate('e=>e.href="https://www.youtube.com/watch?v=details"')
    expect(stats).to_have_text('853 · '+date('2 января 2025 г.','2 January 2025'))
    page.locator('link[rel=canonical]').evaluate('e=>e.href="https://www.youtube.com/watch?v=previous"')
    page.locator('#info-container').evaluate('e=>e.insertAdjacentHTML("beforeend",\'<tp-yt-paper-tooltip hidden>6 августа 2020 г.</tp-yt-paper-tooltip>\')')
    expect(stats).to_have_text('853 · '+date('6 августа 2020 г.','6 August 2020'))
    page.locator('#info-container').evaluate('e=>e.textContent="Mar 8, 2025"')
    expect(stats).to_have_text('8 March 2025')
    expect(stats.locator('.views-icon')).to_be_hidden()
    page.locator('#info-container').evaluate('e=>e.textContent="No views · Mar 8, 2025"')
    expect(stats).to_have_text('0 · 8 March 2025')
    expect(stats.locator('.views-icon')).to_be_visible()
    page.close()


def check_description_icons(browser):
    page=setup(browser,'/watch?v=details',watch_details_fixture())
    button=page.locator('.expand')
    expect(button).to_have_text('')
    expect(button.locator('svg')).to_have_count(1)
    expect(button).to_have_attribute('aria-label','Show more')
    button.focus();button.press('Enter')
    expect(button).to_have_attribute('aria-expanded','true')
    expect(button).to_have_attribute('aria-label','Show less')
    expect(button).to_have_text('')
    button.press('Enter')
    expect(button).to_have_attribute('aria-expanded','false')
    expect(button).to_have_attribute('aria-label','Show more')
    assert_stable(page)
    page.close()


def check_chapter_sources(browser):
    page=setup(browser,'/watch?v=details',watch_details_fixture())
    page.locator('ytd-watch-flexy').evaluate('''e=>{
      const copies=document.createElement('div');copies.id='chapter-copies';
      for(const [time,title,video] of [['2:40:00','Outro','details'],['0:00','Duplicate introduction','details'],['2:45','Duplicate story','details'],['4:00','Next chapter','details'],['0:05','Different video','old-video']])copies.insertAdjacentHTML('beforeend',`<ytd-macro-markers-list-item-renderer><a href="/watch?v=${video}"><span id=time>${time}</span><h3 id=title>${title}</h3></a></ytd-macro-markers-list-item-renderer>`);
      e.prepend(copies);
    }''')
    expect(page.locator('.chapter')).to_have_count(4)
    assert page.locator('.chapter').evaluate_all('nodes=>nodes.map(e=>e.dataset.seconds)')==['0','165','240','9600']
    expect(page.locator('.chapter-title').first).to_have_text('Introduction')
    expect(page.locator('.chapter-title').last).to_have_text('Outro')
    page.locator('video').evaluate('e=>{e.currentTime=9600;e.dispatchEvent(new Event("timeupdate"));}')
    expect(page.locator('.chapter[aria-current=true]')).to_have_attribute('data-seconds','9600')
    page.locator('#chapter-copies').evaluate('e=>e.append(e.firstElementChild.cloneNode(true))')
    expect(page.locator('.chapter')).to_have_count(4)
    assert page.locator('.chapter').evaluate_all('nodes=>nodes.map(e=>e.dataset.seconds)')==['0','165','240','9600']
    page.close()


def check_chapter_follow(browser, width):
    page=setup(browser,'/watch?v=details',watch_details_fixture(),width=width)
    page.locator('ytd-video-description-chapters-section-renderer #items').evaluate('''e=>{
      e.replaceChildren();
      for(let i=0;i<12;i++)e.insertAdjacentHTML('beforeend',`<ytd-macro-markers-list-item-renderer><button><span id=time>${i}:00</span><h3 id=title>Chapter ${i}: stories behind the music</h3></button></ytd-macro-markers-list-item-renderer>`);
    }''')
    expect(page.locator('.chapter')).to_have_count(12)
    page.locator('.chapter-list').scroll_into_view_if_needed()
    scroll_top=page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')

    def seek(seconds, event):
        page.locator('video').evaluate('(e,args)=>{e.currentTime=args[0];e.dispatchEvent(new Event(args[1]));}',[seconds,event])

    def current_is_visible(seconds):
        expect(page.locator('.chapter[aria-current=true]')).to_have_attribute('data-seconds',str(seconds))
        page.wait_for_function('''() => {
          const ui=document.querySelector('#myt-watch').firstElementChild.shadowRoot;
          const list=ui.querySelector('.chapter-list'),card=list.querySelector('[aria-current=true]');
          const rail=list.getBoundingClientRect(),active=card.getBoundingClientRect();
          return active.left>=rail.left-1&&active.right<=rail.left+list.clientWidth+1;
        }''')
        assert abs(page.locator('#myt-watch .viewport').evaluate('e=>e.scrollTop')-scroll_top)<1

    # Playback crossing a boundary reveals the active card without moving the page.
    seek(660,'timeupdate')
    current_is_visible(660)
    # Browsing the rail stays possible until the next chapter or explicit seek.
    page.locator('.chapter-list').evaluate('e=>e.scrollLeft=0')
    seek(661,'timeupdate')
    assert page.locator('.chapter-list').evaluate('e=>e.scrollLeft')==0
    # Seeking inside the same chapter follows it again, including backwards seeks.
    seek(662,'seeked')
    current_is_visible(660)
    seek(0,'seeked')
    current_is_visible(0)
    # A chapter click uses the same follow behavior and retains native playback.
    page.locator('.chapter').nth(5).click()
    current_is_visible(300)
    # Fullscreen hides the rail; crossing a boundary there must still reveal
    # the selected chapter when the page becomes visible again.
    page.locator('.chapter-list').evaluate('e=>e.hidden=true')
    seek(660,'timeupdate')
    page.locator('.chapter-list').evaluate('e=>e.hidden=false')
    seek(661,'timeupdate')
    current_is_visible(660)
    assert_stable(page)
    page.close()


def check_removed_chat(browser, replay):
    page=setup(browser, '/watch?v=chat', native_watch_fixture())
    errors=[]
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/live_chat**', lambda route: route.fulfill(status=200,content_type='text/html',body='<p>Chat document</p>'))
    # Share also moves under More when YouTube exposes no native More control.
    expect(page.locator('.actions > button').filter(has_text='Share')).to_have_count(0)
    page.locator('#share').evaluate('e=>e.onclick=()=>window.__shareOnly=true')
    page.locator('.more-toggle').click()
    expect(page.locator('.more-popup button')).to_have_count(2)
    page.locator('.more-popup').get_by_role('menuitem',name='Share',exact=True).click()
    assert page.evaluate('window.__shareOnly') is True
    source='/live_chat_replay?v=chat' if replay else '/live_chat?v=chat'
    page.evaluate("""source => {
        window.__player=document.querySelector('video');
        const chat=document.createElement('ytd-live-chat-frame');chat.id='chat';
        const frame=document.createElement('iframe');frame.id='chatframe';frame.src=source;
        chat.append(frame);document.querySelector('#secondary-inner').append(chat);
        const unrelated=document.createElement('iframe');unrelated.id='unrelated-embed';unrelated.src='about:blank#keep';
        document.querySelector('#secondary-inner').append(unrelated);
    }""",source)
    expect(page.locator('#chatframe')).to_have_attribute('src','about:blank')
    expect(page.locator('#chat')).to_be_hidden()
    expect(page.locator('.sidecar')).to_be_hidden()
    assert page.locator('#chat').get_attribute('data-myt-watch-island') is None
    expect(page.locator('#unrelated-embed')).to_have_attribute('src','about:blank#keep')
    # Late source changes must also release the chat browsing context.
    page.locator('#chatframe').evaluate('(e,src)=>e.src=src',source+'&continuation=late')
    expect(page.locator('#chatframe')).to_have_attribute('src','about:blank')
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#chatframe')).to_have_attribute('src',source+'&continuation=late')
    expect(page.locator('#chat')).to_be_visible()
    page.evaluate('__setEnabled(true)')
    expect(page.locator('#chatframe')).to_have_attribute('src','about:blank')
    expect(page.locator('#chat')).to_be_hidden()
    assert page.evaluate("window.__player===document.querySelector('video')")
    assert not errors,errors
    page.close()


def main():
    passed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"PASS {name}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])

        page = setup(browser, body='<ytd-app id="native-app"><ytd-page-manager><p id="native-state">Native state</p></ytd-page-manager></ytd-app>')
        expect(page.locator("#myt-home")).to_be_visible()
        expect(page.locator("#myt-query")).to_be_focused()
        expect(page.locator("#myt-home .myt-search__icon")).to_have_count(0)
        home_mark = page.locator("#myt-home .myt-home__mark").inner_html()
        home_wordmark = page.locator("#myt-home .myt-home__wordmark").text_content()
        assert page.locator("#native-state").count() == 1, "Homepage must preserve YouTube's native DOM"
        expect(page).to_have_title("YouTube")
        centered(page, ".myt-search")
        expect(page.locator(".myt-search button[type=submit], .myt-search circle")).to_have_count(0)
        assert page.locator(".myt-search").evaluate("element => getComputedStyle(element).boxShadow") == "none"
        home_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        for selector in ["html", "body", "#native-app"]:
            background = page.locator(selector).evaluate("element => getComputedStyle(element).backgroundColor")
            assert background in [home_bg, "rgba(0, 0, 0, 0)"], (selector, background, home_bg)
        page.locator("#myt-query").fill("    ")
        page.locator("#myt-query").press("Enter")
        assert page.url == "https://www.youtube.com/", "Empty search must stay on home"
        ok("homepage preserves native DOM, centers search and ignores blank query")

        page.locator("#myt-query").fill("  кот & C++ #музыка  ")
        page.locator("#myt-query").press("Enter")
        page.wait_for_url("**/results?**")
        assert parse_qs(urlparse(page.url).query)["search_query"] == ["кот & C++ #музыка"], page.url
        ok("search encodes Unicode, ampersands, plus signs and hash")
        page.close()

        page = setup(browser, native_dark=True)
        expect(page.locator("#myt-home h1, #myt-home .myt-home__eyebrow, #myt-home .myt-home__description, #myt-home .myt-home__hint")).to_have_count(0)
        expect(page.locator("#myt-theme-toggle")).to_have_count(0)
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "dark")
        dark_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        select_home_theme(page, "light")
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "light")
        light_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        assert dark_bg != light_bg, (dark_bg, light_bg)
        assert page.evaluate("__stored.theme") == "light"
        assert page.locator("html[dark]").count() == 1, "Homepage theme must preserve YouTube's native theme"
        select_home_theme(page, "dark")
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "dark")
        assert page.evaluate("__stored.theme") == "dark"
        ok("homepage keeps brand/search without a theme toggle and switches persisted theme through settings")
        page.close()

        page = setup(browser, theme="light", native_dark=True)
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "light")
        page.evaluate("chrome.storage.local.set({theme: 'dark'})")
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "dark")
        expect(page.locator("#myt-home")).to_be_visible()
        ok("saved homepage theme loads and external theme-only changes preserve the enabled extension")
        page.close()

        for theme in ["dark", "light"]:
            page = browser.new_page(viewport={"width":1440,"height":960})
            page.route("https://www.youtube.com/**", lambda route: route.fulfill(content_type="text/html", body=document('<ytd-app id="tall-native" style="height:2400px;background:linear-gradient(red,blue)">Tall native content</ytd-app>')))
            page.goto("https://www.youtube.com/")
            page.evaluate("document.body.style.cssText='transform:translateY(80px);filter:brightness(.85);contain:layout;min-height:2400px'; window.scrollTo(0,300)")
            assert page.evaluate("scrollY") >= 300, "Fixture must start with a genuinely scrolled native document"
            body_style = page.locator("body").get_attribute("style")
            page.evaluate(MOCK, {"theme":theme})
            page.add_style_tag(path=str(ROOT / "src/styles/styles.css"))
            page.add_script_tag(path=str(ROOT / "src/content/watch.js"))
            page.add_script_tag(path=str(ROOT / "src/content/playlist.js"))
            page.add_script_tag(path=str(ROOT / "src/content/content.js"))
            page.emulate_media(reduced_motion="reduce")
            expect(page.locator("#myt-home")).to_be_visible()
            assert page.locator("#myt-home").evaluate("element => element.parentElement === document.documentElement")
            bounds = page.locator("#myt-home").bounding_box()
            assert bounds["x"] == bounds["y"] == 0 and bounds["width"] == 1440 and bounds["height"] == 960, bounds
            assert_uniform_full_page(page)
            page.set_viewport_size({"width":1024,"height":700})
            bounds = page.locator("#myt-home").bounding_box()
            assert bounds["x"] == bounds["y"] == 0 and bounds["width"] == 1024 and bounds["height"] == 700, bounds
            assert_uniform_full_page(page)
            page.evaluate("__setEnabled(false)")
            expect(page.locator("#myt-home")).to_have_count(0)
            expect(page.locator("#tall-native")).to_be_visible()
            assert page.locator("body").get_attribute("style") == body_style
            assert page.evaluate("document.documentElement.scrollHeight") >= 2400
            ok(f"{theme} home escapes transformed/filtered body, removes tall native flow, stays flat full-page after resize and restores on disable")
            page.close()

        for theme in ["dark", "light"]:
            page = setup(browser, theme=theme)
            # Late native styles can paint stripes above the home background,
            # even when its computed backgroundColor is already correct.
            page.add_style_tag(content="""
              html::before, main::before, main::after {
                content: ''; position: fixed; pointer-events: none;
                left: 0; right: 0; height: 27vh; z-index: 9999;
                background: rgba(0, 0, 0, .15);
              }
              html::before { top: 0; }
              main::before { top: 27vh; }
              main::after { bottom: 0; }
              main { background-image: linear-gradient(#111, #222) !important;
                     box-shadow: inset 0 200px 0 rgba(0, 0, 0, .1) !important; }
            """)
            page.emulate_media(reduced_motion="reduce")
            assert_uniform_full_page(page)
            for size in [{"width":1996,"height":1248}, {"width":390,"height":844}]:
                page.set_viewport_size(size)
                assert_uniform_full_page(page)
            select_home_theme(page, 'light' if theme=='dark' else 'dark')
            assert_uniform_full_page(page)
            page.evaluate('__setEnabled(false)')
            assert page.locator('html').evaluate("element => getComputedStyle(element, '::before').content") == '""'
            ok(f"{theme} homepage keeps a solid background despite late native gradients/pseudo-elements, resize and theme change; disabling restores native styles")
            page.close()

        for theme in ['dark', 'light']:
            check_home_isolation(browser, theme)
            ok(f'{theme} home isolates native overlays, root filters and form styles; keeps keyboard/theme controls and restores native interaction')

        page = setup(browser)
        page.locator("#myt-query").fill("remove me")
        page.locator(".myt-search__clear").click()
        expect(page.locator("#myt-query")).to_have_value("")
        expect(page.locator("#myt-query")).to_be_focused()
        page.locator("#myt-query").fill("keyboard search")
        page.locator("#myt-query").press("Enter")
        page.wait_for_url("**/results?**")
        assert parse_qs(urlparse(page.url).query)["search_query"] == ["keyboard search"]
        ok("clear control restores focus and Enter submits search")
        page.close()

        page = setup(browser)
        page.set_viewport_size({"width": 1440, "height": 320})
        brand = page.locator(".myt-home__brand").bounding_box()
        assert brand["y"] >= 0, "Short viewport must keep the start of the home screen reachable"
        page.locator("#myt-query").scroll_into_view_if_needed()
        expect(page.locator("#myt-query")).to_be_in_viewport()
        expect(page.locator("#myt-query")).to_be_in_viewport()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        ok("320px-tall desktop homepage keeps its brand and search reachable")
        page.close()

        page = setup(browser, enabled=False)
        assert page.locator("#myt-home").count() == 0
        assert page.locator("html.minimal-youtube").count() == 0
        expect(page).to_have_title("(12) YouTube")
        page.evaluate("__setEnabled(true)")
        expect(page.locator("#myt-home")).to_be_visible()
        page.evaluate("__setEnabled(false)")
        expect(page.locator("#myt-home")).to_have_count(0)
        assert page.locator("html.minimal-youtube").count() == 0
        ok("disabled extension leaves page intact and storage toggles apply without reload")
        page.close()

        cards = '''<ytd-app><ytd-page-manager><ytd-browse>
          <ytd-rich-item-renderer id="short-card"><a href="/shorts/abc">Short</a></ytd-rich-item-renderer>
          <ytd-video-renderer id="regular-card"><a href="/watch?v=xyz">Regular video</a></ytd-video-renderer>
          <ytd-reel-shelf-renderer id="shorts-shelf">Shorts</ytd-reel-shelf-renderer>
          <yt-tab-shape id="shorts-tab"><a href="/@creator/shorts">Shorts</a></yt-tab-shape>
          <yt-tab-shape id="videos-tab"><a href="/@creator/videos">Videos</a></yt-tab-shape>
          <tp-yt-paper-tab id="reused-tab"><span>Videos</span></tp-yt-paper-tab>
        </ytd-browse></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/results?search_query=fixture", cards)
        expect(page.locator("#short-card")).to_be_hidden()
        expect(page.locator("#shorts-shelf")).to_be_hidden()
        expect(page.locator("#shorts-tab")).to_be_hidden()
        expect(page.locator("#regular-card")).to_be_visible()
        expect(page.locator("#videos-tab")).to_be_visible()
        page.evaluate("""() => {
          const card = document.createElement('ytd-rich-item-renderer');
          card.id = 'dynamic-short'; card.innerHTML = '<a href="/shorts/new">New short</a>';
          document.querySelector('ytd-browse').append(card);
        }""")
        expect(page.locator("#dynamic-short")).to_be_hidden()
        page.locator("#dynamic-short a").evaluate("anchor => anchor.href = '/watch?v=reused'")
        expect(page.locator("#dynamic-short")).to_be_visible()
        page.locator("#reused-tab span").evaluate("span => span.firstChild.nodeValue = 'Shorts'")
        expect(page.locator("#reused-tab")).to_be_hidden()
        page.locator("#reused-tab span").evaluate("span => span.firstChild.nodeValue = 'Videos'")
        expect(page.locator("#reused-tab")).to_be_visible()
        page.evaluate("__setEnabled(false)")
        expect(page.locator("#short-card")).to_be_visible()
        expect(page.locator("#shorts-tab")).to_be_visible()
        expect(page.locator("#shorts-shelf")).to_be_visible()
        ok("Shorts shelves, cards, channel tab and dynamic items disappear and restore on disable")
        page.close()

        page = setup(browser, "/results?search_query=fixture", cards, enabled=False)
        expect(page.locator("#short-card")).to_be_visible()
        expect(page.locator("#shorts-shelf")).to_be_visible()
        assert page.locator("[data-myt-hidden]").count() == 0
        ok("initially disabled extension leaves Shorts and cards untouched")
        page.close()

        page = setup(browser, "/results?search_query=shorts", '<ytd-app><div id="shelves"></div></ytd-app>')
        immediate = page.evaluate("""() => {
          document.querySelector('#shelves').innerHTML = `
            <ytd-reel-shelf-renderer id="instant-old">Old Shorts</ytd-reel-shelf-renderer>
            <ytd-rich-section-renderer id="instant-modern"><ytm-shorts-lockup-view-model><a href="/shorts/modern">Modern Short</a></ytm-shorts-lockup-view-model></ytd-rich-section-renderer>
            <yt-horizontal-list-renderer id="mixed-shelf"><yt-lockup-view-model id="mixed-regular"><a href="/watch?v=normal">Ordinary video</a></yt-lockup-view-model><yt-lockup-view-model id="mixed-short"><a href="/shorts/mixed">Short</a></yt-lockup-view-model></yt-horizontal-list-renderer>
            <ytd-video-renderer id="short-badge"><a href="/watch?v=badge">Short video</a><ytd-thumbnail-overlay-time-status-renderer overlay-style="SHORTS">0:30</ytd-thumbnail-overlay-time-status-renderer></ytd-video-renderer>
            <ytd-video-renderer id="subdomain-short"><a href="https://m.youtube.com/shorts/subdomain">Mobile short</a></ytd-video-renderer>`;
          return Object.fromEntries(['instant-old','instant-modern','mixed-short','mixed-regular'].map(id => [id, getComputedStyle(document.getElementById(id)).display]));
        }""")
        assert immediate["instant-old"] == immediate["instant-modern"] == immediate["mixed-short"] == "none", immediate
        assert immediate["mixed-regular"] != "none", immediate
        expect(page.locator("#mixed-regular")).to_be_visible()
        expect(page.locator("#mixed-short")).to_have_attribute("data-myt-hidden", "shorts")
        expect(page.locator("#short-badge")).to_be_hidden()
        expect(page.locator("#subdomain-short")).to_be_hidden()
        expect(page.locator("#instant-modern")).to_be_hidden()
        ok("new Shorts shelves/cards hide before the next frame and mixed shelves preserve ordinary videos")
        page.close()

        for path, kind in [("/watch?v=early", "watch"), ("/results?search_query=early", "search"), ("/@creator/videos", "channel"), ("/", "home")]:
            page = setup_at_document_start(browser, path)
            early = page.evaluate("__earlyStartup")
            assert early["enabled"] and early["page"] == kind and not early["bodyExists"], (path, early)
            assert not page.errors, page.errors
            assert page.locator("#early-native").count() == 1
            if kind == "home":
                expect(page.locator("#myt-home")).to_be_visible()
            ok(f"document_start applies {kind} styling before body/app markup without initialization errors")
            page.close()

        page = setup_at_document_start(browser, "/watch?v=disabled", enabled=False, defer_settings=True)
        expect(page).to_have_title("(12) YouTube")
        assert page.locator("#myt-home").count() == 0
        assert page.locator("#early-native").count() == 1
        page.evaluate("__resolveSettings()")
        expect(page.locator("html.minimal-youtube")).to_have_count(0)
        expect(page).to_have_title("(12) YouTube")
        assert not page.errors, page.errors
        ok("delayed saved-disabled startup preserves native DOM/title and removes provisional styling")
        page.close()

        check_navigation_style_retention(browser)
        ok('outgoing minimalist styles survive pending/committed navigation until destination DOM mounts; cancellation restores the source route')

        page = setup_at_document_start(browser, "/watch?v=history")
        state = page.evaluate("""() => {
          document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail:{url:'/results?search_query=history'}}));
          return {enabled:document.documentElement.classList.contains('minimal-youtube'), page:document.documentElement.dataset.mytPage};
        }""")
        assert state == {"enabled": True, "page": "search"}, state
        navigate_spa(page, "/results?search_query=history")
        expect(page.locator("html")).to_have_attribute("data-myt-page", "search")
        page.go_back()
        expect(page.locator("html")).to_have_attribute("data-myt-page", "watch")
        page.go_forward()
        expect(page.locator("html")).to_have_attribute("data-myt-page", "search")
        page.evaluate("document.documentElement.className = 'native-theme'")
        expect(page.locator("html.minimal-youtube")).to_have_count(1)
        paints = page.evaluate("""async () => {
          const states=[];
          for(let n=0;n<4;n++){await new Promise(requestAnimationFrame); states.push({enabled:document.documentElement.classList.contains('minimal-youtube'),page:document.documentElement.dataset.mytPage});}
          return states;
        }""")
        assert all(state == {"enabled": True, "page": "search"} for state in paints), paints
        assert not page.errors, page.errors
        ok("SPA start/finish, history back/forward and native html-class replacement keep styles active before paint")
        page.close()

        page = setup(browser, body='<ytd-app><ytd-page-manager class="ytd-app"><p id="preserved-home-state">Native app</p></ytd-page-manager></ytd-app>', theme="dark")
        page.evaluate("document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail:{url:'/results?search_query=delayed'}}))")
        expect(page.locator("html")).to_have_attribute("data-myt-page", "search")
        expect(page.locator("#myt-home")).to_be_visible()
        page.evaluate("history.pushState({}, '', '/results?search_query=delayed')")
        page.evaluate("async () => { for(let n=0;n<3;n++) await new Promise(requestAnimationFrame); }")
        expect(page.locator("#myt-home")).to_be_visible()
        page.locator("ytd-page-manager").evaluate("element => element.insertAdjacentHTML('beforeend', '<ytd-search id=ready-results>Results ready</ytd-search>')")
        expect(page.locator("#myt-home")).to_have_count(0)
        expect(page.locator("#ready-results")).to_be_visible()
        assert page.locator("#preserved-home-state").count() == 1
        ok("home overlay persists through pending/committed navigation until the native destination mounts")
        page.close()

        page = setup(browser)
        page.evaluate("document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail:{url:'/results?search_query=cancel'}})); document.dispatchEvent(new Event('yt-navigate-cancel'))")
        expect(page.locator("#myt-home")).to_be_visible()
        assert page.url == "https://www.youtube.com/"
        expect(page.locator("html")).to_have_attribute("data-myt-page", "home")
        ok("cancelled navigation keeps the home overlay and original route intact")
        page.close()

        page = setup(browser, "/feed/trending", '<ytd-app><ytd-page-manager class="ytd-app"><ytd-browse><div id="primary" style="width: 700px; margin-left: 37px">Subscriptions</div></ytd-browse></ytd-page-manager></ytd-app>')
        bounds = page.locator("#primary").bounding_box()
        assert bounds["width"] == 700 and bounds["x"] == 37, bounds
        ok("nonchannel browse primary dimensions are not globally overridden")
        page.close()

        page = setup(browser, "/shorts/abc")
        page.wait_for_url("https://www.youtube.com/")
        ok("direct Shorts playback redirects to home")
        page.close()
        for path, target, label in [
            ("/@creator/shorts", "https://www.youtube.com/", "channel Shorts tab"),
            ("/@creator/releases", "https://www.youtube.com/", "rare channel tab"),
            ("/feed/subscriptions", "https://www.youtube.com/", "subscriptions feed"),
            ("/feed/history", "https://www.youtube.com/", "history feed"),
            ("/feed/you", "https://www.youtube.com/", "You page"),
            ("/hashtag/%D0%BC%D0%B0%D0%B9%D0%BD", "https://www.youtube.com/results?search_query=%23%D0%BC%D0%B0%D0%B9%D0%BD", "hashtag page"),
        ]:
            page = setup(browser, path)
            page.wait_for_url(target)
            ok(f"{label} redirects to {target.removeprefix('https://www.youtube.com')}")
            page.close()
        # Kept channel sections are not redirected.
        page = setup(browser, "/@creator/streams")
        page.wait_for_timeout(300)
        assert page.url == "https://www.youtube.com/@creator/streams", page.url
        page.close()

        page = setup(browser, body='<ytd-app id="keep"><ytd-page-manager></ytd-page-manager></ytd-app>')
        page.evaluate("""() => {
          history.pushState({}, '', '/watch?v=abc');
          document.dispatchEvent(new Event('yt-navigate-finish'));
        }""")
        expect(page.locator("#myt-home")).to_have_count(0)
        assert page.locator("#keep").count() == 1
        page.evaluate("""() => {
          history.pushState({}, '', '/');
          window.dispatchEvent(new PopStateEvent('popstate'));
        }""")
        expect(page.locator("#myt-home")).to_be_visible()
        assert page.locator("#myt-home").count() == 1
        page.evaluate("""() => {
          history.pushState({}, '', '/shorts/spa');
          document.dispatchEvent(new Event('yt-navigate-finish'));
        }""")
        page.wait_for_url("https://www.youtube.com/")
        ok("SPA navigation restores home once, preserves app and blocks Shorts route")
        page.close()

        channel = '''<ytd-app mini-guide-visible><ytd-page-manager id="page-manager" class="ytd-app">
          <ytd-browse page-subtype="channels"><div id="header" class="ytd-browse">Channel header</div>
          <div id="contents" class="ytd-browse"><ytd-rich-grid-renderer>Videos</ytd-rich-grid-renderer></div>
          </ytd-browse></ytd-page-manager></ytd-app>'''
        for width in [1440, 390]:
            page = setup(browser, "/@creator/videos", channel, width=width)
            centered(page, "ytd-browse")
            centered(page, "ytd-browse > #header")
            centered(page, "ytd-browse > #contents")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow"
            ok(f"channel centered without horizontal overflow at {width}px")
            page.close()

        channel_profile = '<ytd-app>' + MASTHEAD + '''
          <ytd-page-manager class="ytd-app"><ytd-browse page-subtype="channels">
          <div id="header"><div id="banner" style="height:180px;background:#345"><img id="banner-image" alt="Channel banner" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27%3E%3Crect width=%2716%27 height=%2716%27 fill=%27%23345%27/%3E%3C/svg%3E" style="display:block;width:100%;height:180px"></div>
          <ytd-c4-tabbed-header-renderer><div id="channel-header-container"><div id="profile"><img id="profile-avatar" alt="Profile" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27%3E%3Crect width=%2716%27 height=%2716%27 fill=%27%23345%27/%3E%3C/svg%3E" style="display:block;width:160px;height:160px;border-radius:50%"><h1>Channel title</h1></div></div></ytd-c4-tabbed-header-renderer></div>
          <div id="tabs"><tp-yt-paper-tabs><tp-yt-paper-tab>Home</tp-yt-paper-tab><tp-yt-paper-tab>Videos</tp-yt-paper-tab></tp-yt-paper-tabs></div>
          <div id="contents"><ytd-rich-grid-renderer id="channel-grid"><ytd-rich-item-renderer><ytd-thumbnail id="channel-thumbnail" style="height:180px;background:#345">Thumbnail</ytd-thumbnail></ytd-rich-item-renderer></ytd-rich-grid-renderer></div>
          </ytd-browse></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/@creator/videos", channel_profile)
        # The owned header replaces the native banner and profile.
        expect(page.locator("#banner")).to_be_hidden()
        expect(page.locator("#channel-header-container")).to_be_hidden()
        banner = page.locator("#myt-channel-header .myt-ch-banner").bounding_box()
        assert banner["x"] == 0 and banner["width"] == 1440, banner
        assert page.locator("#myt-channel-header .myt-ch-banner img").bounding_box()["width"] == 1440
        assert page.locator("#myt-channel-header .myt-ch-avatar").bounding_box()["width"] == 300, "Owned avatar size"
        expect(page.locator("#myt-channel-header h1")).to_have_text("Channel title")
        centered(page, "#myt-channel-header .myt-ch-profile")
        centered(page, "#tabs")
        assert page.locator("#myt-channel-header .myt-ch-profile").bounding_box()["width"] <= 1280
        assert page.locator("#tabs").evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
        assert page.locator("#channel-thumbnail").evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
        grid_gap = page.locator("#channel-grid").evaluate("element => parseFloat(getComputedStyle(element).getPropertyValue('--ytd-rich-grid-item-margin'))")
        assert grid_gap >= 28, grid_gap
        columns = page.locator("#channel-grid").evaluate("element => parseInt(getComputedStyle(element).getPropertyValue('--ytd-rich-grid-items-per-row'))")
        assert columns == 3, columns
        centered_header(page)
        for selector in ["#myt-masthead .myt-masthead-link", "#myt-masthead .myt-masthead-query"]:
            expect(page.locator(selector)).to_be_visible()
        for selector in ["#logo", "#search"]:
            expect(page.locator(selector)).to_be_hidden()
        for selector in ["#create", "#avatar-btn", "#voice-search-button"]:
            expect(page.locator(selector)).to_be_hidden()
        ok("channel banner fills the viewport while profile/avatar, rounded tabs and spaced cards keep centered dimensions")
        page.close()

        modern_channel = channel_profile.replace('<div id="banner" style="height:180px;background:#345"><img id="banner-image" alt="Channel banner" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27%3E%3Crect width=%2716%27 height=%2716%27 fill=%27%23345%27/%3E%3C/svg%3E" style="display:block;width:100%;height:180px"></div>', '<yt-image-banner-view-model id="modern-channel-banner" style="height:180px;background:#345"><img alt="" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27%3E%3Crect width=%2716%27 height=%2716%27 fill=%27%23345%27/%3E%3C/svg%3E"></yt-image-banner-view-model>')
        page = setup(browser, "/@creator/videos", modern_channel)
        expect(page.locator("#modern-channel-banner")).to_be_hidden()
        modern_banner = page.locator("#myt-channel-header .myt-ch-banner").bounding_box()
        assert modern_banner["x"] == 0 and modern_banner["width"] == 1440, modern_banner
        assert page.locator("#myt-channel-header .myt-ch-avatar").bounding_box()["width"] == 300
        ok("modern image-banner component also spans the channel width without resizing the avatar")
        page.close()

        for width in [2016, 900, 390]:
            check_channel_sections(browser, width)
            ok(f'channel at {width}px removes New Uploads, renders equal search-style cards and groups and restores native sections on disable')

        channel_scroll = '''<ytd-app style="height:100%"><div id="main-scroll" style="position:absolute;top:60px;left:120px;width:calc(100% - 240px);height:840px;overflow-y:auto"><ytd-page-manager class="ytd-app">
          <ytd-browse page-subtype="channels" style="min-height:2400px">
          <div id="nested-scroll" style="width:300px;height:120px;overflow-y:auto"><div style="height:800px">Nested native scrollbox</div></div>
          <div style="height:2000px">Channel videos</div></ytd-browse></ytd-page-manager></div></ytd-app>'''
        page = setup(browser, "/@creator/videos", channel_scroll)
        page.evaluate("document.documentElement.style.cssText = 'height:100%;overflow:hidden'; document.body.style.cssText = 'height:100%;overflow:hidden'")
        page.mouse.move(10, 400)
        page.mouse.wheel(0, 300)
        page.wait_for_function("document.querySelector('#main-scroll').scrollTop >= 250")
        page.locator("#main-scroll").evaluate("element => element.scrollTop = 0")
        page.locator("#nested-scroll").hover()
        page.mouse.wheel(0, 100)
        page.wait_for_function("document.querySelector('#nested-scroll').scrollTop > 0")
        assert page.locator("#main-scroll").evaluate("element => element.scrollTop") == 0
        ok("wheel over channel gutters scrolls the main native scrollport while nested scrolling stays native")

        page.evaluate("__setEnabled(false); document.querySelector('#main-scroll').scrollTop = 0")
        page.mouse.move(10, 400)
        page.mouse.wheel(0, 300)
        page.evaluate("async () => { for (let n=0;n<5;n++) await new Promise(requestAnimationFrame); }")
        assert page.locator("#main-scroll").evaluate("element => element.scrollTop") == 0
        page.evaluate("__setEnabled(true)")
        navigate_spa(page, "/feed/trending")
        page.mouse.wheel(0, 300)
        page.evaluate("async () => { for (let n=0;n<5;n++) await new Promise(requestAnimationFrame); }")
        page.wait_for_function("document.querySelector('#main-scroll').scrollTop >= 250")
        ok("gutter-wheel fallback stays inactive when disabled and also supports other enabled pages")
        page.close()

        for path, renderer in [("/watch?v=scroll", "ytd-watch-flexy"), ("/results?search_query=scroll", "ytd-search")]:
            scroll_fixture = channel_scroll.replace("ytd-browse", renderer)
            page = setup(browser, path, scroll_fixture, watch_ui=False)
            page.evaluate("document.documentElement.style.cssText = 'height:100%;overflow:hidden'; document.body.style.cssText = 'height:100%;overflow:hidden'")
            page.mouse.move(10, 400)
            page.mouse.wheel(0, 300)
            page.wait_for_function("document.querySelector('#main-scroll').scrollTop >= 250")
            page.locator("#main-scroll").evaluate("element => element.scrollTop = 0")
            page.evaluate("document.body.insertAdjacentHTML('beforeend', '<div id=movie_player class=html5-video-player style=position:absolute;left:0;top:100px;width:100px;height:100px>Player</div>')")
            page.mouse.move(10, 140)
            page.mouse.wheel(0, 300)
            page.evaluate("async () => { for (let n=0;n<5;n++) await new Promise(requestAnimationFrame); }")
            assert page.locator("#main-scroll").evaluate("element => element.scrollTop") == 0
            ok(f"gutter scrolling works on {renderer} while player-area wheel events stay untouched")
            page.close()

        for path, renderer in [("/@creator/videos", "ytd-browse"), ("/results?search_query=inner", "ytd-search")]:
            fixture = f'''<ytd-app><ytd-page-manager>
              <div style="display:none"><{renderer}><div>Stale SPA page</div></{renderer}></div>
              <{renderer}><div id="inner-scroll" style="position:absolute;left:120px;top:60px;width:calc(100% - 240px);height:840px;overflow-y:auto">
              <div style="height:3000px">Native content</div></div></{renderer}>
              </ytd-page-manager></ytd-app>'''
            page = setup(browser, path, fixture)
            if renderer=='ytd-search':
                from search import video as owned_video
                page.locator('#inner-scroll').evaluate('(node,html)=>node.insertAdjacentHTML("beforeend",html)',''.join(owned_video(i) for i in range(12)))
                expect(page.locator('#myt-search .media')).to_have_count(12)
                assert page.locator('#myt-search').evaluate('node=>node.getClientRects().length>0')
            page.evaluate("document.documentElement.style.cssText='height:100%;overflow:hidden'; document.body.style.cssText='height:100%;overflow:hidden'")
            if renderer=='ytd-browse':expect(page.locator('#inner-scroll')).to_have_css('visibility','visible')
            page.mouse.move(10, 400)
            page.mouse.wheel(0, 300)
            page.wait_for_function('scrollY>=250' if renderer=='ytd-search' else "document.querySelector('#inner-scroll').scrollTop >= 250")
            ok(f"{renderer} detects an inner scrollport and ignores a stale hidden SPA renderer")
            page.close()

        for path, renderer in [('/results?search_query=gutter', 'ytd-search'), ('/@creator/videos', 'ytd-browse')]:
            check_gutter_document_scroll(browser, path, renderer)
            ok(f'{renderer} forwards both blocked gutters to the document scrollport without double scrolling, and stays inactive when disabled')

        for path in ["/watch?v=header", "/results?search_query=header", "/@creator/videos", "/feed/trending"]:
            page = setup(browser, path, '<ytd-app>' + MASTHEAD + '<ytd-page-manager class="ytd-app"><ytd-browse>Native content</ytd-browse></ytd-page-manager></ytd-app>', watch_ui=False)
            centered_header(page)
            page.locator('#myt-masthead .myt-masthead-link').focus()
            assert page.locator('#myt-masthead .myt-masthead-link').evaluate('element => getComputedStyle(element).outlineStyle') == 'none'
            expect(page.locator("#create")).to_be_hidden()
            expect(page.locator("#avatar-btn")).to_be_hidden()
            page.locator('#myt-masthead .myt-masthead-query').fill("кот & C++")
            expect(page.locator("#search")).to_be_hidden()
            page.locator('#myt-masthead .myt-masthead-query').press("Enter")
            page.wait_for_url("**/results?**")
            assert parse_qs(urlparse(page.url).query)["search_query"] == ["кот & C++"], page.url
            ok(f"logo and functional owned search stay centered together on {path.split('?')[0]}")
            page.close()

        legacy_searchbox = MASTHEAD[MASTHEAD.index('<ytd-searchbox>'):MASTHEAD.index('</ytd-searchbox>') + len('</ytd-searchbox>')]
        modern_searchbox = '''<yt-searchbox><div class="ytSearchboxComponentHost"><form class="ytSearchboxComponentSearchForm" action="/results" method="get"><div class="ytSearchboxComponentInputBox"><input class="ytSearchboxComponentInput" id="search" name="search_query" aria-label="Search"></div><button class="ytSearchboxComponentSearchButton" type="submit" aria-label="Search"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="m15 15 5 5"/></svg></button></form></div></yt-searchbox>'''
        modern_header = MASTHEAD.replace(legacy_searchbox, modern_searchbox)
        page = setup(browser, "/results?search_query=modern", '<ytd-app>' + modern_header + '<ytd-page-manager class="ytd-app"><ytd-search>Modern results</ytd-search></ytd-page-manager></ytd-app>')
        centered_header(page)
        page.locator('#myt-masthead .myt-masthead-query').fill("modern & search")
        expect(page.locator(".ytSearchboxComponentSearchButton")).to_be_hidden()
        page.locator('#myt-masthead .myt-masthead-query').press("Enter")
        page.wait_for_url("**/results?**")
        assert parse_qs(urlparse(page.url).query)["search_query"] == ["modern & search"]
        ok("owned header replaces the modern native searchbox, stays centered and submits normally")
        page.close()

        for variant, header in [('legacy', MASTHEAD), ('modern', modern_header)]:
            for width in [1440, 390]:
                page = setup(browser, '/results?search_query=icon', '<ytd-app>' + header + '<ytd-page-manager class="ytd-app"><ytd-search>Results</ytd-search></ytd-page-manager></ytd-app>', width=width)
                icon_class = 'search-icon' if variant == 'legacy' else 'ytSearchboxComponentSearchIconContainer'
                icon_id = 'search-icon' if variant == 'legacy' else 'fixture-modern-icon'
                holder = '#search-input' if variant == 'legacy' else '.ytSearchboxComponentInputBox'
                page.locator(holder).evaluate("(element, fixture) => { element.style.position='relative'; element.insertAdjacentHTML('afterbegin', fixture); }", f'<span id="{icon_id}" class="{icon_class}" data-fixture-leading style="position:absolute;left:0;top:0;width:24px;height:24px"><svg viewBox="0 0 24 24" width="24" height="24"><circle cx="10" cy="10" r="7"/></svg></span>')
                expect(page.locator('[data-fixture-leading]')).to_be_hidden()
                expect(page.locator('#myt-masthead .myt-masthead-brand')).to_have_count(1)
                expect(page.locator('#logo-icon')).to_be_hidden()
                assert page.locator('#myt-masthead .myt-masthead-brand .myt-home__mark').inner_html() == home_mark
                assert page.locator('#myt-masthead .myt-masthead-brand .myt-home__wordmark').text_content() == home_wordmark
                centered_header(page)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Header must fit narrow screens'
                page.locator('#myt-masthead .myt-masthead-query').fill('Савельев Сергей & C++')
                expect(page.locator('#myt-masthead .myt-masthead-query')).to_have_value('Савельев Сергей & C++')
                submit = page.locator('#search-icon-legacy' if variant == 'legacy' else '.ytSearchboxComponentSearchButton')
                expect(submit).to_be_hidden()
                page.evaluate('__setEnabled(false)')
                expect(submit).to_be_visible()
                page.evaluate('__setEnabled(true)')
                expect(submit).to_be_hidden()
                # A recreated header shows the page's query; type the new one again.
                expect(page.locator('#myt-masthead .myt-masthead-query')).to_have_value('icon')
                page.locator('#myt-masthead .myt-masthead-query').fill('Савельев Сергей & C++')
                page.locator('#myt-masthead .myt-masthead-query').press('Enter')
                page.wait_for_url('**/results?**')
                assert parse_qs(urlparse(page.url).query)['search_query'] == ['Савельев Сергей & C++']
                ok(f'{variant} search at {width}px removes all search magnifiers, restores native buttons on disable and submits with Enter')
                page.close()

        for variant in ['legacy', 'modern']:
            for path, width in [('/results?search_query=mr+beast', 1440), ('/@creator/videos', 390)]:
                check_search_icon_variants(browser, variant, width, path)
                ok(f'{variant} search at {width}px hides focus-mounted sibling magnifiers and browser decorations, keeps clear/Enter and restores native icons on disable')

        page = setup(browser, '/results?search_query=brand', '<ytd-app>' + MASTHEAD + '<ytd-page-manager class="ytd-app"><ytd-search>Results</ytd-search></ytd-page-manager></ytd-app>')
        page.locator('#logo').evaluate("element => element.innerHTML = '<span id=logo-icon><svg viewBox=\"0 0 90 20\"><rect width=90 height=20/></svg></span>'")
        expect(page.locator('#logo .myt-masthead-brand')).to_have_count(1)
        expect(page.locator('#logo-icon')).to_be_hidden()
        page.locator('#logo').evaluate("element => element.append(element.querySelector('.myt-masthead-brand').cloneNode(true))")
        expect(page.locator('#logo .myt-masthead-brand')).to_have_count(1)
        assert_stable(page)
        page.evaluate('__setEnabled(false)')
        expect(page.locator('.myt-masthead-brand')).to_have_count(0)
        expect(page.locator('#logo-icon')).to_be_visible()
        expect(page.locator('#logo')).to_have_attribute('href', '/')
        page.evaluate('__setEnabled(true)')
        expect(page.locator('#logo .myt-masthead-brand')).to_have_count(1)
        page.locator('#myt-masthead .myt-masthead-link').click()
        page.wait_for_url('https://www.youtube.com/')
        ok('homepage-style masthead brand repairs native rerenders without duplicates, restores native logo on disable and keeps its home link')
        page.close()

        for width,api in [(1440,'direct'),(390,'wrapper'),(1440,None)]:
            check_fullscreen_timeline(browser,width,api)
            ok(f'native fullscreen timeline at {width}px (API={api}) spans the frame, keeps proportional chapters and seeks decoded video by click/drag/keyboard')
        for width,height in [(1440,480),(390,360)]:
            check_theater_edges(browser,width,height)
            ok(f'theater at {width}px is edge-to-edge at native aspect ratio, with no top gap, rounded corners or playlist side gutter')
        for state in ['collapsed','class','hidden']:
            for theater in [False,True]:
                check_collapsed_playlist(browser,theater,1440,state)
                ok(f'collapsed playlist ({state}, theater={theater}) restores centered layout and reopens through its native control from the action row')
        check_collapsed_playlist(browser,False,390)
        ok('collapsed playlist action remains usable on a narrow viewport')
        for width in [1440,390]:
            check_description_link_styles(browser,width)
            ok(f'description links at {width}px use bold text and a decorative chain symbol, keep native navigation/timestamps and have no copy buttons')
        for theater in [False,True]:
            for width in [2010,1440,390]:
                check_playlist_layout(browser,theater,width)
                ok(f'playlist layout (theater={theater}, {width}px) aligns to the window edge, centers content, matches player/current-description height and keeps native scrolling/actions')
        check_theater_responsive_width(browser)
        ok('theater follows the current browser width on resize, despite cached 5000px native sizes and long content')
        check_fast_fullscreen(browser)
        ok('trusted fullscreen gestures request the native player directly and preserve decoded video/media identity')
        check_player_ad_data(browser)
        ok('initial player bootstrap and real Response.json discard ad slots but preserve native content URLs, playability and disabled parsers')
        check_player_ad_controls(browser)
        ok('only visible enabled native ad skip controls are clicked, with consecutive-ad/off support and unchanged media volume/rate/identity')
        check_native_home_fallback(browser)
        ok('native and SPA home stay usable when local extension files are unavailable; settings and search still work without a blind redirect')
        for modern,width in [(False,1440),(True,1440),(True,390)]:
            check_unsubscribe_staged_dialog(browser,modern,width)
            ok(f'unsubscribe dialog (modern={modern}, {width}px) never paints its outer shell, late heading/buttons or closing backdrop')
        for attributed in [False,True]:
            for width in [1440,390]:
                check_collaboration_card(browser,width,attributed)
                ok(f'collaborating authors (attributed={attributed}, {width}px) retain names, avatars, native author links/panels and subscription actions')
        check_local_title_fonts(browser)
        ok('packaged title fonts render real Latin/Cyrillic glyphs under a restrictive font policy and load each asset only once')
        for legacy in [False,True]:
            check_watch_language_change(browser,legacy)
            ok(f'watch language (legacy={legacy}) keeps English counts/full dates through legacy language settings, preserving source content')
        for language in ['ru','en']:
            check_watch_stats(browser,language)
            ok(f'watch stats ({language}) use compact counts without a views label and an exact calendar day, without relative-date guesses or stale-video metadata')
        check_description_icons(browser)
        ok('description arrows replace visible text and preserve accessible labels, keyboard expansion and collapse')
        check_chapter_sources(browser)
        ok('description and engagement-panel chapters are deduplicated by time, sorted and restricted to the current video')
        for dark in [False,True]:
            for width in [1440,390]:
                check_subscription_card(browser,dark,width,modern=dark)
                ok(f'channel card at {width}px (dark={dark}) groups metadata, toggles actual native subscriptions and preserves channel links, keyboard use, confirmation and signed-out state')
        for width in [1440,390]:
            check_chapter_follow(browser,width)
            ok(f'chapter rail at {width}px follows playback and forward/backward seeks without moving the page or resetting manual browsing on every clock tick')
            check_short_watch_scroll(browser,width)
            ok(f'short description at {width}px permits scrolling the whole player offscreen and back; native fixed video descendants track the page')
        for theater,width in [(False,1440),(True,1440),(False,390)]:
            check_native_watch(browser,theater,width)
            ok(f'native YouTube player at {width}px (theater={theater}) paints decoded frames, keeps controls/fullscreen and restores its nodes; channel and modern description render correctly; chapters scroll in one row')
        for target,theater,width in [('#ytd-player',False,1440),('#player',True,1440),('#movie_player',False,390)]:
            check_fullscreen_cached_layout(browser,target,theater,width)
            ok(f'fullscreen {target} at {width}px repairs cached zero-sized native wrappers, paints the full decoded picture and keeps controls/player cleanup')
        for replay in [False,True]:
            check_removed_chat(browser,replay)
            ok(f'live chat (replay={replay}) is hidden and its iframe unloaded; late mounts, disabled mode, native player and unrelated embeds remain safe')
        check_background_work(browser)
        ok('player clock and hidden home mutations do not rescan/rebuild UI; metadata still updates and hidden homepage previews pause')

        for dark in [False, True]:
            for width in [1440, 390]:
                check_watch_details(browser, dark, width)
                ok(f'watch description at {width}px ({"dark" if dark else "light"}) uses an isolated canvas with readable controls, chapter cards and transcript; preserves native player, actions, replies and cleanup')
        check_watch_details(browser, True, legacy=True)
        ok('legacy secondary-info data feeds the own isolated watch UI and restores native components on disable')

        # Exercise the native comment engine independently; own renderer integration
        # (including replies, player, menus and playlists) is checked above.
        watch = '<ytd-app>' + MASTHEAD + '''
          <ytd-page-manager class="ytd-app"><ytd-watch-flexy>
          <div id="columns"><div id="primary"><div id="player"><video></video></div>
          <ytd-watch-metadata><div id="above-the-fold"><h1>Video title</h1>
          <div id="top-row"><div id="owner">Channel</div><div id="actions"><div id="top-level-buttons-computed">
          <segmented-like-dislike-button-view-model id="video-votes"><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model>
          <button id="share">Share</button><button id="save">Save</button></div></div></div>
          <div id="description">Description</div></div></ytd-watch-metadata>
          <ytd-comments-entry-point-header-renderer id="comments-teaser">Comment teaser</ytd-comments-entry-point-header-renderer>
          <comments-entry-point-header-view-model id="modern-comments-teaser">Modern comment teaser</comments-entry-point-header-view-model>
          <ytd-comments id="comments"><div id="native-thread">Comment and replies <input id="reply-draft"></div></ytd-comments></div>
          <div id="secondary"><div id="secondary-inner"><div id="related">Recommendations</div></div></div></div>
        </ytd-watch-flexy></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/watch?v=abc", watch, watch_ui=False)
        centered(page, "#columns")
        expect(page.locator("#related")).to_be_hidden()
        expect(page.locator("ytd-comments")).to_be_hidden()
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<div id=playlist><ytd-playlist-panel-renderer><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer></div>')")
        expect(page.locator("ytd-playlist-panel-renderer")).to_be_visible()
        for mode in ["theater", "fullscreen"]:
            page.locator("ytd-watch-flexy").evaluate("(element, mode) => { element.removeAttribute('theater'); element.removeAttribute('fullscreen'); element.setAttribute(mode, ''); }", mode)
            video = page.locator("video").bounding_box()
            assert video["width"] == 640 and video["height"] == 360, (mode, video)
        ok("watch page centers, collapses comments, retains playlist and leaves native video dimensions intact")
        page.close()

        page = setup(browser, "/watch?v=abc", watch, watch_ui=False)
        toggle = page.locator("#myt-comments-toggle")
        expect(toggle).to_have_count(1)
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(page.locator("#video-votes")).to_be_hidden()
        expect(page.locator("#share")).to_be_visible()
        expect(page.locator("#save")).to_be_visible()
        expect(page.locator("#myt-masthead .myt-masthead-link")).to_be_visible()
        expect(page.locator("#myt-masthead .myt-masthead-query")).to_be_visible()
        expect(page.locator("#create")).to_be_hidden()
        expect(page.locator("#avatar-btn")).to_be_hidden()
        expect(page.locator("#voice-search-button")).to_be_hidden()
        centered_header(page)
        expect(page.locator("#comments-teaser")).to_be_hidden()
        expect(page.locator("#modern-comments-teaser")).to_be_hidden()
        metadata = page.locator("ytd-watch-metadata").bounding_box()
        primary = page.locator("#primary").bounding_box()
        assert metadata["width"] <= 900 and metadata["width"] < primary["width"], (metadata, primary)
        assert abs(metadata["x"] * 2 + metadata["width"] - (primary["x"] * 2 + primary["width"])) < 3
        video = page.locator("video").bounding_box()
        assert video["width"] == 640 and video["height"] == 360
        ok("watch header shows only logo/search, comments replace votes and metadata has a centered narrower rail")

        toggle.click()
        expect(toggle).to_have_attribute("aria-expanded", "true")
        expect(page.locator("ytd-comments")).to_be_visible()
        page.locator("#reply-draft").fill("Keep my native reply draft")
        toggle.press("Enter")
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(page.locator("ytd-comments")).to_be_hidden()
        toggle.press("Space")
        expect(page.locator("ytd-comments")).to_be_visible()
        expect(page.locator("#reply-draft")).to_have_value("Keep my native reply draft")
        assert page.locator("#native-thread").count() == 1
        assert_stable(page)
        ok("comments button opens/closes by mouse and keyboard while preserving native replies")

        navigate_spa(page, "/watch?v=abc&t=20&list=fixture")
        expect(toggle).to_have_attribute("aria-expanded", "true")
        expect(page.locator("ytd-comments")).to_be_visible()
        navigate_spa(page, "/watch?v=next")
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(page.locator("ytd-comments")).to_be_hidden()
        expect(toggle).to_have_count(1)
        ok("same-video time/playlist changes keep comments open; a new SPA video closes them")

        page.evaluate("__setEnabled(false)")
        expect(toggle).to_have_count(0)
        expect(page.locator("#video-votes")).to_be_visible()
        expect(page.locator("#create")).to_be_visible()
        expect(page.locator("#avatar-btn")).to_be_visible()
        expect(page.locator("ytd-comments")).to_be_visible()
        page.evaluate("__setEnabled(true)")
        expect(toggle).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        expect(page.locator("ytd-comments")).to_be_hidden()
        ok("disabling restores native votes/header/comments and re-enabling adds one toggle")

        page.locator("#top-level-buttons-computed").evaluate("element => element.innerHTML = '<segmented-like-dislike-button-view-model id=video-votes><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model><button id=share>Share</button><button id=save>Save</button>'")
        expect(toggle).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        toggle.click()
        expect(page.locator("ytd-comments")).to_be_visible()
        page.evaluate("""() => {
          const old = document.querySelector('ytd-watch-flexy').cloneNode(true);
          old.id = 'old-watch'; old.hidden = true;
          old.querySelector('#myt-comments-toggle')?.remove();
          document.querySelector('ytd-watch-flexy').before(old);
        }""")
        expect(toggle).to_have_count(1)
        assert page.locator("#old-watch #myt-comments-toggle").count() == 0
        ok("action rerenders repair the comments control without mounting duplicates in hidden watch components")
        page.close()

        legacy = watch.replace('''<div id="actions"><div id="top-level-buttons-computed">''', '''<div id="menu-container"><div id="top-level-buttons-computed">''').replace("segmented-like-dislike-button-view-model", "ytd-segmented-like-dislike-button-renderer")
        page = setup(browser, "/watch?v=legacy", legacy, watch_ui=False)
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        expect(page.locator("#share")).to_be_visible()
        expect(page.locator("#save")).to_be_visible()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("legacy segmented-vote/menu layout supports the same comments control")
        page.close()

        classic = legacy.replace('ytd-watch-metadata', 'ytd-video-primary-info-renderer')
        page = setup(browser, "/watch?v=classic", classic, language="ru", watch_ui=False)
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#myt-comments-toggle")).to_contain_text("Comments")
        expect(page.locator("#video-votes")).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("classic primary-info layout keeps the comments control English with Russian native markup")
        page.close()

        delayed = watch.replace('''<div id="actions"><div id="top-level-buttons-computed">
          <segmented-like-dislike-button-view-model id="video-votes"><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model>
          <button id="share">Share</button><button id="save">Save</button></div></div>''', '<div id="actions"></div>')
        assert 'id="top-level-buttons-computed"' not in delayed, "Delayed fixture must start without the action row"
        page = setup(browser, "/watch?v=delayed", delayed, watch_ui=False)
        page.locator("#actions").evaluate("element => element.innerHTML = '<div id=top-level-buttons-computed><segmented-like-dislike-button-view-model id=video-votes><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model><button id=share>Share</button><button id=save>Save</button></div>'")
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("comments control mounts when YouTube renders the video action row later")
        page.close()

        panel = '<ytd-engagement-panel-section-list-renderer target-id="engagement-panel-comments-section" visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED">Side comments</ytd-engagement-panel-section-list-renderer>'
        page = setup(browser, "/watch?v=panel", watch.replace('</ytd-watch-flexy>', panel + '</ytd-watch-flexy>'), watch_ui=False)
        expect(page.locator('ytd-engagement-panel-section-list-renderer')).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator('ytd-engagement-panel-section-list-renderer')).to_be_hidden()
        ok("expanded native comments side panels stay hidden while comments are closed")
        page.close()

        panel_only = watch.replace('<ytd-comments id="comments"><div id="native-thread">Comment and replies <input id="reply-draft"></div></ytd-comments>', '')
        collapsed_panel = '<ytd-engagement-panel-section-list-renderer id="native-comment-panel" target-id="engagement-panel-comments-section" visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN" hidden="native" aria-hidden="true"><div id="panel-threads">Native panel comments</div></ytd-engagement-panel-section-list-renderer>'
        page = setup(browser, "/watch?v=panel-only", panel_only.replace('</ytd-watch-flexy>', collapsed_panel + '</ytd-watch-flexy>'), watch_ui=False)
        panel = page.locator("#native-comment-panel")
        original_attributes = panel.evaluate("element => Object.fromEntries(['visibility', 'hidden', 'aria-hidden'].map(name => [name, element.getAttribute(name)]))")
        expect(panel).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(panel).to_be_visible()
        expect(panel).to_have_attribute("visibility", "ENGAGEMENT_PANEL_VISIBILITY_EXPANDED")
        expect(panel).to_have_attribute("aria-hidden", "false")
        assert panel.get_attribute("hidden") is None
        expect(page.locator("#myt-comments-toggle")).to_have_attribute("aria-controls", "native-comment-panel")
        assert_stable(page)
        page.locator("#myt-comments-toggle").click()
        expect(panel).to_be_hidden()
        assert panel.evaluate("element => Object.fromEntries(['visibility', 'hidden', 'aria-hidden'].map(name => [name, element.getAttribute(name)]))") == original_attributes
        page.locator("#myt-comments-toggle").click()
        expect(panel).to_be_visible()
        panel.evaluate("element => element.setAttribute('visibility', 'ENGAGEMENT_PANEL_VISIBILITY_HIDDEN')")
        expect(page.locator("#myt-comments-toggle")).to_have_attribute("aria-expanded", "false")
        expect(panel).to_be_hidden()
        assert panel.evaluate("element => Object.fromEntries(['visibility', 'hidden', 'aria-hidden'].map(name => [name, element.getAttribute(name)]))") == original_attributes
        assert_stable(page)
        page.locator("#myt-comments-toggle").click()
        expect(panel).to_be_visible()
        navigate_spa(page, "/watch?v=panel-next")
        expect(panel).to_be_hidden()
        assert panel.evaluate("element => Object.fromEntries(['visibility', 'hidden', 'aria-hidden'].map(name => [name, element.getAttribute(name)]))") == original_attributes
        page.locator("#myt-comments-toggle").click()
        expect(panel).to_be_visible()
        page.evaluate("__setEnabled(false)")
        expect(page.locator("#myt-comments-toggle")).to_have_count(0)
        assert panel.evaluate("element => Object.fromEntries(['visibility', 'hidden', 'aria-hidden'].map(name => [name, element.getAttribute(name)]))") == original_attributes
        ok("panel-only comments expand and exactly restore native attributes on close, video change and disable without observer loops")
        page.close()

        inactive_metadata = watch.replace('<ytd-watch-metadata>', '<ytd-watch-metadata aria-hidden="true">')
        page = setup(browser, "/watch?v=activating", inactive_metadata, watch_ui=False)
        expect(page.locator("#myt-comments-toggle")).to_have_count(0)
        page.locator("ytd-watch-metadata").evaluate("element => element.setAttribute('aria-hidden', 'false')")
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        assert_stable(page)
        ok("native aria-hidden-only metadata activation mounts one functioning comments control")
        page.close()

        unavailable = watch.replace('<ytd-comments id="comments"><div id="native-thread">Comment and replies <input id="reply-draft"></div></ytd-comments>', '<p id="comments-disabled">Comments are disabled</p>')
        assert '<ytd-comments ' not in unavailable, "Unavailable fixture must omit native comment threads"
        page = setup(browser, "/watch?v=disabled-comments", unavailable, watch_ui=False)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        toggle = page.locator("#myt-comments-toggle")
        expect(toggle).to_have_count(1)
        if toggle.is_enabled():
            toggle.click()
        expect(page.locator("#comments-disabled")).to_be_visible()
        assert not errors, errors
        ok("videos with disabled/unavailable comments keep the page usable without script errors")
        page.close()

        page = setup(browser, "/watch?v=abc&list=fixture", watch, watch_ui=False)
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<ytd-playlist-panel-renderer id=playlist><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer>')")
        expect(page.locator("#secondary")).to_be_visible()
        expect(page.locator("#playlist")).to_be_visible()
        page.locator("#playlist").evaluate("element => element.hidden = true")
        expect(page.locator("#secondary")).to_be_hidden()
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<ytd-live-chat-frame id=chat>Live chat</ytd-live-chat-frame>')")
        expect(page.locator("#secondary")).to_be_hidden()
        expect(page.locator("#chat")).to_be_hidden()
        ok("native playlist retains its sidebar; hidden playlist and removed live chat leave no blank sidebar")
        page.close()

        page = setup(browser, "/watch?v=abc&list=fixture", watch, width=390, watch_ui=False)
        page.locator("video").evaluate("element => element.style.cssText = 'width: 100%; max-width: 640px; height: auto; aspect-ratio: 16 / 9'")
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<ytd-playlist-panel-renderer id=playlist><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer>')")
        expect(page.locator("#playlist")).to_be_visible()
        centered(page, "#columns")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile watch page overflows"
        primary = page.locator("#primary").bounding_box()
        secondary = page.locator("#secondary").bounding_box()
        assert secondary["y"] >= primary["y"] + primary["height"], (primary, secondary)
        ok("390px watch page stacks playlist below responsive native player without overflow")
        page.close()

        from search import check as check_owned_search
        for width in [1440,900,390]:
            check_owned_search(browser,width,True)
            ok(f'owned search at {width}px extracts minimal cards, puts channels first and preserves ordered rows, filters and pagination')

        for width in [1440, 390]:
            check_home_settings(browser,width)
            ok(f'home settings at {width}px expose official account controls, confirm scoped cookie deletion, save theme and keep English UI and close accessibly')
        check_settings_failures(browser)
        ok('settings show cookie permission failures and restore theme after failed storage writes')

        for width in [1440,390]:
            check_header_alignment_and_anonymous_icons(browser,width)
            ok(f'header at {width}px aligns logo/field/text centers and hides unnamed focus magnifiers while preserving keyboard/clear/Enter')

        check_channel_row_gaps(browser)
        ok('native channel row wrappers keep one 32px gap and restore original spacing on disable')

        check_full_width_background_scroll(browser)
        ok('left and right empty areas inside a full-width renderer scroll the document even when native wheel is blocked; nested scrolling and disabled mode stay native')

        for dark in [False,True]:
            check_channel_hover_surface(browser,dark)
            ok(f'{"dark" if dark else "light"} channel-page rich/grid/modern video backgrounds survive native hover/focus overrides')

        check_settings_short_viewport(browser)
        ok('settings fit a short viewport, keep the close control visible while scrolling and restore home on Escape')

        popup_html = (ROOT / "src/popup/popup.html").read_text().replace('<script src="./popup.js"></script>', '')
        page = browser.new_page()
        page.set_content(popup_html)
        page.evaluate(MOCK, {})
        page.add_style_tag(path=str(ROOT / "src/popup/popup.css"))
        page.add_script_tag(path=str(ROOT / "src/popup/popup.js"))
        expect(page.locator("#toggle")).to_be_checked()
        page.locator("#toggle").uncheck()
        assert page.evaluate("__stored.enabled") is False
        page.evaluate("__setEnabled(true)")
        expect(page.locator("#toggle")).to_be_checked()
        page.evaluate("""() => { chrome.storage.local.set = (value, cb) => {
            chrome.runtime.lastError = {message: 'Fixture write failure'};
            cb(); delete chrome.runtime.lastError;
        }; }""")
        page.locator("#toggle").click()
        expect(page.locator("#toggle")).to_be_checked()
        expect(page.locator("#toggle")).to_be_enabled()
        expect(page.locator("#error")).to_be_visible()
        ok("popup writes settings, tracks external changes and restores state after write failure")
        page.close()

        page = browser.new_page()
        page.set_content(popup_html)
        page.evaluate(MOCK, {})
        page.evaluate("chrome.runtime.lastError = {message: 'Fixture read failure'}")
        page.add_script_tag(path=str(ROOT / "src/popup/popup.js"))
        expect(page.locator("#toggle")).to_be_disabled()
        expect(page.locator("#error")).to_be_visible()
        ok("popup handles storage read failure without accepting an unknown state")
        page.close()
        page = browser.new_page()
        page.set_content(popup_html)
        page.evaluate(MOCK, {'language':'ru'})
        page.add_script_tag(path=str(ROOT / 'src/popup/popup.js'))
        expect(page.locator('html')).to_have_attribute('lang','en')
        expect(page.locator('#setting-title')).to_have_text('Focus mode')
        page.evaluate("chrome.storage.local.set({language:'en'})")
        expect(page.locator('#setting-title')).to_have_text('Focus mode')
        expect(page.locator('#toggle')).to_be_checked()
        ok('popup stays English with legacy language settings and retains focus mode')
        page.close()

        browser.close()
    print(f"{passed} browser fixture checks passed (mock storage; live integration not tested)")


if __name__ == "__main__":
    main()
