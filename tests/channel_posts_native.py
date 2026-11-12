"""Posts without tab data on the page still show as the owned read-only feed.

The Posts tab used the owned feed only when the browse page data held the
tab's contents; otherwise YouTube's own posts stayed. YouTube's post elements
carry their own data (ytd-backstage-post-thread-renderer / ytd-post-renderer
.data), so the owned feed now reads them from there.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup
import channel as channel_test

POSTS = '''<ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents">
<ytd-backstage-post-thread-renderer id="native-post-1"><p>Native post one</p></ytd-backstage-post-thread-renderer>
<ytd-post-renderer id="native-post-2"><p>Native post two</p></ytd-post-renderer>
<ytd-continuation-item-renderer id="posts-continuation"></ytd-continuation-item-renderer>
</div></ytd-item-section-renderer></div></ytd-section-list-renderer>'''

DATA = '''() => {
  const renderer = (id, text) => ({postId: id, authorText: {runs: [{text: 'Data Creator'}]}, publishedTimeText: {runs: [{text: '2 days ago'}]}, contentText: {runs: [{text}]}, voteCount: {simpleText: '12'}});
  document.querySelector('#native-post-1').data = {post: {backstagePostRenderer: renderer('UgNode1', 'First native post')}};
  document.querySelector('#native-post-2').data = renderer('UgNode2', 'Second native post');
  document.querySelector('#posts-continuation').data = {continuationEndpoint: {continuationCommand: {token: 'posts-more'}}};
  document.dispatchEvent(new Event('yt-page-data-updated'));
}'''


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        body = channel_test.fixture()
        start = body.index('<ytd-rich-grid-renderer>')
        end = body.index('</ytd-rich-grid-renderer>', start) + len('</ytd-rich-grid-renderer>')
        body = body[:start] + POSTS + body[end:]
        page = setup(browser, '/@creator/posts', body)
        page.route('https://www.youtube.com/youtubei/v1/browse**', lambda route: None)
        page.evaluate(DATA)
        posts = page.locator('#myt-search .post')
        expect(posts).to_have_count(2)
        expect(posts.locator('.post-text')).to_have_text(['First native post', 'Second native post'])
        expect(posts.first.locator('.post-time')).to_have_attribute('href', 'https://www.youtube.com/post/UgNode1')
        expect(page.locator('#myt-search .post button')).to_have_count(0)
        assert page.evaluate("JSON.parse(document.documentElement.getAttribute('data-myt-page-model')).type") == 'posts'
        page.close()
        browser.close()
        print('PASS Posts without tab data use the owned feed from the posts themselves', flush=True)


if __name__ == '__main__':
    main()
