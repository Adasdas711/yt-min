"""Channel SPA navigation across MAIN/ISOLATED worlds, delayed replies and history."""
import json
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, document
from channel_header import fixture
from search import video, playlist

ROUTER=r'''(() => {
    const start=()=>{
        const browse=document.querySelector('ytd-browse'),app=document.querySelector('ytd-app');
        const names=[['videos','Videos'],['streams','Live'],['playlists','Playlists'],['posts','Posts'],['search','Search']];
        const labels=new Map([['Видео','videos'],['Трансляции','streams'],['Плейлисты','playlists'],['Записи','posts'],['Поиск','search']]);
        const base='/@JoeSpeen',id='UCfixtureNavigation';
        const key=()=>location.pathname+location.search;
        const section=()=>{const s=location.pathname.split('/').pop();return s==='community'?'posts':s;};
        window.__native={token:crypto.randomUUID(),serial:0,mode:'normal',events:[],contentReads:0,pages:new Map()};
        const state=window.__native;
        const records=names.map(([name,title])=>{
            const endpoint={browseEndpoint:{browseId:id,params:'native-'+name},clickTrackingParams:'native-tracking-'+name,commandMetadata:{webCommandMetadata:{url:base+'/'+(name==='posts'?'community':name),webPageType:'WEB_PAGE_TYPE_CHANNEL',apiUrl:'/youtubei/v1/browse'}}};
            const tab={title,endpoint,selected:name===section()};
            if(name==='videos')Object.defineProperty(tab,'content',{enumerable:true,get:()=>{state.contentReads++;throw new Error('Video feed must not be inspected to find tabs')}});
            return name==='search'?{expandableTabRenderer:tab}:{tabRenderer:tab};
        });
        const model=()=>{
            browse.data={metadata:{channelMetadataRenderer:{externalId:id,vanityChannelUrl:'https://www.youtube.com'+base,description:'Channel biography'}},contents:window.__nativeOptions.domOnly?{}:{twoColumnBrowseResultsRenderer:{tabs:records}}};
            window.ytInitialData=browse.data;
            for(const node of browse.querySelectorAll('yt-tab-shape')){
                const title=node.textContent.trim(),name=labels.get(title)||names.find(([,label])=>label===title)?.[0];
                if(!name)continue;
                const record=records[names.findIndex(([value])=>value===name)],tab=record.tabRenderer||record.expandableTabRenderer;
                tab.selected=name===section();node.setAttribute('aria-selected',String(tab.selected));
                if(window.__nativeOptions.domOnly)node.viewModel={tabViewModel:{title:tab.title,rendererContext:{commandContext:{onTap:{innertubeCommand:tab.endpoint}}}}};
            }
        };
        model();state.pages.set(key(),browse.querySelector(':scope > #contents').innerHTML);
        window.__originalChannelNav=null;
        const notify=(type,endpoint)=>(window.__nativeOptions.domOnly?window:document).dispatchEvent(new CustomEvent(type,{detail:{endpoint,url:endpoint.commandMetadata.webCommandMetadata.url}}));
        document.addEventListener('yt-navigate',event=>{
            const endpoint=event.detail?.endpoint;if(!endpoint?.browseEndpoint)return;
            event.preventDefault();state.events.push(endpoint);
            if(state.mode==='silent')return;
            const serial=++state.serial;notify('yt-navigate-start',endpoint);
            if(state.mode==='error'){document.dispatchEvent(new CustomEvent('yt-navigate-error'));return;}
            if(state.mode==='hang')return;
            fetch('/youtubei/v1/browse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(endpoint.browseEndpoint)})
                .then(response=>{if(!response.ok)throw new Error('Native request failed');return response.json()})
                .then(response=>{
                    if(serial!==state.serial)return;
                    history.pushState({},'',endpoint.commandMetadata.webCommandMetadata.url);
                    browse.querySelector(':scope > #contents').innerHTML=response.html;
                    model();state.pages.set(key(),response.html);
                    notify('yt-page-data-updated',endpoint);notify('yt-navigate-finish',endpoint);
                }).catch(()=>{if(serial===state.serial)notify('yt-navigate-error',endpoint);});
        });
        window.addEventListener('popstate',()=>{
            state.serial++;
            const html=state.pages.get(key());if(html!==undefined)browse.querySelector(':scope > #contents').innerHTML=html;
            model();document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
        });
        // Page capture handlers must not swallow extension links or search input.
        document.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation()},true);
        document.addEventListener('keydown',event=>{event.preventDefault();event.stopImmediatePropagation()},true);
    };
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();'''


def setup(browser,width=1440,dom_only=False,bridge=True,search_context_bug=False):
    context=browser.new_context(viewport={'width':width,'height':960})
    page=context.new_page();documents=[];requests=[];pending=[];errors=[]
    def route(route):
        request=route.request
        if urlparse(request.url).path=='/youtubei/v1/browse':
            requests.append(request.post_data_json);pending.append(route);return
        if request.resource_type=='document':
            documents.append(request.url)
            contents=None
            if len(documents)>1:
                section=urlparse(request.url).path.rstrip('/').split('/')[-1]
                contents=playlist(22,count=12) if section=='playlists' else '<ytd-backstage-post-renderer>Channel post</ytd-backstage-post-renderer>' if section in ('posts','community') else video(24 if section=='search' else 21 if section=='streams' else 20)
            body=document(fixture(contents=contents)).replace('</head>','<style>'+(ROOT/'src/styles/styles.css').read_text()+'</style></head>')
            route.fulfill(content_type='text/html; charset=utf-8',body=body)
        else:route.fulfill(status=204,body='')
    context.route('https://www.youtube.com/**',route)
    page.on('pageerror',lambda error:errors.append(error))
    main=(ROOT/'src/content/search-data.js').read_text()+'\n'+(ROOT/'src/content/channel-main.js').read_text()
    if bridge:main+='\n'+(ROOT/'src/content/channel-navigation-main.js').read_text()
    if search_context_bug:main+='''
      document.addEventListener('yt-navigate',event=>{
        const endpoint=event.detail?.endpoint,url=endpoint?.commandMetadata?.webCommandMetadata?.url;
        if(!/\\/search$/.test(location.pathname)||!url||/\\/search(?:[?#]|$)/.test(url))return;
        event.preventDefault();event.stopImmediatePropagation();
        history.pushState({},'',url);
        document.querySelector('ytd-browse > #contents').innerHTML='<ytd-message-renderer>No results found</ytd-message-renderer>';
        document.dispatchEvent(new CustomEvent('yt-page-data-updated',{detail:{endpoint,url}}));
        document.dispatchEvent(new CustomEvent('yt-navigate-finish',{detail:{endpoint,url}}));
      },true);
    '''
    main+='\nwindow.__nativeOptions='+json.dumps({'domOnly':dom_only})+';\n'+ROUTER
    page.add_init_script(main)
    isolated='('+MOCK+')({enabled:true});chrome.runtime.id="channel-navigation";\n'
    isolated+='\n'.join((ROOT/'src/content'/f'{module}.js').read_text() for module in ['ads','watch','playlist','search-data','search','channel','content'])
    session=context.new_cdp_session(page)
    session.send('Page.enable')
    session.send('Page.addScriptToEvaluateOnNewDocument',{'source':isolated,'worldName':'channel-navigation-extension'})
    page.goto('https://www.youtube.com/@JoeSpeen/videos?hl=en&persist_hl=1')
    nav=page.locator('#myt-channel-nav')
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_be_visible()
    page.evaluate('window.__originalChannelNav=document.querySelector("#myt-channel-nav")')
    return context,page,nav,documents,requests,pending,errors


def finish(pending,index=0):
    route=pending.pop(index);data=route.request.post_data_json;section=data['params'].removeprefix('native-')
    number={'videos':20,'streams':21,'playlists':22,'posts':23,'search':24}[section]
    html=f'<div id="section-result">{section}:{data.get("query","")}</div>'
    html+=playlist(number,count=12) if section=='playlists' else '<ytd-backstage-post-renderer>Channel post</ytd-backstage-post-renderer>' if section=='posts' else video(number)
    route.fulfill(content_type='application/json',body=json.dumps({'html':html}))
    return section


def transitions(browser,width,dom_only):
    context,page,nav,documents,requests,pending,errors=setup(browser,width,dom_only)
    token=page.evaluate('__native.token')
    for title,section in [('Live','streams'),('Playlists','playlists'),('Posts','posts'),('Videos','videos')]:
        link=nav.get_by_role('link',name=title,exact=True)
        if title=='Posts':link.focus();link.press('Enter')
        else:link.click()
        expect(nav).to_have_attribute('aria-busy','true')
        expect(link).to_have_attribute('aria-current','page')
        expect(link).to_have_attribute('data-pending','')
        assert page.evaluate('__native.events.at(-1).clickTrackingParams')=='native-tracking-'+section
        count=len(requests);link.click();assert len(requests)==count
        if title=='Live':
            page.wait_for_timeout(800)
            assert len(documents)==1,'An accepted slow SPA request must not cause a reload'
            page.evaluate('''()=>{
                const group=document.querySelector('yt-tab-group-shape');
                window.__nativeTabMarkup=group.innerHTML;group.replaceChildren();
            }''')
            expect(nav).to_be_visible()
            expect(nav.get_by_role('link',name='Playlists',exact=True)).to_be_visible()
            page.evaluate('document.querySelector("yt-tab-group-shape").innerHTML=__nativeTabMarkup')
        finish(pending)
        page.wait_for_url('**/'+section)
        expect(nav).to_have_attribute('aria-busy','false')
        expect(page.locator('#section-result')).to_have_text(section+':')
        assert page.evaluate('__native.token')==token
        assert page.evaluate('document.querySelector("#myt-channel-nav")===__originalChannelNav')
        assert len(documents)==1
    count=len(requests)
    nav.get_by_role('link',name='Videos',exact=True).click()
    assert len(requests)==count,'The active section must not be requested again'
    page.go_back();page.wait_for_url('**/posts')
    expect(nav.get_by_role('link',name='Posts',exact=True)).to_have_attribute('aria-current','page')
    page.go_forward();page.wait_for_url('**/videos')
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_have_attribute('aria-current','page')
    assert len(documents)==1
    assert page.evaluate('__native.contentReads')==0
    assert not errors,errors
    context.close()
    print(f'PASS instant pending state, native SPA sections, duplicates, keyboard and history without document reload: {width}px, DOM models={dom_only}',flush=True)


def search_and_races(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser,390)
    nav.get_by_role('link',name='Playlists',exact=True).click()
    nav.get_by_role('link',name='Live',exact=True).click()
    finish(pending,1)
    page.wait_for_url('**/streams')
    finish(pending)
    expect(nav.get_by_role('link',name='Live',exact=True)).to_have_attribute('aria-current','page')
    assert urlparse(page.url).path.endswith('/streams')
    button=nav.get_by_role('button',name='Search',exact=True);button.focus();button.press('Space')
    assert requests[-1]['params']=='native-videos','Opening empty search from Live must request Videos'
    field=nav.get_by_role('searchbox',name='Search this channel')
    assert not button.text_content().strip(),'Channel search must use an icon instead of a text tab'
    expect(button.locator('svg')).to_have_count(1)
    icon=button.bounding_box();box=field.bounding_box()
    assert box['x']>=icon['x']+icon['width'],(icon,box)
    assert abs((box['y']+box['height']/2)-(icon['y']+icon['height']/2))<2,(icon,box)
    query='Поиск & + #';field.fill(query);field.press('Enter')
    expect(nav).to_have_attribute('aria-busy','true')
    assert requests[-1]['query']==query
    finish(pending,1);page.wait_for_url('**/search?**');finish(pending)
    expect(field).to_have_value(query)
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_have_attribute('aria-current','page')
    expect(page.locator('#myt-search').get_by_role('link',name='Regular video 24',exact=True)).to_be_visible()
    expect(page.locator('html')).to_have_attribute('data-myt-page','channel')
    assert parse_qs(urlparse(page.url).query)=={'query':[query]}
    field.fill('Another query');nav.get_by_role('button',name='Search',exact=True).last.click()
    finish(pending);page.wait_for_url('**query=Another+query')
    page.go_back();expect(field).to_have_value(query)
    field.press('Escape');expect(field).to_be_hidden()
    expect(button).to_be_focused()
    assert len(documents)==1
    assert not errors,errors
    context.close()
    print('PASS rapid replies, icon search with its field on the right, results under Videos, Unicode, query history and Escape',flush=True)


def fallback_and_cleanup(browser):
    for mode in ('silent','error','hang','no-bridge','no-models'):
        context,page,nav,documents,requests,pending,errors=setup(browser,bridge=mode!='no-bridge')
        if mode!='no-bridge':page.evaluate('mode=>__native.mode=mode',mode)
        if mode=='no-models':page.evaluate('delete document.querySelector("ytd-browse").data.contents')
        if mode=='hang':page.clock.install()
        nav.get_by_role('link',name='Playlists',exact=True).click()
        if mode=='hang':page.clock.fast_forward(12050)
        page.wait_for_url('**/playlists?**')
        assert len(documents)==2,(mode,documents)
        assert not requests
        assert not errors,errors
        context.close()
    context,page,nav,documents,requests,pending,errors=setup(browser)
    nav.get_by_role('link',name='Playlists',exact=True).click()
    session=context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'channel-navigation-extension'})['executionContextId']
    result=session.send('Runtime.evaluate',{'expression':'__setEnabled(false)','contextId':world})
    assert not result.get('exceptionDetails'),result
    expect(nav).to_have_count(0)
    page.clock.install();page.clock.fast_forward(12500)
    assert len(documents)==1,'Disabling must cancel compatibility timers'
    finish(pending);page.wait_for_url('**/playlists')
    assert len(documents)==1
    context.close()
    print('PASS single compatibility fallback for missing/silent/failed native routing and timer cleanup on disable',flush=True)


def modified_clicks(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser)
    token=page.evaluate('__native.token')
    for options in ({'modifiers':['Control']},{'button':'middle'}):
        with context.expect_page() as created:nav.get_by_role('link',name='Playlists',exact=True).click(**options)
        other=created.value
        other.wait_for_function('location.href!=="about:blank"')
        frame=context.new_cdp_session(other).send('Page.getFrameTree')['frameTree']['frame']
        target=other.url
        if frame.get('unreachableUrl'):
            # Background-tab navigation can reach the managed proxy before
            # Playwright installs its route. Check its actual destination.
            expect(other.locator('body')).to_contain_text('ERR_TUNNEL_CONNECTION_FAILED')
            target=frame['unreachableUrl']
        assert urlparse(target).path.endswith('/playlists')
        assert parse_qs(urlparse(target).query)=={'hl':['en'],'persist_hl':['1']}
        other.close()
    assert not requests
    assert page.evaluate('__native.token')==token
    assert not errors,errors
    context.close()
    print('PASS Ctrl-click and middle-click retain browser new-tab behavior',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width,dom_only in ((1440,False),(390,True)):transitions(browser,width,dom_only)
        search_and_races(browser)
        fallback_and_cleanup(browser)
        modified_clicks(browser)
        browser.close()
