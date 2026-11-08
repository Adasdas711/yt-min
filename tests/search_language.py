"""Filters always open in the owned English panel, including localized SPA data."""
import base64
from playwright.sync_api import sync_playwright,expect
from smoke import setup,MASTHEAD,assert_stable
from search import video


def check(browser,language,width):
    native='Видео' if language=='ru' else 'Video';button='Фильтры' if language=='ru' else 'Filter'
    body='<ytd-app>'+MASTHEAD+'<ytd-search><ytd-search-sub-menu-renderer><button>'+button+'</button><ytd-search-filter-group-renderer><ytd-search-filter-renderer><a href="/results?search_query=fixture&sp=EgIQAQ%3D%3D" onclick="event.preventDefault();window.__nativeFilterClicked=true">'+native+'</a></ytd-search-filter-renderer></ytd-search-filter-group-renderer></ytd-search-sub-menu-renderer><ytd-section-list-renderer>'+video(1)+'</ytd-section-list-renderer></ytd-search></ytd-app>'
    page=setup(browser,'/results?search_query=fixture',body,width=width,language=language,native_dark=True)
    root=page.locator('#myt-search');button=root.locator('.filters-toggle')
    page.evaluate('''()=>{
      // Native containers can clip descendants and paint over their controls.
      const source=document.querySelector('ytd-search');source.style.cssText+=';contain:paint!important;max-height:150px!important;overflow:hidden!important';
      const cover=document.createElement('div');cover.id='native-cover';cover.style.cssText='position:fixed;inset:'+document.querySelector('#myt-search').shadowRoot.querySelector('.toolbar').getBoundingClientRect().bottom+'px 0 0;z-index:2147483647;background:#666';document.body.append(cover);
      navigation.addEventListener('navigate',event=>{if(new URL(event.destination.url).searchParams.get('sp')==='EgIQAQ=='){event.preventDefault();window.__filterDestination=event.destination.url;}});
    }''')
    expect(button).to_have_text('Filters')
    expect(button).to_have_attribute('popovertarget','search-filters')
    button.locator('svg').click();expect(root.locator('.filter-panel')).to_be_visible()
    button.click();expect(root.locator('.filter-panel')).to_be_hidden()
    for _ in range(4):
        button.click();expect(root.locator('.filter-panel')).to_be_visible()
        assert root.locator('.filter-panel').evaluate('node=>node.matches(":popover-open")')
        expect(button).to_have_attribute('aria-expanded','true')
        expect(root.locator('.filter-group h3')).to_have_text(['Upload date','Type','Duration','Features','Sort by'])
        option=root.locator('.filter-group a').filter(has_text='Video').first
        expect(option).to_have_attribute('href','https://www.youtube.com/results?search_query=fixture&sp=EgIQAQ%3D%3D')
        option.click();expect(root.locator('.filter-panel')).to_be_hidden()
        expect(button).to_have_attribute('aria-expanded','false')
        assert page.evaluate('__filterDestination.endsWith("sp=EgIQAQ%3D%3D")&&!window.__nativeFilterClicked')
    # Native labels and the source button may rerender; our control keeps focus.
    button.focus();page.locator('ytd-search-sub-menu-renderer > button').evaluate('e=>e.textContent="Фильтры"')
    expect(button).to_be_focused()
    button.press('Enter');expect(root.locator('.filter-panel')).to_be_visible()
    page.keyboard.press('Escape');expect(root.locator('.filter-panel')).to_be_hidden()
    button.click();page.mouse.click(width-4,240);expect(root.locator('.filter-panel')).to_be_hidden()
    assert_stable(page)
    button.click()
    page.screenshot(path=f'/workspace/yt-min-qa/search-native-filters-{language}-{width}.png',full_page=True)
    playlist=root.locator('.filter-group a').filter(has_text='Playlist')
    href=playlist.get_attribute('href')
    from urllib.parse import urlparse,parse_qs
    assert list(base64.b64decode(parse_qs(urlparse(href).query)['sp'][0]))==[18,2,16,3]
    with page.expect_navigation():playlist.click()
    assert page.url==href
    page.close();print(f'PASS native popover activation above clipped/covered page, English options, mouse/keyboard, dismissal and actual filter URLs: {language}, {width}px',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for language in ['ru','de']:
            for width in [1440,390]:check(browser,language,width)
        browser.close()


if __name__=='__main__':main()
