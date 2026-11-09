"""Channel search uses the Videos grid for nested/cached native result layouts."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable
from channel_header import fixture
from search import video


def geometry(page):
    return page.locator('#myt-search').evaluate('''host=>{
        const card=host.shadowRoot.querySelector('.media'),cover=card.querySelector('.cover'),title=card.querySelector('.media-title'),row=card.parentElement;
        const style=getComputedStyle(card),heading=getComputedStyle(title),box=cover.getBoundingClientRect();
        return {width:card.getBoundingClientRect().width,display:style.display,direction:style.flexDirection,padding:style.padding,border:style.borderRadius,background:style.backgroundColor,title:heading.fontSize,ratio:box.width/box.height,columns:getComputedStyle(row).gridTemplateColumns.split(' ').length};
    }''')


def check(browser,width,cached,primary=True):
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=True)
    expect(page.locator('#myt-search .media')).to_have_count(2)
    before=geometry(page)
    page.evaluate('window.__grid=document.querySelector("#myt-search");window.__documentToken=crypto.randomUUID()')
    token=page.evaluate('__documentToken')
    inactive=''.join('<div '+state+'>'+video(index)+'<ytd-continuation-item-renderer class="cached-continuation"></ytd-continuation-item-renderer></div>' for index,state in enumerate(('hidden','aria-hidden="true"','style="display:none"'),301))
    rows=inactive+video(201)+video(202)+'<ytd-continuation-item-renderer id="search-continuation"></ytd-continuation-item-renderer>'
    markup='<ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents" class="search-items">'+rows+'</div></ytd-item-section-renderer></div></ytd-section-list-renderer>'
    if primary:markup='<ytd-two-column-browse-results-renderer><div id="primary">'+markup+'</div></ytd-two-column-browse-results-renderer>'
    page.evaluate('''({markup,cached})=>{
        const browse=document.querySelector('ytd-browse'),old=browse.querySelector(':scope > #contents');
        if(cached){old.hidden=true;old.setAttribute('aria-hidden','true');}else old.remove();
        const shell=document.createElement('div');shell.id='channel-search-shell';shell.innerHTML=markup;browse.append(shell);
        history.pushState({},'', '/@JoeSpeen/search?query=test');
        document.dispatchEvent(new Event('yt-page-data-updated'));
        document.dispatchEvent(new Event('yt-navigate-finish'));
    }''',{'markup':markup,'cached':cached})
    host=page.locator('#myt-search')
    expect(host).to_be_visible()
    expect(host.locator('.media-title')).to_have_text(['Regular video 201','Regular video 202'])
    after=geometry(page)
    for key in ('display','direction','padding','border','background','title','columns'):assert after[key]==before[key],(key,before,after)
    assert abs(after['width']-before['width'])<1,(before,after)
    assert abs(after['ratio']-16/9)<.01,after
    expect(page.locator('#myt-channel-nav').get_by_role('link',name='Videos',exact=True)).to_have_attribute('aria-current','page')
    expect(page.get_by_role('searchbox',name='Search this channel')).to_have_value('test')
    expect(page.locator('#video-201')).to_be_hidden()
    expect(page.locator('#video-202')).to_be_hidden()
    expect(page.locator('.cached-continuation[data-myt-search-layout-path]')).to_have_count(0)
    if cached:
        expect(page.locator('ytd-browse > #contents [data-myt-search-native-root],ytd-browse > #contents [data-myt-search-layout-path]')).to_have_count(0)
    assert page.evaluate('document.querySelector("#myt-search")===__grid')
    assert page.evaluate('__documentToken')==token
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # Native continuation stays in its parent and new cards use the same grid.
    page.locator('#search-continuation').evaluate('e=>{window.__continuation=e;window.__continuationParent=e.parentElement}')
    page.locator('#search-continuation').evaluate('(e,html)=>e.insertAdjacentHTML("beforebegin",html)',video(203))
    expect(host.locator('.media-title')).to_have_text(['Regular video 201','Regular video 202','Regular video 203'])
    assert page.evaluate('document.querySelector("#search-continuation")===__continuation&&__continuation.parentElement===__continuationParent')
    expect(page.locator('#search-continuation')).to_be_visible()
    assert page.locator('#search-continuation').evaluate('e=>e.getBoundingClientRect().top>=document.querySelector("#myt-search").getBoundingClientRect().bottom-1')
    if cached:
        page.evaluate('''()=>{
            const root=document.querySelector('ytd-browse > #contents');root.hidden=false;root.setAttribute('aria-hidden','false');
            document.querySelector('#channel-search-shell').remove();history.pushState({},'', '/@JoeSpeen/videos');
            document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
        }''')
        expect(host.locator('.media')).to_have_count(2)
        expect(host.locator('.media-title').first).to_have_text('Regular video 1')
        assert page.evaluate('document.querySelector("#myt-search")===__grid')
    else:
        page.locator('.search-items').evaluate('e=>e.querySelectorAll("ytd-video-renderer").forEach(card=>card.remove())')
        expect(host.locator('.media')).to_have_count(0)
        expect(host.locator('.empty')).to_be_visible()
    page.wait_for_timeout(100);assert_stable(page)
    Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
    if cached:
        page.evaluate('''markup=>{
            const browse=document.querySelector('ytd-browse');browse.querySelector(':scope > #contents').hidden=true;
            const shell=document.createElement('div');shell.id='channel-search-shell';shell.innerHTML=markup;browse.append(shell);
            history.pushState({},'', '/@JoeSpeen/search?query=test');document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
        }''',markup)
        expect(host.locator('.media-title')).to_have_text(['Regular video 201','Regular video 202'])
        page.screenshot(path=f'/tmp/yt-min-qa/channel-query-grid-{width}.png')
    page.evaluate('__setEnabled(false)')
    expect(host).to_have_count(0)
    expect(page.locator('[data-myt-channel-results]')).to_have_count(0)
    expect(page.locator('[data-myt-search-native-root],[data-myt-search-layout-path]')).to_have_count(0)
    page.close()
    print(f'PASS nested channel-search Videos grid, cached-feed exclusion, pagination, empty/back and restoration: {width}px, cache={cached}, primary={primary}',flush=True)


def direct_search(browser,width):
    body=fixture().replace('<div id="contents"><ytd-feed-filter-chip-bar-renderer>','<ytd-two-column-browse-results-renderer><div id="primary"><div id="contents"><ytd-feed-filter-chip-bar-renderer>').replace('</ytd-browse>','</div></ytd-two-column-browse-results-renderer></ytd-browse>')
    page=setup(browser,'/@JoeSpeen/search?query=direct',body,width=width,native_dark=True)
    expect(page.locator('#myt-search .media')).to_have_count(2)
    expect(page.locator('#myt-channel-nav').get_by_role('link',name='Videos',exact=True)).to_have_attribute('aria-current','page')
    expect(page.get_by_role('searchbox',name='Search this channel')).to_have_value('direct')
    assert geometry(page)['direction']=='column'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.wait_for_timeout(100);assert_stable(page);page.close()
    print(f'PASS direct channel search opens the Videos grid: {width}px',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (1440,390):
            direct_search(browser,width)
            for cached,primary in ((False,True),(True,True),(False,False)):check(browser,width,cached,primary)
        browser.close()
