"""The fullscreen progress bar spans the screen.

Live (Chrome, the F key on a watch page): YouTube's own fullscreen is on
<html> and the window kept its size (1048x872 in and out), so no resize
event followed the transition. The player then stayed in
ytp-xsmall-width-mode/ytp-tiny-mode, with an inline width of 100px on its
control bar and chapter segment, on a 1048px wide player: a progress bar of
about 10% of the screen. While fullscreen, a player YouTube believes tiny or
a bar much narrower than the player is now measured again.

The fixture's player behaves like that: it lays the bar out on window
resize, and after entering fullscreen it applies a stale tiny measurement.
"""
from playwright.sync_api import sync_playwright
from smoke import setup, native_watch_fixture

PLAYER = '''() => {
  const player = document.querySelector('#movie_player');
  const bar = document.createElement('div'); bar.className = 'ytp-chrome-bottom';
  bar.style.cssText = 'position:absolute;left:12px;bottom:0;height:48px;z-index:2';
  bar.innerHTML = '<div class="ytp-progress-bar-container"><div class="ytp-progress-bar" role="slider"><div class="ytp-chapters-container"><div class="ytp-chapter-hover-container" style="height:4px;background:red"></div></div></div></div>';
  player.append(bar);
  const chapter = bar.querySelector('.ytp-chapter-hover-container');
  const layout = () => {
    const width = Math.max(0, player.getBoundingClientRect().width - 24);
    player.classList.toggle('ytp-tiny-mode', width < 300); player.classList.toggle('ytp-xsmall-width-mode', width < 300);
    bar.style.width = width + 'px'; chapter.style.width = width + 'px';
  };
  layout();
  window.addEventListener('resize', layout);
  // YouTube's own fullscreen: on <html>, and a stale tiny measurement after it.
  const button = document.createElement('button'); button.id = 'youtube-fullscreen'; button.textContent = 'YouTube fullscreen';
  button.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647';
  button.onclick = () => document.documentElement.requestFullscreen();
  document.body.append(button);
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) return;
    setTimeout(() => {
      player.classList.add('ytp-tiny-mode', 'ytp-xsmall-width-mode');
      bar.style.width = '100px'; chapter.style.width = '100px';
    }, 200);
  });
}'''


def ratio(page):
    return page.evaluate("() => document.querySelector('.ytp-chapter-hover-container').getBoundingClientRect().width / document.querySelector('#movie_player').getBoundingClientRect().width")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = setup(browser, '/watch?v=native', native_watch_fixture())
        page.wait_for_selector('[data-myt-watch-island="media"]', state='attached')
        page.evaluate(PLAYER)
        for attempt in range(3):
            page.evaluate("document.querySelector('#youtube-fullscreen').click()")
            page.wait_for_function("document.fullscreenElement === document.documentElement")
            page.wait_for_timeout(2000)
            value = ratio(page)
            tiny = page.evaluate("document.querySelector('#movie_player').classList.contains('ytp-tiny-mode')")
            assert value > .9 and not tiny, (attempt, value, tiny)
            page.evaluate('document.exitFullscreen()')
            page.wait_for_function('!document.fullscreenElement')
            page.wait_for_timeout(300)
        page.close()
        browser.close()
        print('PASS fullscreen progress bar spans the player after YouTube\'s own fullscreen, three times', flush=True)


if __name__ == '__main__':
    main()
