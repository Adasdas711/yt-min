"""Search channels share watch subscriptions and retain native navigation/data."""
import re
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable, check_subscription_card
from search_channel_layout import fixture, check_geometry


def restamps(browser):
    page=setup(browser,'/results?search_query=mrbeast',fixture('nested'),native_dark=True)
    card=page.locator('[data-myt-search-channel-card]');control=card.locator('.subscribe')
    page.evaluate('''()=>{
      window.__ownButton=document.querySelector('[data-myt-search-channel-card]').shadowRoot.querySelector('.subscribe');
      const native=document.querySelector('#native-subscribe');native.style.borderColor='pink';
      window.__originalStyle=native.getAttribute('style');
      native.onclick=()=>{
        const rect=native.getBoundingClientRect();window.__anchorAtClick={x:rect.x,y:rect.y,width:rect.width,height:rect.height};
        window.__userActivation=navigator.userActivation.isActive;
        native.parentElement.setAttribute('subscribed','');native.textContent='Subscribed';
      };
    }''')
    own=control.bounding_box();control.click(position={'x':12,'y':12})
    expect(control).to_have_attribute('aria-pressed','true')
    assert page.evaluate('__userActivation')
    anchor=page.evaluate('__anchorAtClick')
    assert all(abs(own[key]-anchor[key])<1 for key in own),(own,anchor)
    page.wait_for_function('document.querySelector("#native-subscribe").getAttribute("style")===__originalStyle')
    assert page.evaluate('!document.querySelector("#native-subscribe").hasAttribute("popover")')
    for index in range(5):
        html=fixture('renamed').split('<ytd-channel-renderer>',1)[1].split('</ytd-channel-renderer>',1)[0]
        html=html.replace('MrBeast',f'UpdatedCreator{index}').replace('525M','600M')
        page.locator('ytd-channel-renderer').evaluate('(node,html)=>node.innerHTML=html',html)
        expect(card.locator('.name')).to_have_text(f'UpdatedCreator{index}')
        expect(card.locator('.metadata')).to_contain_text('600M subscribers')
        assert page.evaluate('document.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector(".subscribe")===__ownButton')
        check_geometry(page)
    control.click(position={'x':12,'y':12});expect(control).to_have_attribute('aria-pressed','true')
    assert page.evaluate('__subscribed===1')
    page.evaluate('__setEnabled(false)');expect(card).to_have_count(0)
    expect(page.locator('[data-myt-search-channel-source]')).to_have_count(0)
    expect(page.locator('#native-subscribe')).to_be_visible()
    page.evaluate('__setEnabled(true)');expect(card.locator('.name')).to_have_text('UpdatedCreator4')
    check_geometry(page);assert_stable(page)
    page.screenshot(path='/tmp/yt-min-owned-channel-after-restamp.png');page.close()
    print('PASS native action/user activation/anchor, style restore, five full restamps and cleanup',flush=True)


def cached_photo(browser,width):
    body=fixture('nested')
    # Native lazy avatar/anchors never mount; metadata identifies the channel.
    body=re.sub(r'<img alt="MrBeast"[^>]+>','',body).replace('href="/@MrBeast"','')
    page=setup(browser,'/results?search_query=mrbeast',body,width=width,native_dark=True,prune_data=True)
    photo='https://yt3.ggpht.com/test-channel-photo=s160-c-k-c0x00ffffff-no-rj'
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><rect width="160" height="160" fill="#00bcd4"/><path d="M20 90 70 25 140 80 90 140Z" fill="#ff2863"/><circle cx="90" cy="60" r="10" fill="white"/></svg>'
    page.route('https://yt3.ggpht.com/**',lambda route:route.fulfill(status=404,content_type='text/plain',body='') if route.request.url.endswith('/unavailable') else route.fulfill(content_type='image/svg+xml',body=svg))
    page.evaluate('''photo=>window.ytInitialData={contents:{twoColumnSearchResultsRenderer:{contents:[
      {channelRenderer:{channelId:'UCxxxxxxxxxxxxxxxxxxxxxx',title:{simpleText:'MrBeast'},subscriberCountText:{simpleText:'@OtherCreator'},navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@OtherCreator'}},thumbnail:{thumbnails:[{url:'https://yt3.ggpht.com/wrong-channel',width:160}]}}},
      {channelRenderer:{channelId:'UCX6OQ3DkcsbYNE6H8uQQuVA',title:{simpleText:'MrBeast'},subscriberCountText:{simpleText:'@MrBeast'},videoCountText:{simpleText:'525M subscribers'},navigationEndpoint:{browseEndpoint:{canonicalBaseUrl:'/@MrBeast'}},thumbnail:{thumbnails:[{url:photo,width:160}]},descriptionSnippet:{simpleText:'Never display this description'},trackingParams:'Never copy this field'}}
    ]}}}''',photo)
    card=page.locator('[data-myt-search-channel-card]');image=card.locator('.avatar img')
    expect(image).to_have_attribute('src',photo);expect(image).to_be_visible()
    page.wait_for_function('document.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector("img").naturalWidth===160')
    expect(card.locator('.avatar')).to_have_attribute('href','https://www.youtube.com/@MrBeast')
    expect(card.locator('.name')).to_have_attribute('href','https://www.youtube.com/@MrBeast')
    expect(card.locator('.description')).to_have_count(0)
    page.locator('#channel-stats').evaluate('e=>e.textContent="@MrBeast · 525 Mio. Abonnenten"')
    expect(card.locator('.metadata')).to_have_text('@MrBeast · 525M subscribers')
    page.locator('#channel-stats').evaluate('e=>e.textContent="@MrBeast · 525 млн подписчиков"')
    expect(card.locator('.metadata')).to_have_text('@MrBeast · 525M subscribers')
    updated='https://yt3.ggpht.com/updated-channel-photo'
    page.locator('#avatar').evaluate('(node,src)=>{const img=document.createElement("img");img.src=src;node.append(img);}',updated)
    expect(image).to_have_attribute('src',updated)
    page.locator('#avatar img').evaluate('e=>e.src="https://yt3.ggpht.com/unavailable"')
    expect(image).to_have_attribute('src',photo);expect(image).to_be_visible()
    page.locator('#avatar img').evaluate('e=>e.src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"')
    expect(image).to_have_attribute('src',photo);expect(image).to_be_visible()
    page.locator('#avatar img').evaluate('e=>e.remove()')
    check_geometry(page);assert_stable(page)
    page.screenshot(path=f'/tmp/yt-min-channel-photo-{width}.png')
    with page.expect_navigation():image.click()
    assert page.url=='https://www.youtube.com/@MrBeast'
    page.close();print(f'PASS image from search payload without native photo/links, duplicate names and avatar navigation: {width}px',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,390]:
            cached_photo(browser,width)
            for dark in [False,True]:
                for modern in [False,True]:
                    check_subscription_card(browser,dark,width,modern=modern,search=True)
        restamps(browser);browser.close()
    print('PASS shared subscription background, avatar/name links, keyboard, pending/disabled states, dialogs and motion',flush=True)


if __name__=='__main__':main()
