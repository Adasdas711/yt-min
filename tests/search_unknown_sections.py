"""Sections YouTube adds later never appear on the owned search page.

Search shows ordinary results plus the sections it knows (For you, Watch
again, Previously watched, Related videos, People also watched, Latest from
<channel>). A new shelf title, carousel or block, from page data or from
YouTube's rendered page, stays out instead of leaking into the results.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup
from page_data import CONFIG, ITEM
from search import video

DATA = ITEM + """
const shelf=(title,items)=>({shelfRenderer:{title:{simpleText:title},content:{verticalListRenderer:{items}}}});
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[
    item('result00001','Result one'),
    shelf('People also watched',[item('known000001','Known shelf video')]),
    shelf('Explore more topics',[item('unknown0001','Unknown shelf video')]),
    {horizontalCardListRenderer:{cards:[item('carousel001','Carousel video')]}},
    {searchRefinementCardListViewModel:{items:[item('newblock001','New block video')]}},
    shelf('Latest from MrBeast',[item('latest00001','Latest video')]),
    item('result00002','Result two')]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));"""


def native_shelf(title, inner):
    return '<ytd-shelf-renderer><div id="title-container"><h2><span id="title">' + title + '</span></h2></div><div id="contents"><ytd-vertical-list-renderer><div id="items">' + inner + '</div></ytd-vertical-list-renderer></div></ytd-shelf-renderer>'


def native_body():
    titled = lambda i, title: video(i).replace(f'Regular video {i}<', title + '<')
    contents = (titled(1, 'Result one') + native_shelf('For you', titled(2, 'Known shelf video'))
                + native_shelf('Explore more topics', titled(3, 'Unknown shelf video'))
                + '<ytd-horizontal-card-list-renderer><div id="cards">' + titled(4, 'Carousel video') + '</div></ytd-horizontal-card-list-renderer>'
                + '<ytd-search-refinement-card-renderer>' + titled(5, 'New block video') + '</ytd-search-refinement-card-renderer>'
                + titled(6, 'Result two'))
    return ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + contents + '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')


def check(page, groups, titles):
    root = page.locator('#myt-search')
    expect(root.locator('.media-title')).to_have_text(titles)
    expect(root.locator('.group h2')).to_have_text(groups)
    text = root.inner_text()
    for leaked in ['Unknown shelf video', 'Explore more topics', 'Carousel video', 'New block video']:
        assert leaked not in text, leaked


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        empty = '<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents"></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
        page = setup(browser, '/results?search_query=mr', empty)
        page.evaluate(CONFIG + DATA)
        check(page, ['People also watched', 'Latest from MrBeast'], ['Result one', 'Known shelf video', 'Latest video', 'Result two'])
        page.close()
        print('PASS page data: unknown shelves, carousels and blocks stay out of search', flush=True)

        page = setup(browser, '/results?search_query=mr', native_body())
        check(page, ['For you'], ['Result one', 'Known shelf video', 'Result two'])
        page.close()
        print('PASS rendered page: unknown shelves, carousels and blocks stay out of search', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
