"""Real MAIN/ISOLATED worlds and a native opener that refuses synthetic clicks."""
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, document
from channel_header import fixture
from channel_about import about_dialog


def check(browser,width):
    page=browser.new_page(viewport={'width':width,'height':960})
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html; charset=utf-8',body=document(fixture())))
    page.goto('https://www.youtube.com/@JoeSpeen/videos?hl=en')
    page.add_style_tag(path=str(ROOT/'src/styles/styles.css'))
    full='Full channel description from public MAIN data.\n'+('Readable author text, with original paragraphs.\n'*12)
    page.evaluate('''full=>{
        const source=document.querySelector('yt-description-preview-view-model');
        source.data={description:{content:'SUBSCRIBE FOR A COOKIE!'},trackingParams:'DO-NOT-COPY-TRACKING'};
        document.querySelector('#author-description').textContent='SUBSCRIBE FOR A COOKIE! SUBSCRIBE FOR A COOKIE!';
        document.querySelector('#description-more').onclick=event=>{window.__nativeAttempts=(window.__nativeAttempts||0)+1;if(!event.isTrusted)return;};
        window.ytInitialData={metadata:{channelMetadataRenderer:{vanityChannelUrl:'https://www.youtube.com/@JoeSpeen',description:full}},privateField:'DO-NOT-COPY-PRIVATE'};
    }''',full)
    page.add_script_tag(path=str(ROOT/'src/content/channel-main.js'))
    session=page.context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'channel-description-extension'})['executionContextId']
    def evaluate(code):
        result=session.send('Runtime.evaluate',{'expression':code,'contextId':world,'returnByValue':True})
        assert not result.get('exceptionDetails'),result.get('exceptionDetails')
        return result.get('result',{}).get('value')
    evaluate('('+MOCK+')({enabled:true});chrome.runtime.id="description-extension";')
    assert evaluate('document.querySelector("yt-description-preview-view-model").data===undefined')
    for module in ['ads','watch','playlist','search-data','search','channel','content']:
        evaluate((ROOT/'src/content'/f'{module}.js').read_text())
    host=page.locator('#myt-channel-description')
    expect(host.locator('.summary')).to_have_text('SUBSCRIBE FOR A COOKIE!')
    expect(host.locator('.more')).to_have_text('...more')
    expect(host.locator('.more svg')).to_have_count(0)
    for selector in ('section','.more'):
        style=host.locator(selector).evaluate('e=>({background:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderTopWidth})')
        assert style=={'background':'rgba(0, 0, 0, 0)','border':'0px'},style
    snapshot=page.locator('yt-description-preview-view-model').get_attribute('data-myt-channel-description-data')
    assert 'DO-NOT-COPY' not in snapshot
    page.evaluate('''()=>document.body.insertAdjacentHTML('beforeend','<div style="height:0;overflow:hidden"><ytd-about-channel-renderer style="height:200px">Cached inactive channel dialog</ytd-about-channel-renderer></div>')''')
    # The native target receives the attempted click but opens nothing. The
    # visible button must still open a real modal containing the full biography.
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    expect(host.locator('.full-text')).to_have_text(full)
    assert page.evaluate('__nativeAttempts')==1
    host.locator('.close').click()
    expect(host.locator('.more')).to_be_focused()
    # Stale initial data from the previous channel must never supply its bio.
    page.evaluate('''()=>{
        history.pushState({},'', '/@Other/videos?hl=en');
        document.querySelector('yt-description-preview-view-model').data={description:{content:'Other channel description'}};
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''')
    expect(host.locator('.summary')).to_have_text('Other channel description')
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    expect(host.locator('.full-text')).to_have_text('Other channel description')
    host.locator('.close').click()
    # A working native opener keeps the existing full Links/More info dialog.
    page.locator('#description-more').evaluate('(e,html)=>e.onclick=()=>document.body.insertAdjacentHTML("beforeend",html)',about_dialog())
    host.locator('.more').click()
    expect(page.locator('#about-dialog')).to_be_visible()
    page.wait_for_timeout(250)
    expect(host.locator('.full')).not_to_be_visible()
    expect(page.get_by_role('dialog',name='About this channel',exact=True)).to_have_count(1)
    page.locator('#close-about').click()
    page.close()
    print(f'PASS transparent UI, single public description across worlds, functional fallback/native dialogs and stale-data isolation: {width}px',flush=True)


def dom_duplicates(browser):
    from smoke import setup
    page=setup(browser,'/@JoeSpeen/videos',fixture())
    page.locator('#author-description').evaluate('e=>e.textContent="SUBSCRIBE FOR A COOKIE! SUBSCRIBE FOR A COOKIE!"')
    expect(page.locator('#myt-channel-description .summary')).to_have_text('SUBSCRIBE FOR A COOKIE!')
    page.close()
    print('PASS duplicate DOM copies collapse when the public data bridge is unavailable',flush=True)


def blocked_input(browser,width):
    from smoke import setup
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width)
    host=page.locator('#myt-channel-description')
    page.evaluate('''()=>{
        document.body.insertAdjacentHTML('beforeend','<ytd-about-channel-renderer style="position:fixed;top:180px;left:20px;height:150px">Cached content outside an active dialog</ytd-about-channel-renderer>');
    }''')
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    expect(host.locator('.full-text')).to_contain_text('Пщщ! Я Joe Speen')
    page.wait_for_timeout(250)
    expect(host.locator('.full')).to_be_visible()
    host.locator('.close').click()
    expect(host.locator('.full')).not_to_be_visible()
    # Native controls cannot disable or break the independent description.
    page.locator('#description-more').evaluate('''e=>{
        e.disabled=true;e.click=()=>{throw new Error('Native description opener failed')};
    }''')
    expect(host.locator('.more')).to_be_enabled()
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    host.locator('.close').click()
    page.locator('#description-more').evaluate('''e=>{
        const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.id=e.id;svg.setAttribute('role','button');e.replaceWith(svg);
    }''')
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    host.locator('.close').click()
    # Page capture handlers must not swallow mouse or keyboard activation.
    page.evaluate('''()=>{
        for(const type of ['click','keydown'])document.addEventListener(type,event=>{event.preventDefault();event.stopImmediatePropagation()},true);
    }''')
    host.locator('.more').click()
    expect(host.locator('.full')).to_be_visible()
    host.locator('.close').click()
    for key in ('Enter','Space'):
        host.locator('.more').focus()
        host.locator('.more').press(key)
        expect(host.locator('.full')).to_be_visible()
        page.keyboard.press('Escape')
        expect(host.locator('.full')).not_to_be_visible()
        expect(host.locator('.more')).to_be_focused()
    page.close()
    print(f'PASS document capture blockers, inactive about caches, disabled/throwing/non-clickable native targets and mouse/Enter/Space/Escape: {width}px',flush=True)


def description_scroll(browser,width,nested=False):
    from smoke import setup
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width)
    page.set_viewport_size({'width':width,'height':640})
    full='Full biography\n\n'+''.join(f'Paragraph {i}: original channel description with enough text to wrap on smaller screens.\n\n' for i in range(60))+'Last line of the biography.'
    page.evaluate('''({full,nested})=>{
        document.querySelector('ytd-browse').style.minHeight='4000px';
        const source=document.querySelector('yt-description-preview-view-model');
        source.data={description:{content:'Full biography'}};
        window.ytInitialData={metadata:{channelMetadataRenderer:{vanityChannelUrl:'https://www.youtube.com/@JoeSpeen',description:full}}};
        document.querySelector('#author-description').textContent='Full biography';
        if(nested){
            const manager=document.querySelector('ytd-page-manager'),scroll=document.createElement('div');
            scroll.id='channel-scrollport';scroll.style.cssText='position:fixed;inset:56px 0 0;overflow-y:auto';
            manager.before(scroll);scroll.append(manager);
        }
    }''',{'full':full,'nested':nested})
    host=page.locator('#myt-channel-description')
    expect(host.locator('.summary')).to_have_text('Full biography')
    host.locator('.more').click()
    body=host.locator('.full-body')
    expect(body).to_be_visible()
    expect(host.locator('.full-text')).to_have_text(full)
    background=lambda:page.evaluate('({document:scrollY,nested:document.querySelector("#channel-scrollport")?.scrollTop||0})')
    before=background()
    body.hover()
    page.mouse.wheel(0,320)
    page.wait_for_timeout(180)
    assert body.evaluate('e=>e.scrollTop')>0,{'descriptionScroll':body.evaluate('e=>e.scrollTop'),'backgroundBefore':before,'backgroundAfter':background()}
    assert background()==before,(before,background())
    # Neither scroll boundary, the title nor the backdrop may move the channel.
    for end,delta in ((True,500),(False,-500)):
        body.evaluate('(e,end)=>e.scrollTop=end?e.scrollHeight:0',end)
        page.mouse.wheel(0,delta)
        page.wait_for_timeout(120)
        assert background()==before,(before,background())
    for target in ('header',None):
        if target:host.locator(target).hover()
        else:page.mouse.move(3,320)
        page.mouse.wheel(0,400)
        page.wait_for_timeout(120)
        assert background()==before,(target,before,background())
    if width==390:
        session=page.context.new_cdp_session(page)
        session.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':1})
        box=body.bounding_box()
        def swipe(x,delta):
            start=box['y']+box['height']/2
            session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':start}]})
            for step in range(1,7):
                session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':start+delta*step/6}]})
                page.wait_for_timeout(30)
            page.wait_for_timeout(150)
            session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            page.wait_for_timeout(80)
        swipe(box['x']+box['width']/2,-180)
        page.wait_for_function('document.querySelector("#myt-channel-description").shadowRoot.querySelector(".full-body").scrollTop>0')
        assert background()==before,(before,background())
        body.evaluate('e=>e.scrollTop=e.scrollHeight')
        swipe(box['x']+box['width']/2,-180)
        swipe(3,-180)
        assert background()==before,(before,background())
        body.evaluate('e=>e.scrollTop=0')
        swipe(box['x']+box['width']/2,180)
        assert background()==before,(before,background())
    # Keyboard scrolling belongs to the description and reaches its last line.
    body.focus()
    page.keyboard.press('PageDown')
    page.wait_for_function('document.querySelector("#myt-channel-description").shadowRoot.querySelector(".full-body").scrollTop>0')
    page.keyboard.press('End')
    page.wait_for_function('''()=>{const e=document.querySelector('#myt-channel-description').shadowRoot.querySelector('.full-body');return e.scrollTop+e.clientHeight>=e.scrollHeight-1}''')
    assert background()==before,(before,background())
    page.keyboard.press('Home')
    page.wait_for_function('document.querySelector("#myt-channel-description").shadowRoot.querySelector(".full-body").scrollTop===0')
    host.locator('.close').click()
    page.mouse.move(3,320)
    page.mouse.wheel(0,320)
    page.wait_for_function('(before)=>scrollY>before.document||(document.querySelector("#channel-scrollport")?.scrollTop||0)>before.nested',arg=before)
    # Disabling while the dialog is open must also release the scroll lock.
    host.locator('.more').click()
    page.evaluate('__setEnabled(false)')
    expect(host).to_have_count(0)
    unlocked=background()
    page.locator('#channel-scrollport' if nested else 'body').hover(position={'x':5,'y':320})
    page.mouse.wheel(0,320)
    page.wait_for_function('(before)=>scrollY>before.document||(document.querySelector("#channel-scrollport")?.scrollTop||0)>before.nested',arg=unlocked)
    page.close()
    print(f'PASS description wheel/keyboard/touch, boundaries/backdrop isolation and restored document/nested scroll: {width}px, nested={nested}',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (1440,390):check(browser,width)
        dom_duplicates(browser)
        for width in (1440,390):blocked_input(browser,width)
        for width in (1440,390):
            for nested in (False,True):description_scroll(browser,width,nested)
        browser.close()
