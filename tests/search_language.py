"""Filters always open in the owned English panel, including localized SPA data."""
import base64
from playwright.sync_api import sync_playwright,expect
from smoke import setup,MASTHEAD,assert_stable
from search import video


def check(browser,language,width):
    native='Видео' if language=='ru' else 'Video';button='Фильтры' if language=='ru' else 'Filter'
    body='<ytd-app>'+MASTHEAD+'<ytd-search><ytd-search-sub-menu-renderer><button>'+button+'</button><ytd-search-filter-group-renderer><ytd-search-filter-renderer><a href="/results?search_query=fixture&sp=native-video" onclick="event.preventDefault();window.__filterChosen=this.href">'+native+'</a></ytd-search-filter-renderer></ytd-search-filter-group-renderer></ytd-search-sub-menu-renderer><ytd-section-list-renderer>'+video(1)+'</ytd-section-list-renderer></ytd-search></ytd-app>'
    page=setup(browser,'/results?search_query=fixture',body,width=width,language=language,native_dark=True)
    root=page.locator('#myt-search');button=root.locator('.filters-toggle')
    expect(button).to_have_text('Filters')
    for _ in range(4):
        button.click();expect(root.locator('.filter-panel')).to_be_visible()
        expect(root.locator('.filter-group h3')).to_have_text(['Upload date','Type','Duration','Features','Sort by'])
        option=root.locator('.filter-group a').filter(has_text='Video').first
        expect(option).to_have_attribute('href','https://www.youtube.com/results?search_query=fixture&sp=native-video')
        option.click();expect(root.locator('.filter-panel')).to_be_hidden()
        assert page.evaluate('__filterChosen.endsWith("sp=native-video")')
    # Native labels and the source button may rerender; our control keeps focus.
    button.focus();page.locator('ytd-search-sub-menu-renderer > button').evaluate('e=>e.textContent="Фильтры"')
    expect(button).to_be_focused()
    button.press('Enter');expect(root.locator('.filter-panel')).to_be_visible()
    page.keyboard.press('Escape');expect(root.locator('.filter-panel')).to_be_hidden()
    assert_stable(page)
    button.click()
    playlist=root.locator('.filter-group a').filter(has_text='Playlist')
    href=playlist.get_attribute('href')
    from urllib.parse import urlparse,parse_qs
    assert list(base64.b64decode(parse_qs(urlparse(href).query)['sp'][0]))==[18,2,16,3]
    with page.expect_navigation():playlist.click()
    assert page.url==href
    page.close();print(f'PASS English owned filters, native option action, repeated mouse/keyboard toggles and working fallback URL: {language}, {width}px',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for language in ['ru','de']:
            for width in [1440,390]:check(browser,language,width)
        browser.close()


if __name__=='__main__':main()
