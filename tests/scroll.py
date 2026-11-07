"""Player alignment at paint, scroll boundaries and fullscreen input isolation."""
from playwright.sync_api import sync_playwright, expect
from smoke import (ROOT, setup, native_watch_fixture, playlist_panel_fixture,
                   VIDEO_STREAM, assert_stable, rendered_pixel)


def fullscreen_preview(browser):
    page=fixture(browser, playlist=True)
    page.evaluate('''() => {
      const outer=document.querySelector('#player-container-outer');
      outer.style.cssText='transform:translate(43px,31px);contain:paint;overflow:hidden;width:640px;height:360px';
      const player=document.querySelector('#movie_player'),request=player.requestFullscreen;
      player.requestFullscreen=function(options){
        const b=document.querySelector('video').getBoundingClientRect();
        window.__preview={x:b.x,y:b.y,width:b.width,height:b.height,topLayer:this.closest('ytd-player').matches(':popover-open')};
        return new Promise((resolve,reject)=>{window.__finishFullscreen=()=>request.call(this,options).then(resolve,reject);});
      };
    }''')
    page.locator('#native-fullscreen').click()
    assert not page.evaluate('!!document.fullscreenElement')
    assert page.evaluate('__preview') == {'x':0,'y':0,'width':1440,'height':960,'topLayer':True}
    # The real decoded video must cover the first painted preview, even while
    # the browser fullscreen request is deliberately held pending.
    for x,y in [(20,100),(720,480),(1420,860)]:
        pixel=rendered_pixel(page,x,y)
        assert all(abs(a-b)<=6 for a,b in zip(pixel,[24,180,96,255])),pixel
    page.evaluate('__finishFullscreen()')
    page.wait_for_function('!!document.fullscreenElement')
    assert page.locator('video').bounding_box()=={'x':0,'y':0,'width':1440,'height':960}
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(t=>t.stop())')
    page.close()
    print('PASS first-click fullscreen preview stays in the top layer and paints decoded video before the browser request completes',flush=True)


def fixture(browser, theater=False, playlist=False, fallback=False):
    body = native_watch_fixture(theater)
    if playlist:
        body = body.replace('<div id="secondary-inner"></div>',
            '<div id="secondary-inner">'+playlist_panel_fixture()+'</div>')
    page = setup(browser, '/watch?v=native'+('&list=fixture' if playlist else ''),
                 body, native_dark=True, watch_ui=False)
    if fallback:
        page.evaluate('window.ScrollTimeline=undefined')
    page.add_script_tag(path=str(ROOT/'src/content/watch.js'))
    page.evaluate("document.dispatchEvent(new Event('yt-navigate-finish'))")
    page.evaluate(VIDEO_STREAM)
    page.wait_for_timeout(50)
    return page


def alignment(browser, theater, playlist, fallback):
    page = fixture(browser, theater, playlist, fallback)
    result = page.evaluate('''async () => {
      const root=document.querySelector('#myt-watch').firstChild.shadowRoot;
      const viewport=root.querySelector('.viewport'),media=root.querySelector('.media');
      const video=document.querySelector('video'),parent=video.parentElement;
      let maxError=0,leaks=0;
      window.addEventListener('wheel',()=>leaks++);
      const frame=()=>new Promise(requestAnimationFrame);
      const check=()=>{
        const a=media.getBoundingClientRect(),b=video.getBoundingClientRect();
        maxError=Math.max(maxError,Math.abs(a.x-b.x),Math.abs(a.y-b.y),Math.abs(a.width-b.width),Math.abs(a.height-b.height));
        if(root.querySelector('.sidecar')&&!root.querySelector('.sidecar').hidden){
          const c=root.querySelector('.sidecar').getBoundingClientRect(),d=document.querySelector('#playlist').getBoundingClientRect();
          maxError=Math.max(maxError,Math.abs(c.y-d.y),Math.abs(c.x-d.x));
        }
      };
      for(const offset of [0,21,160,300,900,999999,999999,70,0,-500]){
        viewport.scrollTop=offset;await frame();check();
      }
      for(const end of [false,true]){
        viewport.scrollTop=end?viewport.scrollHeight:0;await frame();
        const before=viewport.scrollTop,documentBefore=document.scrollingElement.scrollTop;
        for(let i=0;i<18;i++){
          const event=new WheelEvent('wheel',{deltaY:end?500:-500,bubbles:true,cancelable:true,composed:true});
          video.dispatchEvent(event);
          if(!event.defaultPrevented)throw new Error('Boundary wheel escaped to YouTube');
          await frame();check();
        }
        if(viewport.scrollTop!==before||document.scrollingElement.scrollTop!==documentBefore)throw new Error('Boundary drift');
      }
      return {maxError,leaks,sameVideo:video===document.querySelector('video')&&parent===video.parentElement,playing:!video.paused,animations:document.getAnimations().length};
    }''')
    assert result['maxError'] < 1, result
    assert result['leaks'] == 0 and result['sameVideo'] and result['playing'], result
    page.locator('.viewport').evaluate('e=>e.scrollTop=0')
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-scroll-bound]')).to_have_count(0)
    assert page.evaluate('document.getAnimations().length') == 0
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(t=>t.stop())')
    page.close()
    print(f'PASS paint alignment and hard boundaries (theater={theater}, playlist={playlist}, fallback={fallback}): {result}', flush=True)


def fullscreen(browser):
    page = fixture(browser, playlist=True)
    previous_scroll=page.locator('.viewport').evaluate('e=>{e.scrollTop=120;return e.scrollTop;}')
    page.evaluate('''() => {
      const player=document.querySelector('#movie_player');
      player.insertAdjacentHTML('beforeend','<button class="ytp-fullerscreen-edu-button">Scroll for details</button><div class="ytp-pause-overlay">Recommendations</div><button class="ytp-show-tiles">Other videos</button><button title="Показать другие видео (v)">V</button><button aria-label="Show other videos (v)">V</button>');
      document.querySelector('#native-fullscreen').onclick=()=>{throw new Error('Slow native fullscreen transition was used');};
      window.__wheelLeaked=0;window.__touchLeaked=0;
      window.addEventListener('wheel',()=>__wheelLeaked++);
      window.addEventListener('touchmove',()=>__touchLeaked++);
      window.__otherVideosKey=0;window.addEventListener('keydown',e=>{if(e.key.toLowerCase()==='v')__otherVideosKey++;});
    }''')
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!!document.fullscreenElement')
    assert page.evaluate('document.fullscreenElement.id') == 'movie_player'
    for node in page.locator('.ytp-fullerscreen-edu-button,.ytp-pause-overlay').all():
        expect(node).to_be_hidden()
    for node in page.locator('.ytp-show-tiles,button[title="Показать другие видео (v)"],button[aria-label="Show other videos (v)"]').all():
        expect(node).to_be_hidden()
    page.keyboard.press('v')
    assert page.evaluate('__otherVideosKey')==0
    result = page.evaluate('''async () => {
      const fs=document.fullscreenElement,video=document.querySelector('video');
      for(let i=0;i<20;i++){
        video.dispatchEvent(new WheelEvent('wheel',{deltaY:600,bubbles:true,cancelable:true}));
        video.dispatchEvent(new TouchEvent('touchmove',{bubbles:true,cancelable:true}));
        fs.scrollTop=800;
        await new Promise(requestAnimationFrame);
      }
      const b=video.getBoundingClientRect();
      return {scroll:fs.scrollTop,wheel:__wheelLeaked,touch:__touchLeaked,box:{x:b.x,y:b.y,width:b.width,height:b.height},playing:!video.paused};
    }''')
    assert result['scroll']==result['wheel']==result['touch']==0, result
    assert result['box']=={'x':0,'y':0,'width':1440,'height':960} and result['playing'], result
    page.locator('#movie_player').evaluate('''e=>e.insertAdjacentHTML('beforeend','<div id="fullscreen-settings" class="ytp-settings-menu" style="position:absolute;right:20px;top:20px;width:150px;height:100px;overflow:auto;background:white"><div style="height:500px">Native settings</div></div>')''')
    page.locator('#fullscreen-settings').hover()
    page.mouse.wheel(0,100)
    page.wait_for_function('document.querySelector("#fullscreen-settings").scrollTop>0')
    assert page.evaluate('document.fullscreenElement.scrollTop')==0
    page.locator('#fullscreen-settings').evaluate('e=>e.remove()')
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    expect(page.locator('#myt-watch')).to_be_visible()
    assert page.locator('.viewport').evaluate('e=>e.scrollTop')==previous_scroll
    assert page.evaluate('''async()=>{
      await new Promise(requestAnimationFrame);
      const root=document.querySelector('#myt-watch').firstChild.shadowRoot;
      return Math.abs(root.querySelector('.media').getBoundingClientRect().y-document.querySelector('video').getBoundingClientRect().y)<1;
    }''')
    assert_stable(page)
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(t=>t.stop())')
    page.close()
    print('PASS direct fullscreen, no details shelf, no wheel/touch/programmatic scrolling; clean exit', flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for fallback in [False,True]:
            for theater in [False,True]:
                for playlist in [False,True]:
                    alignment(browser,theater,playlist,fallback)
        fullscreen_preview(browser)
        fullscreen(browser)
        browser.close()


if __name__=='__main__':
    main()
