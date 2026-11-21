"""An ad that still shows (server-stitched ads of streams) plays muted and
unseen; the viewer's own sound setting returns when it ends.

Run: python tests/live_ads.py
"""
from playwright.sync_api import sync_playwright
from smoke import setup, native_watch_fixture

PLAYER_API = """() => {
  const player=document.querySelector('#movie_player');window.__muted=false;window.__calls=[];
  player.isMuted=()=>window.__muted;
  player.mute=()=>{window.__calls.push('mute');window.__muted=true;};
  player.unMute=()=>{window.__calls.push('unMute');window.__muted=false;};
}"""


def check(browser):
    page = setup(browser, '/watch?v=live-ad', native_watch_fixture())
    page.evaluate(PLAYER_API)
    player = page.locator('#movie_player')
    video = page.locator('#movie_player video')
    opacity = lambda: video.evaluate('e=>getComputedStyle(e).opacity')
    assert opacity() == '1'
    player.evaluate("e=>e.classList.add('ad-showing')")
    page.wait_for_function('window.__muted===true')
    assert opacity() == '0', opacity()
    player.evaluate("e=>e.classList.remove('ad-showing')")
    page.wait_for_function('window.__muted===false')
    assert opacity() == '1'
    assert page.evaluate('window.__calls') == ['mute', 'unMute'], page.evaluate('window.__calls')
    # A viewer who had muted the player keeps it muted after the ad.
    page.evaluate('window.__muted=true;window.__calls=[]')
    player.evaluate("e=>e.classList.add('ad-interrupting')")
    page.wait_for_timeout(100)
    player.evaluate("e=>e.classList.remove('ad-interrupting')")
    page.wait_for_timeout(100)
    assert page.evaluate('window.__muted') is True and page.evaluate('window.__calls') == [], page.evaluate('window.__calls')
    # Turning the extension off mid-ad gives the sound back.
    page.evaluate('window.__muted=false;window.__calls=[]')
    player.evaluate("e=>e.classList.add('ad-showing')")
    page.wait_for_function('window.__muted===true')
    page.evaluate('__setEnabled(false)')
    page.wait_for_function('window.__muted===false')
    page.close()
    print('PASS an ad that shows plays muted and hidden; the viewer sound setting returns', flush=True)


if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        check(browser)
        browser.close()
