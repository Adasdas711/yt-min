"""Native channel result layouts must keep avatar, copy and actions apart."""
import base64
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, assert_stable
from search import video


def fixture(layout):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><rect width="160" height="160" fill="#03bbdc"/><text x="38" y="110" fill="white" font-family="Arial" font-size="96" font-weight="bold">M</text></svg>'
    image = '<yt-img-shadow id="avatar"><img alt="MrBeast" src="data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '"></yt-img-shadow>'
    avatar = image if layout == 'direct-avatar' else '<div id="avatar-section">' + image + '</div>'
    copy = '<div id="channel-info"><h3 id="channel-title">MrBeast <span aria-label="Verified">✓</span></h3><p id="channel-stats">@MrBeast · 525M subscribers</p><p id="description">SUBSCRIBE FOR A COOKIE! New MrBeast or MrBeast Gaming video every single Saturday at noon eastern time!</p></div>'
    action = '<ytd-subscribe-button-renderer id="subscribe-button"><button id="native-subscribe" aria-label="Subscribe to MrBeast" onclick="window.__subscribed=(window.__subscribed||0)+1">Subscribe</button></ytd-subscribe-button-renderer>'
    link = lambda text: '<a id="main-link" href="/@MrBeast" onclick="event.preventDefault();window.__channelVisits=(window.__channelVisits||0)+1">' + text + '</a>'
    if layout == 'legacy':
        content = avatar + '<div id="info-section">' + link(copy) + action + '</div>'
    elif layout == 'flat':
        content = avatar + '<div id="info-section">' + link(copy) + '</div>' + action
    else:
        content = link(avatar + '<div id="info-section">' + copy + '</div>') + action
    return '''<style>
      ytd-channel-renderer { font:16px/1.4 Arial,sans-serif; }
      #content-section,#main-link { display:flex;align-items:center; }
      #main-link { flex:1;color:inherit;text-decoration:none; }
      #avatar-section { display:flex;justify-content:center;width:246px; }
      #avatar { display:inline-block;width:136px;height:136px; }
      #avatar img { width:136px;height:136px;border-radius:50%; }
      /* Cached native offsets for a wider channel row, including its link. */
      #info-section { display:flex;flex-direction:column;align-items:flex-start;position:relative;left:-42px;margin-left:-28px;transform:translateX(-10px); }
      #main-link { position:relative;left:18px;transform:translateX(10px); }
      h3,p { margin:4px 0; } #channel-title { font-size:18px; }
      #channel-stats,#description { font-size:13px;color:#aaa;overflow-wrap:anywhere; }
      #description { display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden; }
    </style><ytd-app>''' + MASTHEAD + '<ytd-page-manager><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-channel-renderer><div id="content-section">' + content + '</div></ytd-channel-renderer>' + video(1) + '</div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'


def check_geometry(page):
    metrics = page.evaluate('''() => {
      const rect=selector=>{const b=document.querySelector(selector).getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,right:b.right,bottom:b.bottom};};
      return {card:rect('ytd-channel-renderer'),avatar:rect('#avatar img'),title:rect('#channel-title'),stats:rect('#channel-stats'),description:rect('#description'),button:rect('#native-subscribe'),overflow:document.documentElement.scrollWidth>innerWidth};
    }''')
    avatar, button, card = (metrics[key] for key in ['avatar', 'button', 'card'])
    assert avatar['width'] == avatar['height'] == 80, metrics
    for key in ['title', 'stats', 'description']:
        box = metrics[key]
        assert box['x'] >= avatar['right'] + 11, (key, metrics)
        assert box['right'] <= card['right'] + 1, (key, metrics)
        overlap = box['x'] < button['right'] and box['right'] > button['x'] and box['y'] < button['bottom'] and box['bottom'] > button['y']
        assert not overlap, (key, metrics)
    for box in [avatar, button]:
        assert box['x'] >= card['x'] and box['right'] <= card['right'] + 1, metrics
        assert box['y'] >= card['y'] and box['bottom'] <= card['bottom'] + 1, metrics
    assert not metrics['overflow'], metrics
    return metrics


def check(browser, layout, dark):
    page = setup(browser, '/results?search_query=mrbeast', fixture(layout), native_dark=dark)
    page.evaluate('''() => {
      window.__nativeNodes=[...document.querySelectorAll('ytd-channel-renderer *:not([data-myt-search-avatar-overlay])')].map(node=>[node,node.parentElement,node.getAttribute('style')]);
      document.querySelector('ytd-channel-renderer').addEventListener('click',event=>{
        if(event.target.closest('[data-myt-search-avatar-overlay]')){event.preventDefault();window.__channelVisits=(window.__channelVisits||0)+1;}
      },true);
    }''')
    for width in [1440, 2016, 900, 390, 320]:
        page.set_viewport_size({'width': width, 'height': 960})
        try:
            metrics = check_geometry(page)
        except AssertionError:
            page.screenshot(path=f'/tmp/yt-min-channel-overlap-before-{layout}-{width}.png')
            raise
        # The native card still occupies 1.5 ordinary video columns on desktop.
        regular = page.locator('#video-1').bounding_box()
        expected = regular['width'] * 1.5 + 12 if width > 1000 else regular['width'] * 2 + 24 if width > 600 else regular['width']
        assert abs(metrics['card']['width'] - expected) < 1, metrics
        avatar = page.locator('#avatar img')
        assert avatar.evaluate('''image=>{
          const box=image.getBoundingClientRect(),hit=document.elementFromPoint(box.x+box.width/2,box.y+box.height/2);
          const link=image.closest('ytd-channel-renderer').querySelector('[data-myt-search-avatar-link]');
          return link===hit||link.contains(hit);
        }''')
        box=avatar.bounding_box();page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
        assert page.evaluate('__channelVisits>0')
        before = page.evaluate('__channelVisits')
        page.locator('#native-subscribe').click()
        assert page.evaluate('__subscribed>0&&__channelVisits') == before
        assert page.evaluate('__nativeNodes.every(([node,parent])=>node.parentElement===parent)')
        assert_stable(page)
        page.screenshot(path=f'/tmp/yt-min-channel-fixed-{layout}-{width}-{dark}.png')
    # Native rerenders, long names and recycled URLs must not reintroduce overlap.
    page.set_viewport_size({'width': 390, 'height': 960})
    page.locator('#channel-title').evaluate('e=>e.firstChild.data="A very long creator name with words that should wrap "')
    page.locator('#info-section').evaluate('e=>{e.style.left="-80px";e.style.transform="translateX(-40px)";}')
    check_geometry(page)
    page.locator('ytd-channel-renderer a#main-link').evaluate('e=>e.href="/@updated"')
    expect(page.locator('[data-myt-search-avatar-link]')).to_have_attribute('href', 'https://www.youtube.com/@updated' if layout in ['flat', 'legacy'] else '/@updated')
    assert_stable(page)
    page.evaluate('window.__latestInfoStyle=document.querySelector("#info-section").getAttribute("style")')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-search-avatar-host],[data-myt-search-avatar-link]')).to_have_count(0)
    assert page.evaluate('__nativeNodes.every(([node,parent,style])=>node.parentElement===parent&&(node.id==="info-section"||node.getAttribute("style")===style))')
    assert page.evaluate('document.querySelector("#info-section").getAttribute("style")===__latestInfoStyle')
    page.evaluate('__setEnabled(true)')
    expect(page.locator('[data-myt-search-avatar-link]')).to_have_count(1)
    check_geometry(page)
    page.close()
    print(f'PASS channel avatar/copy/subscribe geometry, resize, native actions, rerender and restore: {layout}, dark={dark}', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for layout in ['wrapped', 'direct-avatar', 'flat', 'legacy']:
            for dark in [True, False]: check(browser, layout, dark)
        browser.close()


if __name__ == '__main__': main()
