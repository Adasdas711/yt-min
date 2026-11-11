"""Watch responsiveness and long-session regressions on local Chromium fixtures.

Run: python tests/performance.py --soak-seconds 610
The video is a real canvas MediaStream; YouTube counters/hidden cards are local
fixtures. Heap figures are post-GC JavaScript heap, not total browser/Arc RAM.
"""
import argparse
import json
import time
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, setup, native_watch_fixture, VIDEO_STREAM


def fixture(browser):
    page = setup(browser, '/watch?v=native', native_watch_fixture(),
                 native_dark=True, watch_ui=False)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.evaluate('''() => {
      const below=document.querySelector('#below');
      for(let i=0;i<150;i++)below.insertAdjacentHTML('beforeend',`<ytd-macro-markers-list-item-renderer><button><span id=time>${i}:00</span><h3 id=title>Chapter ${i}: stories behind the music</h3></button></ytd-macro-markers-list-item-renderer>`);
      document.querySelector('#attributed-description-text').innerHTML=Array.from({length:100},(_,i)=>`<p>Paragraph ${i}: a longer video description with <a href="https://example.com/${i}">a source link</a>.</p>`).join('');
      const related=document.createElement('div');related.id='related';related.innerHTML=Array.from({length:1000},(_,i)=>`<ytd-compact-video-renderer><span class=hidden-counter>${i}</span><a href="/watch?v=related${i}">Hidden suggestion</a></ytd-compact-video-renderer>`).join('');document.querySelector('#secondary-inner').append(related);
      chrome.runtime.getURL=path=>'https://www.youtube.com/__performance_fonts__/'+path.split('/').pop();
    }''')
    page.route('https://www.youtube.com/__performance_fonts__/*', lambda route:
               route.fulfill(body=(ROOT/'src/assets/fonts'/route.request.url.rsplit('/',1)[-1]).read_bytes(), content_type='font/ttf'))
    page.add_script_tag(path=str(ROOT/'src/content/watch.js'))
    page.evaluate('''() => {
      window.__perf={};
      for(const name of ['sync','syncStats','position','layoutTitle','renderDescription','updateCurrentChapter']){
        const original=MinimalYouTubeWatch.prototype[name];
        MinimalYouTubeWatch.prototype[name]=function(...args){
          window.__view=this;const start=performance.now();
          try{return original.apply(this,args);}finally{
            const item=window.__perf[name]||={calls:0,ms:0,max:0};
            const elapsed=performance.now()-start;item.calls++;item.ms+=elapsed;item.max=Math.max(item.max,elapsed);
          }
        };
      }
      document.dispatchEvent(new Event('yt-navigate-finish'));
    }''')
    expect(page.locator('.chapter')).to_have_count(150)
    page.wait_for_function("[...document.fonts].some(f=>f.family.includes('Barlow')&&f.status==='loaded')")
    page.evaluate(VIDEO_STREAM)
    page.wait_for_timeout(150)
    return page, errors


def noise_check(page):
    # A native rerender with identical text must refresh source references and
    # keep statistics; counter-only changes afterward must preserve the own UI.
    page.locator('#description').evaluate('''e=>{
      const next=e.cloneNode(true);next.querySelector('a').onclick=()=>{window.__freshDescriptionLink=true;return false;};e.replaceWith(next);
    }''')
    expect(page.locator('#myt-watch .stats')).to_have_text('906.35k')
    page.locator('.prose a').first.click()
    assert page.evaluate('window.__freshDescriptionLink===true')
    page.evaluate('__view.viewport.scrollTop=0;__view.position()')
    page.locator('.more-toggle').click()
    result = page.evaluate('''async () => {
      const root=__view.shadow,chapter=root.querySelector('.chapter'),link=root.querySelector('.prose a');
      const related=document.querySelector('#related .hidden-counter'),info=document.querySelector('#info-container');
      const image=document.createElement('img');related.append(image);
      window.__perf={};
      let adChecks=0;const original=MinimalYouTubeAds.prototype.showing;
      MinimalYouTubeAds.prototype.showing=function(){adChecks++;return original.call(this);};
      const clock=document.querySelector('#clock');
      for(let i=0;i<90;i++){
        related.firstChild.textContent=String(i);
        info.textContent=(906359+i)+' views · Mar 8, 2025';
        clock.style.width=i+'px';clock.textContent=String(i);
        image.dispatchEvent(new Event('load'));
        await new Promise(requestAnimationFrame);
      }
      await new Promise(requestAnimationFrame);
      MinimalYouTubeAds.prototype.showing=original;
      return {methods:__perf,adChecks,sameChapter:chapter===root.querySelector('.chapter'),sameProse:link===root.querySelector('.prose a'),menuOpen:root.querySelector('.more-popup').matches(':popover-open'),stats:root.querySelector('.stats').textContent};
    }''')
    assert result['sameChapter'] and result['sameProse'] and result['menuOpen'], result
    assert result['methods'].get('renderDescription', {}).get('calls', 0) == 0, result
    assert result['methods'].get('sync', {}).get('calls', 0) == 0, result
    assert result['methods']['syncStats']['calls'] > 10 and result['adChecks'] == 0, result
    assert result['stats'] == '906.44k · 8 March 2025', result
    page.locator('.more-toggle').click()
    print('Counter/hidden-surface profile:', json.dumps(result), flush=True)


def resize_check(page):
    page.evaluate('''() => {
      __perf={};window.__nativeResizes=0;
      document.querySelector('ytd-watch-flexy').addEventListener('minimal-youtube:player-resize',()=>__nativeResizes++);
    }''')
    # Native events and ResizeObserver deliveries, including real layout changes.
    for width in range(1400, 700, -35):
        page.set_viewport_size({'width': width, 'height': 960})
    page.set_viewport_size({'width': 1440, 'height': 960})
    page.wait_for_timeout(250)
    before = page.evaluate('({methods:__perf,nativeResizes:__nativeResizes})')
    page.wait_for_timeout(180)
    after = page.evaluate('({methods:__perf,nativeResizes:__nativeResizes})')
    for name in ['position','layoutTitle']:
        assert before['methods'].get(name)==after['methods'].get(name), ('Resize feedback continues after window settles', before, after)
    assert before['nativeResizes']==after['nativeResizes'], (before,after)
    assert before['methods'].get('layoutTitle', {}).get('calls', 0) < 10, before
    assert 0 < before['nativeResizes'] < 25, before
    assert page.locator('video').bounding_box() == page.locator('.media').bounding_box()
    print('Resize burst:', json.dumps(before), flush=True)


def response_check(page):
    page.evaluate('__view.viewport.scrollTop=0;__view.position()')
    # Measure synchronous handler cost; compare alignment at the following paint.
    scroll = page.evaluate('''async () => {
      const video=document.querySelector('video'),before=video.getBoundingClientRect().y;
      video.dispatchEvent(new PointerEvent('pointerover',{bubbles:true,composed:true}));
      const start=performance.now();
      video.dispatchEvent(new WheelEvent('wheel',{deltaY:150,bubbles:true,cancelable:true,composed:true}));
      const elapsed=performance.now()-start;
      // A wheel notch animates to its target like native wheel scrolling.
      const until=performance.now()+2000;while(performance.now()<until&&__view.viewport.scrollTop<150)await new Promise(requestAnimationFrame);
      await new Promise(requestAnimationFrame);return {ms:elapsed,moved:before-video.getBoundingClientRect().y,scroll:__view.viewport.scrollTop};
    }''')
    assert scroll['moved'] >= 149 and scroll['scroll'] >= 150, scroll
    page.evaluate('__view.viewport.scrollTop=0;__view.position()')
    page.evaluate('''() => {
      if(!window.__measuredFullscreen){
        window.__measuredFullscreen=true;
        const prepare=MinimalYouTubeWatch.prototype.prepareFullscreen;
        MinimalYouTubeWatch.prototype.prepareFullscreen=function(...args){window.__fullscreenStart=performance.now();return prepare.apply(this,args);};
      }
      window.__fullscreenMs=null;
      document.addEventListener('fullscreenchange',()=>{if(document.fullscreenElement)__fullscreenMs=performance.now()-__fullscreenStart;},{once:true});
    }''')
    page.locator('#native-fullscreen').click()
    page.wait_for_function('document.fullscreenElement && __fullscreenMs!==null')
    fullscreen = page.evaluate('__fullscreenMs')
    assert page.evaluate('document.querySelector("video")===__nativeVideo && document.querySelector("video").readyState>=2')
    assert page.locator('video').bounding_box() == {'x':0,'y':0,'width':1440,'height':960}
    page.locator('#native-fullscreen').click()
    page.wait_for_function('!document.fullscreenElement')
    # Conservative thresholds catch seconds-long freezes while tolerating shared CI.
    assert scroll['ms'] < 150 and fullscreen < 500, (scroll, fullscreen)
    return {'scroll_ms': round(scroll['ms'], 2), 'fullscreen_ms': round(fullscreen, 2)}


def soak(page, seconds):
    session = page.context.new_cdp_session(page)
    session.send('Performance.enable')
    def snapshot():
        session.send('HeapProfiler.collectGarbage')
        metrics = {item['name']:item['value'] for item in session.send('Performance.getMetrics')['metrics']}
        return {key: metrics[key] for key in ['JSHeapUsedSize','Nodes','JSEventListeners','LayoutCount','LayoutDuration','TaskDuration']}
    page.evaluate('''() => {
      window.__perf={};window.__ticks=0;
      const related=document.querySelector('#related .hidden-counter'),info=document.querySelector('#info-container'),clock=document.querySelector('#clock');
      window.__stress=setInterval(()=>{
        const i=++window.__ticks;related.firstChild.textContent=String(i);
        info.textContent=(906359+i)+' views · Mar 8, 2025';clock.textContent=String(i);clock.style.width=(i%100)+'px';
      },50);
    }''')
    baseline = snapshot()
    started = time.monotonic()
    while time.monotonic()-started < seconds:
        remaining = seconds-(time.monotonic()-started)
        page.wait_for_timeout(min(30, remaining)*1000)
        print('Soak:', json.dumps({'seconds':round(time.monotonic()-started),'ticks':page.evaluate('__ticks'),**snapshot()}), flush=True)
    page.evaluate('clearInterval(__stress)')
    final = snapshot()
    methods = page.evaluate('__perf')
    assert methods.get('renderDescription', {}).get('calls', 0) == 0, methods
    assert methods.get('sync', {}).get('calls', 0) == 0, methods
    assert final['JSEventListeners'] <= baseline['JSEventListeners']+2, (baseline, final)
    assert final['Nodes'] <= baseline['Nodes']+25, (baseline, final)
    assert final['JSHeapUsedSize'] < baseline['JSHeapUsedSize']+1_000_000, (baseline, final)
    result = {'seconds':round(time.monotonic()-started), 'baseline':baseline,'final':final,'response':response_check(page),'methods':methods}
    print('Long-session result:', json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--soak-seconds',type=float,default=6)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page,errors=fixture(browser)
        noise_check(page)
        resize_check(page)
        print('Initial response:',json.dumps(response_check(page)),flush=True)
        # Flush native fullscreen attributes before measuring the stable session.
        page.wait_for_timeout(200)
        soak(page,args.soak_seconds)
        # Relevant source changes must continue to update the actual UI.
        page.locator('ytd-watch-metadata h1').evaluate("e=>e.textContent='Updated after a long session'")
        expect(page.locator('#watch-title')).to_have_text('Updated after a long session')
        page.evaluate('__setEnabled(false)')
        expect(page.locator('#myt-watch')).to_have_count(0)
        page.evaluate('__setEnabled(true)')
        expect(page.locator('#myt-watch')).to_have_count(1)
        assert not errors, errors
        page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(track=>track.stop())')
        page.close();browser.close()
    print('PASS watch responsiveness and long-session checks',flush=True)


if __name__=='__main__':
    main()
