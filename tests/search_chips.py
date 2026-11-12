"""Search header chips (All, Unwatched, Watched, Videos...) in the owned design.

Live data (Chrome, search "mr"): ytd-search-header-renderer[has-chip-bar]
holds div#chip-bar > yt-chip-cloud-renderer and div#about-these-results; its
data carries chipBar.chipCloudRenderer.chips. "All" is selected and has no
endpoint; every other chip reloads the results with a continuationCommand
sent to /youtubei/v1/search, without changing the URL. The owned page shows
those chips itself (Shorts excluded), reloads its results the same way, and
hides the native header and "About these results".
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
        page = setup(browser, '/results?search_query=mr', body)
        page.add_script_tag(path=str(ROOT / 'src/content/navigation.js'))
        requests = []

        def api(route):
            token = route.request.post_data_json.get('continuation')
            requests.append(token)
            items = {'token-unwatched': "item('unwVideo001','Unwatched one')", 'token-videos': "item('vidVideo001','Videos one'),item('vidVideo002','Videos two')"}.get(token, "item('pageVideo01','Page two')")
            command = 'appendContinuationItemsAction' if token == 'page-two' else 'reloadContinuationItemsCommand'
            route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + ITEM + 'return JSON.stringify({onResponseReceivedCommands:[{reloadContinuationItemsCommand:{slot:"RELOAD_CONTINUATION_SLOT_HEADER",continuationItems:[]}},{' + command + ':{slot:"RELOAD_CONTINUATION_SLOT_BODY",continuationItems:[{itemSectionRenderer:{contents:[' + items + ']}}]}}]});})()'))
        page.route('https://www.youtube.com/youtubei/v1/search**', api)
        page.evaluate(CONFIG + DATA)

        root = page.locator('#myt-search')
        titles = root.locator('.media-title')
        chips = root.locator('.chips .chip')
        expect(titles).to_have_text(['All one', 'All two'])
        # The same chips as YouTube, without Shorts; All is selected.
        expect(chips).to_have_text(['All', 'Unwatched', 'Watched', 'Videos'])
        expect(chips.first).to_have_attribute('aria-pressed', 'true')
        # They take the native bar's place: above Filters.
        assert page.evaluate("()=>{const s=document.querySelector('#myt-search').shadowRoot;return s.querySelector('.chips').nextElementSibling===s.querySelector('.filters')}")
        expect(root.locator('.filters-toggle')).to_be_visible()
        # The native header, its chips and "About these results" are hidden.
        for selector in ['ytd-search-header-renderer', 'yt-chip-cloud-renderer', '#about-these-results']:
            expect(page.locator(selector)).to_be_hidden()

        url = page.url
        chips.nth(3).click()
        expect(titles).to_have_text(['Videos one', 'Videos two'])
        assert requests[-1] == 'token-videos', requests
        expect(chips.nth(3)).to_have_attribute('aria-pressed', 'true')
        expect(chips.first).to_have_attribute('aria-pressed', 'false')
        assert page.url == url
        chips.nth(1).click()
        expect(titles).to_have_text(['Unwatched one'])
        # All restores the original results without a request.
        count = len(requests)
        chips.first.click()
        expect(titles).to_have_text(['All one', 'All two'])
        expect(chips.first).to_have_attribute('aria-pressed', 'true')
        assert len(requests) == count, requests

        # Disabling the extension returns YouTube's own header.
        page.evaluate('__setEnabled(false)')
        for selector in ['ytd-search-header-renderer', 'yt-chip-cloud-renderer', '#about-these-results']:
            expect(page.locator(selector)).to_be_visible()
        page.evaluate('__setEnabled(true)')
        expect(page.locator('#about-these-results')).to_be_hidden()
        page.close()
        browser.close()
        print('PASS search chips from YouTube data, reload in place, All restores, native header hidden and restored', flush=True)


if __name__ == '__main__':
    main()
