"""Page-to-page transitions into and out of the watch page, and back/forward.

YouTube's SPA navigation is simulated step by step: yt-navigate-start, a
data delay with the old page still mounted, the page swap with the history
update, and yt-navigate-finish. Back/forward changes the URL first
(popstate), then swaps the page. Every animation frame is sampled:

* no native YouTube surface may show at the sample points: each point shows
  the old page or the new page as they look when settled;
* the old page's owned elements keep their exact place while it is shown.
"""
import re
from playwright.sync_api import sync_playwright, expect
from smoke import setup, native_watch_fixture, MASTHEAD
from channel import fixture as channel_fixture
from search import fixture as search_fixture
from playlist import body as playlist_body


def element(html, tag):
    match = re.search(rf'<{tag}\b.*</{tag}>', html, re.S)
    assert match, tag
    return match.group(0)


def styles(html):
    return ''.join(re.findall(r'<style>.*?</style>', html, re.S))


WATCH_HTML = native_watch_fixture()
PAGES = {
    'watch': element(WATCH_HTML, 'ytd-watch-flexy'),
    'channel': element(channel_fixture(), 'ytd-browse'),
    'search': element(search_fixture(), 'ytd-search'),
    'home': '<ytd-browse page-subtype="home"><div id="contents">Native home feed</div></ytd-browse>',
    'playlist': element(playlist_body(), 'ytd-browse'),
}
PATHS = {'playlist': '/playlist?list=PLfixture', 'watch': '/watch?v=native', 'channel': '/@creator/videos', 'search': '/results?search_query=music', 'home': '/'}
ALL_STYLES = styles(WATCH_HTML) + styles(channel_fixture()) + styles(search_fixture()) + styles(playlist_body())


def document(start):
    return '<ytd-app>' + MASTHEAD + ALL_STYLES + '<ytd-page-manager class="ytd-app">' + PAGES[start] + '</ytd-page-manager></ytd-app>'


SAMPLER = r"""
window.__probe = () => {
  const points=[[innerWidth/2,180],[innerWidth/2,innerHeight/2],[Math.min(260,innerWidth/4),innerHeight*0.7],[innerWidth-Math.min(260,innerWidth/4),innerHeight*0.7]];
  const owner=node=>{
    let own='',pageRoot='';
    for(let n=node;n;n=n.parentElement||(n.getRootNode() instanceof ShadowRoot?n.getRootNode().host:null)){
      if(!own&&n.hasAttribute?.('data-myt-watch-island'))own='island-'+n.getAttribute('data-myt-watch-island');
      if(!own&&(n.id?.startsWith?.('myt-')||n.hasAttribute?.('data-myt-owned-playlist-card')||n.hasAttribute?.('data-myt-search-channel-card')))own=n.id||'card';
      if(!pageRoot&&n.matches?.('ytd-watch-flexy,ytd-browse,ytd-search'))pageRoot=n.localName+(n.getAttribute('page-subtype')?'['+n.getAttribute('page-subtype')+']':'');
      if(n.matches?.('ytd-masthead'))return 'masthead';
    }
    return own?'own:'+own:pageRoot?'native:'+pageRoot:'blank';
  };
  return points.map(([x,y])=>{
    let hit=document.elementFromPoint(x,y);
    while(hit?.shadowRoot){const inner=hit.shadowRoot.elementFromPoint(x,y);if(!inner||inner===hit)break;hit=inner;}
    return owner(hit);
  });
};
window.__deep = selector => {
  const find=(root)=>{const direct=root.querySelector(selector);if(direct)return direct;for(const host of root.querySelectorAll('*'))if(host.shadowRoot){const inner=find(host.shadowRoot);if(inner)return inner;}return null;};
  return find(document);
};
"""

NAVIGATE = r"""
async ({path, html, mode, delay, keys}) => {
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const manager = document.querySelector('ytd-page-manager');
  const old = [...manager.children].find(node => !node.hidden);
  const rect = selector => { const node = __deep(selector); if (!node || !node.isConnected) return null; const r = node.getBoundingClientRect(); return r.width && r.height ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] : null; };
  const frames = []; let running = true;
  const sample = () => { frames.push({probe: __probe(), rects: keys.map(rect), page: document.documentElement.dataset.mytPage || ''}); if (running) requestAnimationFrame(sample); };
  requestAnimationFrame(sample);
  await new Promise(requestAnimationFrame);
  const swap = () => {
    // YouTube reuses a page element of the destination's kind, or stamps one.
    const template = document.createElement('template'); template.innerHTML = html;
    const fresh = template.content.firstElementChild;
    let next = [...manager.children].find(node => node !== old && node.localName === fresh.localName && node.getAttribute('page-subtype') === fresh.getAttribute('page-subtype'));
    if (!next) { next = fresh; next.hidden = true; manager.append(next); }
    old.hidden = true; next.hidden = false;
  };
  if (mode === 'push') {
    document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail: {url: path}}));
    await wait(delay);
    swap(); history.pushState({}, '', path);
    document.dispatchEvent(new Event('yt-navigate-finish'));
    document.dispatchEvent(new Event('yt-page-data-updated'));
  } else {
    // Back/forward: the URL changes first, YouTube swaps the page afterwards.
    const moved = new Promise(resolve => addEventListener('popstate', resolve, {once: true}));
    mode === 'back' ? history.back() : history.forward(); await moved;
    document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail: {url: location.pathname + location.search}}));
    await wait(delay);
    swap();
    document.dispatchEvent(new Event('yt-navigate-finish'));
    document.dispatchEvent(new Event('yt-page-data-updated'));
  }
  await wait(700); running = false;
  return frames;
}
"""

# Owned elements of each page whose place must hold while the page is shown.
KEYS = {
    'watch': ['#watch-title', '.media'],
    'channel': ['#myt-channel-nav', '#myt-search'],
    'search': ['#myt-search'],
    'home': ['#myt-home'],
    'playlist': ['#myt-playlist-summary'],
}


def settle(page, frames=10):
    page.evaluate('async n=>{for(let i=0;i<n;i++)await new Promise(requestAnimationFrame);}', frames)


def check(page, start, target, mode='push', delay=250):
    page.wait_for_timeout(300); settle(page)
    before = page.evaluate('__probe()')
    old_keys = KEYS[start]
    frames = page.evaluate(NAVIGATE, {'path': PATHS[target], 'html': PAGES[target], 'mode': mode, 'delay': delay, 'keys': old_keys})
    page.wait_for_timeout(300); settle(page)
    after = page.evaluate('__probe()')
    label = f'{start} -> {target} ({mode})'
    assert page.evaluate('document.documentElement.dataset.mytPage') == target, (label, page.evaluate('document.documentElement.dataset.mytPage'))
    assert not any(value.startswith('native:') and 'watch' in value for value in after), (label, after)
    # 1. Every sampled frame shows the old page or the new page, never a
    #    native YouTube surface in between.
    for index, frame in enumerate(frames):
        for point, value in enumerate(frame['probe']):
            assert value in (before[point], after[point]), (label, 'frame', index, 'point', point, value, before[point], after[point], frame['page'])
    # 2. While the old page is still on screen, its owned elements hold still.
    first = frames[0]['rects']
    for index, frame in enumerate(frames):
        if frame['probe'] != before:
            break
        for key, (initial, current) in enumerate(zip(first, frame['rects'])):
            if initial and current:
                assert initial == current, (label, 'old page moved', old_keys[key], 'frame', index, initial, current)
    return before, after


def run(browser, width=1440):
    page = setup(browser, PATHS['channel'], document('channel'), width=width, native_dark=True)
    page.evaluate(SAMPLER)
    expect(page.locator('#myt-channel-nav')).to_be_visible()
    for start, target in [('channel', 'watch'), ('watch', 'channel'), ('channel', 'watch'), ('watch', 'search'), ('search', 'watch'), ('watch', 'home'), ('home', 'watch'), ('watch', 'playlist'), ('playlist', 'watch'), ('watch', 'playlist')]:
        check(page, start, target)
        print(f'PASS {start} -> {target}: no native flash, old page holds still ({width}px)', flush=True)
    # Back and forward between the last pages.
    for mode, start, target in [('back', 'playlist', 'watch'), ('forward', 'watch', 'playlist'), ('back', 'playlist', 'watch'), ('back', 'watch', 'playlist')]:
        check(page, start, target, mode)
        print(f'PASS {mode}: {start} -> {target}: no native flash, old page holds still ({width}px)', flush=True)
    page.close()


def watch_to_watch(browser, width=1440):
    page = setup(browser, PATHS['watch'], document('watch'), width=width, native_dark=True)
    page.evaluate(SAMPLER)
    expect(page.locator('#myt-watch')).to_be_visible()
    page.wait_for_timeout(300); settle(page)
    before = page.evaluate('__probe()')
    # The next video reuses the watch page: the overlay stays on screen.
    frames = page.evaluate(r"""async () => {
      const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
      const frames = []; let running = true;
      const sample = () => { frames.push(__probe()); if (running) requestAnimationFrame(sample); };
      requestAnimationFrame(sample);
      document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail: {url: '/watch?v=second'}}));
      await wait(250);
      history.pushState({}, '', '/watch?v=second');
      document.querySelector('ytd-watch-metadata h1').textContent = 'The second video';
      document.dispatchEvent(new Event('yt-navigate-finish'));
      await wait(500); running = false; return frames;
    }""")
    for index, probe in enumerate(frames):
        assert probe == before, ('watch -> watch', index, probe, before)
    expect(page.locator('#watch-title')).to_have_text('The second video')
    page.close()
    print(f'PASS watch -> watch: the watch page stays on screen ({width}px)', flush=True)


def home_typing(browser):
    # After a video, YouTube's player and hotkeys stay alive on the home page.
    # A space typed into the owned home search is text, not play/pause.
    page = setup(browser, PATHS['watch'], document('watch'), native_dark=True)
    expect(page.locator('#myt-watch')).to_be_visible()
    page.evaluate(r"""() => {
      window.__hotkeys = 0;
      // YouTube-like hotkeys: capture on document, skip only real inputs.
      document.addEventListener('keydown', event => {
        if ([' ', 'k', 'j', 'l', 'ArrowLeft'].includes(event.key) && !/^(INPUT|TEXTAREA)$/.test(event.target.tagName)) { window.__hotkeys++; event.preventDefault(); }
      }, true);
      history.pushState({}, '', '/'); dispatchEvent(new PopStateEvent('popstate'));
    }""")
    field = page.locator('#myt-query')
    expect(field).to_be_visible()
    field.click()
    page.keyboard.type('cats and jokes')
    page.keyboard.press('ArrowLeft')
    expect(field).to_have_value('cats and jokes')
    assert page.evaluate('__hotkeys') == 0, page.evaluate('__hotkeys')
    # Outside owned fields, YouTube's hotkeys keep working.
    page.locator('#myt-home').evaluate("e=>e.dispatchEvent(new KeyboardEvent('keydown',{key:' ',bubbles:true,composed:true}))")
    assert page.evaluate('__hotkeys') == 1
    page.close()
    print('PASS typing into the owned home search never triggers YouTube hotkeys', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in (1440, 390):
            run(browser, width)
            watch_to_watch(browser, width)
        home_typing(browser)
        browser.close()
