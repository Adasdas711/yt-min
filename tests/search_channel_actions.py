"""Owned channel cards keep native commands, popup anchors and live data."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable
from search_channel_layout import fixture, check_geometry


def check(browser):
    page = setup(browser, '/results?search_query=mrbeast', fixture('nested'), native_dark=True)
    card = page.locator('[data-myt-search-channel-card]')
    control = card.locator('.subscribe')
    expect(card.locator('.verified')).to_be_visible()
    page.evaluate('''() => {
      window.__sourceButton=document.querySelector('#native-subscribe');
      __sourceButton.setAttribute('style','border-color: pink;');
      __sourceButton.onclick=()=>{
        window.__calls=(window.__calls||0)+1;
        const rect=__sourceButton.getBoundingClientRect();window.__anchorAtClick={x:rect.x,y:rect.y,width:rect.width,height:rect.height};
        window.__userActivation=navigator.userActivation.isActive;
        if(!__sourceButton.parentElement.hasAttribute('subscribed')){
          __sourceButton.parentElement.setAttribute('subscribed','');__sourceButton.textContent='Subscribed';return;
        }
        let popups=document.querySelector('ytd-popup-container');
        if(!popups){popups=document.createElement('ytd-popup-container');document.body.append(popups);}
        popups.innerHTML=`<div id="native-menu" role="menu" style="position:fixed;left:${Math.min(rect.x,innerWidth-170)}px;top:${rect.bottom+4}px;background:#eee;color:#111;padding:12px;z-index:99999"><button id="unsubscribe">Unsubscribe</button></div>`;
        popups.querySelector('button').onclick=()=>{
          window.__unsubscribed=true;__sourceButton.parentElement.removeAttribute('subscribed');__sourceButton.textContent='Subscribe';popups.replaceChildren();
        };
      };
      document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelector('#native-menu')?.remove();});
    }''')
    own_before = control.bounding_box()
    control.click()
    expect(control).to_have_text('Subscribed')
    expect(control.locator('svg')).to_be_visible()
    assert page.evaluate('__calls===1&&__userActivation')
    own = own_before
    anchor = page.evaluate('__anchorAtClick')
    assert all(abs(own[key] - anchor[key]) < 1 for key in own), (own, anchor)
    own, anchor = control.bounding_box(), page.locator('#native-subscribe').bounding_box()
    assert all(abs(own[key] - anchor[key]) < 1 for key in own), (own, anchor)
    control.click()
    expect(page.locator('#native-menu')).to_be_visible()
    assert page.evaluate('__calls===2')
    page.set_viewport_size({'width': 390, 'height': 960})
    own, anchor = control.bounding_box(), page.locator('#native-subscribe').bounding_box()
    assert all(abs(own[key] - anchor[key]) < 1 for key in own), (own, anchor)
    # Native style writes must remain hidden, and survive removing our anchor.
    page.locator('#native-subscribe').evaluate('e=>{e.style.opacity="1";e.style.backgroundColor="rgb(1, 2, 3)";}')
    expect(page.locator('#native-subscribe')).to_have_css('opacity', '0')
    page.keyboard.press('Escape')
    expect(page.locator('#native-menu')).to_have_count(0)
    expect(control).to_be_focused()
    control.click()
    expect(page.locator('#native-menu')).to_be_visible()
    page.locator('#unsubscribe').click()
    expect(control).to_have_text('Subscribe')
    assert page.evaluate('__unsubscribed&&__calls===3&&document.querySelector("#native-subscribe")===__sourceButton')
    assert page.evaluate('__sourceButton.style.backgroundColor==="rgb(1, 2, 3)"&&__sourceButton.style.opacity==="1"')
    assert page.evaluate('!__sourceButton.hasAttribute("popover")&&!__sourceButton.hasAttribute("aria-hidden")&&!__sourceButton.hasAttribute("tabindex")')
    # Full native restamps reuse the owned controls, with fresh data and commands.
    page.evaluate('window.__ownButton=document.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector(".subscribe")')
    for index in range(5):
        html = fixture('renamed').split('<ytd-channel-renderer>', 1)[1].split('</ytd-channel-renderer>', 1)[0]
        html = html.replace('MrBeast', f'UpdatedCreator{index}').replace('525M', '600M')
        page.locator('ytd-channel-renderer').evaluate('(node,html)=>node.innerHTML=html', html)
        expect(card.locator('.name')).to_have_text(f'UpdatedCreator{index}')
        expect(card.locator('.metadata')).to_contain_text('600M subscribers')
        assert page.evaluate('document.querySelector("[data-myt-search-channel-card]").shadowRoot.querySelector(".subscribe")===__ownButton')
        check_geometry(page)
    control.click()
    assert page.evaluate('__subscribed===1')
    page.evaluate('__setEnabled(false)')
    expect(card).to_have_count(0)
    expect(page.locator('[data-myt-search-channel-source]')).to_have_count(0)
    expect(page.locator('#native-subscribe')).to_be_visible()
    assert page.evaluate('!document.querySelector("#native-subscribe").hasAttribute("popover")')
    page.evaluate('__setEnabled(true)')
    expect(card.locator('.name')).to_have_text('UpdatedCreator4')
    check_geometry(page)
    assert_stable(page)
    page.screenshot(path='/tmp/yt-min-owned-channel-after-restamp.png')
    page.close()
    print('PASS source command/user activation, native popup anchor, style restore, five restamps and cleanup', flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        check(browser)
        browser.close()


if __name__=='__main__': main()
