"""Own links, searches and channel links open through YouTube's SPA router.

A page that stays on screen until the next route is ready never loads a new
document. Router failures still reach the destination with a document load.
"""
import json
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, setup, native_watch_fixture

ROUTER = """() => {
  window.ytcfg = {data_: {INNERTUBE_CONTEXT: {client: {clientName: 'WEB', clientVersion: '2.20260101'}}, INNERTUBE_API_KEY: 'fixture'}};
  window.__navigations = [];
  // A minimal stand-in for YouTube's router: accept the command and start.
  document.querySelector('ytd-app').addEventListener('yt-navigate', event => {
    const endpoint = event.detail.endpoint;
    __navigations.push(JSON.parse(JSON.stringify(endpoint)));
    document.dispatchEvent(new CustomEvent('yt-navigate-start', {detail: {url: endpoint.commandMetadata.webCommandMetadata.url}}));
  });
}"""


def prepare(browser, path, body, resolve=None, **options):
    page = setup(browser, path, body, **options)
    page.documents = []
    page.on('request', lambda request: request.resource_type == 'document' and page.documents.append(request.url))
    page.resolved = []

    def resolver(route):
        page.resolved.append(json.loads(route.request.post_data))
        if resolve is None:
            route.fulfill(status=500, body='{}')
        else:
            route.fulfill(content_type='application/json', body=json.dumps(resolve))
    page.route('https://www.youtube.com/youtubei/v1/navigation/resolve_url**', resolver)
    page.add_script_tag(path=str(ROOT / 'src/content/navigation-main.js'))
    page.add_script_tag(path=str(ROOT / 'src/content/navigation.js'))
    page.evaluate(ROUTER)
    return page


CHANNEL = {'endpoint': {'clickTrackingParams': 'ct', 'commandMetadata': {'webCommandMetadata': {
    'url': '/@creator/videos', 'webPageType': 'WEB_PAGE_TYPE_CHANNEL', 'rootVe': 3611, 'apiUrl': '/youtubei/v1/browse'}},
    'browseEndpoint': {'browseId': 'UC' + 'a' * 22, 'params': 'EgZ2aWRlb3PyBgQKAjoA', 'canonicalBaseUrl': '/@creator'}}}


def channel_links(browser):
    body = '<ytd-app><ytd-page-manager><ytd-search><a id="native-channel" href="/@creator">Creator</a></ytd-search></ytd-page-manager></ytd-app>'
    page = prepare(browser, '/results?search_query=creator', body, resolve=CHANNEL)
    start = len(page.documents)
    page.evaluate("document.querySelector('#native-channel').click()")
    page.wait_for_function('__navigations.length === 1')
    endpoint = page.evaluate('__navigations[0]')
    # The channel home is routed straight to Videos: no second document load.
    assert endpoint['browseEndpoint']['browseId'] == 'UC' + 'a' * 22, endpoint
    assert endpoint['commandMetadata']['webCommandMetadata']['url'] == '/@creator/videos', endpoint
    assert page.resolved[0]['url'] == 'https://www.youtube.com/@creator/videos', page.resolved
    page.wait_for_timeout(300)
    assert len(page.documents) == start, page.documents
    # Modified clicks keep the browser's own behavior.
    assert page.evaluate("""() => {
      const event = new MouseEvent('click', {bubbles: true, cancelable: true, ctrlKey: true});
      const anchor = document.querySelector('#native-channel');
      anchor.addEventListener('click', e => e.preventDefault(), {once: true});
      anchor.dispatchEvent(event);
      return __navigations.length;
    }""") == 1
    page.close()
    print('PASS channel links open Videos through the SPA router without a document load', flush=True)


def router_failure(browser):
    body = '<ytd-app><ytd-page-manager><ytd-search><a id="native-channel" href="/@creator">Creator</a></ytd-search></ytd-page-manager></ytd-app>'
    page = prepare(browser, '/results?search_query=creator', body, resolve=None)
    page.evaluate("document.querySelector('#native-channel').click()")
    page.wait_for_url('**/@creator/videos')
    assert page.evaluate('window.__navigations === undefined'), 'A failed resolution must load the document'
    page.close()
    print('PASS a failed route resolution falls back to a regular document load', flush=True)


def home_search(browser):
    page = prepare(browser, '/', '<ytd-app><ytd-page-manager></ytd-page-manager></ytd-app>')
    start = len(page.documents)
    page.locator('#myt-query').fill('  cats & dogs  ')
    page.locator('#myt-query').press('Enter')
    page.wait_for_function('__navigations.length === 1')
    endpoint = page.evaluate('__navigations[0]')
    assert endpoint['searchEndpoint'] == {'query': 'cats & dogs'}, endpoint
    assert endpoint['commandMetadata']['webCommandMetadata']['url'] == '/results?search_query=cats+%26+dogs', endpoint
    # The home stays on screen until YouTube's router replaces it.
    expect(page.locator('#myt-home')).to_be_visible()
    page.wait_for_timeout(300)
    assert len(page.documents) == start and not page.resolved, (page.documents, page.resolved)
    page.close()
    print('PASS home search keeps the page and opens results through the router', flush=True)


def watch_search(browser):
    page = prepare(browser, '/watch?v=abcdefghijk', native_watch_fixture())
    expect(page.locator('#myt-watch')).to_be_visible()
    start = len(page.documents)
    page.locator('#watch-search').fill('next video')
    page.locator('#watch-search').press('Enter')
    page.wait_for_function('__navigations.length === 1')
    assert page.evaluate('__navigations[0].searchEndpoint.query') == 'next video'
    page.wait_for_timeout(300)
    assert len(page.documents) == start, page.documents
    page.close()
    print('PASS watch header search opens results through the router', flush=True)


def own_links(browser):
    page = prepare(browser, '/', '<ytd-app><ytd-page-manager></ytd-page-manager></ytd-app>')
    # An own link without a native counterpart: watch endpoint built locally.
    page.evaluate("""() => {
      const host = document.createElement('div'); host.id = 'myt-fixture-card';
      host.attachShadow({mode: 'open'}).innerHTML = '<a id="own" href="/watch?v=abcdefghijk&list=PLx&index=3&t=1m5s">Own</a><a id="external" href="https://example.com/">External</a>';
      document.body.append(host);
    }""")
    page.evaluate("document.querySelector('#myt-fixture-card').shadowRoot.querySelector('#own').click()")
    page.wait_for_function('__navigations.length === 1')
    endpoint = page.evaluate('__navigations[0]')
    assert endpoint['watchEndpoint'] == {'videoId': 'abcdefghijk', 'playlistId': 'PLx', 'index': 2, 'startTimeSeconds': 65}, endpoint
    # External links and a disabled extension are never routed.
    page.evaluate("document.querySelector('#myt-fixture-card').shadowRoot.querySelector('#external').addEventListener('click', e => e.preventDefault())")
    page.evaluate("document.querySelector('#myt-fixture-card').shadowRoot.querySelector('#external').click()")
    page.evaluate('__setEnabled(false)')
    page.evaluate("""() => {
      const a = document.createElement('a'); a.id = 'plain-channel'; a.href = '/@creator';
      a.addEventListener('click', e => { window.__nativeHandled = e.defaultPrevented === false; e.preventDefault(); });
      document.body.append(a);
    }""")
    page.evaluate("document.querySelector('#plain-channel').click()")
    assert page.evaluate('__navigations.length') == 1 and page.evaluate('window.__nativeHandled') is True
    page.close()
    print('PASS own links route locally; external links and disabled state stay native', flush=True)


def native_links(browser):
    body = ('<ytd-app><ytd-page-manager><ytd-browse>'
            '<a id="unhandled" href="/watch?v=abcdefghijk">Unhandled</a>'
            '<a id="handled" href="/watch?v=bbbbbbbbbbb">Handled</a>'
            '<a id="account" href="/account">Account</a>'
            '</ytd-browse></ytd-page-manager></ytd-app>')
    page = prepare(browser, '/feed/trending', body)
    start = len(page.documents)
    # YouTube handles this one itself: the router must not run twice.
    page.evaluate("document.querySelector('#handled').addEventListener('click', e => e.preventDefault())")
    page.evaluate("document.querySelector('#handled').click()")
    page.evaluate("document.querySelector('#account').addEventListener('click', e => { window.__accountDefault = !e.defaultPrevented; e.preventDefault(); })")
    page.evaluate("document.querySelector('#account').click()")
    assert page.evaluate('__navigations.length') == 0
    # A forwarded synthetic click that no native handler accepted would load
    # a new document; it opens through the router instead.
    page.evaluate("document.querySelector('#unhandled').click()")
    page.wait_for_function('__navigations.length === 1')
    assert page.evaluate('__navigations[0].watchEndpoint.videoId') == 'abcdefghijk'
    page.wait_for_timeout(300)
    assert len(page.documents) == start, page.documents
    page.close()
    print('PASS unhandled native links open through the router; handled and other links stay native', flush=True)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        channel_links(browser)
        router_failure(browser)
        home_search(browser)
        watch_search(browser)
        own_links(browser)
        native_links(browser)
        browser.close()
