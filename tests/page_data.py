"""Search and channel results drawn from YouTube's page data in the existing design.

The page data always holds a page's items, while YouTube's own grid can fail
to stamp them. Cards, groups and pagination come from that data; channel cards
in search keep their native nodes for YouTube's live subscribe controls.
"""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup
from search import video, channel
from channel import fixture as channel_fixture

CONFIG = "window.ytcfg={get:name=>name==='INNERTUBE_CONTEXT'?{client:{clientName:'WEB',clientVersion:'2.20260101'}}:name==='INNERTUBE_API_KEY'?'fixture':undefined};"
ITEM = """const item=(id,title,owner)=>({videoRenderer:{videoId:id,title:{runs:[{text:title}]},
    thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},
    ownerText:{runs:[{text:owner||'Data creator',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/@datacreator'}},browseEndpoint:{browseId:'UCdata',canonicalBaseUrl:'/@datacreator'}}}]},
    navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}}}});
const more=token=>({continuationItemRenderer:{continuationEndpoint:{continuationCommand:{token}}}});"""




def search_page(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + video(1) + channel(1) + '<ytd-continuation-item-renderer id="native-continuation"></ytd-continuation-item-renderer></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    page = setup(browser, '/results?search_query=cats', body)
    requests = []

    def api(route):
        body = route.request.post_data_json
        requests.append(body)
        items = "item('dataVideo05','Data five'),item('dataVideo06','Data six')"
        route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + ITEM + 'return JSON.stringify({onResponseReceivedCommands:[{appendContinuationItemsAction:{continuationItems:[{itemSectionRenderer:{contents:[' + items + ']}}]}}]});})()'))
    page.route('https://www.youtube.com/youtubei/v1/search**', api)
    page.evaluate(CONFIG + ITEM + """
      document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
        {itemSectionRenderer:{contents:[item('dataVideo01','Data one'),
          {shelfRenderer:{title:{simpleText:'People also watched'},content:{verticalListRenderer:{items:[item('dataVideo02','Data two')]}}}},
          {shelfRenderer:{title:{simpleText:'Shorts'},content:{verticalListRenderer:{items:[item('shortVideo1','Short in shelf')]}}}},
          {reelShelfRenderer:{items:[]}},
          {videoRenderer:{videoId:'shortVideo2',title:{runs:[{text:'Reel'}]},navigationEndpoint:{reelWatchEndpoint:{videoId:'shortVideo2'}}}},
          item('dataVideo03','Data three')]}},
        more('page-two')]}}}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    titles = page.locator('#myt-search .media-title')
    # Data order and groups; Shorts never appear; the native video is not a source.
    expect(titles).to_have_text(['Data one', 'Data two', 'Data three', 'Data five', 'Data six'])
    expect(page.locator('#myt-search .group h2')).to_have_count(1)
    assert requests and requests[0]['continuation'] == 'page-two', requests
    # Native channel cards keep their own node and subscribe control.
    expect(page.locator('#myt-search [data-myt-search-channel-card]')).to_have_count(1)
    # YouTube's own continuation is off while page data loads further results.
    expect(page.locator('#native-continuation')).to_have_css('display', 'none')
    assert titles.first.get_attribute('href') == 'https://www.youtube.com/watch?v=dataVideo01'
    page.wait_for_timeout(300)
    assert len(requests) == 1, 'No further request once the data has no continuation'
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-search')).to_have_count(0)
    assert page.evaluate("!document.documentElement.hasAttribute('data-myt-page-data')")
    page.close()
    print('PASS search results, groups and continuation come from page data; channel cards stay native', flush=True)


def channel_page(browser):
    page = setup(browser, '/@creator/videos', channel_fixture())
    requests = []

    def api(route):
        requests.append(route.request.post_data_json)
        route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + ITEM + "return JSON.stringify({onResponseReceivedActions:[{appendContinuationItemsAction:{continuationItems:[{richItemRenderer:{content:item('chanVideo03','Channel three')}}]}}]});})()"))
    page.route('https://www.youtube.com/youtubei/v1/browse**', api)
    expect(page.locator('#myt-search .media')).to_have_count(18)
    page.evaluate(CONFIG + ITEM + """
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[
        tab('Videos',true,{richGridRenderer:{contents:[{richItemRenderer:{content:item('chanVideo01','Channel one')}},{richItemRenderer:{content:item('chanVideo02','Channel two')}},more('channel-two')]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Channel one', 'Channel two', 'Channel three'])
    assert requests and requests[0]['continuation'] == 'channel-two', requests
    # The design is unchanged: the same owned cards, header and navigation.
    expect(page.locator('#myt-channel-nav')).to_be_visible()
    assert page.locator('#myt-search').evaluate("h=>getComputedStyle(h.shadowRoot.querySelector('.stream')).display") in ('grid', 'flex', 'block')
    page.close()
    print('PASS channel Videos come from page data with continuation in the existing design', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        search_page(browser)
        channel_page(browser)
        browser.close()
