"""Browser regression checks using local YouTube DOM fixtures and mock storage.

Run: python tests/smoke.py (requires installed Playwright and Chromium).
No live YouTube requests or unpacked-extension installation are performed.
"""
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
</style>"""


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
    page = browser.new_page(viewport={"width": width, "height": 960})
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
        assert page.locator("#native-state").count() == 1, "Homepage must preserve YouTube's native DOM"
        expect(page).to_have_title("YouTube")
        centered(page, ".myt-search")
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

        channel_profile = '''<ytd-app>
          <ytd-masthead><div id="container"><div id="start"><a id="logo" href="/">YouTube</a></div>
          <div id="center"><input id="search" aria-label="Search"></div>
          <div id="end"><div id="buttons"><button id="create">Create</button><button id="avatar-btn">Account</button></div></div>
          <button id="voice-search-button">Voice</button></div></ytd-masthead>
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

        channel_scroll = '''<ytd-app style="height:100%"><ytd-page-manager id="main-scroll" class="ytd-app" style="position:absolute;top:60px;left:120px;width:calc(100% - 240px);height:840px;overflow-y:auto">
          <ytd-browse page-subtype="channels" style="min-height:2400px">
          <div id="nested-scroll" style="width:300px;height:120px;overflow-y:auto"><div style="height:800px">Nested native scrollbox</div></div>
          <div style="height:2000px">Channel videos</div></ytd-browse></ytd-page-manager></ytd-app>'''
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
        assert page.locator("#main-scroll").evaluate("element => element.scrollTop") == 0
        ok("gutter-wheel fallback stays inactive when disabled or outside channel pages")
        page.close()

        watch = '''<ytd-app>
          <ytd-masthead><div id="container"><div id="start"><a id="logo" href="/">YouTube</a></div>
          <div id="center"><input id="search" aria-label="Search"></div>
          <div id="end"><div id="buttons"><button id="create">Create</button><button id="avatar-btn">Account</button></div></div>
          <button id="voice-search-button">Voice</button></div></ytd-masthead>
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
          <ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">''' + result_card(1) + result_card(2) + '''
          <ytd-channel-renderer id="channel-result"><a href="/@channel">Channel result</a></ytd-channel-renderer>
          <ytd-playlist-renderer id="playlist-result"><a href="/playlist?list=fixture">Playlist result</a></ytd-playlist-renderer>
          ''' + modern + result_card(3) + '''<ytd-continuation-item-renderer id="continuation">Load more</ytd-continuation-item-renderer>
          </div></ytd-item-section-renderer></div></ytd-section-list-renderer>
          </div></ytd-search></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/results?search_query=fixture", search)
        expect(page.locator("html")).to_have_attribute("data-myt-page", "search")
        left = page.locator("#result-1").bounding_box()
        right = page.locator("#result-2").bounding_box()
        assert abs(left["y"] - right["y"]) < 2 and right["x"] > left["x"] + left["width"], (left, right)
        assert abs(left["width"] - right["width"]) < 2, (left, right)
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
        ok("desktop search uses two equal preview-top cards with title/channel and a logo/search-only header")

        for selector in ["#channel-result", "#playlist-result", "#continuation"]:
            expect(page.locator(selector)).to_be_visible()
            bounds = page.locator(selector).bounding_box()
            assert bounds["width"] > left["width"] * 1.9, (selector, bounds, left)
        expect(page.locator("#channel-result a")).to_have_attribute("href", "/@channel")
        expect(page.locator("#playlist-result a")).to_have_attribute("href", "/playlist?list=fixture")
        expect(page.locator("#modern-video[data-myt-search-video]")).to_have_count(1)
        modern_bounds = page.locator("#modern-video").bounding_box()
        assert abs(modern_bounds["width"] - left["width"]) < 2, (modern_bounds, left)
        page.locator("ytd-item-section-renderer > #contents").evaluate("(element, card) => element.insertAdjacentHTML('beforeend', card)", result_card(4))
        expect(page.locator("#result-4 #description-text")).to_be_hidden()
        dynamic = page.locator("#result-4").bounding_box()
        assert abs(dynamic["width"] - left["width"]) < 2, (dynamic, left)
        ok("mixed search channels/playlists/continuation retain full width and dynamic/modern video cards use the grid")
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
