"""Native parts the owned pages replace cost no rendering, and no miniplayer.

Live (Chrome, 30 s after load):
- a watch page with a playlist held 10,743 nodes, 6,413 of them in YouTube's
  hidden ytd-playlist-panel-renderer (the owned panel replaces it), and the
  watch page is visibility:hidden, so all of it was still styled and laid out;
- a search page held ~6,000 nodes of hidden native result cards, while the
  owned results come from page data.
These parts stay in the DOM with their data, but content-visibility: hidden
makes the browser skip their style, layout and paint. Leaving a watch page
never opens YouTube's miniplayer: the video stops and the miniplayer closes.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, watch_details_fixture, MASTHEAD, ROOT
from watch_data import RESPONSE
from page_data import CONFIG, ITEM
from search import video, channel


def check_watch_playlist(browser):
    native_panel = '<ytd-playlist-panel-renderer id="playlist"><div id="items">' + ''.join(f'<ytd-playlist-panel-video-renderer><a href="/watch?v=v{i}&amp;list=PLwatch">Item {i}</a></ytd-playlist-panel-video-renderer>' for i in range(50)) + '</div></ytd-playlist-panel-renderer>'
    body = watch_details_fixture().replace('</ytd-watch-flexy>', native_panel + '</ytd-watch-flexy>', 1)
    page = setup(browser, '/watch?v=details&list=PLwatch', body)
    expect(page.locator('#myt-watch')).to_be_visible()
    page.evaluate(RESPONSE)
    expect(page.locator('#myt-watch .own-playlist-name')).to_have_count(3)
    panel = page.locator('ytd-playlist-panel-renderer')
    expect(panel).to_have_attribute('data-myt-dormant', '')
    assert panel.evaluate('e=>getComputedStyle(e).contentVisibility') == 'hidden'
    # Its data and nodes stay for YouTube.
    expect(page.locator('ytd-playlist-panel-video-renderer')).to_have_count(50)
    page.evaluate('__setEnabled(false)')
    expect(panel).not_to_have_attribute('data-myt-dormant', '')
    page.close()
    print('PASS watch: the native playlist panel the owned panel replaces is not rendered', flush=True)


def check_search(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + video(1) + channel(1) + video(2) + '<ytd-continuation-item-renderer id="native-continuation"></ytd-continuation-item-renderer></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    # Live: the continuation sits beside the cards, so their wrappers are
    # layout paths; the cards inside them must still sleep.
    page = setup(browser, '/results?search_query=cats', body)
    page.evaluate(CONFIG + ITEM + """
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[item('dataVideo01','Data one')]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Data one'])
    assert page.evaluate('document.documentElement.hasAttribute("data-myt-page-data")')
    for card in ['#video-1', '#video-2']:
        assert page.locator(card).evaluate('e=>getComputedStyle(e).contentVisibility') == 'hidden', card
    assert page.locator('#native-continuation').evaluate('e=>getComputedStyle(e).contentVisibility') == 'visible'
    skipped = page.evaluate("[...document.querySelectorAll('[data-myt-dormant]')].reduce((s,n)=>s+n.getElementsByTagName('*').length,0)")
    assert skipped > 20, skipped
    # Channel cards keep their live native controls.
    assert page.locator('#channel-1').evaluate('e=>getComputedStyle(e).contentVisibility') == 'visible'
    page.close()
    print('PASS search: hidden native result cards are not rendered with page data', flush=True)


def check_miniplayer(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-browse><p>Channel</p></ytd-browse></ytd-page-manager>'
            '<ytd-miniplayer><div id="movie_player"><video id="mini-video"></video><button class="ytp-miniplayer-close-button" onclick="window.__closed=(window.__closed||0)+1;document.querySelector(\'ytd-app\').removeAttribute(\'miniplayer-is-active\')">Close</button></div></ytd-miniplayer></ytd-app>')
    page = setup(browser, '/@creator/videos', body)
    page.add_script_tag(path=str(ROOT / 'src/content/navigation-main.js'))
    page.evaluate('''() => { const player = document.querySelector('#movie_player'); window.__stopped = 0; player.stopVideo = () => { window.__stopped++; };
      document.querySelector('ytd-miniplayer').setAttribute('active', ''); document.querySelector('ytd-app').setAttribute('miniplayer-is-active', ''); }''')
    page.wait_for_function('window.__stopped > 0 && window.__closed > 0', timeout=3000)
    expect(page.locator('ytd-miniplayer')).to_be_hidden()
    page.close()
    print('PASS no miniplayer: leaving a watch page stops the video and closes it', flush=True)


def check_picture_in_picture(browser):
    """The browser's own picture-in-picture window (macOS opens one when a
    playing video leaves the screen) closes off a watch page, and on a watch
    page, where the player is already shown."""
    body = '<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-browse><p>Channel</p></ytd-browse></ytd-page-manager><div id="movie_player"><video id="pip-video"></video></div></ytd-app>'
    page = setup(browser, '/@creator/videos', body)
    page.add_script_tag(path=str(ROOT / 'src/content/navigation-main.js'))
    page.evaluate("""() => { let current = null; window.__exited = 0; window.__stopped = 0;
      Object.defineProperty(document, 'pictureInPictureElement', {configurable: true, get: () => current});
      document.exitPictureInPicture = () => { current = null; window.__exited++; return Promise.resolve(); };
      document.querySelector('#movie_player').stopVideo = () => { window.__stopped++; };
      window.__enterPip = () => { current = document.querySelector('#pip-video'); current.dispatchEvent(new Event('enterpictureinpicture', {bubbles: true})); }; }""")
    # Off a watch page: the window closes and the video stops as soon as it opens.
    page.evaluate('__enterPip()')
    page.wait_for_function('window.__exited === 1 && window.__stopped === 1', timeout=3000)
    # Back on a watch page: a window left open by the browser closes too.
    page.evaluate("() => { history.pushState({}, '', '/watch?v=details'); __enterPip(); document.dispatchEvent(new Event('yt-navigate-finish')); }")
    page.wait_for_function('window.__exited === 2', timeout=3000)
    assert page.evaluate('window.__stopped') == 1, 'a watch page never stops its own video'
    page.close()
    print('PASS no second video window: picture-in-picture closes off and on watch pages', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        check_watch_playlist(browser)
        check_search(browser)
        check_miniplayer(browser)
        check_picture_in_picture(browser)
        browser.close()


if __name__ == '__main__':
    main()
