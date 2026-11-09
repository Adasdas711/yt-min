"""Exit search even when YouTube acknowledges an unusable SPA tab transition."""
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright,expect
from channel_navigation import setup,finish


def check(browser,width,section,empty=None):
    context,page,nav,documents,requests,pending,errors=setup(browser,width,search_context_bug=True)
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('cookie');field.press('Enter')
    finish(pending);page.wait_for_url('**/search?**')
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 24'])
    token=page.evaluate('__native.token');count=len(requests)
    if empty=='enter':
        field.evaluate('e=>e.value=""');field.press('Enter')
    elif empty is not None:field.fill(empty)
    else:nav.get_by_role('link',name={'videos':'Videos','streams':'Live','playlists':'Playlists','posts':'Posts'}[section],exact=True).click()
    page.wait_for_url(lambda url:urlparse(str(url)).path.rstrip('/').endswith('/'+section))
    if section=='posts':
        expect(page.locator('ytd-backstage-post-renderer')).to_have_text('Channel post')
        expect(page.locator('#myt-search')).to_have_count(0)
    else:
        expected='Playlist 22' if section=='playlists' else 'Regular video 21' if section=='streams' else 'Regular video 20'
        expect(page.locator('#myt-search .media-title')).to_have_text([expected])
        expect(page.locator('#myt-search .empty')).to_be_hidden()
        expect(page.locator('#myt-search .results-heading')).to_be_hidden()
    assert len(documents)==2,documents
    assert page.evaluate('__native.token')!=token,'A search context must not be reused for other channel sections'
    assert len(requests)==count and not pending,'Leaving search must not dispatch a tab command in the search context'
    assert 'query' not in parse_qs(urlparse(page.url).query),page.url
    expect(nav.get_by_role('link',name={'videos':'Videos','streams':'Live','playlists':'Playlists','posts':'Posts'}[section],exact=True)).to_have_attribute('aria-current','page')
    if empty is not None:
        expect(field).to_be_visible();expect(field).to_have_value('');expect(field).to_be_focused()
        page.reload();expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 20'])
        expect(field).to_be_hidden()
    else:expect(field).to_be_hidden()
    assert not errors,errors
    context.close()
    print(f'PASS fresh {section} from search despite broken native SPA context, clean URL and one-shot empty-field restoration: {width}px, empty={empty!r}',flush=True)


def clear_pending_search(browser):
    context,page,nav,documents,requests,pending,errors=setup(browser,search_context_bug=True)
    nav.get_by_role('button',name='Search',exact=True).click()
    field=nav.get_by_role('searchbox',name='Search this channel');field.fill('still loading');field.press('Enter')
    expect(nav).to_have_attribute('aria-busy','true')
    assert len(pending)==1 and requests[-1]['query']=='still loading'
    token=page.evaluate('__native.token')
    field.fill('')
    page.wait_for_url(lambda url:urlparse(str(url)).path.rstrip('/').endswith('/videos'))
    expect(page.locator('#myt-search .media-title')).to_have_text(['Regular video 20'])
    expect(field).to_be_visible();expect(field).to_have_value('');expect(field).to_be_focused()
    assert len(documents)==2 and len(requests)==1,documents
    assert page.evaluate('__native.token')!=token
    assert not errors,errors
    pending.pop().abort()
    context.close()
    print('PASS clearing a pending search reloads Videos even before the search URL commits',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        clear_pending_search(browser)
        for width in (1440,390):
            for section in ('videos','streams','playlists','posts'):check(browser,width,section)
            for empty in ('','   ','enter'):check(browser,width,'videos',empty)
        browser.close()
