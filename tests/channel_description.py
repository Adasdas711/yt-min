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


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (1440,390):check(browser,width)
        dom_duplicates(browser)
        for width in (1440,390):blocked_input(browser,width)
        browser.close()
