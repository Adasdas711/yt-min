"""Search rows never keep an empty cell that a later video can fill.

Live (Chrome, search results for a channel's name): videos and playlists
alternate as video, video, playlist, video, video, playlist... A playlist
spans two of the three columns, so a playlist after two videos did not fit,
moved to the next row and left the first row with an empty third cell; the
page looked as if results were skipped. The nearest following video now
fills that cell; nothing moves across a group.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, ROOT
from page_data import CONFIG, ITEM

DATA = ITEM + """
const list=(id,title)=>({playlistRenderer:{playlistId:id,title:{simpleText:title},videoCount:'12',
  thumbnails:[{thumbnails:[{url:'https://i.ytimg.com/vi/x/hqdefault.jpg',width:480}]}],
  shortBylineText:{runs:[{text:'Joe Speen',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/@JoeSpeen'}},browseEndpoint:{browseId:'UCjoe',canonicalBaseUrl:'/@JoeSpeen'}}}]},
  navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v=listVideo01&list='+id}},watchEndpoint:{videoId:'listVideo01',playlistId:id}}}});
const shelf=(title,items)=>({shelfRenderer:{title:{simpleText:title},content:{verticalListRenderer:{items}}}});
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[
    item('video000001','V1'),item('video000002','V2'),list('PLlist0001','P1'),
    item('video000003','V3'),item('video000004','V4'),item('video000005','V5'),list('PLlist0002','P2'),
    item('video000006','V6'),item('video000007','V7'),list('PLlist0003','P3'),
    shelf('Latest from Joe Speen',[item('video000008','G1'),item('video000009','G2'),item('video000010','G3')]),
    item('video000011','V8')]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));"""


def rows(page):
    return page.evaluate('''() => [...document.querySelector('#myt-search').shadowRoot.querySelectorAll('.stream > .row, .stream > .group')].map(row =>
      row.classList.contains('group') ? 'group' : [...row.children].map(card => card.querySelector('.media-title').textContent))''')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents"></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
        expected = {
            1440: [['V1', 'V2', 'V3'], ['P1', 'V4'], ['V5', 'P2'], ['V6', 'V7'], ['P3'], 'group', ['V8']],
            800: [['V1', 'V2'], ['P1'], ['V3', 'V4'], ['V5', 'V6'], ['P2'], ['V7'], ['P3'], 'group', ['V8']],
            390: [['V1'], ['V2'], ['P1'], ['V3'], ['V4'], ['V5'], ['P2'], ['V6'], ['V7'], ['P3'], 'group', ['V8']],
        }
        for width, layout in expected.items():
            page = setup(browser, '/results?search_query=joe+speen', body, width=width)
            page.evaluate(CONFIG + DATA)
            expect(page.locator('#myt-search .stream .media-title')).to_have_count(14)
            actual = rows(page)
            assert actual == layout, (width, actual)
            page.close()
            print(f'PASS search rows fill every cell in order: {width}px', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
