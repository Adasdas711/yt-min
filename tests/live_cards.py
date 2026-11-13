"""Streams that are live now carry a LIVE badge and their current viewers on
search and channel cards; other videos keep their publication date.

Run: python tests/live_cards.py
"""
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup
from search import video
from channel import fixture as channel_fixture
from page_data import CONFIG, ITEM

LIVE = """const live=(id,title)=>{const value=item(id,title);const v=value.videoRenderer;delete v.publishedTimeText;
  v.viewCountText={runs:[{text:'1,234'},{text:' watching'}]};
  v.thumbnailOverlays=[{thumbnailOverlayTimeStatusRenderer:{style:'LIVE',text:{simpleText:'LIVE'}}}];
  v.badges=[{metadataBadgeRenderer:{style:'BADGE_STYLE_TYPE_LIVE_NOW',label:'LIVE'}}];return value;};
const lockup=(id,title)=>({lockupViewModel:{contentId:id,contentType:'LOCKUP_CONTENT_TYPE_VIDEO',
  contentImage:{thumbnailViewModel:{image:{sources:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},
    overlays:[{thumbnailOverlayBadgeViewModel:{thumbnailBadges:[{thumbnailBadgeViewModel:{text:'LIVE',badgeStyle:'THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE'}}]}}]}},
  metadata:{lockupMetadataViewModel:{title:{content:title},metadata:{contentMetadataViewModel:{metadataRows:[{metadataParts:[{text:{content:'88 watching'}}]}]}}}},
  rendererContext:{commandContext:{onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}}}}}}});"""


def badges(page):
    return page.locator('#myt-search .media').evaluate_all(
        "cards=>cards.map(c=>[c.querySelector('.media-title').textContent,Boolean(c.querySelector('.live-badge')&&!c.querySelector('.live-badge').hidden&&c.querySelector('.live-badge').getClientRects().length),c.querySelector('.media-date').textContent])")


def search(browser, width):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + video(1) + '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    page = setup(browser, '/results?search_query=stream', body, width=width)
    page.evaluate(CONFIG + ITEM + LIVE + """
      document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
        {itemSectionRenderer:{contents:[live('liveVideo01','Live now'),item('dataVideo01','Recorded'),lockup('liveLockup1','Lockup live')]}}]}}}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Live now', 'Recorded', 'Lockup live'])
    assert badges(page) == [['Live now', True, '1,234 watching'], ['Recorded', False, '3 days ago'], ['Lockup live', True, '88 watching']], badges(page)
    page.close()
    print(f'PASS search: live cards show LIVE and viewers: {width}px', flush=True)


def channel(browser):
    page = setup(browser, '/@creator/videos', channel_fixture())
    expect(page.locator('#myt-search .media').first).to_be_visible()
    page.evaluate(CONFIG + ITEM + LIVE + """
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[
        tab('Videos',true,{richGridRenderer:{contents:[{richItemRenderer:{content:live('chanLive001','Streaming now')}},{richItemRenderer:{content:item('chanVideo02','Past stream','','Streamed 2 days ago')}}]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Streaming now', 'Past stream'])
    assert badges(page) == [['Streaming now', True, '1,234 watching'], ['Past stream', False, 'Streamed 2 days ago']], badges(page)
    page.close()
    print('PASS channel: the live stream card shows LIVE and viewers', flush=True)


def native_fallback(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            + video(1) + '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    page = setup(browser, '/results?search_query=stream', body)
    expect(page.locator('#myt-search .media')).to_have_count(1)
    page.evaluate("""()=>{const v=document.querySelector('ytd-video-renderer');
      v.insertAdjacentHTML('beforeend','<ytd-thumbnail-overlay-time-status-renderer overlay-style="LIVE">LIVE</ytd-thumbnail-overlay-time-status-renderer>');}""")
    expect(page.locator('#myt-search .live-badge')).to_be_visible()
    page.close()
    print('PASS search without page data: a native LIVE overlay marks the card', flush=True)


if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in (1440, 390):
            search(browser, width)
        channel(browser)
        native_fallback(browser)
        browser.close()
