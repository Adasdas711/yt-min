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
ytd-app, ytd-page-manager, ytd-browse, ytd-rich-grid-renderer,
ytd-watch-flexy, ytd-reel-shelf-renderer, ytd-rich-item-renderer,
ytd-video-renderer, ytd-playlist-panel-renderer, ytd-playlist-panel-video-renderer,
ytd-comments, yt-tab-shape, tp-yt-paper-tab { display: block; }
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
        for (const fn of window.__storageListeners)
          fn({enabled: {oldValue: old.enabled, newValue: value.enabled}}, 'local');
        if (cb) cb();
      }
    },
    onChanged: {addListener: fn => window.__storageListeners.push(fn)}
  }};
  window.__setEnabled = enabled => chrome.storage.local.set({enabled});
}"""


def setup(browser, path="/", body="", enabled=None, width=1440):
    page = browser.new_page(viewport={"width": width, "height": 960})
    page.route("https://www.youtube.com/**", lambda route: route.fulfill(
        status=200, content_type="text/html", body=document(body)))
    page.goto("https://www.youtube.com" + path)
    page.evaluate(MOCK, {} if enabled is None else {"enabled": enabled})
    page.add_style_tag(path=str(ROOT / "src/styles/styles.css"))
    page.add_script_tag(path=str(ROOT / "src/content/content.js"))
    return page


def centered(page, selector, tolerance=3):
    bounds = page.locator(selector).bounding_box()
    assert bounds and bounds["width"] > 0, f"Missing layout box: {selector}"
    viewport = page.viewport_size["width"]
    assert abs(bounds["x"] * 2 + bounds["width"] - viewport) < tolerance, (selector, bounds, viewport)
    assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= viewport + 1, bounds


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
        ok("320px-tall desktop homepage keeps its heading and search reachable")
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

        watch = '''<ytd-app><ytd-page-manager class="ytd-app"><ytd-watch-flexy>
          <div id="columns"><div id="primary"><div id="player"><video></video></div>
          <div id="info">Video title</div><ytd-comments>Comments</ytd-comments></div>
          <div id="secondary"><div id="secondary-inner"><div id="related">Recommendations</div></div></div></div>
        </ytd-watch-flexy></ytd-page-manager></ytd-app>'''
        page = setup(browser, "/watch?v=abc", watch)
        centered(page, "#columns")
        expect(page.locator("#related")).to_be_hidden()
        expect(page.locator("ytd-comments")).to_be_visible()
        page.evaluate("document.querySelector('#secondary-inner').insertAdjacentHTML('beforeend', '<div id=playlist><ytd-playlist-panel-renderer><ytd-playlist-panel-video-renderer>Playlist video</ytd-playlist-panel-video-renderer></ytd-playlist-panel-renderer></div>')")
        expect(page.locator("ytd-playlist-panel-renderer")).to_be_visible()
        for mode in ["theater", "fullscreen"]:
            page.locator("ytd-watch-flexy").evaluate("(element, mode) => { element.removeAttribute('theater'); element.removeAttribute('fullscreen'); element.setAttribute(mode, ''); }", mode)
            video = page.locator("video").bounding_box()
            assert video["width"] == 640 and video["height"] == 360, (mode, video)
        ok("watch page centers, retains comments and playlist, and leaves native video dimensions intact")
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
