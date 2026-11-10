"""Fullscreen playback responds in the input event, before native click delays."""
import json
from playwright.sync_api import sync_playwright,expect
from smoke import ROOT,MOCK,document,setup,native_watch_fixture,VIDEO_STREAM


def check(browser,width):
    page=setup(browser,'/watch?v=instant-playback',native_watch_fixture(),native_dark=True,width=width)
    page.evaluate(VIDEO_STREAM)
    page.evaluate('''()=>{
        const video=document.querySelector('video'),player=document.querySelector('#movie_player');
        window.__original={video,parent:video.parentElement,source:video.srcObject,volume:video.volume,rate:video.playbackRate};
        window.__delayed=0;window.__toggleCount=0;
        const toggle=()=>{__toggleCount++;video.paused?video.play():video.pause();};
        const later=()=>{__delayed++;setTimeout(toggle,320);};
        player.addEventListener('click',event=>{
            if(event.target===video||event.target===player)later();
        });
        const button=document.querySelector('#native-play');button.classList.add('ytp-play-button');button.onclick=later;
        document.addEventListener('keydown',event=>{
            if(document.fullscreenElement&&[' ','k','K'].includes(event.key)&&!event.target.matches('input,textarea,button,[role="slider"]')){event.preventDefault();later();}
        });
        player.insertAdjacentHTML('beforeend','<div class="ytp-settings-menu" style="position:absolute;top:30px;right:30px;z-index:10"><input id="caption-input"><button id="setting" onclick="window.__settings=(window.__settings||0)+1">Settings</button><input id="volume-slider" type="range"></div>');
    }''')
    page.locator('#native-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
    video=page.locator('video')
    # Synchronous state checks cannot pass by waiting for the native timeout.
    for selector in ('video','.ytp-play-button'):
        for _ in range(4):
            state=page.locator(selector).evaluate('e=>{const v=document.querySelector("video"),before=v.paused;e.click();return {before,after:v.paused}}')
            assert state['before']!=state['after'],(selector,state)
    assert page.evaluate('__delayed')==0
    for key in ('Space','k','K'):
        video.evaluate('e=>{e.tabIndex=0;e.focus()}')
        before=video.evaluate('e=>e.paused')
        page.keyboard.down(key)
        assert video.evaluate('e=>e.paused')!=before,key
        page.keyboard.down(key)
        assert video.evaluate('e=>e.paused')!=before,'Repeated keydown must not toggle again'
        page.keyboard.up(key)
    page.wait_for_timeout(450)
    assert page.evaluate('__delayed')==0,'A native delayed handler received the same command'
    page.locator('#caption-input').fill('k K ')
    before=video.evaluate('e=>e.paused');page.keyboard.press('Space')
    assert video.evaluate('e=>e.paused')==before
    page.locator('#setting').click();assert page.evaluate('__settings')==1
    assert video.evaluate('e=>e.paused')==before
    page.locator('#volume-slider').focus();page.keyboard.press('Space')
    assert video.evaluate('e=>e.paused')==before
    page.locator('#caption-input').fill('');page.locator('#caption-input').blur()
    touch=video.evaluate('e=>{const before=e.paused;e.dispatchEvent(new PointerEvent("click",{pointerType:"touch",button:0,bubbles:true,composed:true}));return {before,after:e.paused}}')
    assert touch['before']==touch['after'],'Touch surface gestures must stay with the native player'
    page.wait_for_timeout(400);assert video.evaluate('e=>e.paused')!=touch['before']
    # Both clicks toggle once, leaving the original playback state after the
    # existing double-click fullscreen exit gesture.
    before=video.evaluate('e=>e.paused');video.dblclick(position={'x':100,'y':100})
    page.wait_for_function('!document.fullscreenElement')
    assert video.evaluate('e=>e.paused')==before
    # Outside fullscreen, original player behavior is unchanged.
    state=video.evaluate('e=>{const before=e.paused;e.click();return {before,after:e.paused}}')
    assert state['before']==state['after']
    page.wait_for_timeout(400)
    assert video.evaluate('e=>e.paused')!=state['before']
    page.locator('#native-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
    page.evaluate('__setEnabled(false)')
    before=video.evaluate('e=>e.paused');video.evaluate('e=>e.click()')
    assert video.evaluate('e=>e.paused')==before
    page.wait_for_timeout(400);assert video.evaluate('e=>e.paused')!=before
    assert page.evaluate('''()=>{const old=__original,v=document.querySelector('video');return v===old.video&&v.parentElement===old.parent&&v.srcObject===old.source&&v.volume===old.volume&&v.playbackRate===old.rate}''')
    page.evaluate('document.exitFullscreen();clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
    page.close()
    print(f'PASS immediate fullscreen click/button/Space/K, repeat protection, controls, double-click, media identity and disable: {width}px',flush=True)


def isolated_world(browser):
    page=browser.new_page(viewport={'width':1440,'height':960})
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html',body=document(native_watch_fixture())))
    page.goto('https://www.youtube.com/watch?v=isolated-playback')
    page.add_style_tag(path=str(ROOT/'src/styles/styles.css'))
    page.evaluate(VIDEO_STREAM)
    page.evaluate('''()=>{
        window.__nativeDelayed=0;
        const video=document.querySelector('video');video.tabIndex=0;
        const delayed=()=>{__nativeDelayed++;setTimeout(()=>video.paused?video.play():video.pause(),320)};
        document.querySelector('#movie_player').addEventListener('click',event=>{if(event.target===video)delayed()});
        document.addEventListener('keydown',event=>{if(event.key===' '){event.preventDefault();delayed()}});
    }''')
    session=page.context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'fullscreen-playback-extension'})['executionContextId']
    def evaluate(code):
        result=session.send('Runtime.evaluate',{'expression':code,'contextId':world,'returnByValue':True})
        assert not result.get('exceptionDetails'),result
    evaluate('('+MOCK+')({enabled:true});chrome.runtime.id="playback-extension";')
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for path in manifest['content_scripts'][1]['js']:evaluate((ROOT/path).read_text())
    expect(page.locator('#myt-watch')).to_be_visible()
    page.locator('#native-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
    video=page.locator('video')
    result=video.evaluate('e=>{const before=e.paused;e.click();return {before,after:e.paused}}')
    assert result['before']!=result['after'],result
    video.focus();before=video.evaluate('e=>e.paused');page.keyboard.press('Space')
    assert video.evaluate('e=>e.paused')!=before
    page.wait_for_timeout(400);assert page.evaluate('__nativeDelayed')==0
    evaluate('__setEnabled(false)')
    before=video.evaluate('e=>e.paused');video.evaluate('e=>e.click()')
    assert video.evaluate('e=>e.paused')==before
    page.wait_for_timeout(400);assert video.evaluate('e=>e.paused')!=before
    assert page.evaluate('__nativeDelayed')==1
    page.evaluate('document.exitFullscreen();clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
    page.close()
    print('PASS actual MAIN/ISOLATED playback, delayed native handlers suppressed once and restored on disable',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (1440,390):check(browser,width)
        isolated_world(browser)
        browser.close()
