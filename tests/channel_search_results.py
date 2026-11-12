"""Channel search uses the Videos grid for nested/cached native result layouts."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable
from channel_header import fixture
from search import video
from channel_navigation import setup as navigation_setup, finish


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
    expect(page.locator('#myt-channel-nav').locator('nav a[aria-current]')).to_have_count(0)
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
        expect(host.locator('.skeleton')).to_be_visible();expect(host.locator('.empty')).to_be_hidden()
        page.locator('.search-items').evaluate('e=>e.insertAdjacentHTML("beforeend","<ytd-message-renderer>No results</ytd-message-renderer>")')
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
    expect(page.locator('#myt-channel-nav').locator('nav a[aria-current]')).to_have_count(0)
    expect(page.get_by_role('searchbox',name='Search this channel')).to_have_value('direct')
    assert geometry(page)['direction']=='column'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.wait_for_timeout(100);assert_stable(page);page.close()
    print(f'PASS direct channel search opens the Videos grid: {width}px',flush=True)


def changed_wrappers(browser,width,untyped=False):
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=True)
    expect(page.locator('#myt-search .media')).to_have_count(2)
    before=geometry(page)
    page.add_style_tag(content='ytd-video-renderer > #dismissible{display:flex;gap:24px}ytd-video-renderer ytd-thumbnail{display:block;flex:0 0 320px}ytd-video-renderer img{width:100%}')
    markup='<section class="native-feed-shell" style="max-width:920px;padding:32px;margin:auto"><yt-section-list-view-model><yt-item-section-view-model>'+video(401)+video(402)+'<ytd-continuation-item-renderer id="changed-continuation"></ytd-continuation-item-renderer></yt-item-section-view-model></yt-section-list-view-model></section>'
    page.evaluate('''({markup,untyped})=>{
        const browse=document.querySelector('ytd-browse');browse.querySelector(':scope > #contents').remove();
        if(untyped)browse.removeAttribute('page-subtype');
        browse.insertAdjacentHTML('beforeend',markup);history.pushState({},'', '/@JoeSpeen/search?query=changed');
        document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
    }''',{'markup':markup,'untyped':untyped})
    host=page.locator('#myt-search')
    expect(host).to_be_visible()
    expect(host.locator('.media-title')).to_have_text(['Regular video 401','Regular video 402'])
    after=geometry(page)
    for key in ('display','direction','padding','border','background','title','columns'):assert after[key]==before[key],(key,before,after)
    assert abs(after['width']-before['width'])<1,(before,after)
    expect(page.locator('#video-401')).to_be_hidden()
    expect(page.locator('#video-402')).to_be_hidden()
    expect(page.locator('#myt-channel-nav').locator('nav a[aria-current]')).to_have_count(0)
    expect(page.locator('#subscribe')).to_be_visible()
    sentinel=page.locator('#changed-continuation')
    sentinel.evaluate('(e,html)=>e.insertAdjacentHTML("beforebegin",html)',video(403))
    expect(host.locator('.media-title')).to_have_text(['Regular video 401','Regular video 402','Regular video 403'])
    assert sentinel.evaluate('e=>e.getBoundingClientRect().top>=document.querySelector("#myt-search").getBoundingClientRect().bottom-1'),sentinel.evaluate('e=>[e.getBoundingClientRect().top,document.querySelector("#myt-search").getBoundingClientRect().bottom,innerWidth]')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.wait_for_timeout(100);assert_stable(page)
    Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
    page.screenshot(path=f'/tmp/yt-min-qa/channel-changed-search-{width}-{untyped}.png')
    page.locator('yt-item-section-view-model').evaluate('e=>e.querySelectorAll("ytd-video-renderer").forEach(card=>card.remove())')
    expect(host.locator('.media')).to_have_count(0)
    # Without YouTube's confirmation the results are still loading.
    expect(host.locator('.skeleton')).to_be_visible();expect(host.locator('.empty')).to_be_hidden()
    sentinel.evaluate('e=>e.insertAdjacentHTML("beforebegin","<ytd-message-renderer id=\\"changed-empty\\">No results</ytd-message-renderer>")')
    expect(host.locator('.empty')).to_be_visible();expect(host.locator('.skeleton')).to_be_hidden()
    page.locator('#changed-empty').evaluate('e=>e.remove()')
    sentinel.evaluate('(e,html)=>e.insertAdjacentHTML("beforebegin",html)',video(404))
    expect(host.locator('.media-title')).to_have_text(['Regular video 404'])
    page.evaluate('__setEnabled(false)')
    expect(host).to_have_count(0)
    expect(page.locator('#video-404')).to_be_visible()
    expect(page.locator('[data-myt-channel-results],[data-myt-search-native-root],[data-myt-search-layout-path]')).to_have_count(0)
    page.close()
    print(f'PASS channel search with new wrapper names, native width constraints and late subtype: {width}px, untyped={untyped}',flush=True)


def separate_worlds(browser):
    context,page,nav,documents,requests,pending,errors=navigation_setup(browser)
    expect(page.locator('#myt-search .media')).to_have_count(2)
    before=geometry(page)
    page.evaluate('document.querySelector("ytd-browse").removeAttribute("page-subtype")')
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('new layout');field.press('Enter')
    expect(nav).to_have_attribute('aria-busy','true')
    finish(pending);page.wait_for_url('**/search?**')
    page.evaluate('''()=>{
        const old=document.querySelector('ytd-browse > #contents'),shell=document.createElement('section');
        shell.className='new-native-search';shell.style.cssText='max-width:920px;margin:auto;padding:32px';
        shell.append(...[...old.childNodes].filter(node=>node.id!=='myt-search'));old.replaceWith(shell);
        document.dispatchEvent(new Event('yt-page-data-updated'));document.dispatchEvent(new Event('yt-navigate-finish'));
    }''')
    host=page.locator('#myt-search')
    expect(host.locator('.media-title')).to_have_text(['Regular video 24'])
    expect(page.locator('#video-24')).to_be_hidden()
    after=geometry(page)
    assert abs(after['width']-before['width'])<1,(before,after)
    assert after['direction']=='column' and after['columns']==before['columns'],(before,after)
    expect(nav.locator('nav a[aria-current]')).to_have_count(0)
    assert requests[-1]['query']=='new layout'
    assert len(documents)==1,'Search must not fall back to reloading the page'
    assert not errors,errors
    context.close()
    print('PASS actual MAIN/ISOLATED worlds: SPA search, missing subtype and renamed content branch use the Videos grid',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        separate_worlds(browser)
        for width in (1440,900,700,390):
            changed_wrappers(browser,width)
            changed_wrappers(browser,width,True)
            direct_search(browser,width)
            for cached,primary in ((False,True),(True,True),(False,False)):check(browser,width,cached,primary)
        browser.close()
