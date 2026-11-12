"""Owned loading states on every page, and empty states only once confirmed.

- every navigation: a loading bar from the request until the destination;
- search/channel results: placeholder cards while loading, "No results"
  only when the page data (or YouTube's own message) confirms it, and a
  loading row while the next page loads;
- playlist: placeholder rows while loading, a loading row for more rows;
- watch: placeholders instead of the previous video's text after a switch,
  and placeholders while comments load.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, native_watch_fixture
from page_data import CONFIG, ITEM, PLAYLIST_ITEM
from watch_data import RESPONSE
from smoke import watch_details_fixture

SHELL = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
         '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')


def search_states(browser):
    page = setup(browser, '/results?search_query=cats', SHELL)
    root = page.locator('#myt-search')
    # Nothing loaded yet: placeholders, never "No results found".
    expect(root.locator('.skeleton')).to_be_visible()
    expect(root.locator('.empty')).to_be_hidden()
    held = []
    page.route('https://www.youtube.com/youtubei/v1/search**', lambda route: held.append(route))
    page.evaluate(CONFIG + ITEM + """
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[item('dataVideo01','Data one'),item('dataVideo02','Data two')]}},more('page-two')]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(root.locator('.media-title')).to_have_text(['Data one', 'Data two'])
    expect(root.locator('.skeleton')).to_be_hidden()
    # The next page is requested at the end of the list: a loading row shows.
    expect(root.locator('.loading-more')).to_be_visible(timeout=5000)
    assert held, 'the next page was not requested'
    held[0].fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + ITEM + 'return JSON.stringify({onResponseReceivedCommands:[{appendContinuationItemsAction:{continuationItems:[{itemSectionRenderer:{contents:[item("dataVideo03","Data three")]}}]}}]});})()'))
    expect(root.locator('.media-title')).to_have_count(3)
    expect(root.locator('.loading-more')).to_be_hidden()
    page.close()

    page = setup(browser, '/results?search_query=nothing', SHELL)
    root = page.locator('#myt-search')
    expect(root.locator('.skeleton')).to_be_visible()
    # Page data with no results and no next page confirms an empty search.
    page.evaluate(CONFIG + """
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(root.locator('.empty')).to_be_visible()
    expect(root.locator('.skeleton')).to_be_hidden()
    page.close()
    print('PASS search: placeholders, loading row, and "No results" only when confirmed', flush=True)


def progress_bar(browser):
    page = setup(browser, '/results?search_query=cats', SHELL)
    bar = page.locator('#myt-progress')
    page.evaluate("document.dispatchEvent(new Event('minimal-youtube:navigate'))")
    page.wait_for_function("document.querySelector('#myt-progress')?.matches(':popover-open')")
    expect(bar).to_be_visible()
    assert page.evaluate("document.documentElement.hasAttribute('data-myt-loading')")
    page.evaluate("document.dispatchEvent(new Event('yt-navigate-finish'))")
    page.wait_for_function("!document.querySelector('#myt-progress')", timeout=3000)
    page.evaluate("document.dispatchEvent(new Event('minimal-youtube:navigate'))")
    page.wait_for_function("document.querySelector('#myt-progress')?.matches(':popover-open')")
    page.evaluate('__setEnabled(false)')
    page.wait_for_function("!document.querySelector('#myt-progress')", timeout=3000)
    page.close()
    print('PASS navigation: a loading bar from the request until the destination', flush=True)


def playlist_states(browser):
    from playlist import body as playlist_body
    page = setup(browser, '/playlist?list=PLfixture', playlist_body(count=3))
    held = []
    page.route('https://www.youtube.com/youtubei/v1/browse?**', lambda route: held.append(route))
    page.evaluate(CONFIG + PLAYLIST_ITEM + """
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[{playlistVideoListRenderer:{playlistId:'PLfixture',
        contents:[pitem('dataVideo01','Data one','set1',1),{continuationItemRenderer:{continuationEndpoint:{continuationCommand:{token:'playlist-more'}}}}]}}]}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    rows = page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]')
    expect(rows).to_have_count(1)
    expect(page.locator('.myt-playlist-skeleton')).to_be_hidden()
    page.locator('#myt-playlist-rows .myt-playlist-more').scroll_into_view_if_needed()
    expect(page.locator('#myt-playlist-rows .myt-loading-more')).to_be_visible()
    expect(page.locator('.myt-playlist-empty')).to_be_hidden()
    held[0].fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + PLAYLIST_ITEM + "return JSON.stringify({onResponseReceivedActions:[{appendContinuationItemsAction:{continuationItems:[pitem('dataVideo02','Data two','set2',2)]}}]})})()"))
    expect(rows).to_have_count(2)
    expect(page.locator('#myt-playlist-rows .myt-loading-more')).to_be_hidden()
    page.close()

    page = setup(browser, '/playlist?list=PLfixture', playlist_body(count=3))
    page.route('https://www.youtube.com/youtubei/v1/browse?**', lambda route: None)
    page.evaluate(CONFIG + """
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[{playlistVideoListRenderer:{playlistId:'PLfixture',
        contents:[{continuationItemRenderer:{continuationEndpoint:{continuationCommand:{token:'playlist-more'}}}}]}}]}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    # No rows yet but more to come: placeholder rows, never "No videos".
    expect(page.locator('.myt-playlist-skeleton')).to_be_visible()
    expect(page.locator('.myt-playlist-empty')).to_be_hidden()
    page.close()
    print('PASS playlist: placeholder rows and a loading row for more rows', flush=True)


def watch_states(browser):
    page = setup(browser, '/watch?v=details&list=PLwatch', watch_details_fixture())
    page.evaluate(RESPONSE)
    details = page.locator('#myt-watch .details')
    expect(page.locator('#myt-watch #watch-title')).to_have_text('Data title from the page')
    expect(details).not_to_have_attribute('data-loading', '')
    # Switching videos: placeholders until this video's data (at most 4 s).
    page.evaluate("history.pushState({},'','/watch?v=switched12345');document.dispatchEvent(new Event('yt-navigate-finish'))")
    expect(details).to_have_attribute('data-loading', '')
    expect(details).not_to_have_attribute('data-loading', '', timeout=6000)
    page.close()

    comments = ('<ytd-comments id="comments"><ytd-item-section-renderer id="sections"><div id="header"><ytd-comments-header-renderer><h2>Comments</h2></ytd-comments-header-renderer></div>'
                '<div id="contents"><ytd-continuation-item-renderer id="comment-continuation"><p>spinner</p></ytd-continuation-item-renderer></div></ytd-item-section-renderer></ytd-comments>')
    page = setup(browser, '/watch?v=native', native_watch_fixture().replace('</ytd-watch-metadata>', '</ytd-watch-metadata>' + comments))
    page.locator('#myt-watch .more-toggle').click()
    page.locator('#myt-comments-toggle').click()
    expect(page.locator('[data-myt-watch-island="comments"]')).to_be_visible()
    contents = page.locator('ytd-comments #sections > #contents')
    assert contents.evaluate("e=>getComputedStyle(e,'::before').content") != 'none'
    assert page.locator('#comment-continuation').evaluate('e=>getComputedStyle(e).opacity') == '0'
    contents.evaluate("e=>e.insertAdjacentHTML('afterbegin','<ytd-comment-thread-renderer><p>First</p></ytd-comment-thread-renderer>')")
    page.wait_for_function("getComputedStyle(document.querySelector('ytd-comments #sections > #contents'),'::before').content==='none'")
    page.close()
    print('PASS watch: placeholders after a video switch and while comments load', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        search_states(browser)
        progress_bar(browser)
        playlist_states(browser)
        watch_states(browser)
        browser.close()


if __name__ == '__main__':
    main()
