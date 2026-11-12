"""Search page header: no result chips, no "About these results", centered Filters.

Live data (Chrome, search "mr"): ytd-search-header-renderer[has-chip-bar]
holds div#chip-bar > yt-chip-cloud-renderer (All, Unwatched, Watched,
Videos, Recently uploaded, Live) and div#about-these-results; the groups of
the filter dialog live in its data. The owned search page shows none of the
chips and none of the native header: only its own Filters button, centered
above the results.
"""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, ROOT
from page_data import CONFIG, ITEM

HEADER = '''<div id="header"><ytd-search-header-renderer class="style-scope ytd-search" has-chip-bar>
  <div id="back-button"></div>
  <div id="chip-bar"><yt-chip-cloud-renderer><div id="container"><iron-selector id="chips">
    <yt-chip-cloud-chip-renderer selected><chip-shape><button aria-selected="true">All</button></chip-shape></yt-chip-cloud-chip-renderer>
    <yt-chip-cloud-chip-renderer><chip-shape><button aria-selected="false">Shorts</button></chip-shape></yt-chip-cloud-chip-renderer>
    <yt-chip-cloud-chip-renderer><chip-shape><button aria-selected="false">Unwatched</button></chip-shape></yt-chip-cloud-chip-renderer>
    <yt-chip-cloud-chip-renderer><chip-shape><button aria-selected="false">Watched</button></chip-shape></yt-chip-cloud-chip-renderer>
    <yt-chip-cloud-chip-renderer><chip-shape><button aria-selected="false">Videos</button></chip-shape></yt-chip-cloud-chip-renderer>
  </iron-selector></div></yt-chip-cloud-renderer></div>
  <ytd-search-sub-menu-renderer><div id="filter-menu"><div id="container"><ytd-toggle-button-renderer><yt-button-shape><button aria-label="Search filters">Filters</button></yt-button-shape></ytd-toggle-button-renderer></div></div></ytd-search-sub-menu-renderer>
  <div id="about-these-results"><span>About these results</span><button aria-label="About these results">i</button></div>
</ytd-search-header-renderer></div>'''

DATA = ITEM + """
const chip=(text,token,selected)=>({chipCloudChipRenderer:{style:{styleType:'STYLE_HOME_FILTER'},text:{simpleText:text},trackingParams:'CEMQ',isSelected:Boolean(selected),location:'CHIP_LOCATION_SEARCH_RESULTS',
  ...(token?{navigationEndpoint:{clickTrackingParams:'CEIQ',commandMetadata:{webCommandMetadata:{sendPost:true,apiUrl:'/youtubei/v1/search'}},
    continuationCommand:{token,request:'CONTINUATION_REQUEST_TYPE_SEARCH',command:{showReloadUiCommand:{targetId:'search-page'}}}}}:{})}});
document.querySelector('ytd-search-sub-menu-renderer').data={trackingParams:'CEUQ'};
document.querySelector('ytd-search-header-renderer').data={trackingParams:'CEQQ',aboutTheseResultsButton:{},
  chipBar:{chipCloudRenderer:{chips:[chip('All','',true),chip('Shorts','token-shorts'),chip('Unwatched','token-unwatched'),chip('Watched','token-watched'),chip('Videos','token-videos')]}},
  searchFilterButton:{buttonRenderer:{command:{openPopupAction:{popup:{searchFilterOptionsDialogRenderer:{groups:[
    {searchFilterGroupRenderer:{title:{simpleText:'Type'},filters:[{searchFilterRenderer:{label:{simpleText:'Video'},status:'FILTER_STATUS_UNSELECTED',
      navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=mr&sp=EgIQAQ%253D%253D'}}}}}]}}]}}}}}}};
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[item('allVideo001','All one'),item('allVideo002','All two')]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><div id="container">' + HEADER
                + '<ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents"><ytd-continuation-item-renderer id="native-continuation"></ytd-continuation-item-renderer></div></ytd-item-section-renderer></div></ytd-section-list-renderer></div></ytd-search></ytd-page-manager></ytd-app>')
        for width in [1440, 900, 390]:
            page = setup(browser, '/results?search_query=mr', body, width=width)
            page.add_script_tag(path=str(ROOT / 'src/content/navigation.js'))
            page.evaluate(CONFIG + DATA)
            root = page.locator('#myt-search')
            expect(root.locator('.media-title')).to_have_text(['All one', 'All two'])
            # No chips at all: neither YouTube's nor owned ones.
            expect(root.locator('.chips .chip')).to_have_count(0)
            for selector in ['ytd-search-header-renderer', 'yt-chip-cloud-renderer', '#about-these-results']:
                expect(page.locator(selector)).to_be_hidden()
            # Filters is centered over the results and still opens.
            toggle = root.locator('.filters-toggle')
            expect(toggle).to_be_visible()
            box, area = toggle.bounding_box(), page.locator('#myt-search').bounding_box()
            assert abs((box['x'] + box['width'] / 2) - (area['x'] + area['width'] / 2)) < 2, (box, area)
            toggle.click()
            panel = root.locator('.filters-panel')
            expect(panel).to_be_visible()
            panel_box = panel.bounding_box()
            assert abs(panel_box['width'] - area['width']) < 2, (panel_box, area)
            # Disabling the extension returns YouTube's own header.
            page.evaluate('__setEnabled(false)')
            for selector in ['ytd-search-header-renderer', 'yt-chip-cloud-renderer', '#about-these-results']:
                expect(page.locator(selector)).to_be_visible()
            page.evaluate('__setEnabled(true)')
            expect(page.locator('ytd-search-header-renderer')).to_be_hidden()
            page.close()
            print(f'PASS search header: no chips, native header hidden, Filters centered: {width}px', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
