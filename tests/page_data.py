"""Search and channel results drawn from YouTube's page data in the existing design.

The page data always holds a page's items, while YouTube's own grid can fail
to stamp them. Cards, groups and pagination come from that data; channel cards
in search keep their native nodes for YouTube's live subscribe controls.
"""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, ROOT
from search import video, channel
from channel import fixture as channel_fixture

CONFIG = "window.ytcfg={get:name=>name==='INNERTUBE_CONTEXT'?{client:{clientName:'WEB',clientVersion:'2.20260101'}}:name==='INNERTUBE_API_KEY'?'fixture':undefined};"
ITEM = """const item=(id,title,owner,published)=>({videoRenderer:{videoId:id,title:{runs:[{text:title}]},
    thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},publishedTimeText:{simpleText:published||'3 days ago'},
    ownerText:{runs:[{text:owner||'Data creator',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/@datacreator'}},browseEndpoint:{browseId:'UCdata',canonicalBaseUrl:'/@datacreator'}}}]},
    navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}}}});
const more=token=>({continuationItemRenderer:{continuationEndpoint:{continuationCommand:{token}}}});"""




def search_page(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-search-sub-menu-renderer id="native-toolbar"><div id="filter-menu"><div id="container"><ytd-toggle-button-renderer><button id="native-filter-button" aria-label="Filters">Filters</button></ytd-toggle-button-renderer></div></div><iron-collapse id="collapse-content" style="max-height:0;overflow:hidden" aria-hidden="true"><ytd-search-filter-group-renderer><h4>Upload date</h4><a id="native-filter-today" href="/results?search_query=cats&amp;sp=EgIIAg%253D%253D">Today</a></ytd-search-filter-group-renderer></iron-collapse></ytd-search-sub-menu-renderer><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + video(1) + channel(1) + '<ytd-continuation-item-renderer id="native-continuation"></ytd-continuation-item-renderer></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    page = setup(browser, '/results?search_query=cats', body)
    page.add_script_tag(path=str(ROOT / 'src/content/navigation.js'))
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
          {backstagePostThreadRenderer:{post:{backstagePostRenderer:{postId:'UgSearchPost',contentText:{runs:[{text:'A post in search'}]},authorText:{runs:[{text:'Poster'}]}}}}},
          {shelfRenderer:{title:{simpleText:'Latest posts'},content:{verticalListRenderer:{items:[{postRenderer:{postId:'UgShelfPost',contentText:{runs:[{text:'Shelf post'}]}}}]}}}},
          {videoRenderer:{videoId:'shortVideo2',title:{runs:[{text:'Reel'}]},navigationEndpoint:{reelWatchEndpoint:{videoId:'shortVideo2'}}}},
          {channelRenderer:{channelId:'UCdatachannel00000000000',title:{simpleText:'Data Channel'},navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/@datachannel'}},browseEndpoint:{browseId:'UCdatachannel00000000000',canonicalBaseUrl:'/@datachannel'}},
            thumbnail:{thumbnails:[{url:'https://yt3.ggpht.com/datachannel=s176',width:176}]},subscriberCountText:{simpleText:'1.2M subscribers'}}},
          item('dataVideo03','Data three')]}},
        more('page-two')],
        subMenu:{searchSubMenuRenderer:{groups:[
          {searchFilterGroupRenderer:{title:{simpleText:'Upload date'},filters:[
            {searchFilterRenderer:{label:{simpleText:'Today'},status:'FILTER_STATUS_UNSELECTED',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=cats&sp=EgIIAg%253D%253D'}}}}},
            {searchFilterRenderer:{label:{simpleText:'This week'},status:'FILTER_STATUS_SELECTED',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=cats'}}}}}]}},
          {searchFilterGroupRenderer:{title:{simpleText:'Type'},filters:[
            {searchFilterRenderer:{label:{simpleText:'Video'},status:'FILTER_STATUS_UNSELECTED',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=cats&sp=EgIQAQ%253D%253D'}}}}}]}}]}}}}}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    titles = page.locator('#myt-search .media-title')
    # Data order and groups; Shorts never appear; the native video is not a source.
    expect(titles).to_have_text(['Data one', 'Data two', 'Data three', 'Data five', 'Data six'])
    expect(page.locator('#myt-search .group h2')).to_have_count(1)
    # Posts never appear in search, alone or in a posts shelf.
    expect(page.locator('#myt-search .post')).to_have_count(0)
    expect(page.locator('#myt-search')).not_to_contain_text('post')
    assert requests and requests[0]['continuation'] == 'page-two', requests
    # Native channel cards keep their own node and subscribe control.
    expect(page.locator('#myt-search [data-myt-search-channel-card]')).to_have_count(2)
    # A channel without a native card gets one from the data; its photo opens the channel.
    card = page.locator('#myt-search [data-myt-search-channel-card]').filter(has_text='Data Channel')
    expect(card.locator('.channel-link')).to_have_attribute('href', 'https://www.youtube.com/@datachannel')
    expect(card.locator('.subscriber-value')).to_have_text('1.2 M')
    # The photo and the card cannot be dragged, so a click on the photo is never lost to a drag.
    assert card.locator('.channel-link').get_attribute('draggable') == 'false' and card.locator('.avatar img').get_attribute('draggable') == 'false'
    # A press and release that never becomes a click still opens the channel.
    page.evaluate("document.documentElement.removeAttribute('data-myt-navigate-request')")
    for kind in ('pointerdown', 'pointerup'):
        card.locator('.avatar img').dispatch_event(kind, {'button': 0, 'isPrimary': True, 'bubbles': True, 'composed': True})
    page.wait_for_function("(document.documentElement.getAttribute('data-myt-navigate-request')||'').includes('/@datachannel')")
    page.evaluate("document.documentElement.removeAttribute('data-myt-navigate-request')")
    # A real click that moves the mouse a few pixels (as hands do) still opens the channel.
    photo = card.locator('.avatar').bounding_box()
    page.mouse.move(photo['x'] + 40, photo['y'] + 40); page.mouse.down()
    page.mouse.move(photo['x'] + 46, photo['y'] + 44, steps=3); page.mouse.up()
    assert '/@datachannel' in (page.evaluate("document.documentElement.getAttribute('data-myt-navigate-request')") or ''), page.evaluate("document.documentElement.getAttribute('data-myt-navigate-request')")
    # YouTube's filters are read from YouTube and rebuilt: same groups, same
    # applied state, same action (the filter's URL); YouTube's own are hidden.
    filters = page.locator('#myt-search .filters')
    expect(page.locator('#native-filter-button')).to_be_hidden()
    expect(page.locator('#collapse-content')).to_be_hidden()
    expect(filters.locator('.filters-panel')).to_be_hidden()
    filters.get_by_role('button', name='Filters').click()
    expect(filters.locator('.filter-group h3')).to_have_text(['Upload date', 'Type'])
    expect(filters.locator('[aria-current="true"]')).to_have_text('This week')
    today = filters.get_by_role('link', name='Today')
    expect(today).to_have_attribute('href', 'https://www.youtube.com/results?search_query=cats&sp=EgIIAg%253D%253D')
    today.click()
    expect(filters.locator('.filters-panel')).to_be_hidden()
    assert 'sp=EgIIAg' in page.evaluate("document.documentElement.getAttribute('data-myt-navigate-request')")
    # Without readable data, the filters come from YouTube's rendered panel.
    page.evaluate("""()=>{const d=document.querySelector('ytd-search').data;delete d.contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.subMenu;
      document.querySelector('#collapse-content').innerHTML='<ytd-search-filter-group-renderer><h4 id="filter-group-name">Duration</h4><ytd-search-filter-renderer><a id="endpoint" href="/results?search_query=cats&sp=EgIYAQ%253D%253D"><yt-formatted-string id="label">Under 4 minutes</yt-formatted-string></a></ytd-search-filter-renderer></ytd-search-filter-group-renderer>';
      document.dispatchEvent(new Event('yt-page-data-updated'));}""")
    expect(filters.locator('.filter-group h3')).to_have_text(['Duration'])
    filters.get_by_role('button', name='Filters').click()
    expect(filters.get_by_role('link', name='Under 4 minutes')).to_have_attribute('href', 'https://www.youtube.com/results?search_query=cats&sp=EgIYAQ%253D%253D')
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
        tab('Videos',true,{richGridRenderer:{contents:[{richItemRenderer:{content:item('chanVideo01','Channel one')}},{richItemRenderer:{content:item('chanVideo02','Channel two','','\u202aStreamed \u20681\u2069 year ago\u202c')}},{richItemRenderer:{content:item('chanVideo04','Channel four','','Трансляция закончилась 2 г. назад')}},{richItemRenderer:{content:item('chanVideo05','Channel five','','3 нед. назад')}},more('channel-two')]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Channel one', 'Channel two', 'Channel four', 'Channel five', 'Channel three'])
    # Every video shows its upload date below the title.
    # Older than four months: month and year, counted back from today.
    import datetime
    year_ago = datetime.date.today().replace(year=datetime.date.today().year - 1).strftime('%B %Y')
    # YouTube's Russian abbreviations convert too: "2 г. назад", "6 л. назад".
    two_years = datetime.date.today().replace(year=datetime.date.today().year - 2).strftime('%B %Y')
    expect(page.locator('#myt-search .media-date')).to_have_text(['3 days ago', 'Streamed ' + year_ago, 'Streamed ' + two_years, '3 нед. назад', '3 days ago'])
    # A channel's own cards carry no owner line.
    expect(page.locator('#myt-search .media-channel')).to_have_count(5)
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


PLAYLIST_ITEM = """const pitem=(id,title,set,index)=>({playlistVideoRenderer:{videoId:id,setVideoId:set,index:{simpleText:String(index)},title:{runs:[{text:title}]},
    thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},lengthText:{simpleText:'12:34'},
    shortBylineText:{runs:[{text:'Some creator',navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/@somecreator'}},browseEndpoint:{browseId:'UCsome',canonicalBaseUrl:'/@somecreator'}}}]},
    videoInfo:{runs:[{text:'1.2M views'},{text:' • '},{text:'2 years ago'}]},
    navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id+'&list=PLfixture&index='+index}},watchEndpoint:{videoId:id,playlistId:'PLfixture'}},
    menu:{menuRenderer:{items:[
      {menuServiceItemRenderer:{text:{runs:[{text:'Remove from Fixture'}]},serviceEndpoint:{commandMetadata:{webCommandMetadata:{sendPost:true,apiUrl:'/youtubei/v1/browse/edit_playlist'}},playlistEditEndpoint:{playlistId:'PLfixture',actions:[{setVideoId:set,action:'ACTION_REMOVE_VIDEO'}],params:'CAFAAQ%3D%3D'}}}},
      {menuServiceItemRenderer:{text:{runs:[{text:'Move to top'}]},serviceEndpoint:{commandMetadata:{webCommandMetadata:{sendPost:true,apiUrl:'/youtubei/v1/browse/edit_playlist'}},playlistEditEndpoint:{playlistId:'PLfixture',actions:[{setVideoId:set,action:'ACTION_MOVE_VIDEO_AFTER'}]}}}},
      {menuServiceItemRenderer:{text:{runs:[{text:'Save to playlist'}]},serviceEndpoint:{addToPlaylistServiceEndpoint:{videoId:id}}}}]}}}});"""


def playlist_page(browser):
    from playlist import body as playlist_body
    page = setup(browser, '/playlist?list=PLfixture', playlist_body(count=3))
    edits, more = [], []

    def edit(route):
        edits.append({'body': route.request.post_data_json, 'auth': route.request.headers.get('authorization', '')})
        route.fulfill(content_type='application/json', body='{"status":"STATUS_SUCCEEDED"}')

    def browse(route):
        more.append(route.request.post_data_json)
        route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + PLAYLIST_ITEM + "return JSON.stringify({onResponseReceivedActions:[{appendContinuationItemsAction:{continuationItems:[pitem('dataVideo04','Data four','set4',4)]}}]})})()"))
    page.route('https://www.youtube.com/youtubei/v1/browse/edit_playlist**', edit)
    page.route('https://www.youtube.com/youtubei/v1/browse?**', browse)
    page.evaluate("document.cookie='SAPISID=fixturesid; path=/; secure'")
    page.evaluate(CONFIG + PLAYLIST_ITEM + """
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[{playlistVideoListRenderer:{playlistId:'PLfixture',
        contents:[pitem('dataVideo01','Data one','set1',1),pitem('dataVideo02','Data two','set2',2),pitem('dataVideo03','Data three','set3',3),{continuationItemRenderer:{continuationEndpoint:{continuationCommand:{token:'playlist-more'}}}}]}}]}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    rows = page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]')
    # Rows come from the playlist's page data; the native rows are hidden.
    # Row geometry matches the native-backed rows: a compact grid.
    assert rows.first.bounding_box()['height'] < 220, rows.first.bounding_box()
    page.locator('#myt-playlist-rows .myt-playlist-more').scroll_into_view_if_needed()
    expect(rows.locator('.title')).to_have_text(['Data one', 'Data two', 'Data three', 'Data four'])
    assert more and more[0]['continuation'] == 'playlist-more', more
    expect(page.locator('ytd-playlist-video-renderer').first).to_be_hidden()
    expect(rows.first.locator('.duration')).to_have_text('12:34')
    import datetime
    two_years = datetime.date.today().replace(year=datetime.date.today().year - 2).strftime('%B %Y')
    expect(rows.first.locator('.metadata')).to_have_text('1.2M views · ' + two_years)
    expect(rows.first.locator('a.title')).to_have_attribute('href', 'https://www.youtube.com/watch?v=dataVideo01&list=PLfixture&index=1')
    # The video menu offers YouTube's playlist edits; dialogs it cannot run are left out.
    rows.nth(1).get_by_role('button', name='Video actions').click()
    menu = page.locator('#myt-playlist-menu')
    expect(menu.get_by_role('menuitem')).to_have_text(['Remove from Fixture', 'Move to top', 'Copy link'])
    menu.get_by_role('menuitem', name='Remove from Fixture').click()
    expect(menu).to_be_hidden()
    expect(rows.locator('.title')).to_have_text(['Data one', 'Data three', 'Data four'])
    assert edits[-1]['body']['actions'] == [{'setVideoId': 'set2', 'action': 'ACTION_REMOVE_VIDEO'}] and edits[-1]['body']['playlistId'] == 'PLfixture', edits
    assert edits[-1]['body']['context']['client']['clientVersion'] == '2.20260101', edits
    assert edits[-1]['auth'].startswith('SAPISIDHASH '), edits
    expect(rows.locator('.index')).to_have_text(['1', '2', '3'])
    rows.nth(2).get_by_role('button', name='Video actions').click()
    menu.get_by_role('menuitem', name='Move to top').click()
    expect(rows.locator('.title')).to_have_text(['Data four', 'Data one', 'Data three'])
    # A failed edit leaves the list and says so.
    page.unroute('https://www.youtube.com/youtubei/v1/browse/edit_playlist**')
    page.route('https://www.youtube.com/youtubei/v1/browse/edit_playlist**', lambda route: route.fulfill(status=401, body='{}'))
    rows.first.get_by_role('button', name='Video actions').click()
    menu.get_by_role('menuitem', name='Remove from Fixture').click()
    expect(page.locator('#myt-playlist-rows .myt-playlist-status')).to_have_text('Could not update the playlist. Try again.')
    expect(rows.locator('.title')).to_have_text(['Data four', 'Data one', 'Data three'])
    # The header keeps YouTube's own controls.
    expect(page.locator('[data-myt-playlist-summary]').get_by_role('button', name='Shuffle', exact=True)).to_be_visible()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-playlist-rows')).to_have_count(0)
    expect(page.locator('ytd-playlist-video-renderer').first).to_be_visible()
    page.close()
    print('PASS playlist rows, continuation and edits come from page data in the owned design', flush=True)


LESSON = """const lesson=(id,title,index)=>({lockupViewModel:{contentId:id,contentType:'LOCKUP_CONTENT_TYPE_VIDEO',
    contentImage:{thumbnailViewModel:{image:{sources:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:246}]},overlays:[{thumbnailBottomOverlayViewModel:{badges:[{thumbnailBadgeViewModel:{text:'16:23'}}]}}]}},
    metadata:{lockupMetadataViewModel:{title:{content:title},
      image:{decoratedAvatarViewModel:{a11yLabel:'Перейти на канал "Немецкий с нуля!"',rendererContext:{commandContext:{onTap:{innertubeCommand:{browseEndpoint:{browseId:'UCdeu',canonicalBaseUrl:'/@deu'}}}}}}},
      metadata:{contentMetadataViewModel:{metadataRows:[{metadataParts:[{text:{content:'10 млн'}},{text:{content:'6 л. назад'}}]}]}}}},
    rendererContext:{commandContext:{onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id+'&list=PLcourse&index='+index}},watchEndpoint:{videoId:id,playlistId:'PLcourse',index:index-1}}}}}}});"""


def course_page(browser):
    """A course lists its lessons as video lockups in an item section; the
    page shows them as owned playlist rows, with further lessons from the
    continuation."""
    from playlist import cover, MASTHEAD
    header = f'<div id="header"><ytd-playlist-header-renderer style="display:block"><img src="{cover()}"><yt-dynamic-sizing-formatted-string>Немецкий с нуля. ВИДЕОУРОКИ</yt-dynamic-sizing-formatted-string><a href="/@deu">Немецкий с нуля!</a><button>Продолжить</button></ytd-playlist-header-renderer></div>'
    native = ''.join(f'<yt-lockup-view-model style="display:block"><a href="/watch?v=lessonVid0{n}&list=PLcourse">Native {n}</a></yt-lockup-view-model>' for n in range(1, 4))
    html = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-browse page-subtype="playlist" style="display:block">' + header
            + '<div id="contents" style="display:block"><ytd-two-column-browse-results-renderer style="display:block"><div id="primary"><yt-section-list-renderer style="display:block"><yt-item-section-renderer style="display:block"><div id="contents">'
            + native + '</div></yt-item-section-renderer></yt-section-list-renderer></div></ytd-two-column-browse-results-renderer></div></ytd-browse></ytd-page-manager></ytd-app>')
    page = setup(browser, '/playlist?list=PLcourse', html)
    more = []

    def browse(route):
        more.append(route.request.post_data_json)
        route.fulfill(content_type='application/json', body=page.evaluate('()=>(()=>{' + LESSON + "return JSON.stringify({onResponseReceivedActions:[{appendContinuationItemsAction:{continuationItems:[lesson('lessonVid04','Урок 4',4)]}}]})})()"))
    page.route('https://www.youtube.com/youtubei/v1/browse?**', browse)
    page.evaluate(CONFIG + LESSON + """
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{targetId:'VLPLcourse',contents:[
        {itemSectionRenderer:{targetId:'PLcourse',contents:[lesson('lessonVid01','Урок 1',1),lesson('lessonVid02','Урок 2',2),lesson('lessonVid03','Урок 3',3)]}},
        {continuationItemViewModel:{continuationCommand:{innertubeCommand:{continuationCommand:{token:'course-more'}}}}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('[data-myt-playlist-summary]')).to_have_count(1)
    rows = page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]')
    expect(rows.first.locator('.title')).to_have_text('Урок 1')
    page.locator('#myt-playlist-rows .myt-playlist-more').scroll_into_view_if_needed()
    expect(rows.locator('.title')).to_have_text(['Урок 1', 'Урок 2', 'Урок 3', 'Урок 4'])
    assert more and more[0]['continuation'] == 'course-more', more
    expect(rows.locator('.index')).to_have_text(['1', '2', '3', '4'])
    expect(rows.first.locator('.duration')).to_have_text('16:23')
    expect(rows.first.locator('a.title')).to_have_attribute('href', 'https://www.youtube.com/watch?v=lessonVid01&list=PLcourse&index=1')
    expect(page.locator('yt-lockup-view-model').first).to_be_hidden()
    page.close()
    print('PASS course lessons come from page data as owned playlist rows', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        search_page(browser)
        channel_page(browser)
        channel_header_and_chips(browser)
        channel_posts(browser)
        playlist_page(browser)
        course_page(browser)
        browser.close()
