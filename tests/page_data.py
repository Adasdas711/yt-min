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
ITEM = """const item=(id,title,owner,published)=>({videoRenderer:{videoId:id,title:{runs:[{text:title}]},
    thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},publishedTimeText:{simpleText:published||'3 days ago'},
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
    # Live YouTube keeps the sort chips inside the rich grid's header.
    page.evaluate("""document.querySelector('ytd-rich-grid-renderer').insertAdjacentHTML('afterbegin','<div id="header"><ytd-feed-filter-chip-bar-renderer><button id="sort-latest">Latest</button></ytd-feed-filter-chip-bar-renderer></div>')""")
    page.evaluate(CONFIG + ITEM + """
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[
        tab('Videos',true,{richGridRenderer:{contents:[{richItemRenderer:{content:item('chanVideo01','Channel one')}},{richItemRenderer:{content:item('chanVideo02','Channel two','','\u202aStreamed \u20681\u2069 year ago\u202c')}},more('channel-two')]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Channel one', 'Channel two', 'Channel three'])
    # Every video shows its upload date below the title.
    # Older than four months: month and year, counted back from today.
    import datetime
    year_ago = datetime.date.today().replace(year=datetime.date.today().year - 1).strftime('%B %Y')
    expect(page.locator('#myt-search .media-date')).to_have_text(['3 days ago', 'Streamed ' + year_ago, '3 days ago'])
    # A channel's own cards carry no owner line.
    expect(page.locator('#myt-search .media-channel')).to_have_count(3)
    assert page.locator('#myt-search .media-channel').evaluate_all('nodes=>nodes.every(n=>!n.getClientRects().length)')
    expect(page.locator('#sort-latest')).to_be_visible()
    page.locator('#sort-latest').scroll_into_view_if_needed()
    hit = page.locator('#sort-latest').evaluate('e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {height:r.height,hit:e===hit||e.contains(hit)}}')
    assert hit['height'] > 10 and hit['hit'], hit
    assert requests and requests[0]['continuation'] == 'channel-two', requests
    # The design is unchanged: the same owned cards, header and navigation.
    expect(page.locator('#myt-channel-nav')).to_be_visible()
    assert page.locator('#myt-search').evaluate("h=>getComputedStyle(h.shadowRoot.querySelector('.stream')).display") in ('grid', 'flex', 'block')
    page.close()
    print('PASS channel Videos come from page data with continuation in the existing design', flush=True)


def channel_header_and_chips(browser):
    page = setup(browser, '/@creator/videos', channel_fixture())
    chip_requests = []

    def api(route):
        chip_requests.append(route.request.post_data_json)
        route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + ITEM + "return JSON.stringify({onResponseReceivedActions:[{reloadContinuationItemsCommand:{slot:'RELOAD_CONTINUATION_SLOT_BODY',continuationItems:[{richItemRenderer:{content:item('popular0001','Most popular')}}]}}]});})()"))
    page.route('https://www.youtube.com/youtubei/v1/browse**', api)
    page.route('https://yt3.ggpht.com/**', lambda route: route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="16" height="9"/>'))
    expect(page.locator('#myt-search .media')).to_have_count(18)
    page.evaluate(CONFIG + ITEM + """
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      const chip=(text,selected,token)=>({chipCloudChipRenderer:{text:{simpleText:text},isSelected:selected,navigationEndpoint:{continuationCommand:{token}}}});
      document.querySelector('ytd-browse').data={
        metadata:{channelMetadataRenderer:{title:'Data Creator',externalId:'UCdatacreator0000000000',vanityChannelUrl:'https://www.youtube.com/@creator',
          avatar:{thumbnails:[{url:'https://yt3.ggpht.com/avatar=s88',width:88},{url:'https://yt3.ggpht.com/avatar=s900',width:900}]}}},
        header:{pageHeaderRenderer:{content:{pageHeaderViewModel:{banner:{imageBannerViewModel:{image:{sources:[{url:'https://yt3.ggpht.com/banner=w1060',width:1060},{url:'https://yt3.ggpht.com/banner=w2560-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj',width:2560}]}}},
          title:{dynamicTextViewModel:{text:{content:'Data Creator',attachmentRuns:[{element:{type:{imageType:{image:{sources:[{clientResource:{imageName:'CHECK_CIRCLE_FILLED'}}]}}}}}]}}}}}}},
        contents:{twoColumnBrowseResultsRenderer:{tabs:[tab('Videos',true,{richGridRenderer:{
          header:{feedFilterChipBarRenderer:{contents:[chip('Новые',true,'chip-latest'),chip('Популярные',false,'chip-popular'),chip('Старые',false,'chip-oldest')]}},
          contents:[{richItemRenderer:{content:item('chanVideo01','Channel one')}}]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    # The owned header uses the public page data: name, avatar, banner and badge.
    header = page.locator('#myt-channel-header')
    expect(header.locator('.myt-ch-name')).to_have_text('Data Creator')
    expect(header.locator('.myt-ch-avatar')).to_have_attribute('src', 'https://yt3.ggpht.com/avatar=s900')
    # The banner loads the whole channel art, not YouTube's thin crop of it.
    expect(header.locator('.myt-ch-banner img')).to_have_attribute('src', 'https://yt3.ggpht.com/banner=w2560-k-c0xffffffff-no-nd-rj')
    expect(header.locator('.myt-ch-verified')).to_be_visible()
    # YouTube's subscribe control is the only native part, beside the name.
    expect(header.locator('.myt-ch-actions #subscribe')).to_be_visible()
    # Owned sort chips replace YouTube's and reload the feed in place.
    chips = page.locator('#myt-search').locator('.chip')
    expect(chips).to_have_text(['Latest', 'Popular', 'Oldest'])
    expect(chips.first).to_have_attribute('aria-pressed', 'true')
    chips.nth(1).click()
    expect(page.locator('#myt-search .media-title')).to_have_text(['Most popular'])
    expect(chips.nth(1)).to_have_attribute('aria-pressed', 'true')
    assert chip_requests and chip_requests[-1]['continuation'] == 'chip-popular', chip_requests
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-channel-header')).to_have_count(0)
    expect(page.locator('#subscribe')).to_be_visible()
    page.close()
    print('PASS owned channel header from page data with native subscribe only; owned sort chips reload the feed', flush=True)


def channel_posts(browser):
    page = setup(browser, '/@creator/posts', channel_fixture())
    page.evaluate(CONFIG + """
      const post=(id,text,extra)=>({backstagePostThreadRenderer:{post:{backstagePostRenderer:{postId:id,authorText:{runs:[{text:'Data Creator'}]},
        authorThumbnail:{thumbnails:[{url:'https://yt3.ggpht.com/author=s88',width:88}]},publishedTimeText:{runs:[{text:'\u20681\u2069 year ago (edited)'}]},
        contentText:{runs:[{text:text}]},voteCount:{simpleText:'1.2K'},...extra}}}});
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[tab('Posts',true,{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[
        post('UgPost1','First post\\nwith two lines',{backstageAttachment:{backstageImageRenderer:{image:{thumbnails:[{url:'https://yt3.ggpht.com/post-image=s1080',width:1080}]}}}}),
        post('UgPost2','Which one?',{backstageAttachment:{pollRenderer:{choices:[{text:{runs:[{text:'Option A'}]}},{text:{runs:[{text:'Option B'}]}}],totalVotes:{simpleText:'321 votes'}}}})
      ]}}]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    posts = page.locator('#myt-search .post')
    expect(posts).to_have_count(2)
    expect(posts.first.locator('.post-text')).to_have_text('First post\nwith two lines')
    assert 'monospace' in posts.first.locator('.post-text').evaluate('e=>getComputedStyle(e).fontFamily')
    # Post dates older than four months read as month and year as well.
    import datetime
    year_ago = datetime.date.today().replace(year=datetime.date.today().year - 1).strftime('%B %Y')
    expect(posts.first.locator('.post-time')).to_have_text(year_ago + ' (edited)')
    expect(posts.first.locator('.post-images img')).to_have_attribute('src', 'https://yt3.ggpht.com/post-image=s1080')
    expect(posts.first.locator('.post-time')).to_have_attribute('href', 'https://www.youtube.com/post/UgPost1')
    expect(posts.nth(1).locator('.post-poll li')).to_have_text(['Option A', 'Option B'])
    expect(posts.nth(1).locator('.post-meta')).to_contain_text('321 votes')
    # Read only: no like, vote or comment controls.
    expect(page.locator('#myt-search .post button')).to_have_count(0)
    page.close()
    print('PASS Posts is an owned read-only feed from page data', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        search_page(browser)
        channel_page(browser)
        channel_header_and_chips(browser)
        channel_posts(browser)
        browser.close()
