"""Scrolling continues over the player's progress bar.

Live: on a watch page, with the pointer over the red progress bar at the
bottom of the video, the wheel stopped scrolling the page. The wheel over the
native player is forwarded to the owned page, except over controls that use
the wheel themselves; that list held [role="slider"], and YouTube's progress
bar (.ytp-progress-bar) is a slider. YouTube never seeks by wheel, so over
the progress bar the page now keeps scrolling; the volume slider keeps the
wheel.
"""
from playwright.sync_api import sync_playwright
from smoke import setup, native_watch_fixture

CONTROLS = '''e => {
  const bar = document.createElement('div'); bar.className = 'ytp-progress-bar-container';
  bar.style.cssText = 'position:absolute;left:12px;right:12px;bottom:48px;height:16px;z-index:5';
  bar.innerHTML = '<div class="ytp-progress-bar" role="slider" aria-label="Seek slider" style="position:absolute;inset:0;background:red"><div class="ytp-progress-list" style="height:100%"></div></div>';
  const volume = document.createElement('span'); volume.className = 'ytp-volume-area';
  volume.style.cssText = 'position:absolute;left:12px;bottom:8px;width:120px;height:30px;z-index:5';
  volume.innerHTML = '<div class="ytp-volume-panel" role="slider" aria-label="Volume" style="width:100%;height:100%;background:white"></div>';
  e.append(bar, volume);
}'''


def scrolled(page):
    return page.locator('#myt-watch .viewport').evaluate('e => e.scrollTop')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in [1440, 900]:
            page = setup(browser, '/watch?v=native', native_watch_fixture(), width=width)
            page.wait_for_selector('[data-myt-watch-island="media"]', state='attached')
            page.locator('#movie_player').evaluate(CONTROLS)
            # Over the progress bar: the wheel scrolls the owned page.
            page.locator('.ytp-progress-list').hover()
            page.mouse.wheel(0, 240)
            page.wait_for_function("document.querySelector('#myt-watch').firstElementChild.shadowRoot.querySelector('.viewport').scrollTop > 0", timeout=3000)
            assert page.evaluate('document.scrollingElement.scrollTop') == 0
            # Over the volume slider the wheel stays with the player.
            page.wait_for_timeout(800)
            page.locator('.ytp-volume-panel').hover()
            before = scrolled(page)
            page.mouse.wheel(0, 240)
            page.wait_for_timeout(600)
            assert scrolled(page) == before, (before, scrolled(page))
            page.close()
            print(f'PASS the page scrolls over the progress bar; the volume slider keeps the wheel: {width}px', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
