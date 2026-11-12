"""Owned search: data extraction, channels first, ordered compact flow and filters."""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from native_search_filters import filters,NATIVE_STYLE
from smoke import setup, MASTHEAD, ROOT, assert_stable
from playlist import cover

def video(i):
    return f'''<ytd-video-renderer id="video-{i}"><div id="dismissible"><ytd-thumbnail><a href="/watch?v=video{i}"><img src="{cover()}"></a></ytd-thumbnail><div id="details"><h3><a id="video-title" href="/watch?v=video{i}">Regular video {i}</a></h3><div id="channel-info"><ytd-channel-name><a href="/@creator">Creator</a></ytd-channel-name></div><div class="metadata-snippet-container">Unwanted description</div><ytd-expandable-metadata-renderer>Transcript excerpt 1:02</ytd-expandable-metadata-renderer></div></div></ytd-video-renderer>'''



def playlist(i,modern=False,count=None):
    content=f'<a class="cover-link" href="/playlist?list=PL{i}"><img src="{cover()}"></a><h3><a href="/playlist?list=PL{i}">Playlist {i}</a></h3><a href="/@creator">Creator {i}</a>'
    if count is not None:content+=f'<span id="video-count-text">{count} videos</span>'
    return ('<yt-lockup-view-model content-type="playlist">' + content + '</yt-lockup-view-model>') if modern else '<ytd-playlist-renderer>'+content+'</ytd-playlist-renderer>'


def channel(i):
    return f'<ytd-channel-renderer id="channel-{i}"><a href="/@creator{i}" onclick="event.preventDefault();window.__visits=(window.__visits||0)+1"><h3>Creator {i}</h3></a><span id="channel-handle">@creator{i}</span><ytd-subscribe-button-renderer><button onclick="this.parentElement.toggleAttribute(\'subscribed\');this.textContent=this.parentElement.hasAttribute(\'subscribed\')?\'Subscribed\':\'Subscribe\'">Subscribe</button></ytd-subscribe-button-renderer></ytd-channel-renderer>'


def fixture():
    toolbar,_=filters()
    return NATIVE_STYLE+'<style>.native-offset{position:relative;left:180px;margin-left:200px;width:1400px}ytd-video-renderer{height:500px!important}#native-comment{display:block!important}</style><ytd-app>'+MASTHEAD+'''<ytd-page-manager><ytd-search>'''+toolbar+'''<ytd-section-list-renderer><div id="contents" class="native-results"><ytd-item-section-renderer><div id="contents">'''+video(1)+channel(1)+playlist(1)+'''</div></ytd-item-section-renderer><div class="native-offset">'''+video(2)+playlist(2,True)+'''</div><ytd-shelf-renderer id="for-you"><div id="title-container"><h2>Для вас</h2><button>Ещё</button></div><div id="content">'''+video(3)+video(4)+'''</div></ytd-shelf-renderer>'''+video(5).replace('Regular video 5','Посмотреть ещё раз — пользовательский заголовок')+'''<ytd-shelf-renderer id="watch-again"><div id="title-container"><h2>Посмотреть ещё раз</h2></div><div id="content">'''+''.join(video(i) for i in range(6,10))+'''</div></ytd-shelf-renderer>'''+channel(2)+'''<ytd-continuation-item-renderer id="continuation"></ytd-continuation-item-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'''


def geometry(page):
    result=page.evaluate("""()=>{
      const root=document.querySelector('#myt-search').shadowRoot,box=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
      const rows=[...root.querySelectorAll('.row')].map(row=>({row:box(row),cards:[...row.children].map(box),gap:parseFloat(getComputedStyle(row).gap)}));
      const channels=[...root.querySelectorAll('[data-myt-search-channel-card]')].map(box),first=root.querySelector('.media');
      return{rows,channels,first:box(first),overflow:document.documentElement.scrollWidth>innerWidth};
    }""")
    assert not result['overflow'],result
    assert max(item['bottom'] for item in result['channels'])<=result['first']['y'],result
    for row in result['rows']:
        assert abs(row['cards'][0]['x']-row['row']['x'])<1,row
        for before,after in zip(row['cards'],row['cards'][1:]):
            assert abs(after['x']-before['right']-row['gap'])<1,row
            assert abs(after['y']-before['y'])<1,row
            assert abs(after['height']-before['height'])<1,row
    return result


def check(browser,width,dark,prune=True):
    page=setup(browser,'/results?search_query=owned',fixture(),width=width,native_dark=dark,prune_data=prune,enabled=False)
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('https://yt3.googleusercontent.com/**',lambda route:route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="176" height="176"><rect width="176" height="176" fill="#00bcd4"/><circle cx="90" cy="70" r="45" fill="#ef2848"/></svg>'))
    page.route('https://www.youtube.com/src/assets/fonts/**',lambda route:route.fulfill(content_type='font/ttf',body=(ROOT/'src/assets/fonts'/route.request.url.rsplit('/',1)[-1]).read_bytes()))
    page.evaluate("""()=>{
      // Data lives on real renderer objects, not a fabricated root cache.
      for(const i of [1,2])document.querySelector('#channel-'+i).data={
        channelId:'UC'+String(i).padStart(22,'0'),title:{simpleText:'Creator '+i},
        navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@creator'+i}},
        avatar:{decoratedAvatarViewModel:{avatar:{avatarViewModel:{image:{sources:[{url:'https://yt3.googleusercontent.com/avatar'+i,width:176}]}}}}},
        subscriberCountText:{simpleText:'@creator'+i},videoCountText:{simpleText:i===1?'525M subscribers':'2.24M subscribers'}
      };
      document.querySelector('#video-1 #video-title').onclick=e=>{e.preventDefault();window.__videoClicked=true;};
      document.querySelector('#video-2').insertAdjacentHTML('beforeend','<div id="native-comment">52:12 комментарии и описание</div>');
      window.__parents=[...document.querySelectorAll('ytd-search *')].filter(node=>node.id!=='myt-search').map(node=>[node,node.parentElement]);
      document.dispatchEvent(new Event('yt-page-data-updated'));
      chrome.runtime.getURL=path=>'https://www.youtube.com/'+path;__setEnabled(true);
    }""")
    root=page.locator('#myt-search');expect(root.locator('.media')).to_have_count(11)
    expect(root.locator('.subscriber-value')).to_have_text(['525 M','2.24 M'])
    sources=page.locator('ytd-playlist-renderer,yt-lockup-view-model[content-type="playlist"]')
    for index,count in enumerate([256,64]):sources.nth(index).evaluate('(node,count)=>node.insertAdjacentHTML("beforeend",`<span id="video-count-text">${count} videos</span>`)',count)
    expect(root.locator('.playlist-badge')).to_have_text(['256','64'])
    # The count reads as a number with a video icon; no "Playlist" fallback.
    expect(root.locator('.playlist-badge svg')).to_have_count(2)
    expect(root.locator('.playlist-badge').first).to_have_attribute('aria-label','256 videos')
    assert 'monospace' in root.locator('.media.playlist .media-title').first.evaluate('e=>getComputedStyle(e).fontFamily')
    dimensions=page.evaluate('''()=>{const search=document.querySelector('#myt-search').parentElement,s=getComputedStyle(search),box=search.getBoundingClientRect(),result=document.querySelector('#myt-search').getBoundingClientRect();return{before:search.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight),after:result.width,offset:result.x+result.width/2-box.x-box.width/2};}''')
    assert abs(dimensions['after']-dimensions['before']*.9*.9)<.05,dimensions
    assert abs(dimensions['offset'])<1,dimensions
    if width>=900:
        columns=3 if dimensions['before']>=900 else 2
        old_card=(dimensions['before']*.9-20*(columns-1))/columns*2+20
        old_cover=(old_card-44)*2/3
        cover_box=root.locator('.media.playlist .cover').first.bounding_box()
        assert abs(cover_box['width']/old_cover-.9)<.025,(cover_box,old_cover)
        assert abs(cover_box['height']-cover_box['width']*9/16)<1,cover_box
    count_source=sources.first.locator('#video-count-text')
    count_source.evaluate('node=>node.firstChild.data="257 videos"')
    expect(root.locator('.playlist-badge').first).to_have_text('257')
    for count,label in [(0,'0'),(1,'1'),(256,'256')]:
        count_source.evaluate('(node,count)=>node.setAttribute("data-video-count",String(count))',count)
        expect(root.locator('.playlist-badge').first).to_have_text(label)
    page.locator('.native-results').evaluate('(node,html)=>node.insertAdjacentHTML("beforeend",html)',playlist(99))
    page.evaluate('document.documentElement.setAttribute("data-myt-search-playlists",JSON.stringify([{id:"PL99",count:"347"}]))')
    expect(root.locator('.playlist-badge')).to_have_text(['256','64','347'])
    page.locator('ytd-playlist-renderer').last.evaluate('node=>node.remove()')
    expect(root.locator('.media')).to_have_count(11)
    expect(root.locator('.group h2')).to_have_text(['For you','Watch again'])
    page.wait_for_function('Array.from(document.fonts).some(face=>face.family==="MYT Barlow Condensed"&&face.status==="loaded")')
    expect(root.locator('.media-channel').first).to_have_text('Creator')
    expect(root.locator('.media-channel').first).to_have_css('font-size','17px' if width<=700 else '18px')
    assert 'Unwanted description' not in root.locator('.stream').inner_text()
    assert 'Transcript excerpt' not in root.locator('.stream').inner_text()
    assert '52:12' not in root.locator('.stream').inner_text()
    expect(root.locator('.media-title',has_text='Посмотреть ещё раз — пользовательский заголовок')).to_have_count(1)
    images=root.locator('[data-myt-search-channel-card] .avatar img')
    expect(images).to_have_count(2)
    for i in range(2):
        expect(images.nth(i)).to_have_attribute('src',f'https://yt3.googleusercontent.com/avatar{i+1}')
        expect(images.nth(i)).to_be_visible()
        page.wait_for_function("""i=>[...document.querySelector('#myt-search').shadowRoot.querySelectorAll('[data-myt-search-channel-card]')][i].shadowRoot.querySelector('img').naturalWidth===176""",arg=i)
    # Two columns: a playlist after a video does not fit, so the next video
    # fills that row instead of leaving an empty cell.
    columns=page.evaluate("()=>Number(document.querySelector('#myt-search').shadowRoot.querySelector('.stream > .row').style.gridTemplateColumns.match(/repeat\\((\\d+)/)[1])")
    expected=['video','video','playlist','playlist','group','video','group'] if columns==2 else ['video','playlist','video','playlist','group','video','group']
    actual=root.locator('.stream > .row > .media,.stream > .group').evaluate_all('(nodes)=>nodes.map(node=>node.dataset.kind)')
    assert actual==expected,actual
    geometry(page)
    if width>=1000:
        cards=root.locator('.stream > .row').first.locator('.media');a,b=cards.nth(0).bounding_box(),cards.nth(1).bounding_box()
        assert abs(b['width']-(a['width']*2+20))<1,(a,b)
    native_button=page.locator('#native-filters-toggle');panel=page.locator('#native-filters')
    for _ in range(3):
        native_button.click();expect(panel).to_be_visible()
        expect(page.locator('ytd-search-filter-group-renderer')).to_have_count(5)
        assert page.evaluate('__filterButtonTrusted')
        page.locator('#native-filters-close').click();expect(panel).to_be_hidden()
    native_button.press('Enter');expect(panel).to_be_visible()
    page.locator('#native-filters-close').click();expect(panel).to_be_hidden()
    root.locator('.media-title').first.click();assert page.evaluate('__videoClicked')
    page.evaluate('''navigation.addEventListener('navigate',event=>{if(new URL(event.destination.url).pathname==='/@creator1'){event.preventDefault();window.__channelDestination=event.destination.url;}})''')
    images.first.click();assert page.evaluate('__channelDestination')=='https://www.youtube.com/@creator1'
    assert page.evaluate('__parents.every(([node,parent])=>node.parentElement===parent)')
    # Continuation sentinel remains at the end of our flow, with native identity.
    sentinel=page.locator('#continuation').bounding_box();last=root.locator('.stream > .group').last.bounding_box()
    assert sentinel and sentinel['y']>=last['y']+last['height']-1,(sentinel,last)
    page.locator('.native-results').evaluate('(node,html)=>node.insertAdjacentHTML("beforeend",html)',video(10))
    expect(root.locator('.media')).to_have_count(12);geometry(page)
    root.locator('.media-title').last.scroll_into_view_if_needed();assert page.evaluate('scrollY')>0
    page.evaluate('scrollTo(0,0)')
    assert_stable(page);assert not errors,errors
    Path('/workspace/yt-min-qa').mkdir(exist_ok=True)
    page.screenshot(path=f'/workspace/yt-min-qa/search-stream-{width}-{dark}.png',full_page=True)
    page.evaluate('__setEnabled(false)');expect(root).to_have_count(0)
    assert page.evaluate('!document.documentElement.hasAttribute("data-myt-search-ui")')
    assert page.evaluate('__parents.every(([node,parent])=>node.parentElement===parent)')
    page.evaluate('__setEnabled(true)');expect(root.locator('.media')).to_have_count(12);geometry(page)
    page.close();print(f'PASS owned stream, order/spacing/spans, renderer avatars, English groups, filters, links, continuation and restore: {width}px, dark={dark}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,900,390]:
            for dark in [True,False]:check(browser,width,dark)
        check(browser,390,True,prune=False)
        browser.close()


if __name__=='__main__':main()
