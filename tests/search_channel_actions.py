"""Every point in a search channel card navigates, without subscribing."""
import re
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable
from search_channel_layout import fixture, check_geometry
from search import channel


def restamps(browser):
    page=setup(browser,'/results?search_query=mrbeast',fixture('nested'),native_dark=True)
    card=page.locator('[data-myt-search-channel-card]');link=card.locator('.channel-link')
    page.evaluate('''()=>{
      window.__ownLink=document.querySelector('#myt-search').shadowRoot.querySelector('[data-myt-search-channel-card]').shadowRoot.querySelector('.channel-link');
      window.__nativeNodes=[...document.querySelectorAll('ytd-channel-renderer *')].map(node=>[node,node.parentElement,node.getAttribute('style')]);
      navigation.addEventListener('navigate',event=>{if(new URL(event.destination.url).pathname.startsWith('/@')){event.preventDefault();window.__channelDestination=event.destination.url;}});
    }''')
    link.click(position={'x':12,'y':12})
    assert page.evaluate('__channelDestination')=='https://www.youtube.com/@MrBeast'
    assert page.evaluate('__nativeNodes.every(([node,parent,style])=>node.parentElement===parent&&node.getAttribute("style")===style)')
    for index in range(5):
        html=fixture('renamed').split('<ytd-channel-renderer>',1)[1].split('</ytd-channel-renderer>',1)[0]
        html=html.replace('MrBeast',f'UpdatedCreator{index}').replace('525M','600M')
        page.locator('ytd-channel-renderer').evaluate('(node,html)=>node.innerHTML=html',html)
        expect(card.locator('.name')).to_have_text(f'UpdatedCreator{index}')
        expect(card.locator('.metadata')).to_contain_text('600M subscribers')
        expect(link).to_have_attribute('href',f'https://www.youtube.com/@UpdatedCreator{index}')
        assert page.evaluate('document.querySelector("#myt-search").shadowRoot.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector(".channel-link")===__ownLink')
        card.locator('.avatar img').click()
        assert page.evaluate('__channelDestination')==f'https://www.youtube.com/@UpdatedCreator{index}'
        check_geometry(page)
    assert page.evaluate('!window.__subscribed')
    page.evaluate('__setEnabled(false)');expect(card).to_have_count(0)
    expect(page.locator('[data-myt-search-channel-source]')).to_have_count(0)
    expect(page.locator('#native-subscribe')).to_be_visible()
    page.evaluate('__setEnabled(true)');expect(card.locator('.name')).to_have_text('UpdatedCreator4')
    check_geometry(page);assert_stable(page)
    page.screenshot(path='/workspace/yt-min-qa/channel-link-after-restamp.png');page.close()
    print('PASS channel destination updates through five restamps, native nodes unchanged and disable/enable cleanup',flush=True)


def full_card(browser,width,dark):
    body=fixture('nested').replace('</ytd-channel-renderer>','</ytd-channel-renderer>'+channel(2),1)
    page=setup(browser,'/results?search_query=mrbeast',body,width=width,native_dark=dark)
    page.evaluate('''()=>{
      window.__destinations=[];window.__subscribeCalls=0;window.__nativeLinkCalls=0;window.__blockedChannelEvents=0;
      for(const button of document.querySelectorAll('ytd-channel-renderer button'))button.onclick=()=>window.__subscribeCalls++;
      for(const link of document.querySelectorAll('ytd-channel-renderer a'))link.onclick=event=>{event.preventDefault();window.__nativeLinkCalls++;};
      window.__recordChannelNavigation=event=>{if(event.sourceElement){event.preventDefault();window.__blockedOwnedAnchor=true;return;}if(new URL(event.destination.url).pathname.startsWith('/@')){event.preventDefault();window.__destinations.push(event.destination.url);}};
      navigation.addEventListener('navigate',window.__recordChannelNavigation);
      for(const type of ['pointerdown','mousedown','click','keydown'])document.addEventListener(type,event=>{
        if(event.composedPath().some(node=>node instanceof Element&&node.matches('.channel-link'))){window.__blockedChannelEvents++;event.preventDefault();event.stopImmediatePropagation();}
      },true);
    }''')
    cards=page.locator('[data-myt-search-channel-card]');expect(cards).to_have_count(2)
    first=cards.first;link=first.locator('.channel-link')
    expect(first.locator('button')).to_have_count(0)
    expect(first.locator('a')).to_have_count(1)
    for selector in ['.avatar img','.name','.metadata','.verified']:
        first.locator(selector).click()
        assert page.evaluate('__destinations.at(-1)')=='https://www.youtube.com/@MrBeast'
    box=link.bounding_box()
    for x,y in [(12,12),(box['width']-12,12),(12,box['height']-12),(box['width']-12,box['height']-12),(box['width']-24,box['height']/2)]:
        link.click(position={'x':x,'y':y})
        assert page.evaluate('__destinations.at(-1)')=='https://www.youtube.com/@MrBeast'
    page.locator('ytd-masthead input').focus();page.keyboard.press('Tab');expect(link).to_be_focused()
    page.keyboard.press('Enter')
    assert page.evaluate('__destinations.length')==10
    page.keyboard.press('Tab');expect(cards.nth(1).locator('.channel-link')).to_be_focused()
    page.keyboard.press('Enter');assert page.evaluate('__destinations.at(-1)')=='https://www.youtube.com/@creator2'
    assert page.evaluate('__subscribeCalls===0&&__nativeLinkCalls===0&&__blockedChannelEvents===0&&!window.__blockedOwnedAnchor')
    # Browser-created tabs exercise the real anchor's modified and middle clicks.
    page.evaluate("navigation.removeEventListener('navigate',window.__recordChannelNavigation)")
    page.context.route('https://www.youtube.com/@MrBeast',lambda route:route.fulfill(content_type='text/html',body='<title>Channel</title>Channel'))
    for arguments in [{'modifiers':['Control']},{'button':'middle'}]:
        with page.context.expect_page() as opened:link.click(**arguments)
        popup=opened.value;popup.bring_to_front();popup.wait_for_url('https://www.youtube.com/@MrBeast',wait_until='domcontentloaded');popup.close();page.bring_to_front()
    page.screenshot(path=f'/workspace/yt-min-qa/channel-link-{width}-{dark}.png',full_page=True)
    assert_stable(page);page.close()
    print(f'PASS first channel avatar/name/metadata/background, keyboard and new tabs, zero subscriptions: {width}px, dark={dark}',flush=True)


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
    page.wait_for_function('document.querySelector("#myt-search").shadowRoot.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector("img").naturalWidth===160')
    expect(card.locator('.channel-link')).to_have_attribute('href','https://www.youtube.com/@MrBeast')
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
            for dark in [False,True]:full_card(browser,width,dark)
        restamps(browser);browser.close()
    print('PASS complete channel links, first avatar, keyboard, modified clicks, cached photos and restoration',flush=True)


if __name__=='__main__':main()
