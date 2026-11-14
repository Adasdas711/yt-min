"""A playlist card in a channel's Playlists section opens the playlist page.

YouTube's playlist lockups link to the playlist's first video
(/watch?v=...&list=...). On a channel the owned card opens the playlist
itself (/playlist?list=...), from its cover and its title. Mixes (RD...)
have no playlist page and keep their link.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup
from search import cover
import channel as channel_test


def lockup(list_id, title, kind='playlist', count='12 videos'):
    href = f'/watch?v=aaaaaaaaaaa&amp;list={list_id}'
    return (f'<ytd-rich-item-renderer><yt-lockup-view-model content-type="{kind}"><a class="cover-link" href="{href}"><yt-collection-thumbnail-view-model><img src="{cover()}"></yt-collection-thumbnail-view-model></a>'
            f'<h3><a href="{href}">{title}</a></h3><span id="video-count-text">{count}</span></yt-lockup-view-model></ytd-rich-item-renderer>')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        body = channel_test.fixture()
        start = body.index('<ytd-rich-grid-renderer><div id="contents">') + len('<ytd-rich-grid-renderer><div id="contents">')
        end = body.index('</div></ytd-rich-grid-renderer>', start)
        body = body[:start] + lockup('PLchannel01', 'Channel playlist') + lockup('RDmix0000001', 'A mix') + lockup('PLcourse0001', 'A course', 'course', '33 lessons') + lockup('PLchannel02', 'Another playlist') + body[end:]
        page = setup(browser, '/@creator/playlists', body)
        cards = page.locator('#myt-search .media')
        expect(cards).to_have_count(4)
        first = cards.first
        expect(first.locator('.media-title')).to_have_text('Channel playlist')
        expect(first.locator('.media-title')).to_have_attribute('href', 'https://www.youtube.com/playlist?list=PLchannel01')
        expect(first.locator('.cover')).to_have_attribute('href', 'https://www.youtube.com/playlist?list=PLchannel01')
        # A mix keeps its watch link.
        expect(cards.nth(1).locator('.media-title')).to_have_attribute('href', 'https://www.youtube.com/watch?v=aaaaaaaaaaa&list=RDmix0000001')
        # A course is a playlist card with a lesson count.
        course = cards.nth(2)
        expect(course.locator('.media-title')).to_have_attribute('href', 'https://www.youtube.com/playlist?list=PLcourse0001')
        expect(course.locator('.playlist-badge')).to_have_attribute('aria-label', '33 lessons')
        expect(cards.first.locator('.playlist-badge')).to_have_attribute('aria-label', '12 videos')
        # Playlists sit four to a row.
        tops = [round(cards.nth(i).bounding_box()['y']) for i in range(4)]
        assert len(set(tops)) == 1, tops
        width = cards.first.bounding_box()['width']
        assert width < 320, width
        page.evaluate('''()=>navigation.addEventListener('navigate',event=>{event.preventDefault();window.__opened=event.destination.url;})''')
        first.locator('.cover').click()
        page.wait_for_function('window.__opened')
        assert page.evaluate('__opened') == 'https://www.youtube.com/playlist?list=PLchannel01', page.evaluate('__opened')
        page.close()
        browser.close()
        print('PASS channel playlist cards open the playlist page; mixes keep their link; courses show lessons; four per row', flush=True)


if __name__ == '__main__':
    main()
