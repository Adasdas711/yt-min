"""The popup copies a diagnostic report of the open YouTube tab.

The report replaces the console scripts used to diagnose live issues: page
state, owned UI state, long frames, network groups and dormant parts. It
holds page structure and timing only, never cookies or account data.
"""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import MASTHEAD, setup, ROOT
from page_data import CONFIG, ITEM

CHROME = '''(tabURL) => {
  window.__copied = null; window.__injected = null;
  window.chrome = {
    runtime: { lastError: null, getManifest: () => ({ version: '1.0.0' }) },
    storage: { local: { get: (keys, cb) => cb({ enabled: true }), set: (v, cb) => cb && cb() }, onChanged: { addListener() {} } },
    tabs: { query: async () => [{ id: 7, url: tabURL }] },
    scripting: { executeScript: async details => { window.__injected = { tabId: details.target.tabId, world: details.world }; return [{ result: details.func() }]; } },
  };
  Object.defineProperty(navigator, 'clipboard', { value: { writeText: async text => { window.__copied = text; } } });
}'''


def popup(browser, tab_url):
    page = browser.new_page()
    page.add_init_script(script='(' + CHROME + ')(' + json.dumps(tab_url) + ')')
    page.goto((ROOT / 'src/popup/popup.html').as_uri())
    return page


def check_popup(browser):
    page = popup(browser, 'https://www.youtube.com/watch?v=abc')
    page.get_by_role('button', name='Copy diagnostic report').click()
    expect(page.locator('#diagnostics-status')).to_have_text('Copied. Paste it into the chat.')
    report = json.loads(page.evaluate('__copied'))
    assert report['version'] == '1.0.0' and report['enabled'] is True and report['report'] == 'minimal-youtube-diagnostics', report
    assert page.evaluate('__injected') == {'tabId': 7, 'world': 'MAIN'}
    text = json.dumps(report).lower()
    assert 'cookie' not in text and 'sapisid' not in text
    page.close()
    page = popup(browser, 'https://example.com/')
    page.get_by_role('button', name='Copy diagnostic report').click()
    expect(page.locator('#diagnostics-status')).to_have_text('Open a YouTube tab first.')
    assert page.evaluate('__copied') is None
    page.close()
    print('PASS popup copies a report of the YouTube tab, and only of a YouTube tab', flush=True)


def check_report(browser):
    body = ('<ytd-app>' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">'
            '</div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>')
    page = setup(browser, '/results?search_query=cats', body)
    page.evaluate(CONFIG + ITEM + """
document.querySelector('ytd-search').data={contents:{twoColumnSearchResultsRenderer:{primaryContents:{sectionListRenderer:{contents:[
  {itemSectionRenderer:{contents:[item('dataVideo01','Data one'),item('dataVideo02','Data two')]}}]}}}}};
document.dispatchEvent(new Event('yt-page-data-updated'));""")
    expect(page.locator('#myt-search .media')).to_have_count(2)
    page.add_script_tag(path=str(ROOT / 'src/popup/diagnostics.js'))
    report = page.evaluate('minimalYouTubeDiagnostics()')
    assert report['url'] == '/results?search_query=cats', report['url']
    assert report['extension']['active'] and report['extension']['page'] == 'search', report['extension']
    assert report['model'] == {'type': 'search', 'items': 2, 'more': False, 'loading': False, 'chips': 0}, report['model']
    assert report['search']['cards'] == 2 and report['search']['.skeleton'] == 'hidden', report['search']
    assert report['dom']['nodes'] > 0 and isinstance(report['longFrames']['scripts'], list)
    json.dumps(report)
    page.close()
    print('PASS the report describes page, model, owned UI, DOM and timing', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        check_popup(browser)
        check_report(browser)
        browser.close()


if __name__ == '__main__':
    main()
