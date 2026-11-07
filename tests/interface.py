"""Startup, playlist state and scroll regressions on local Chromium fixtures."""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import (ROOT, setup, setup_at_document_start, native_watch_fixture,
                   playlist_panel_fixture, VIDEO_STREAM, assert_stable, MOCK)
from urllib.parse import urlparse, parse_qs


def native_language(browser):
    for enabled in [True, False]:
        page = browser.new_page()
        page.add_init_script(script=f'({MOCK})({json.dumps({"enabled":enabled})});\n' +
            (ROOT/'src/content/watch.js').read_text() + '\n' + (ROOT/'src/content/content.js').read_text())
        requests = []
        def route(request):
            requests.append(request.request.url)
            language = 'en' if 'hl=en' in request.request.url else 'ru'
            request.fulfill(content_type='text/html', body=f'<!doctype html><html lang="{language}"><head></head><body></body></html>')
        page.route('https://www.youtube.com/**', route)
        page.goto('https://www.youtube.com/watch?v=native&list=PLfixture&t=42#fragment')
        if enabled:
            page.wait_for_url('**hl=en#fragment')
            query = parse_qs(urlparse(page.url).query)
            assert query == {'v':['native'],'list':['PLfixture'],'t':['42'],'hl':['en']}, query
            assert len(requests) == 2, requests
        else:
            assert len(requests) == 1 and 'hl=' not in page.url, requests
        page.close()


def startup(browser):
    home = setup_at_document_start(browser, '/', defer_settings=True)
    expect(home.locator('#myt-home')).to_be_visible()
    expect(home.locator('#myt-query')).to_have_attribute('placeholder', 'Search YouTube')
    home.evaluate('__resolveSettings()')
    expect(home.locator('#myt-home')).to_be_visible()
    assert not home.errors, home.errors
    home.close()
    page = setup_at_document_start(browser, '/watch?v=native', defer_settings=True)
    expect(page.locator('#myt-watch')).to_be_visible()
    expect(page.locator('.media')).to_have_attribute('aria-busy', 'true')
    expect(page.locator('.details')).to_be_hidden()
    expect(page.locator('#watch-search')).to_have_attribute('placeholder', 'Search YouTube')
    # Native DOM can arrive before storage or video metadata. The same own
    # shell covers each stage before the next paint; native video stays native.
    page.evaluate('''html => {
      document.querySelector('ytd-app').remove();
      document.body.insertAdjacentHTML('beforeend',html);
      window.__sourceVideo=document.querySelector('video');
      window.__metadata=document.querySelector('ytd-watch-metadata');
      __metadata.remove();
    }''', native_watch_fixture())
    expect(page.locator('.media')).to_have_attribute('aria-busy', 'true')
    expect(page.locator('ytd-watch-flexy')).to_have_css('visibility', 'hidden')
    page.evaluate('document.querySelector("#below").append(__metadata)')
    expect(page.locator('.details')).to_be_visible()
    expect(page.locator('.media')).to_have_attribute('aria-busy', 'false')
    assert page.evaluate('document.querySelector("video")===__sourceVideo')
    expect(page.locator('.views-icon')).to_be_visible()
    expect(page.locator('.views-icon svg')).to_have_attribute('aria-hidden', 'true')
    expect(page.locator('.stats')).to_have_text('906.35k')
    page.evaluate('__resolveSettings()')
    expect(page.locator('#myt-watch')).to_be_visible()
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#myt-watch')).to_have_count(0)
    expect(page.locator('ytd-watch-flexy')).not_to_have_css('visibility', 'hidden')
    assert not page.errors, page.errors
    page.close()


def playlist(browser, label='Close playlist', known_id=True, wrapped=False):
    body = native_watch_fixture().replace('<div id="secondary-inner"></div>',
        '<div id="secondary-inner">' + playlist_panel_fixture() + '</div>')
    page = setup(browser, '/watch?v=native&list=fixture', body, watch_ui=False)
    page.evaluate('''config => {
      const panel=document.querySelector('#playlist'),header=panel.querySelector('#header');
      header.innerHTML='<span>Playlist</span><button id="expand-button" aria-label="Expand playlist" hidden>⌄</button><button data-native-close>×</button><button id="shuffle" aria-label="Shuffle playlist">Shuffle</button>';
      window.__expandCalls=0;window.__closeCalls=0;window.__shuffleCalls=0;
      const expand=header.querySelector('#expand-button'),close=header.querySelector('[data-native-close]');
      if(config.known_id)close.id='close-button';
      if(config.wrapped){
        const wrapper=document.createElement('ytd-button-renderer');wrapper.setAttribute('aria-label',config.label);
        close.replaceWith(wrapper);wrapper.innerHTML='<yt-button-shape></yt-button-shape>';wrapper.firstChild.append(close);
      }else close.setAttribute('aria-label',config.label);
      expand.onclick=()=>{__expandCalls++;expand.hidden=true;close.hidden=false;panel.removeAttribute('collapsed');panel.querySelector('#items').hidden=false;};
      close.onclick=()=>{__closeCalls++;panel.setAttribute('collapsed','');expand.hidden=false;close.hidden=true;panel.querySelector('#items').hidden=true;};
      header.querySelector('#shuffle').onclick=()=>__shuffleCalls++;
    }''', {'label':label,'known_id':known_id,'wrapped':wrapped})
    page.add_script_tag(path=str(ROOT/'src/content/watch.js'))
    page.evaluate("document.dispatchEvent(new Event('yt-navigate-finish'))")
    page.evaluate(VIDEO_STREAM)
    expect(page.locator('.sidecar')).to_be_visible()
    # A stale hidden down-arrow must never collapse a fully expanded native list.
    assert page.evaluate('__expandCalls') == 0
    expect(page.locator('#playlist .myt-playlist-close')).to_be_visible()
    expect(page.locator('[data-native-close]')).to_have_css('visibility', 'hidden')
    assert page.locator('[data-native-close],.myt-playlist-close').evaluate_all('''nodes=>nodes.filter(e=>getComputedStyle(e).visibility==='visible'&&e.getClientRects().length).length''') == 1
    page.locator('#shuffle').click()
    assert page.evaluate('__shuffleCalls') == 1
    for _ in range(3):
        page.locator('#playlist .myt-playlist-close').click()
        expect(page.locator('.sidecar')).to_be_hidden()
        page.locator('.playlist-toggle').click()
        expect(page.locator('.sidecar')).to_be_visible()
        expect(page.locator('#playlist .myt-playlist-close')).to_be_visible()
        expect(page.locator('#expand-button')).to_be_hidden()
        expect(page.locator('#playlist #items')).to_be_visible()
        assert_stable(page)
    assert page.evaluate('__expandCalls===3&&__closeCalls===3')
    assert page.evaluate('document.querySelector("video")===__nativeVideo&&!__nativeVideo.paused')
    # Replacing native header controls should mask the new toggle before paint
    # and preserve the injected close action and the native shuffle action.
    page.locator('[data-native-close]').evaluate('e=>e.replaceWith(e.cloneNode(true))')
    expect(page.locator('[data-native-close]')).to_have_css('visibility', 'hidden')
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('.myt-playlist-close,[data-myt-playlist-native-toggle],[data-myt-playlist-owned-header]')).to_have_count(0)
    expect(page.locator('[data-native-close]')).not_to_have_css('visibility', 'hidden')
    assert not page.locator('#playlist').evaluate('e=>e.style.transform||e.style.clipPath')
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(t=>t.stop())')
    page.close()


def scroll_profile(browser):
    body = native_watch_fixture().replace('<div id="secondary-inner"></div>',
        '<div id="secondary-inner">' + playlist_panel_fixture() + '</div>')
    page = setup(browser, '/watch?v=native&list=fixture', body)
    page.evaluate(VIDEO_STREAM)
    page.wait_for_timeout(150)
    result = page.evaluate('''async () => {
      const calls={};
      for(const key of ['sync','renderDescription','layoutTitle']){
        const original=MinimalYouTubeWatch.prototype[key];
        MinimalYouTubeWatch.prototype[key]=function(...args){calls[key]=(calls[key]||0)+1;return original.apply(this,args);};
      }
      const root=document.querySelector('#myt-watch').firstElementChild.shadowRoot;
      const prose=root.querySelector('.prose a'),eye=root.querySelector('.views-icon');
      const panel=document.querySelector('#playlist'),items=panel.querySelector('#items'),view=root.querySelector('.viewport');
      const rows=[...items.children],costs=[];
      for(let i=0;i<90;i++){
        // Real list scroll plus virtualized row/counter updates between frames.
        items.scrollTop=(i*18)%1500;
        for(let j=0;j<rows.length;j++){
          rows[j].style.transform=`translateY(${i%3}px)`;
          rows[j].setAttribute('aria-label','Row '+j+' update '+i);
          rows[j].querySelector('a').firstChild.textContent='Video '+j+' update '+i;
        }
        const start=performance.now();
        document.querySelector('video').dispatchEvent(new WheelEvent('wheel',{deltaY:i%2?45:-45,bubbles:true,cancelable:true,composed:true}));
        costs.push(performance.now()-start);
        await new Promise(requestAnimationFrame);
      }
      await new Promise(requestAnimationFrame);
      costs.sort((a,b)=>a-b);
      return {calls,scrollP95:costs[Math.floor(costs.length*.95)],scrollMax:costs.at(-1),
        sameProse:prose===root.querySelector('.prose a'),sameEye:eye===root.querySelector('.views-icon'),
        nativeVideo:document.querySelector('video')===__nativeVideo,playing:!__nativeVideo.paused,
        independentScroll:items.scrollTop>0,mainScroll:view.scrollTop};
    }''')
    assert not result['calls'].get('sync') and not result['calls'].get('renderDescription'), result
    assert result['calls'].get('layoutTitle', 0) <= 1, result
    assert all(result[key] for key in ['sameProse','sameEye','nativeVideo','playing','independentScroll']), result
    assert result['scrollP95'] < 100, result
    print('Playlist virtualization/scroll profile:', json.dumps(result), flush=True)
    page.evaluate('clearInterval(__frames);__stream.getTracks().forEach(t=>t.stop())')
    page.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        startup(browser)
        print('PASS own loading shell before storage and native metadata; eye icon; native restore', flush=True)
        native_language(browser)
        print('PASS native menus use English at startup; disabled mode and video/playlist/time parameters stay intact', flush=True)
        for label,known_id,wrapped in [('Close playlist',True,False),('Close',False,False),('Закрыть',False,True)]:
            playlist(browser,label,known_id,wrapped)
            print(f'PASS one playlist close control ({label}, wrapped={wrapped}); direct reopen and native restore', flush=True)
        scroll_profile(browser)
        browser.close()


if __name__ == '__main__':
    main()
