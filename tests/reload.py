"""Page reloads reuse the tab's last known settings before async storage replies."""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, document

MODULES = ['src/content/channel-boot.js', 'src/content/watch.js', 'src/content/playlist.js',
           'src/content/search.js', 'src/content/channel.js', 'src/content/content.js']


def open_page(browser, path, stored):
    page = browser.new_page(viewport={'width': 1440, 'height': 960})
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    # Every document load gets fresh mock storage whose reply waits for the test.
    script = f'({MOCK})({json.dumps(stored)});\n'
    script += 'chrome.storage.local.get=(keys,cb)=>{window.__resolveSettings=()=>cb(window.__stored);};\n'
    script += '\n'.join((ROOT / name).read_text() for name in MODULES)
    page.add_init_script(script=script)
    probe = ("<script>window.__early={enabled:document.documentElement.classList.contains('minimal-youtube'),"
             "theme:document.documentElement.dataset.mytTheme||null,"
             "boot:document.documentElement.hasAttribute('data-myt-channel-boot')};</script>")
    html = document('<ytd-app><ytd-page-manager><p id="native">Native app</p></ytd-page-manager></ytd-app>')
    html = html.replace('</head>', f"<style>{(ROOT / 'src/styles/styles.css').read_text()}</style>{probe}</head>")
    page.route('https://www.youtube.com/**', lambda route: route.fulfill(content_type='text/html', body=html))
    page.goto('https://www.youtube.com' + path)
    return page


def enabled_reload(browser):
    page = open_page(browser, '/watch?v=reload', {'enabled': True, 'theme': 'dark'})
    # The first load has no snapshot: the provisional default waits for storage.
    assert page.evaluate('__early') == {'enabled': True, 'theme': 'light', 'boot': False}, page.evaluate('__early')
    page.evaluate('__resolveSettings()')
    expect(page.locator('html')).to_have_attribute('data-myt-theme', 'dark')
    page.reload()
    early = page.evaluate('__early')
    assert early == {'enabled': True, 'theme': 'dark', 'boot': False}, early
    # The owned watch shell and saved theme exist before storage answers.
    expect(page.locator('#myt-watch')).to_be_visible()
    expect(page.locator('html')).to_have_attribute('data-myt-theme', 'dark')
    page.evaluate('__resolveSettings()')
    expect(page.locator('html')).to_have_attribute('data-myt-theme', 'dark')
    # A setting changed in this tab is the next reload's starting point.
    page.evaluate("chrome.storage.local.set({theme:'light'})")
    page.reload()
    assert page.evaluate('__early')['theme'] == 'light', page.evaluate('__early')
    assert not page.errors, page.errors
    page.close()
    print('PASS reload applies the saved theme and watch shell before storage replies', flush=True)


def disabled_reload(browser):
    page = open_page(browser, '/@creator/videos', {'enabled': False})
    page.evaluate('__resolveSettings()')
    expect(page.locator('html.minimal-youtube')).to_have_count(0)
    page.reload()
    early = page.evaluate('__early')
    assert early == {'enabled': False, 'theme': None, 'boot': False}, early
    expect(page).to_have_title('(12) YouTube')
    page.evaluate('__resolveSettings()')
    expect(page.locator('html.minimal-youtube')).to_have_count(0)
    # Storage stays authoritative: enabling elsewhere wins over the snapshot.
    page.evaluate('__setEnabled(true)')
    expect(page.locator('html.minimal-youtube')).to_have_count(1)
    page.reload()
    assert page.evaluate('__early')['enabled'], page.evaluate('__early')
    assert not page.errors, page.errors
    page.close()
    print('PASS disabled reload never flashes provisional styling or hides channels', flush=True)


def stale_snapshot(browser):
    page = open_page(browser, '/watch?v=stale', {'enabled': True})
    page.evaluate('__resolveSettings()')
    page.evaluate("sessionStorage.setItem('minimal-youtube:settings', JSON.stringify({enabled:true,theme:'dark'}))")
    page.reload()
    assert page.evaluate('__early')['theme'] == 'dark'
    # The stored reply (no saved theme, disabled) replaces the stale snapshot.
    page.evaluate("Object.assign(__stored,{enabled:false}); __resolveSettings()")
    expect(page.locator('html.minimal-youtube')).to_have_count(0)
    expect(page.locator('#myt-watch')).to_have_count(0)
    assert json.loads(page.evaluate("sessionStorage.getItem('minimal-youtube:settings')")) == {'enabled': False, 'theme': None}
    page.evaluate("sessionStorage.setItem('minimal-youtube:settings','{broken')")
    page.reload()
    assert page.evaluate('__early')['enabled'] and not page.errors, page.errors
    page.close()
    print('PASS stale or corrupt snapshots are corrected by storage without errors', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
        enabled_reload(browser)
        disabled_reload(browser)
        stale_snapshot(browser)
        browser.close()
