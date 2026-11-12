"""Blocks YouTube adds later never appear on owned playlist, channel and watch pages.

Each page keeps only what it knows:
- playlist: the owned summary and the list; any other block beside them
  in the playlist layout or its wrappers is hidden;
- channel: the owned header, the owned navigation and the results; other
  blocks in the page are hidden, and videos inside an unknown container
  never become result cards;
- watch: comments show their header, threads and continuation; a new
  block inside the comments section is hidden.
Everything returns when the extension is disabled.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, native_watch_fixture
from search import video
import playlist as playlist_test
import channel as channel_test


def check_playlist(browser):
    body = playlist_test.body()
    body = body.replace('<ytd-playlist-video-list-renderer>', '<ytd-playlist-promo-renderer id="new-list-block">Try this new playlist feature</ytd-playlist-promo-renderer><ytd-playlist-video-list-renderer>', 1)
    body = body.replace('<ytd-browse page-subtype="playlist">', '<ytd-browse page-subtype="playlist"><yt-banner-view-model id="new-page-block">A new banner</yt-banner-view-model>', 1)
    page = setup(browser, '/playlist?list=PLfixture', body)
    expect(page.locator('[data-myt-owned-playlist-card="video"]').first).to_be_visible()
    expect(page.locator('#myt-playlist-summary')).to_be_visible()
    for block in ['#new-list-block', '#new-page-block']:
        expect(page.locator(block)).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    for block in ['#new-list-block', '#new-page-block']:
        expect(page.locator(block)).to_be_visible()
    page.close()
    print('PASS playlist: new blocks beside the summary and the list stay hidden', flush=True)


def check_channel(browser):
    body = channel_test.fixture()
    body = body.replace('<div id="contents"><ytd-rich-grid-renderer><div id="contents">',
                        '<yt-membership-promo-view-model id="new-page-block">Join this channel</yt-membership-promo-view-model><div id="contents"><ytd-rich-grid-renderer><div id="contents">'
                        + '<yt-new-carousel-view-model id="new-feed-block">' + video(900).replace('Regular video 900', 'Carousel video') + '</yt-new-carousel-view-model>', 1)
    body = body.replace('<div id="banner">', '<yt-header-promo-view-model id="new-header-block">Header promo</yt-header-promo-view-model><div id="banner">', 1)
    page = setup(browser, '/@creator/videos', body)
    expect(page.locator('#myt-search .media')).to_have_count(18)
    expect(page.locator('#myt-channel-header')).to_be_visible()
    expect(page.locator('#myt-channel-nav')).to_be_visible()
    assert 'Carousel video' not in page.locator('#myt-search').inner_text()
    for block in ['#new-page-block', '#new-header-block', '#new-feed-block']:
        expect(page.locator(block)).to_be_hidden()
    page.evaluate('__setEnabled(false)')
    for block in ['#new-page-block', '#new-header-block', '#new-feed-block']:
        expect(page.locator(block)).to_be_visible()
    page.close()
    print('PASS channel: new page, header and feed blocks stay hidden', flush=True)


def check_watch(browser):
    threads = ''.join(f'<ytd-comment-thread-renderer><ytd-comment-view-model><a id="author-text" href="/@author{i}">Author {i}</a><p id="content-text">Comment {i}</p></ytd-comment-view-model></ytd-comment-thread-renderer>' for i in range(3))
    comments = ('<ytd-comments id="comments"><ytd-item-section-renderer id="sections">'
                '<div id="header"><ytd-comments-header-renderer><h2>3 Comments</h2></ytd-comments-header-renderer><yt-comments-summary-view-model id="new-header-block">AI summary of comments</yt-comments-summary-view-model></div>'
                '<div id="contents"><ytd-comments-promo-renderer id="new-thread-block">A new comments promo</ytd-comments-promo-renderer>' + threads
                + '<ytd-continuation-item-renderer id="comment-continuation"></ytd-continuation-item-renderer></div></ytd-item-section-renderer></ytd-comments>')
    body = native_watch_fixture().replace('</ytd-watch-metadata>', '</ytd-watch-metadata>' + comments)
    page = setup(browser, '/watch?v=native', body)
    page.locator('#myt-watch .more-toggle').click()
    page.locator('#myt-comments-toggle').click()
    expect(page.locator('[data-myt-watch-island="comments"]')).to_be_visible()
    expect(page.locator('ytd-comment-thread-renderer')).to_have_count(3)
    expect(page.locator('ytd-comment-thread-renderer').first).to_be_visible()
    expect(page.locator('ytd-comments-header-renderer')).to_be_visible()
    for block in ['#new-header-block', '#new-thread-block']:
        expect(page.locator(block)).to_be_hidden()
    page.close()
    print('PASS watch: new blocks inside comments stay hidden', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        check_playlist(browser)
        check_channel(browser)
        check_watch(browser)
        browser.close()


if __name__ == '__main__':
    main()
