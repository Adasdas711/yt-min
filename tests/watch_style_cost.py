"""DOM insertions on the watch page never restyle the whole document.

Live (Chrome 157, a watch page with ~10,700 nodes while YouTube builds it):
any DOM insertion or text change, in the player, in comments or in body,
cost ~64 ms of style and layout with the extension and ~40 ms without it.
The cause was html:has(:fullscreen) and html:has(:fullscreen) body: a :has()
on the root with a descendant argument is re-checked on every insertion and
restyles everything below body. During the first 20-30 seconds YouTube
inserts thousands of nodes, so scrolling stuttered. Fullscreen styles now key
on a document mark set by watch.js.
"""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from smoke import setup, native_watch_fixture

ROOT = Path(__file__).resolve().parents[1]
MEASURE = '''() => {
  const time = document.querySelector('#myt-probe-time'), runs = [];
  document.body.offsetHeight;
  for (let i = 0; i < 40; i++) { time.textContent = '0:' + i; const a = performance.now(); document.body.offsetHeight; runs.push(performance.now() - a); }
  runs.sort((a, b) => a - b); return runs[20];
}'''


def static_check():
    css = (ROOT / 'src/styles/styles.css').read_text()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    bad = []
    for selector in re.findall(r'([^{}]+)\{', css):
        for part in selector.split(','):
            # A :has() on the root, body or app whose argument is not limited
            # to direct children is re-checked for every insertion in the page.
            for match in re.finditer(r'(?:^|[\s>])(?:html|body|ytd-app)(?:[.#\[:][^\s>]*)?:has\(\s*([^)]*)\)', part.strip()):
                if not match.group(1).startswith('>'):
                    bad.append(part.strip())
    assert not bad, bad
    print('PASS no document-wide :has() selectors', flush=True)


def dynamic_check(browser):
    filler = '<div id="myt-probe-filler">' + ''.join('<div class="probe"><span>a</span><span>b</span><p>c</p></div>' for _ in range(2500)) + '</div>'
    body = native_watch_fixture().replace('</ytd-watch-flexy>', filler + '</ytd-watch-flexy>', 1)
    page = setup(browser, '/watch?v=native', body)
    page.evaluate('''() => { const player = document.querySelector('#movie_player') || document.querySelector('ytd-player') || document.body;
      const time = document.createElement('span'); time.id = 'myt-probe-time'; time.textContent = '0:00'; player.append(time); }''')
    assert page.evaluate('document.documentElement.hasAttribute("data-myt-watch-ui")')
    assert page.evaluate('document.getElementsByTagName("*").length') > 10000
    # Both runs in one task: the extension restores its class between tasks.
    with_css, without_css = page.evaluate('() => { const measure = (' + MEASURE + '), root = document.documentElement;'
                                          ' const a = measure(); root.classList.remove("minimal-youtube"); const b = measure(); root.classList.add("minimal-youtube"); return [a, b]; }')
    page.close()
    assert with_css <= max(2 * without_css, without_css + 2), (with_css, without_css)
    print(f'PASS a player text change restyles locally: {with_css:.1f} ms with the extension, {without_css:.1f} ms without', flush=True)


def main():
    static_check()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        dynamic_check(browser)
        browser.close()


if __name__ == '__main__':
    main()
