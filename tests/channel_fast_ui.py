"""Early channel paint, visible active sections and a single empty state."""
import json
from playwright.sync_api import sync_playwright,expect
from smoke import ROOT,MOCK,document,setup
from channel_header import fixture


def boot(browser,enabled=True,standalone=False):
    page=browser.new_page(viewport={'width':1440,'height':960})
    html=document(fixture()).replace('</head>','<style>'+(ROOT/'src/styles/styles.css').read_text()+'</style></head>')
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html',body=html))
    page.add_init_script('''window.__paint=[];const sample=()=>{
      const browse=document.querySelector('ytd-browse');
      if(browse)__paint.push({visible:getComputedStyle(browse).visibility!=='hidden',owned:!!document.querySelector('#myt-search'),nav:!!document.querySelector('#myt-channel-nav'),boot:document.documentElement.hasAttribute('data-myt-channel-boot')});
      if(__paint.length<90)requestAnimationFrame(sample);
    };requestAnimationFrame(sample);''')
    manifest=json.loads((ROOT/'manifest.json').read_text())
    isolated='('+MOCK+')('+json.dumps({'enabled':enabled})+');chrome.runtime.id="early-channel";\n'
    isolated+='chrome.storage.local.get=(keys,callback)=>setTimeout(()=>callback(__stored),350);\n'
    modules=['src/content/channel-boot.js'] if standalone else manifest['content_scripts'][1]['js']
    isolated+='\n'.join((ROOT/path).read_text() for path in modules)
    session=page.context.new_cdp_session(page);session.send('Page.enable')
    session.send('Page.addScriptToEvaluateOnNewDocument',{'source':isolated,'worldName':'early-channel'})
    page.goto('https://www.youtube.com/@JoeSpeen/videos')
    if standalone:
        expect(page.locator('ytd-browse')).to_have_css('visibility','hidden')
        expect(page.locator('ytd-browse')).to_have_css('visibility','visible',timeout=3000)
    elif enabled:
        expect(page.locator('#myt-search .media')).to_have_count(2)
        expect(page.locator('html')).not_to_have_attribute('data-myt-channel-boot','')
        expect(page.locator('ytd-browse')).to_have_css('visibility','visible')
        page.wait_for_timeout(80)
        samples=page.evaluate('__paint')
        assert any(item['boot'] for item in samples),samples
        assert all(not item['visible'] or item['owned'] and item['nav'] for item in samples),samples
    else:
        expect(page.locator('html')).not_to_have_class('minimal-youtube')
        expect(page.locator('ytd-browse')).to_have_css('visibility','visible')
        expect(page.locator('#myt-search')).to_have_count(0)
    page.close()
    print(f'PASS document-start channel paint guard, delayed settings and bounded recovery: enabled={enabled}, standalone={standalone}',flush=True)


def active_and_empty(browser,width):
    body=fixture(contents='').replace('</ytd-browse>','<section class="new-empty-feed"><ytd-message-renderer>No results found.</ytd-message-renderer></section></ytd-browse>')
    page=setup(browser,'/@JoeSpeen/search?query=missing',body,width=width,native_dark=True)
    own=page.locator('#myt-search')
    expect(own.locator('.empty')).to_be_visible()
    expect(page.locator('ytd-message-renderer')).to_be_hidden()
    assert page.get_by_text('No results found.',exact=True).evaluate_all('nodes=>nodes.filter(node=>node.getClientRects().length&&getComputedStyle(node).visibility!=="hidden"&&getComputedStyle(node).display!=="none").length')==1
    # A channel search is not a section: no section link is current.
    expect(page.locator('#myt-channel-nav').locator('nav a[aria-current]')).to_have_count(0)
    # The empty search message is one large centered line, without a heading.
    expect(own.locator('.results-heading')).to_be_hidden()
    box=own.locator('.empty').bounding_box();assert float(own.locator('.empty').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)'))>=28
    assert abs(box['x']+box['width']/2-page.evaluate('document.querySelector("#myt-search").getBoundingClientRect().left+document.querySelector("#myt-search").getBoundingClientRect().width/2'))<=2,box
    section=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=True)
    nav=section.locator('#myt-channel-nav');active=nav.get_by_role('link',name='Videos',exact=True);inactive=nav.get_by_role('link',name='Playlists',exact=True)
    expect(active).to_have_attribute('aria-current','page')
    assert active.evaluate('e=>getComputedStyle(e).backgroundColor')!=inactive.evaluate('e=>getComputedStyle(e).backgroundColor')
    assert int(active.evaluate('e=>getComputedStyle(e).fontWeight'))>=700
    assert active.evaluate('e=>getComputedStyle(e).boxShadow')=='none'
    assert active.evaluate('e=>getComputedStyle(e).borderBottomColor')=='rgba(0, 0, 0, 0)'
    section.close()
    nav=page.locator('#myt-channel-nav')
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('')
    expect(own.locator('.empty')).to_be_hidden();expect(page.locator('ytd-message-renderer')).to_be_hidden()
    assert page.get_by_text('No results found.',exact=True).evaluate_all('nodes=>nodes.filter(node=>node.getClientRects().length&&getComputedStyle(node).visibility!=="hidden"&&getComputedStyle(node).display!=="none").length')==0
    page.evaluate('__setEnabled(false)')
    expect(page.locator('ytd-message-renderer')).to_be_visible()
    expect(page.locator('[data-myt-channel-ready]')).to_have_count(0)
    page.close()
    print(f'PASS distinct active section, sibling empty feed, one no-results message, empty-input silence and native restoration: {width}px',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        boot(browser);boot(browser,False);boot(browser,standalone=True)
        for width in (1440,390):active_and_empty(browser,width)
        browser.close()
