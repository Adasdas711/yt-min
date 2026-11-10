"""Repeated section navigation, isolated search, delayed replies and history."""
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
        if(window.__nativeOptions.resolveURLs)window.ytcfg={get:name=>name==='INNERTUBE_CONTEXT'?{client:{clientName:'WEB',clientVersion:'fixture-version'}}:undefined};
        const state=window.__native;
        const records=names.map(([name,title])=>{
            const endpoint={browseEndpoint:{browseId:id,params:'native-'+name},clickTrackingParams:'native-tracking-'+name,commandMetadata:{webCommandMetadata:{url:base+'/'+(name==='posts'?'community':name),webPageType:'WEB_PAGE_TYPE_CHANNEL',apiUrl:'/youtubei/v1/browse'}}};
            const tab={title,endpoint,selected:name===section()};
            if(name==='videos')Object.defineProperty(tab,'content',{enumerable:true,get:()=>{state.contentReads++;throw new Error('Video feed must not be inspected to find tabs')}});
            return name==='search'?{expandableTabRenderer:tab}:{tabRenderer:tab};
        });
        const model=()=>{
            if(window.__nativeOptions.dirtyTabs&&state.serial>=3)for(const record of records)(record.tabRenderer||record.expandableTabRenderer).endpoint.browseEndpoint.params='native-search';
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
        window.__originalChannelHeader=browse.querySelector('#page-header');
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
            // A page controller may mutate the dispatched command. Cached
            // snapshots must remain usable for the next visit to this tab.
            if(window.__nativeOptions.resolveURLs)endpoint.browseEndpoint.params='native-search';
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


def resolve_url(route,section=None):
    target=urlparse(route.request.post_data_json['url'])
    if section:target=target._replace(path=target.path.rsplit('/',1)[0]+'/'+section)
    section=target.path.rstrip('/').split('/')[-1]
    if section=='community':section='posts'
    endpoint={'browseEndpoint':{'browseId':'UCfixtureNavigation','params':'native-'+section},'commandMetadata':{'webCommandMetadata':{'url':target.geturl(),'webPageType':'WEB_PAGE_TYPE_CHANNEL','apiUrl':'/youtubei/v1/browse'}}}
    route.fulfill(content_type='application/json',body=json.dumps({'endpoint':endpoint}))


def setup(browser,width=1440,dom_only=False,bridge=True,search_context_bug=False,dirty_tabs=False,resolve_urls=False,document_language='en'):
    context=browser.new_context(viewport={'width':width,'height':960})
    page=context.new_page();documents=[];requests=[];pending=[];errors=[]
    def route(route):
        request=route.request
        if urlparse(request.url).path=='/youtubei/v1/navigation/resolve_url':
            resolve_url(route);return
        if urlparse(request.url).path=='/youtubei/v1/browse':
            requests.append(request.post_data_json);pending.append(route);return
        if request.resource_type=='document':
            documents.append(request.url)
            contents=None
            if len(documents)>1:
                section=urlparse(request.url).path.rstrip('/').split('/')[-1]
                contents=playlist(22,count=12) if section=='playlists' else '<ytd-backstage-post-renderer>Channel post</ytd-backstage-post-renderer>' if section in ('posts','community') else video(24 if section=='search' else 21 if section=='streams' else 20)
            body=document(fixture(contents=contents)).replace('<html lang="en">',f'<html lang="{document_language}">').replace('</head>','<style>'+(ROOT/'src/styles/styles.css').read_text()+'</style></head>')
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
    main+='\nwindow.__nativeOptions='+json.dumps({'domOnly':dom_only,'dirtyTabs':dirty_tabs,'resolveURLs':resolve_urls})+';\n'+ROUTER
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


def wait_section(page,section):
    page.wait_for_url(lambda url:urlparse(str(url)).path.rstrip('/').endswith('/'+section),timeout=4000)


def transitions(browser,width,dom_only,resolve_urls=False,document_language='en'):
    context,page,nav,documents,requests,pending,errors=setup(browser,width,dom_only,dirty_tabs=True,resolve_urls=resolve_urls,document_language=document_language)
    resolutions=[]
    context.on('request',lambda request:resolutions.append(request.post_data_json) if '/navigation/resolve_url' in request.url else None)
    if resolve_urls:
        # Live must also work when the original tab command is already wrong.
        page.evaluate('document.querySelector("ytd-browse").data.contents.twoColumnBrowseResultsRenderer.tabs[1].tabRenderer.endpoint.browseEndpoint.params="native-search"')
    for cycle in range(5):
        for title,section in [('Live','streams'),('Playlists','playlists'),('Posts','posts'),('Videos','videos')]:
            token=page.evaluate('__native.token')
            link=nav.get_by_role('link',name=title,exact=True)
            if title=='Posts':link.focus();link.press('Enter')
            else:link.click()
            page.wait_for_function('count=>__native.events.length===count',arg=cycle*4+['streams','playlists','posts','videos'].index(section)+1)
            expect(nav).to_be_visible()
            expect(page.locator('#page-header')).to_be_visible()
            assert page.evaluate('document.querySelector("#page-header")===__originalChannelHeader')
            assert finish(pending)==section
            wait_section(page,section)
            expect(link).to_have_attribute('aria-current','page')
            expect(nav).to_have_attribute('aria-busy','false')
            assert page.evaluate('__native.token')==token
            assert page.evaluate('document.querySelector("#myt-channel-nav")===__originalChannelNav')
            assert not pending
            assert 'query' not in parse_qs(urlparse(page.url).query)
            if section=='posts':expect(page.locator('ytd-backstage-post-renderer')).to_have_text('Channel post')
            else:expect(page.locator('#myt-search .media-title')).to_have_text(['Playlist 22' if section=='playlists' else 'Regular video 21' if section=='streams' else 'Regular video 20'])
    assert len(documents)==1 and len(requests)==20,(documents,requests)
    if resolve_urls:
        assert len(resolutions)==4,'Each ordinary section should be resolved once and then use an immutable cached command'
    count=len(requests);nav.get_by_role('link',name='Videos',exact=True).click();page.wait_for_timeout(50)
    assert len(requests)==count and len(documents)==1,'The active section must not reload'
    page.go_back();wait_section(page,'posts')
    expect(nav.get_by_role('link',name='Posts',exact=True)).to_have_attribute('aria-current','page')
    page.go_forward();wait_section(page,'videos')
    expect(nav.get_by_role('link',name='Videos',exact=True)).to_have_attribute('aria-current','page')
    assert not errors,errors
    context.close()
    print(f'PASS 20 SPA section changes including Live, stable header/nav, immutable commands and history: {width}px, DOM models={dom_only}, resolved URLs={resolve_urls}, document language={document_language}',flush=True)


def search_and_races(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser,390)
    button=nav.get_by_role('button',name='Search',exact=True);button.focus();button.press('Space')
    field=nav.get_by_role('searchbox',name='Search this channel')
    assert not requests and len(documents)==1
    expect(button.locator('svg')).to_have_count(1)
    icon=button.bounding_box();box=field.bounding_box()
    assert box['x']>=icon['x']+icon['width'],(icon,box)
    query='Поиск & + #';field.fill('First query');field.press('Enter')
    field.fill(query);field.press('Enter')
    finish(pending,1);page.wait_for_url('**/search?**');finish(pending)
    expect(field).to_have_value(query)
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 24'])
    expect(page.locator('#myt-search .media-channel')).to_be_hidden()
    assert parse_qs(urlparse(page.url).query)=={'query':[query]}
    field.fill('Another query');button.click();finish(pending);page.wait_for_url('**query=Another+query')
    page.go_back();expect(field).to_have_value(query)
    page.go_forward();expect(field).to_have_value('Another query')
    field.press('Escape');expect(field).to_be_hidden();expect(button).to_be_focused()
    assert len(documents)==1 and not errors,(documents,errors)
    context.close()
    print('PASS empty icon is inert, field on the right, rapid query replies, hidden channel names, Unicode, history and Escape',flush=True)


def fallback_and_cleanup(browser):
    for mode in ('silent','error','no-bridge','no-models'):
        context,page,nav,documents,requests,pending,errors=setup(browser,bridge=mode!='no-bridge')
        if mode!='no-bridge':page.evaluate('mode=>__native.mode=mode',mode)
        if mode=='no-models':page.evaluate('delete document.querySelector("ytd-browse").data.contents')
        nav.get_by_role('button',name='Search',exact=True).click()
        field=nav.get_by_role('searchbox',name='Search this channel');field.fill('fallback');field.press('Enter')
        page.wait_for_url('**/search?**')
        expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 24'])
        assert len(documents)==2 and not errors,(mode,documents,errors)
        context.close()
    context,page,nav,documents,requests,pending,errors=setup(browser)
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('pending');field.press('Enter')
    session=context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'channel-navigation-extension'})['executionContextId']
    result=session.send('Runtime.evaluate',{'expression':'__setEnabled(false)','contextId':world})
    assert not result.get('exceptionDetails'),result
    expect(nav).to_have_count(0)
    finish(pending);page.wait_for_url('**/search?**')
    assert len(documents)==1 and not errors,(documents,errors)
    context.close()
    print('PASS search compatibility fallbacks and removal of pending navigation on disable',flush=True)


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


def resolution_races(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser,resolve_urls=True)
    resolving=[]
    context.route('**/navigation/resolve_url?**',lambda route:resolving.append(route))
    nav.get_by_role('link',name='Live',exact=True).click()
    expect(nav).to_have_attribute('aria-busy','true')
    # URL resolution may exceed the old 700ms acknowledgement watchdog.
    page.wait_for_timeout(850)
    assert len(resolving)==1 and len(documents)==1 and not requests
    expect(page.locator('#myt-search .media-title').first).to_have_text('Regular video 1')
    expect(page.locator('#page-header')).to_be_visible()
    nav.get_by_role('link',name='Playlists',exact=True).click()
    page.wait_for_timeout(50)
    assert len(resolving)==2
    resolve_url(resolving.pop())
    page.wait_for_function('__native.events.length===1')
    assert finish(pending)=='playlists'
    wait_section(page,'playlists')
    resolve_url(resolving.pop())
    page.wait_for_timeout(100)
    assert page.evaluate('__native.events.length')==1
    expect(page.locator('#myt-search .media-title')).to_have_text(['Playlist 22'])
    assert len(documents)==1 and not errors,(documents,errors)
    context.close()

    context,page,nav,documents,requests,pending,errors=setup(browser,resolve_urls=True)
    resolving=[]
    context.route('**/navigation/resolve_url?**',lambda route:resolving.append(route))
    nav.get_by_role('link',name='Live',exact=True).click()
    page.wait_for_timeout(50)
    assert len(resolving)==1
    session=context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'channel-navigation-extension'})['executionContextId']
    session.send('Runtime.evaluate',{'expression':'__setEnabled(false)','contextId':world})
    expect(nav).to_have_count(0)
    resolve_url(resolving.pop());page.wait_for_timeout(100)
    assert not requests and len(documents)==1 and not errors,(documents,errors)
    context.close()
    print('PASS slow URL resolution keeps the old feed visible; superseded and disabled requests cannot navigate',flush=True)


def resolved_search_and_empty_live(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser,resolve_urls=True)
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('query & Unicode');field.press('Enter')
    page.wait_for_function('__native.events.length===1');finish(pending);page.wait_for_url('**/search?**')
    nav.get_by_role('link',name='Live',exact=True).click()
    page.wait_for_function('__native.events.length===2')
    assert requests[-1]=={'browseId':'UCfixtureNavigation','params':'native-streams'}
    finish(pending)
    wait_section(page,'streams');expect(nav).to_have_attribute('aria-busy','false')
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 21'])
    assert len(documents)==1
    nav.get_by_role('link',name='Videos',exact=True).click()
    page.wait_for_function('__native.events.length===3');finish(pending);wait_section(page,'videos')
    nav.get_by_role('link',name='Live',exact=True).click()
    page.wait_for_function('__native.events.length===4')
    pending.pop().fulfill(content_type='application/json',body=json.dumps({'html':'<ytd-message-renderer>No results found</ytd-message-renderer>'}))
    wait_section(page,'streams');expect(nav).to_have_attribute('aria-busy','false');page.wait_for_timeout(500)
    assert len(documents)==1 and not errors,(documents,errors)
    context.close()
    print('PASS resolved search exits without reloading or query leakage; an empty Live tab also stays in the document',flush=True)


def invalid_resolution(browser):
    for mode in ('wrong-section','http-error'):
        context,page,nav,documents,requests,pending,errors=setup(browser,resolve_urls=True)
        context.route('**/navigation/resolve_url?**',lambda route:resolve_url(route,'videos') if mode=='wrong-section' else route.fulfill(status=503,body='Unavailable'))
        nav.get_by_role('link',name='Live',exact=True).click()
        wait_section(page,'streams')
        expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 21'])
        assert len(documents)==2 and not requests and not errors,(mode,documents,errors)
        context.close()
    print('PASS wrong section commands and URL resolution errors recover with the actual Live document',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width,dom_only in ((1440,False),(390,True)):transitions(browser,width,dom_only)
        for width in (1440,390):transitions(browser,width,False,resolve_urls=True)
        for language in ('ru','de'):
            for width in (1440,390):transitions(browser,width,False,resolve_urls=True,document_language=language)
        search_and_races(browser)
        fallback_and_cleanup(browser)
        modified_clicks(browser)
        resolution_races(browser)
        resolved_search_and_empty_live(browser)
        invalid_resolution(browser)
        browser.close()
