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


def setup(browser, path="/", body="", enabled=None, width=1440, theme=None, native_dark=False, language="en"):
    page = browser.new_page(viewport={"width": width, "height": 960}, reduced_motion="reduce")
    page.route("https://www.youtube.com/**", lambda route: route.fulfill(
        status=200, content_type="text/html", body=document(body)))
    page.goto("https://www.youtube.com" + path)
    initial = {} if enabled is None else {"enabled": enabled}
    if theme is not None:
        initial["theme"] = theme
    page.evaluate(MOCK, initial)
    page.evaluate("language => document.documentElement.lang = language", language)
    if native_dark:
        page.evaluate("document.documentElement.setAttribute('dark', '')")
    page.add_style_tag(path=str(ROOT / "src/styles/styles.css"))
    page.add_script_tag(path=str(ROOT / "src/content/content.js"))
    return page


def centered(page, selector, tolerance=3):
    bounds = page.locator(selector).bounding_box()
    assert bounds and bounds["width"] > 0, f"Missing layout box: {selector}"
    viewport = page.viewport_size["width"]
    assert abs(bounds["x"] * 2 + bounds["width"] - viewport) < tolerance, (selector, bounds, viewport)
    assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= viewport + 1, bounds


def centered_header(page):
    brand = page.locator("ytd-masthead .myt-masthead-brand")
    logo = brand.bounding_box() if brand.count() else page.locator("#logo-icon svg").bounding_box()
    search = page.locator("#search-form, .ytSearchboxComponentSearchForm").bounding_box()
    assert logo and search, (logo, search)
    left = min(logo["x"], search["x"])
    right = max(logo["x"] + logo["width"], search["x"] + search["width"])
    assert abs(left + right - page.viewport_size["width"]) < 3, (logo, search)
    assert logo["y"] < search["y"] + search["height"] and search["y"] < logo["y"] + logo["height"]


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
    code = (ROOT / "src/content/content.js").read_text()
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


def assert_card_surface(page, selector):
    card = page.locator(selector)
    color = "element => getComputedStyle(element).backgroundColor.match(/[\\d.]+/g).map(Number)"
    page.evaluate("document.activeElement?.blur()")
    page.mouse.move(1, 1)
    base = card.evaluate(color)
    assert len(base) == 3 or base[3] > .95, (selector, base)
    assert max(base[:3]) - min(base[:3]) < 16, (selector, base)
    assert card.evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
    card.hover()
    hover = card.evaluate(color)
    assert sum(hover[:3]) > sum(base[:3]), (selector, base, hover)
    page.mouse.move(1, 1)
    card.locator('a[href]').first.focus()
    focused = card.evaluate(color)
    assert sum(focused[:3]) > sum(base[:3]), (selector, base, focused)
    page.evaluate("document.activeElement?.blur()")


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
        expect(page.locator("#myt-home .myt-search__icon")).to_have_count(0)
        home_mark = page.locator("#myt-home .myt-home__mark").inner_html()
        home_wordmark = page.locator("#myt-home .myt-home__wordmark").text_content()
        assert page.locator("#native-state").count() == 1, "Homepage must preserve YouTube's native DOM"
        expect(page).to_have_title("YouTube")
        centered(page, ".myt-search")
        submit = page.locator(".myt-search__submit")
        assert submit.text_content().strip() == "", "Homepage search should use an icon-only submit button"
        assert submit.get_attribute("aria-label"), "Icon-only search needs an accessible name"
        expect(submit.locator("svg")).to_have_count(1)
        assert page.locator(".myt-search").evaluate("element => getComputedStyle(element).boxShadow") == "none"
        home_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        for selector in ["html", "body", "#native-app"]:
            background = page.locator(selector).evaluate("element => getComputedStyle(element).backgroundColor")
            assert background in [home_bg, "rgba(0, 0, 0, 0)"], (selector, background, home_bg)
        page.locator("#myt-query").fill("    ")
        page.locator(".myt-search__submit").click()
        assert page.url == "https://www.youtube.com/", "Empty search must stay on home"
        ok("homepage preserves native DOM, centers search and ignores blank query")

        page.locator("#myt-query").fill("  кот & C++ #музыка  ")
        page.locator(".myt-search__submit").click()
        page.wait_for_url("**/results?**")
        assert parse_qs(urlparse(page.url).query)["search_query"] == ["кот & C++ #музыка"], page.url
        ok("search encodes Unicode, ampersands, plus signs and hash")
        page.close()

        page = setup(browser, native_dark=True)
        expect(page.locator("#myt-home h1, #myt-home .myt-home__eyebrow, #myt-home .myt-home__description, #myt-home .myt-home__hint")).to_have_count(0)
        expect(page.locator("#myt-theme-toggle")).to_be_visible()
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "dark")
        dark_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        page.locator("#myt-theme-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "light")
        light_bg = page.locator("#myt-home").evaluate("element => getComputedStyle(element).backgroundColor")
        assert dark_bg != light_bg, (dark_bg, light_bg)
        assert page.evaluate("__stored.theme") == "light"
        assert page.locator("html[dark]").count() == 1, "Homepage theme must preserve YouTube's native theme"
        page.locator("#myt-theme-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-myt-theme", "dark")
        assert page.evaluate("__stored.theme") == "dark"
        ok("homepage contains only brand/search/theme and switches persisted local theme without changing YouTube theme")
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
        page.locator(".myt-search__submit").scroll_into_view_if_needed()
        expect(page.locator(".myt-search__submit")).to_be_in_viewport()
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

        page = setup(browser, "/feed/subscriptions", '<ytd-app><ytd-page-manager class="ytd-app"><ytd-browse><div id="primary" style="width: 700px; margin-left: 37px">Subscriptions</div></ytd-browse></ytd-page-manager></ytd-app>')
        bounds = page.locator("#primary").bounding_box()
        assert bounds["width"] == 700 and bounds["x"] == 37, bounds
        ok("nonchannel browse primary dimensions are not globally overridden")
        page.close()

        page = setup(browser, "/shorts/abc")
        page.wait_for_url("https://www.youtube.com/")
        ok("direct Shorts playback redirects to home")
        page.close()
        page = setup(browser, "/@creator/shorts")
        page.wait_for_url("https://www.youtube.com/@creator/videos")
        ok("channel Shorts URL redirects to Videos tab")
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
          <div id="header"><div id="banner" style="height:180px;background:#345"><img id="banner-image" alt="Channel banner" style="display:block;width:100%;height:180px"></div>
          <ytd-c4-tabbed-header-renderer><div id="channel-header-container"><div id="profile"><img id="profile-avatar" alt="Profile" style="display:block;width:160px;height:160px;border-radius:50%"><h1>Channel title</h1></div></div></ytd-c4-tabbed-header-renderer></div>
          <div id="tabs"><tp-yt-paper-tabs><tp-yt-paper-tab>Home</tp-yt-paper-tab><tp-yt-paper-tab>Videos</tp-yt-paper-tab></tp-yt-paper-tabs></div>
          <div id="contents"><ytd-rich-grid-renderer id="channel-grid"><ytd-rich-item-renderer><ytd-thumbnail id="channel-thumbnail" style="height:180px;background:#345">Thumbnail</ytd-thumbnail></ytd-rich-item-renderer></ytd-rich-grid-renderer></div>
          </ytd-browse></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/@creator/videos", channel_profile)
        banner = page.locator("#banner").bounding_box()
        assert banner["x"] == 0 and banner["width"] == 1440, banner
        assert page.locator("#banner-image").bounding_box()["width"] == 1440
        assert page.locator("#profile-avatar").bounding_box()["width"] == 160, "Avatar must keep its own size"
        centered(page, "#channel-header-container")
        centered(page, "#tabs")
        assert page.locator("#channel-header-container").bounding_box()["width"] <= 1280
        assert page.locator("#tabs").evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
        assert page.locator("#channel-thumbnail").evaluate("element => parseFloat(getComputedStyle(element).borderRadius)") >= 12
        grid_gap = page.locator("#channel-grid").evaluate("element => parseFloat(getComputedStyle(element).getPropertyValue('--ytd-rich-grid-item-margin'))")
        assert grid_gap >= 28, grid_gap
        columns = page.locator("#channel-grid").evaluate("element => parseInt(getComputedStyle(element).getPropertyValue('--ytd-rich-grid-items-per-row'))")
        assert columns == 3, columns
        centered_header(page)
        for selector in ["#logo", "#search"]:
            expect(page.locator(selector)).to_be_visible()
        for selector in ["#create", "#avatar-btn", "#voice-search-button"]:
            expect(page.locator(selector)).to_be_hidden()
        ok("channel banner fills the viewport while profile/avatar, rounded tabs and spaced cards keep centered dimensions")
        page.close()

        modern_channel = channel_profile.replace('<div id="banner" style="height:180px;background:#345"><img id="banner-image" alt="Channel banner" style="display:block;width:100%;height:180px"></div>', '<yt-image-banner-view-model id="modern-channel-banner" style="height:180px;background:#345"></yt-image-banner-view-model>')
        page = setup(browser, "/@creator", modern_channel)
        modern_banner = page.locator("#modern-channel-banner").bounding_box()
        assert modern_banner["x"] == 0 and modern_banner["width"] == 1440, modern_banner
        assert page.locator("#profile-avatar").bounding_box()["width"] == 160
        ok("modern image-banner component also spans the channel width without resizing the avatar")
        page.close()

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
        navigate_spa(page, "/feed/subscriptions")
        page.mouse.wheel(0, 300)
        page.evaluate("async () => { for (let n=0;n<5;n++) await new Promise(requestAnimationFrame); }")
        page.wait_for_function("document.querySelector('#main-scroll').scrollTop >= 250")
        ok("gutter-wheel fallback stays inactive when disabled and also supports other enabled pages")
        page.close()

        for path, renderer in [("/watch?v=scroll", "ytd-watch-flexy"), ("/results?search_query=scroll", "ytd-search")]:
            scroll_fixture = channel_scroll.replace("ytd-browse", renderer)
            page = setup(browser, path, scroll_fixture)
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
            page.evaluate("document.documentElement.style.cssText='height:100%;overflow:hidden'; document.body.style.cssText='height:100%;overflow:hidden'")
            page.mouse.move(10, 400)
            page.mouse.wheel(0, 300)
            page.wait_for_function("document.querySelector('#inner-scroll').scrollTop >= 250")
            ok(f"{renderer} detects an inner scrollport and ignores a stale hidden SPA renderer")
            page.close()

        for path in ["/watch?v=header", "/results?search_query=header", "/@creator/videos", "/feed/subscriptions"]:
            page = setup(browser, path, '<ytd-app>' + MASTHEAD + '<ytd-page-manager class="ytd-app"><ytd-browse>Native content</ytd-browse></ytd-page-manager></ytd-app>')
            centered_header(page)
            expect(page.locator("#create")).to_be_hidden()
            expect(page.locator("#avatar-btn")).to_be_hidden()
            page.locator("#search").fill("кот & C++")
            page.locator("#search-icon-legacy").click()
            page.wait_for_url("**/results?**")
            assert parse_qs(urlparse(page.url).query)["search_query"] == ["кот & C++"], page.url
            ok(f"logo and functional native search stay centered together on {path.split('?')[0]}")
            page.close()

        legacy_searchbox = MASTHEAD[MASTHEAD.index('<ytd-searchbox>'):MASTHEAD.index('</ytd-searchbox>') + len('</ytd-searchbox>')]
        modern_searchbox = '''<yt-searchbox><div class="ytSearchboxComponentHost"><form class="ytSearchboxComponentSearchForm" action="/results" method="get"><div class="ytSearchboxComponentInputBox"><input class="ytSearchboxComponentInput" id="search" name="search_query" aria-label="Search"></div><button class="ytSearchboxComponentSearchButton" type="submit" aria-label="Search"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="m15 15 5 5"/></svg></button></form></div></yt-searchbox>'''
        modern_header = MASTHEAD.replace(legacy_searchbox, modern_searchbox)
        page = setup(browser, "/results?search_query=modern", '<ytd-app>' + modern_header + '<ytd-page-manager class="ytd-app"><ytd-search>Modern results</ytd-search></ytd-page-manager></ytd-app>')
        centered_header(page)
        page.locator("#search").fill("modern & search")
        page.locator(".ytSearchboxComponentSearchButton").click()
        page.wait_for_url("**/results?**")
        assert parse_qs(urlparse(page.url).query)["search_query"] == ["modern & search"]
        ok("modern native searchbox keeps its visible logo/form group centered and submits normally")
        page.close()

        for variant, header in [('legacy', MASTHEAD), ('modern', modern_header)]:
            for width in [1440, 390]:
                page = setup(browser, '/results?search_query=icon', '<ytd-app>' + header + '<ytd-page-manager class="ytd-app"><ytd-search>Results</ytd-search></ytd-page-manager></ytd-app>', width=width)
                icon_class = 'search-icon' if variant == 'legacy' else 'ytSearchboxComponentSearchIconContainer'
                icon_id = 'search-icon' if variant == 'legacy' else 'fixture-modern-icon'
                holder = '#search-input' if variant == 'legacy' else '.ytSearchboxComponentInputBox'
                page.locator(holder).evaluate("(element, fixture) => { element.style.position='relative'; element.insertAdjacentHTML('afterbegin', fixture); }", f'<span id="{icon_id}" class="{icon_class}" data-fixture-leading style="position:absolute;left:0;top:0;width:24px;height:24px"><svg viewBox="0 0 24 24" width="24" height="24"><circle cx="10" cy="10" r="7"/></svg></span>')
                expect(page.locator('[data-fixture-leading]')).to_be_hidden()
                expect(page.locator('.myt-masthead-brand')).to_have_count(1)
                expect(page.locator('#logo-icon')).to_be_hidden()
                assert page.locator('.myt-masthead-brand .myt-home__mark').inner_html() == home_mark
                assert page.locator('.myt-masthead-brand .myt-home__wordmark').text_content() == home_wordmark
                centered_header(page)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Header must fit narrow screens'
                page.locator('#search').fill('Савельев Сергей & C++')
                expect(page.locator('#search')).to_have_value('Савельев Сергей & C++')
                submit = page.locator('#search-icon-legacy' if variant == 'legacy' else '.ytSearchboxComponentSearchButton')
                expect(submit).to_be_visible()
                if width == 1440:
                    page.locator('#search').press('Enter')
                else:
                    submit.click()
                page.wait_for_url('**/results?**')
                assert parse_qs(urlparse(page.url).query)['search_query'] == ['Савельев Сергей & C++']
                ok(f'{variant} search at {width}px removes overlapping leading icon, retains native submit and uses homepage brand')
                page.close()

        page = setup(browser, '/results?search_query=brand', '<ytd-app>' + MASTHEAD + '<ytd-page-manager class="ytd-app"><ytd-search>Results</ytd-search></ytd-page-manager></ytd-app>')
        page.locator('#logo').evaluate("element => element.innerHTML = '<span id=logo-icon><svg viewBox=\"0 0 90 20\"><rect width=90 height=20/></svg></span>'")
        expect(page.locator('.myt-masthead-brand')).to_have_count(1)
        expect(page.locator('#logo-icon')).to_be_hidden()
        page.locator('#logo').evaluate("element => element.append(element.querySelector('.myt-masthead-brand').cloneNode(true))")
        expect(page.locator('.myt-masthead-brand')).to_have_count(1)
        assert_stable(page)
        page.evaluate('__setEnabled(false)')
        expect(page.locator('.myt-masthead-brand')).to_have_count(0)
        expect(page.locator('#logo-icon')).to_be_visible()
        expect(page.locator('#logo')).to_have_attribute('href', '/')
        page.evaluate('__setEnabled(true)')
        expect(page.locator('.myt-masthead-brand')).to_have_count(1)
        page.locator('#logo').click()
        page.wait_for_url('https://www.youtube.com/')
        ok('homepage-style masthead brand repairs native rerenders without duplicates, restores native logo on disable and keeps its home link')
        page.close()

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
        page = setup(browser, "/watch?v=abc", watch)
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

        page = setup(browser, "/watch?v=abc", watch)
        toggle = page.locator("#myt-comments-toggle")
        expect(toggle).to_have_count(1)
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(page.locator("#video-votes")).to_be_hidden()
        expect(page.locator("#share")).to_be_visible()
        expect(page.locator("#save")).to_be_visible()
        expect(page.locator("#logo")).to_be_visible()
        expect(page.locator("#search")).to_be_visible()
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
        page = setup(browser, "/watch?v=legacy", legacy)
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        expect(page.locator("#share")).to_be_visible()
        expect(page.locator("#save")).to_be_visible()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("legacy segmented-vote/menu layout supports the same comments control")
        page.close()

        classic = legacy.replace('ytd-watch-metadata', 'ytd-video-primary-info-renderer')
        page = setup(browser, "/watch?v=classic", classic, language="ru")
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#myt-comments-toggle")).to_contain_text("Комментарии")
        expect(page.locator("#video-votes")).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("classic primary-info layout mounts a localized Russian comments control")
        page.close()

        delayed = watch.replace('''<div id="actions"><div id="top-level-buttons-computed">
          <segmented-like-dislike-button-view-model id="video-votes"><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model>
          <button id="share">Share</button><button id="save">Save</button></div></div>''', '<div id="actions"></div>')
        assert 'id="top-level-buttons-computed"' not in delayed, "Delayed fixture must start without the action row"
        page = setup(browser, "/watch?v=delayed", delayed)
        page.locator("#actions").evaluate("element => element.innerHTML = '<div id=top-level-buttons-computed><segmented-like-dislike-button-view-model id=video-votes><button>Like</button><button>Dislike</button></segmented-like-dislike-button-view-model><button id=share>Share</button><button id=save>Save</button></div>'")
        expect(page.locator("#myt-comments-toggle")).to_have_count(1)
        expect(page.locator("#video-votes")).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        ok("comments control mounts when YouTube renders the video action row later")
        page.close()

        panel = '<ytd-engagement-panel-section-list-renderer target-id="engagement-panel-comments-section" visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED">Side comments</ytd-engagement-panel-section-list-renderer>'
        page = setup(browser, "/watch?v=panel", watch.replace('</ytd-watch-flexy>', panel + '</ytd-watch-flexy>'))
        expect(page.locator('ytd-engagement-panel-section-list-renderer')).to_be_hidden()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator("ytd-comments")).to_be_visible()
        page.locator("#myt-comments-toggle").click()
        expect(page.locator('ytd-engagement-panel-section-list-renderer')).to_be_hidden()
        ok("expanded native comments side panels stay hidden while comments are closed")
        page.close()

        panel_only = watch.replace('<ytd-comments id="comments"><div id="native-thread">Comment and replies <input id="reply-draft"></div></ytd-comments>', '')
        collapsed_panel = '<ytd-engagement-panel-section-list-renderer id="native-comment-panel" target-id="engagement-panel-comments-section" visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN" hidden="native" aria-hidden="true"><div id="panel-threads">Native panel comments</div></ytd-engagement-panel-section-list-renderer>'
        page = setup(browser, "/watch?v=panel-only", panel_only.replace('</ytd-watch-flexy>', collapsed_panel + '</ytd-watch-flexy>'))
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
        page = setup(browser, "/watch?v=activating", inactive_metadata)
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
        page = setup(browser, "/watch?v=disabled-comments", unavailable)
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

        page = setup(browser, "/watch?v=abc&list=fixture", watch)
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<ytd-playlist-panel-renderer id=playlist><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer>')")
        expect(page.locator("#secondary")).to_be_visible()
        expect(page.locator("#playlist")).to_be_visible()
        page.locator("#playlist").evaluate("element => element.hidden = true")
        expect(page.locator("#secondary")).to_be_hidden()
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<ytd-live-chat-frame id=chat>Live chat</ytd-live-chat-frame>')")
        expect(page.locator("#secondary")).to_be_visible()
        expect(page.locator("#chat")).to_be_visible()
        page.locator("#chat").evaluate("element => element.setAttribute('collapsed', '')")
        expect(page.locator("#secondary")).to_be_hidden()
        ok("native playlist renderer and live chat retain sidebar; hidden/collapsed panels leave no blank sidebar")
        page.close()

        page = setup(browser, "/watch?v=abc&list=fixture", watch, width=390)
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

        def result_card(number):
            return f'''<ytd-video-renderer id="result-{number}"><div id="dismissible">
              <ytd-thumbnail id="thumbnail"><a href="/watch?v=result{number}" aria-label="Preview {number}"><div style="aspect-ratio:16/9;background:#333"></div></a><ytd-thumbnail-overlay-time-status-renderer>10:00</ytd-thumbnail-overlay-time-status-renderer></ytd-thumbnail>
              <div id="details" class="text-wrapper"><div id="meta"><h3><a id="video-title" href="/watch?v=result{number}">Video title {number}</a></h3>
              <div id="metadata-line">100 views · yesterday</div></div>
              <div id="channel-info"><ytd-channel-name><a href="/@creator{number}">Channel {number}</a></ytd-channel-name></div>
              <div id="description-text">Long video description</div><div class="metadata-snippet-container">Snippet</div>
              <ytd-badge-supported-renderer>Badge</ytd-badge-supported-renderer></div></div></ytd-video-renderer>'''

        search_header = watch.split('<ytd-page-manager')[0]
        modern = '''<yt-lockup-view-model id="modern-video"><div class="ytLockupViewModelHost"><a href="/watch?v=modern"><div style="aspect-ratio:16/9;background:#333">Modern preview</div></a>
          <div class="ytLockupMetadataViewModelHost"><h3><a href="/watch?v=modern">Modern video</a></h3><a href="/@modern">Modern channel</a></div></div></yt-lockup-view-model>'''
        search = search_header + '''<ytd-page-manager class="ytd-app"><ytd-search><div id="container">
          <ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">''' + result_card(1) + result_card(2) + result_card(3) + '''
          <ytd-channel-renderer id="channel-result"><a href="/@channel">Channel result</a></ytd-channel-renderer>
          <ytd-playlist-renderer id="playlist-result"><a href="/playlist?list=fixture">Playlist result</a></ytd-playlist-renderer>
          ''' + modern + result_card(4) + '''<ytd-continuation-item-renderer id="continuation">Load more</ytd-continuation-item-renderer>
          </div></ytd-item-section-renderer></div></ytd-section-list-renderer>
          </div></ytd-search></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/results?search_query=fixture", search)
        expect(page.locator("html")).to_have_attribute("data-myt-page", "search")
        left = page.locator("#result-1").bounding_box()
        right = page.locator("#result-2").bounding_box()
        assert abs(left["y"] - right["y"]) < 2 and right["x"] > left["x"] + left["width"], (left, right)
        assert abs(left["width"] - right["width"]) < 2, (left, right)
        third = page.locator("#result-3").bounding_box()
        assert abs(third["y"] - left["y"]) < 2 and third["x"] > right["x"] + right["width"], (left, right, third)
        assert abs(third["width"] - left["width"]) < 2
        for selector in ["#result-1 #thumbnail", "#result-1 #video-title", "#result-1 ytd-channel-name"]:
            expect(page.locator(selector)).to_be_visible()
        for selector in ["#result-1 #metadata-line", "#result-1 #description-text", "#result-1 .metadata-snippet-container", "#result-1 ytd-badge-supported-renderer"]:
            expect(page.locator(selector)).to_be_hidden()
        thumbnail = page.locator("#result-1 #thumbnail").bounding_box()
        title = page.locator("#result-1 #video-title").bounding_box()
        assert title["y"] >= thumbnail["y"] + thumbnail["height"], (thumbnail, title)
        for selector in ["#logo", "#search"]:
            expect(page.locator(selector)).to_be_visible()
        for selector in ["#create", "#avatar-btn", "#voice-search-button"]:
            expect(page.locator(selector)).to_be_hidden()
        centered_header(page)
        ok("desktop search uses three equal preview-top cards with title/channel and a centered logo/search header")

        for selector in ["#channel-result", "#playlist-result", "#continuation"]:
            expect(page.locator(selector)).to_be_visible()
            bounds = page.locator(selector).bounding_box()
            assert bounds["width"] > left["width"] * 2.9, (selector, bounds, left)
        expect(page.locator("#channel-result a")).to_have_attribute("href", "/@channel")
        expect(page.locator("#playlist-result a")).to_have_attribute("href", "/playlist?list=fixture")
        expect(page.locator("#modern-video[data-myt-search-video]")).to_have_count(1)
        modern_bounds = page.locator("#modern-video").bounding_box()
        assert abs(modern_bounds["width"] - left["width"]) < 2, (modern_bounds, left)
        page.locator("ytd-item-section-renderer > #contents").evaluate("(element, card) => element.insertAdjacentHTML('beforeend', card)", result_card(5))
        expect(page.locator("#result-5 #description-text")).to_be_hidden()
        dynamic = page.locator("#result-5").bounding_box()
        assert abs(dynamic["width"] - left["width"]) < 2, (dynamic, left)
        ok("mixed search channels/playlists/continuation retain full width and dynamic/modern video cards use the grid")
        page.close()

        def modern_result(identifier, href, avatar=False, playlist=False):
            identity = 'content-type="playlist"' if playlist else ''
            avatar_link = '<a id="avatar" href="/@creator">Avatar</a>' if avatar else ''
            return f'''<yt-lockup-view-model id="{identifier}" {identity}><div class="ytLockupViewModelHost">
              {avatar_link}<a class="ytLockupViewModelContentImage" href="{href}"><div style="aspect-ratio:16/9;background:#333">Preview</div></a>
              <div class="ytLockupMetadataViewModelHost"><h3><a href="{href}">Video {identifier}</a></h3><a href="/@creator">Channel</a></div>
              </div></yt-lockup-view-model>'''

        regressions = (modern_result('list-video', '/watch?v=ordinary&list=PLcontext') +
            modern_result('avatar-first', '/watch?v=avatar', avatar=True) +
            '<div id="single-wrapper" style="width:1100px">' + modern_result('wrapped-video', '/watch?v=wrapped') + '</div>' +
            '<ytd-shelf-renderer id="video-shelf"><div id="content"><div id="shelf-items">' +
            result_card(21) + result_card(22) + result_card(23) + '</div></div></ytd-shelf-renderer>' +
            modern_result('real-playlist', '/watch?v=first&list=PLcollection', playlist=True) +
            '<ytd-continuation-item-renderer id="new-continuation">Load more</ytd-continuation-item-renderer>')
        regression_search = search_header + '<ytd-page-manager class="ytd-app"><ytd-search><div id="container"><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">' + regressions + '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></div></ytd-search></ytd-page-manager></ytd-app>'
        page = setup(browser, '/results?search_query=regression', regression_search)
        row_width = page.locator('ytd-item-section-renderer > #contents').bounding_box()['width']
        expected_width = (row_width - 48) / 3
        for selector in ['#list-video', '#avatar-first', '#wrapped-video', '#single-wrapper', '#result-21', '#result-22', '#result-23']:
            expect(page.locator(selector + '[data-myt-search-cell]')).to_have_count(1)
            box = page.locator(selector).bounding_box()
            assert abs(box['width'] - expected_width) < 2, (selector, box, expected_width)
        first_row = [page.locator(selector).bounding_box() for selector in ['#list-video', '#avatar-first', '#single-wrapper']]
        assert max(box['y'] for box in first_row) - min(box['y'] for box in first_row) < 2, first_row
        shelf_row = [page.locator(f'#result-{number}').bounding_box() for number in [21,22,23]]
        assert max(box['y'] for box in shelf_row) - min(box['y'] for box in shelf_row) < 2, shelf_row
        assert page.locator('#real-playlist[data-myt-search-video]').count() == 0
        assert abs(page.locator('#real-playlist').bounding_box()['width'] - row_width) < 2
        assert abs(page.locator('#new-continuation').bounding_box()['width'] - row_width) < 2
        ok('list-context, avatar-first, wrapped and shelved videos stay in three columns while real playlists keep full width')

        page.locator('ytd-item-section-renderer > #contents').evaluate("(element, card) => element.insertAdjacentHTML('beforeend', '<div id=late-wrapper style=width:1100px>' + card + '</div>')", modern_result('late-video', '/watch?v=late&list=PLcontext'))
        expect(page.locator('#late-wrapper[data-myt-search-cell]')).to_have_count(1)
        assert abs(page.locator('#late-video').bounding_box()['width'] - expected_width) < 2
        page.locator('#avatar-first').evaluate("element => { element.setAttribute('content-type','playlist'); element.querySelector('h3 a').href = '/playlist?list=recycled'; }")
        expect(page.locator('#avatar-first[data-myt-search-video]')).to_have_count(0)
        assert abs(page.locator('#avatar-first').bounding_box()['width'] - row_width) < 2
        page.evaluate('__setEnabled(false)')
        assert page.locator('[data-myt-search-video], [data-myt-search-cell], [data-myt-search-grid]').count() == 0
        assert page.locator('#single-wrapper').get_attribute('style') == 'width:1100px'
        ok('dynamic search wrappers get compact cells, recycled playlists restore width and disabling removes all layout markers')
        page.close()

        page = setup(browser, "/results?search_query=fixture", search, width=900)
        first = page.locator("#result-1").bounding_box()
        second = page.locator("#result-2").bounding_box()
        third = page.locator("#result-3").bounding_box()
        assert abs(first["y"] - second["y"]) < 2 and second["x"] > first["x"] + first["width"]
        assert third["y"] >= first["y"] + first["height"] and abs(third["x"] - first["x"]) < 2, (first, second, third)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        ok("900px search reduces the video grid to two columns without overflow")
        page.close()

        page = setup(browser, "/results?search_query=fixture", search, width=390)
        first = page.locator("#result-1").bounding_box()
        second = page.locator("#result-2").bounding_box()
        assert abs(first["x"] - second["x"]) < 2 and second["y"] >= first["y"] + first["height"], (first, second)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Search results overflow mobile width"
        expect(page.locator("#result-1 #video-title")).to_be_visible()
        expect(page.locator("#result-1 ytd-channel-name")).to_be_visible()
        ok("390px search stacks video cards in one column without overflow")
        page.close()

        for dark in [True, False]:
            page = setup(browser, '/results?search_query=surfaces', search, native_dark=dark)
            page.emulate_media(reduced_motion='reduce')
            for selector in ['#result-1', '#modern-video']:
                assert_card_surface(page, selector)
            for selector in ['#playlist-result', '#channel-result', '#continuation']:
                assert page.locator(selector).evaluate("element => getComputedStyle(element).backgroundColor") == 'rgba(0, 0, 0, 0)', selector
            page.set_viewport_size({'width':390, 'height':960})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            expect(page.locator('#result-1 #video-title')).to_be_visible()
            page.evaluate('__setEnabled(false)')
            assert page.locator('#result-1').evaluate("element => getComputedStyle(element).backgroundColor") == 'rgba(0, 0, 0, 0)'
            ok(f"{'dark' if dark else 'light'} search video cards have gray rounded surfaces that brighten on hover/focus without painting playlists or breaking mobile width")
            page.close()

            channel_cards = '''<ytd-app><ytd-page-manager class="ytd-app"><ytd-browse page-subtype="channels"><div id="contents">
              <ytd-rich-grid-renderer style="display:grid;grid-template-columns:repeat(var(--ytd-rich-grid-items-per-row),minmax(0,1fr));gap:28px">
                <ytd-rich-item-renderer id="rich-surface"><yt-lockup-view-model id="nested-lockup"><a href="/watch?v=rich"><div style="height:120px">Preview</div></a><h3><a href="/watch?v=rich">Rich video</a></h3></yt-lockup-view-model></ytd-rich-item-renderer>
              </ytd-rich-grid-renderer>
              <ytd-grid-renderer style="display:block"><div id="items"><ytd-grid-video-renderer id="grid-surface" style="display:block"><a href="/watch?v=grid"><div style="height:120px">Preview</div></a><h3><a href="/watch?v=grid">Grid video</a></h3></ytd-grid-video-renderer></div></ytd-grid-renderer>
              <div style="width:380px;max-width:100%"><yt-lockup-view-model id="standalone-surface"><a href="/watch?v=standalone"><div style="height:120px">Preview</div></a><h3><a href="/watch?v=standalone">Standalone video</a></h3></yt-lockup-view-model></div>
              <ytd-rich-item-renderer id="channel-playlist"><yt-collection-thumbnail-view-model>Playlist cover</yt-collection-thumbnail-view-model><a href="/watch?v=first&list=PLfixture">Playlist</a></ytd-rich-item-renderer>
            </div></ytd-browse></ytd-page-manager></ytd-app>'''
            page = setup(browser, '/@creator/videos', channel_cards, native_dark=dark)
            page.emulate_media(reduced_motion='reduce')
            for selector in ['#rich-surface', '#grid-surface', '#standalone-surface']:
                assert_card_surface(page, selector)
            assert page.locator('#nested-lockup').evaluate("element => getComputedStyle(element).backgroundColor") == 'rgba(0, 0, 0, 0)'
            assert page.locator('#nested-lockup').evaluate("element => parseFloat(getComputedStyle(element).paddingLeft)") == 0
            assert page.locator('#channel-playlist').evaluate("element => getComputedStyle(element).backgroundColor") == 'rgba(0, 0, 0, 0)'
            page.set_viewport_size({'width':390, 'height':960})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            ok(f"{'dark' if dark else 'light'} channel rich/grid/modern video cards brighten on hover/focus with one padded surface and no mobile overflow")
            page.close()

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
        browser.close()
    print(f"{passed} browser fixture checks passed (mock storage; live integration not tested)")


if __name__ == "__main__":
    main()
