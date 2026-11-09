"""Channel search labels, empty queries and leaving cached search feeds."""
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from smoke import setup as local_setup, assert_stable
from channel_header import fixture, startup
from channel_navigation import setup, finish
from search import video, playlist


def wait_section(page,section):
    page.wait_for_url(lambda url:urlparse(str(url)).path.rstrip('/').endswith('/'+section))


def search(page,nav,pending,query='cookie'):
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel')
    field.fill(query);field.press('Enter')
    expect(nav).to_have_attribute('aria-busy','true')
    assert finish(pending)=='search'
    page.wait_for_url('**/search?**')
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 24'])
    return field


def labels_and_sections(browser,width):
    context,page,nav,documents,requests,pending,errors=setup(browser,width)
    root=page.locator('#myt-search')
    for title,section,expected in [('Videos','videos','Regular video 20'),('Playlists','playlists','Playlist 22')]:
        search(page,nav,pending)
        expect(root.get_by_role('heading',name='Результаты поиска',exact=True)).to_be_visible()
        if section=='videos':
            Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
            page.screenshot(path=f'/tmp/yt-min-qa/channel-query-label-{width}.png')
        count=len(requests);nav.get_by_role('link',name=title,exact=True).click()
        wait_section(page,section)
        assert len(requests)==count and not pending
        expect(root.locator('.media-title')).to_have_text([expected])
        expect(root.locator('.media-channel')).to_be_visible()
        expect(root.get_by_role('heading',name='Результаты поиска',exact=True)).to_be_hidden()
        expect(root.locator('.empty')).to_be_hidden()
        expect(nav.get_by_role('link',name=title,exact=True)).to_have_attribute('aria-current','page')
    assert len(documents)==3 and not errors,(documents,errors)
    context.close()
    print(f'PASS search heading and Videos/Playlists after search: {width}px',flush=True)


def empty_queries(browser,width):
    context,page,nav,documents,requests,pending,errors=setup(browser,width)
    field=nav.get_by_role('searchbox',name='Search this channel')
    for title,section in [('Live','streams'),('Playlists','playlists'),('Posts','posts')]:
        nav.get_by_role('link',name=title,exact=True).click();wait_section(page,section)
        count=len(documents)
        nav.get_by_role('button',name='Search',exact=True).click();field.press('Enter')
        expect(field).to_be_visible();expect(field).to_have_value('')
        page.wait_for_timeout(50)
        assert len(documents)==count and not requests and not pending
        assert urlparse(page.url).path.endswith('/'+section)
    field.fill('cookie');field.press('Enter');finish(pending);page.wait_for_url('**/search?**')
    host=page.locator('#myt-search')
    expect(host.locator('.results-heading')).to_be_visible()
    expect(host.locator('.media-channel')).to_be_hidden()
    assert host.locator('.media-channel').text_content()==''
    count=len(documents);request_count=len(requests);query_url=page.url
    for value in ('','   '):
        field.fill(value);field.press('Enter')
        expect(host.locator('.stream')).to_be_hidden()
        expect(host.locator('.results-heading')).to_be_hidden()
        expect(host.locator('.empty')).to_be_hidden()
        assert page.url==query_url and len(documents)==count and len(requests)==request_count
    field.fill('another query');field.press('Enter');finish(pending);page.wait_for_url('**query=another+query')
    expect(host.locator('.stream')).to_be_visible();expect(host.locator('.results-heading')).to_be_visible()
    expect(host.locator('.media-channel')).to_be_hidden()
    # A late response after clearing the input must remain invisible.
    field.fill('still loading');field.press('Enter');field.fill('')
    expect(host.locator('.stream')).to_be_hidden()
    finish(pending);page.wait_for_url('**query=still+loading')
    expect(host.locator('.stream')).to_be_hidden();expect(host.locator('.results-heading')).to_be_hidden()
    expect(host.locator('.empty')).to_be_hidden();expect(field).to_have_value('')
    page.evaluate('''()=>{
        const tabs=document.querySelector('yt-tab-group-shape');window.__savedTabs=tabs.innerHTML;tabs.replaceChildren();
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''')
    expect(host.locator('.stream')).to_be_hidden();expect(host.locator('.empty')).to_be_hidden()
    page.evaluate('''()=>{
        document.querySelector('yt-tab-group-shape').innerHTML=__savedTabs;
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''')
    expect(field).to_be_visible();expect(field).to_have_value('');expect(host.locator('.stream')).to_be_hidden()
    assert len(documents)==count and not errors,(documents,errors)
    context.close()
    print(f'PASS empty input submits nothing, clearing and late replies show no results, and channel search cards omit owners: {width}px',flush=True)


def cached_search(browser,section):
    page=local_setup(browser,'/@JoeSpeen/search?query=cache',fixture(),native_dark=True)
    host=page.locator('#myt-search');expect(host.locator('.media')).to_have_count(2)
    page.add_style_tag(content='.cached-channel-feed{display:none}')
    page.evaluate('window.__originalGrid=document.querySelector("#myt-search")')
    html=playlist(501,count=13) if section=='playlists' else video(501)
    page.evaluate('''({section,html})=>{
        const browse=document.querySelector('ytd-browse'),old=browse.querySelector(':scope > #contents');
        old.querySelectorAll('a[href]').forEach(link=>link.removeAttribute('href'));
        old.classList.add('cached-channel-feed');
        const next=document.createElement('section');next.id='incoming-feed';next.innerHTML=html;browse.append(next);
        history.pushState({},'', '/@JoeSpeen/'+section);
        document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
    }''',{'section':section,'html':html})
    expected='Playlist 501' if section=='playlists' else 'Regular video 501'
    expect(host.locator('.media-title')).to_have_text([expected])
    expect(host.locator('.empty')).to_be_hidden()
    expect(page.locator('ytd-browse > #contents')).to_be_hidden()
    expect(page.locator('ytd-browse > #contents [data-myt-search-native-root],ytd-browse > #contents [data-myt-search-layout-path]')).to_have_count(0)
    assert page.evaluate('document.querySelector("#myt-search")===__originalGrid')
    page.wait_for_timeout(100);assert_stable(page);page.close()
    print(f'PASS leaving a CSS-hidden cached search shell with cleared links for {section}',flush=True)


def empty_search_loading(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser)
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('missing');field.press('Enter')
    pending.pop().fulfill(content_type='application/json',body='{"html":"<ytd-message-renderer>No results found</ytd-message-renderer>"}')
    page.wait_for_url('**/search?**');expect(page.locator('#myt-search .empty')).to_be_visible()
    nav.get_by_role('link',name='Videos',exact=True).click()
    wait_section(page,'videos')
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 20'])
    expect(page.locator('#myt-search .empty')).to_be_hidden()
    assert len(documents)==2 and not pending and not errors,(documents,errors)
    context.close()
    print('PASS genuine zero search results do not flash as an error while loading Videos',flush=True)


def blank_urls(browser):
    for path in ('/@JoeSpeen/search','/@JoeSpeen/search?query=','/@JoeSpeen/search?query=%20%20','/channel/UCfixture/search?query='):
        page,requests=startup(browser,path)
        expect(page.locator('#myt-search .stream')).to_be_hidden()
        expect(page.locator('#myt-search .results-heading')).to_be_hidden()
        expect(page.locator('#myt-search .empty')).to_be_hidden()
        assert urlparse(page.url).path.endswith('/search') and len(requests)<=2 and all(urlparse(url).path.endswith('/search') for url in requests),(page.url,requests)
        page.close()
    print('PASS blank search URLs display no results and never redirect to Videos',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for section in ('videos','playlists'):cached_search(browser,section)
        for width in (1440,390):
            labels_and_sections(browser,width);empty_queries(browser,width)
        empty_search_loading(browser);blank_urls(browser)
        browser.close()
