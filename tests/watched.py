"""Watched videos carry YouTube's red resume bar on their cover: in search,
on a channel, on a playlist or course page and in the watch page playlist."""
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, watch_details_fixture
from channel import fixture as channel_fixture
from page_data import CONFIG, PLAYLIST_ITEM, LESSON
import watch_data

# A video renderer with an optional legacy resume overlay, and a lockup with
# the newer progress bar.
ITEMS = """const watched=(id,title,percent)=>({videoRenderer:{videoId:id,title:{runs:[{text:title}]},
    thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},publishedTimeText:{simpleText:'3 days ago'},
    ownerText:{runs:[{text:'Creator',navigationEndpoint:{browseEndpoint:{browseId:'UCdata',canonicalBaseUrl:'/@creator'}}}]},
    navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}},
    thumbnailOverlays:percent?[{thumbnailOverlayResumePlaybackRenderer:{percentDurationWatched:percent}}]:[]}});
const lockup=(id,title,percent)=>({lockupViewModel:{contentId:id,contentType:'LOCKUP_CONTENT_TYPE_VIDEO',
    contentImage:{thumbnailViewModel:{image:{sources:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},
      overlays:[{thumbnailBottomOverlayViewModel:{progressBar:{thumbnailOverlayProgressBarViewModel:{startPercent:percent}},badges:[{thumbnailBadgeViewModel:{text:'4:00'}}]}}]}},
    metadata:{lockupMetadataViewModel:{title:{content:title}}},
    rendererContext:{commandContext:{onTap:{innertubeCommand:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}}}}}}});"""


def bars(page, selector):
    return page.locator(selector).evaluate_all("cards=>cards.map(card=>{const bar=card.querySelector('.watched');return bar&&!bar.hidden?bar.getAttribute('aria-label'):''})")


def search(browser):
    body = '<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><ytd-item-section-renderer><div id="contents"></div></ytd-item-section-renderer></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
    page = setup(browser, '/results?search_query=cats', body)
    page.evaluate(CONFIG + ITEMS + """
      document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
        {itemSectionRenderer:{contents:[watched('searchVid01','Half watched',40),watched('searchVid02','Not watched',0),lockup('searchVid03','Watched lockup',100)]}}]}}}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Half watched', 'Not watched', 'Watched lockup'])
    assert bars(page, '#myt-search .media') == ['Watched 40%', '', 'Watched 100%'], bars(page, '#myt-search .media')
    width = page.locator('#myt-search .media .watched > i').first.evaluate('e=>e.style.width')
    assert width == '40%', width
    page.close()
    print('PASS search: watched videos show the resume bar', flush=True)


def channel(browser):
    page = setup(browser, '/@creator/videos', channel_fixture())
    expect(page.locator('#myt-search .media').first).to_be_visible()
    page.evaluate(CONFIG + ITEMS + """
      const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[
        tab('Videos',true,{richGridRenderer:{contents:[{richItemRenderer:{content:watched('chanVideo01','Channel one',75)}},{richItemRenderer:{content:watched('chanVideo02','Channel two',0)}}]}})]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media-title')).to_have_text(['Channel one', 'Channel two'])
    assert bars(page, '#myt-search .media') == ['Watched 75%', ''], bars(page, '#myt-search .media')
    page.close()
    print('PASS channel: watched videos show the resume bar', flush=True)


def row_bars(page):
    return page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]').evaluate_all(
        "rows=>rows.map(row=>{const bar=row.shadowRoot.querySelector('.watched');return bar&&!bar.hidden?bar.getAttribute('aria-label'):''})")


def playlist(browser):
    from playlist import body as playlist_body
    page = setup(browser, '/playlist?list=PLfixture', playlist_body(count=2))
    page.evaluate(CONFIG + PLAYLIST_ITEM + """
      const seen=pitem('dataVideo01','Data one','set1',1);seen.playlistVideoRenderer.thumbnailOverlays=[{thumbnailOverlayResumePlaybackRenderer:{percentDurationWatched:60}}];
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[{playlistVideoListRenderer:{playlistId:'PLfixture',
        contents:[seen,pitem('dataVideo02','Data two','set2',2)]}}]}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    rows = page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]')
    expect(rows.locator('.title')).to_have_text(['Data one', 'Data two'])
    assert row_bars(page) == ['Watched 60%', ''], row_bars(page)
    page.close()
    print('PASS playlist page: watched videos show the resume bar', flush=True)


def course(browser):
    from playlist import cover
    header = f'<div id="header"><ytd-playlist-header-renderer style="display:block"><img src="{cover()}"><yt-dynamic-sizing-formatted-string>Course</yt-dynamic-sizing-formatted-string></ytd-playlist-header-renderer></div>'
    native = '<yt-lockup-view-model style="display:block"><a href="/watch?v=lessonVid01&list=PLcourse">Native</a></yt-lockup-view-model>'
    html = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-browse page-subtype="playlist" style="display:block">' + header
            + '<div id="contents" style="display:block"><yt-section-list-renderer style="display:block"><yt-item-section-renderer style="display:block"><div id="contents">'
            + native + '</div></yt-item-section-renderer></yt-section-list-renderer></div></ytd-browse></ytd-page-manager></ytd-app>')
    page = setup(browser, '/playlist?list=PLcourse', html)
    page.evaluate(CONFIG + LESSON + """
      const done=lesson('lessonVid01','Lesson 1',1);done.lockupViewModel.contentImage.thumbnailViewModel.overlays[0].thumbnailBottomOverlayViewModel.progressBar={thumbnailOverlayProgressBarViewModel:{startPercent:100}};
      document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[{tabRenderer:{selected:true,content:{sectionListRenderer:{targetId:'VLPLcourse',contents:[
        {itemSectionRenderer:{targetId:'PLcourse',contents:[done,lesson('lessonVid02','Lesson 2',2)]}}]}}}}]}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));""")
    rows = page.locator('#myt-playlist-rows [data-myt-owned-playlist-card=video]')
    expect(rows.locator('.title')).to_have_text(['Lesson 1', 'Lesson 2'])
    assert row_bars(page) == ['Watched 100%', ''], row_bars(page)
    page.close()
    print('PASS course page: watched lessons show the resume bar', flush=True)


def watch_panel(browser):
    page = setup(browser, '/watch?v=details&list=PLwatch', watch_details_fixture())
    expect(page.locator('#myt-watch')).to_be_visible()
    response = watch_data.RESPONSE.replace(
        "panel('aaaaaaaaaaa','First in list',1,false)",
        "(()=>{const item=panel('aaaaaaaaaaa','First in list',1,false);item.playlistPanelVideoRenderer.thumbnailOverlays=[{thumbnailOverlayResumePlaybackRenderer:{percentDurationWatched:90}}];return item;})()")
    assert response != watch_data.RESPONSE
    page.evaluate(response)
    root = page.locator('#myt-watch')
    expect(root.locator('.own-playlist-name')).to_have_count(3)
    labels = root.locator('.own-playlist-link').evaluate_all("links=>links.map(link=>link.querySelector('.own-playlist-watched')?.getAttribute('aria-label')||'')")
    assert labels == ['Watched 90%', '', ''], labels
    expect(root.locator('.own-playlist-watched').first).to_be_visible()
    page.close()
    print('PASS watch page playlist: watched videos show the resume bar', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        search(browser)
        channel(browser)
        playlist(browser)
        course(browser)
        watch_panel(browser)
        browser.close()
