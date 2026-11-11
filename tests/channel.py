"""Channel layout, native controls, sticky tabs and incremental cards."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, navigate_spa
from search import video, playlist


def fixture():
    tabs=''.join(f'<yt-tab-shape role="tab"><a href="/@creator/{path}">{label}</a></yt-tab-shape>' for path,label in [('featured','Home'),('videos','Videos'),('streams','Live'),('playlists','Playlists'),('community','Posts'),('shorts','Shorts'),('about','About'),('search','Search')])
    return '<style>ytd-browse,yt-page-header-view-model{display:block}#banner{height:120px}#tabs{height:48px}yt-tab-shape{display:inline-block;padding:10px}</style><ytd-app>'+MASTHEAD+'<ytd-page-manager><ytd-browse page-subtype="channels"><div id="header"><div id="banner">Banner</div><yt-page-header-view-model><h1>Название канала</h1><img id="avatar" width="80" height="80"><div id="description-container">Channel description</div><button id="subscribe" onclick="this.textContent=\'Subscribed\'">Subscribe</button></yt-page-header-view-model></div><div id="tabs"><yt-tab-group-shape>'+tabs+'</yt-tab-group-shape></div><div id="contents"><ytd-rich-grid-renderer><div id="contents">'+video(1)+playlist(1,count=12)+''.join(video(i) for i in range(2,18))+'<ytd-continuation-item-renderer id="continuation"></ytd-continuation-item-renderer></div></ytd-rich-grid-renderer></div></ytd-browse></ytd-page-manager></ytd-app>'

if __name__ == '__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width,nested in ((1440,False),(900,False),(390,False),(1440,True)):
            page=setup(browser,path='/@creator/videos',body=fixture().replace('</div><div id="tabs">','<div id="tabs">').replace('</yt-tab-group-shape></div><div id="contents">','</yt-tab-group-shape></div></div><div id="contents">') if nested else fixture(),width=width)
            expect(page.locator('#myt-search .media')).to_have_count(18)
            # YouTube lays out a rich grid from its own width and stamps no
            # items into a boxless grid after an SPA section change.
            grid=page.evaluate('''()=>{const g=document.querySelector('ytd-rich-grid-renderer'),c=document.querySelector('#continuation'),host=document.querySelector('#myt-search');
                const gb=g.getBoundingClientRect(),cb=c.getBoundingClientRect(),hb=host.getBoundingClientRect();
                return {width:gb.width,height:gb.height,hostWidth:hb.width,visibility:getComputedStyle(g).visibility,continuationTop:cb.top,hostBottom:hb.bottom};}''')
            assert grid['width']>=grid['hostWidth']>0 and grid['height']<=2 and grid['visibility']=='hidden',grid
            assert grid['continuationTop']>=grid['hostBottom']-1,grid
            for label in ('Home','About','Shorts'):
                expect(page.get_by_role('tab').filter(has_text=label)).to_be_hidden()
            expect(page.locator('#myt-channel-nav').get_by_role('link',name='Videos',exact=True)).to_be_visible()
            page.locator('#subscribe').click()
            expect(page.locator('#subscribe')).to_have_text('Subscribed')
            assert page.locator('h1').evaluate("e=>getComputedStyle(e).fontStyle")=='italic'
            assert 'Mono' in page.locator('#myt-channel-description .summary').evaluate("e=>getComputedStyle(e).fontFamily")
            result=page.locator('#myt-search').evaluate('''host=>{const q=s=>host.shadowRoot.querySelector(s),a=q('.video').getBoundingClientRect(),b=q('.playlist').getBoundingClientRect();return {video:a.width,playlist:b.width,display:getComputedStyle(q('.playlist')).display,width:host.getBoundingClientRect().width}}''')
            assert abs(result['video']-result['playlist'])<2,result
            assert result['display']=='flex',result
            page.evaluate('window.scrollTo(0,500)')
            page.wait_for_timeout(100)
            assert abs(page.locator('ytd-browse #tabs').bounding_box()['y']-56)<3, page.evaluate("()=>({position:getComputedStyle(document.querySelector('ytd-browse #tabs')).position,scroll:scrollY,tabs:document.querySelector('ytd-browse #tabs').getBoundingClientRect().toJSON(),parents:[...document.querySelectorAll('ytd-app,ytd-page-manager,ytd-browse')].map(e=>[e.tagName,getComputedStyle(e).overflow,getComputedStyle(e).height])})")
            page.locator('ytd-rich-grid-renderer > #contents').evaluate('(e,html)=>e.insertAdjacentHTML("beforeend",html)',video(99))
            expect(page.locator('#myt-search .media')).to_have_count(19)
            page.evaluate('window.__setEnabled(false)')
            expect(page.locator('#myt-search')).to_have_count(0)
            expect(page.get_by_role('tab').filter(has_text='Home')).to_be_visible()
            page.close()
            print(f'PASS nested={nested} channel identity, tabs, sticky navigation, equal playlist/video cells, updates and disable at {width}px')
        # YouTube can hold a section's items in its data without stamping them
        # into the grid after an SPA switch: draw that section from its data.
        empty=fixture().split('<ytd-rich-grid-renderer>')[0]+'<ytd-rich-grid-renderer><div id="contents"><ytd-continuation-item-renderer id="continuation"></ytd-continuation-item-renderer></div></ytd-rich-grid-renderer></div></ytd-browse></ytd-page-manager></ytd-app>'
        page=setup(browser,path='/@creator/videos',body=empty)
        page.evaluate('''()=>{const item=(id,title)=>({richItemRenderer:{content:{videoRenderer:{videoId:id,title:{runs:[{text:title}]},
            thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg',width:480}]},navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/watch?v='+id}},watchEndpoint:{videoId:id}}}}}});
            const tab=(name,selected,content)=>({tabRenderer:{title:name,selected,endpoint:{commandMetadata:{webCommandMetadata:{url:'/@creator/'+name.toLowerCase()}}},content}});
            document.querySelector('ytd-browse').data={contents:{twoColumnBrowseResultsRenderer:{tabs:[
                tab('Videos',true,{richGridRenderer:{contents:[item('dataVideo01','Data video one'),item('dataVideo02','Data video two')]}}),
                tab('Playlists',false,{richGridRenderer:{contents:[item('otherTab001','Wrong section')]}})]}}};
            document.dispatchEvent(new Event('yt-page-data-updated'));}''')
        expect(page.locator('#myt-search .media-title')).to_have_text(['Data video one','Data video two'])
        assert page.locator('#myt-search .media-title').first.get_attribute('href')=='https://www.youtube.com/watch?v=dataVideo01'
        # A selected tab for another URL is never drawn under this one.
        page.evaluate('''()=>{const tabs=document.querySelector('ytd-browse').data.contents.twoColumnBrowseResultsRenderer.tabs;tabs[0].tabRenderer.selected=false;tabs[1].tabRenderer.selected=true;document.dispatchEvent(new Event('yt-page-data-updated'));}''')
        expect(page.locator('#myt-search .media')).to_have_count(0)
        # Once YouTube stamps its own cards, they replace the data cards.
        page.locator('ytd-rich-grid-renderer > #contents').evaluate('(e,html)=>e.insertAdjacentHTML("afterbegin",html)',video(1)+video(2)+video(3))
        expect(page.locator('#myt-search .media')).to_have_count(3)
        page.close()
        print('PASS sections whose data was not stamped into the grid are drawn from that data, never another tab')
        page=setup(browser,path='/@creator/community',body=fixture())
        expect(page.locator('#myt-search')).to_have_count(0)
        expect(page.locator('#subscribe')).to_be_visible()
        navigate_spa(page,'/@creator/videos')
        expect(page.locator('#myt-search .media')).to_have_count(18)
        navigate_spa(page,'/@creator/community')
        expect(page.locator('#myt-search')).to_have_count(0)
        expect(page.locator('#subscribe')).to_be_visible()
        page.close()
        print('PASS native posts and SPA transitions between posts and video grid')
        browser.close()
