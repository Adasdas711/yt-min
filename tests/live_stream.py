"""Live streams: the channel card shows a Live badge with the current audience,
and constant live-only churn (like counters, chat frames) never rebuilds the
owned watch UI.

Run: python tests/live_stream.py
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, native_watch_fixture

CHURN = '''()=>{
  const flexy=document.querySelector('ytd-watch-flexy'),buttons=document.querySelector('#top-level-buttons-computed');
  buttons.insertAdjacentHTML('afterbegin','<segmented-like-dislike-button-view-model><like-button-view-model><button aria-label="like 1"><span class=n>1</span></button></like-button-view-model></segmented-like-dislike-button-view-model>');
  flexy.insertAdjacentHTML('beforeend','<div id=chat><ytd-live-chat-frame><iframe id=chatframe src="https://www.youtube.com/live_chat?v=x"></iframe></ytd-live-chat-frame></div>');
  let n=0;window.__churn=setInterval(()=>{
    n++;const like=buttons.querySelector('like-button-view-model button');like.setAttribute('aria-label','like '+n);like.querySelector('.n').textContent=n;
    const frame=document.querySelector('#chatframe');if(frame.getAttribute('src')==='about:blank')frame.setAttribute('src','https://www.youtube.com/live_chat?v=x&n='+n);
    frame.closest('ytd-live-chat-frame').toggleAttribute('collapsed');
  },50);
}'''


def check_live(browser, width):
    page = setup(browser, '/watch?v=native', native_watch_fixture(), native_dark=True, width=width)
    page.evaluate('''()=>{
      document.querySelector('#info-container').textContent='1,234 watching now Started streaming 2 hours ago';
      document.querySelector('#movie_player').classList.add('ytp-live');
      window.__syncs=0;const sync=MinimalYouTubeWatch.prototype.sync;
      MinimalYouTubeWatch.prototype.sync=function(...args){window.__syncs++;return sync.apply(this,args);};
      document.dispatchEvent(new Event('yt-navigate-finish'));
    }''')
    expect(page.locator('#myt-watch .stats-value')).to_have_text('1,234 watching')
    expect(page.locator('#myt-watch .live-badge')).to_be_visible()
    expect(page.locator('#myt-watch .views-icon')).to_be_hidden()
    page.wait_for_timeout(300)
    page.evaluate(CHURN)
    page.wait_for_timeout(400)
    before = page.evaluate('window.__syncs')
    page.wait_for_timeout(2000)
    after = page.evaluate('window.__syncs')
    assert after - before <= 1, f'live churn rebuilt the watch UI {after - before} times'
    assert page.evaluate("document.querySelector('#chatframe').getAttribute('src')") == 'about:blank'
    page.locator('#info-container').evaluate("e=>e.textContent='1,301 watching now'")
    expect(page.locator('#myt-watch .stats-value')).to_have_text('1,301 watching')
    page.evaluate('clearInterval(window.__churn)')
    page.close()
    print(f'PASS live badge, audience and churn without rebuilds: {width}px ({after - before} syncs)')


def check_recorded(browser):
    page = setup(browser, '/watch?v=native', native_watch_fixture(), native_dark=True)
    page.evaluate("document.dispatchEvent(new Event('yt-navigate-finish'))")
    expect(page.locator('#myt-watch .stats-value')).to_have_text('906.35k')
    expect(page.locator('#myt-watch .live-badge')).to_be_hidden()
    page.close()
    print('PASS recorded video keeps views without a Live badge')


def check_russian(browser):
    page = setup(browser, '/watch?v=native', native_watch_fixture(), native_dark=True, language='ru')
    page.evaluate('''()=>{
      document.querySelector('#info-container').textContent='Сейчас смотрят: 1 232';
      document.querySelector('#movie_player').classList.add('ytp-live');
      document.dispatchEvent(new Event('yt-navigate-finish'));
    }''')
    expect(page.locator('#myt-watch .stats-value')).to_have_text('1,232 watching')
    page.close()
    print('PASS the audience is always English')


if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in (1440, 390):
            check_live(browser, width)
        check_recorded(browser)
        check_russian(browser)
        browser.close()
