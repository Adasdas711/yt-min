"""Views must remain precise across description toggles; footer stays at the edge."""
from playwright.sync_api import sync_playwright,expect
from smoke import setup,native_watch_fixture,assert_stable
import html


def check(browser,width):
    body=native_watch_fixture().replace('<ytd-watch-metadata>','<ytd-watch-metadata><meta itemprop="interactionCount" content="906435"><meta itemprop="datePublished" content="2025-03-08">')
    body=body.replace('Full video description with native markup, links and paragraphs.','Full video description with native markup, links and paragraphs. '*35)
    page=setup(browser,'/watch?v=native',body,width=width,native_dark=True)
    value=page.locator('#myt-watch .stats-value');button=page.locator('#myt-watch .expand')
    expect(value).to_have_text('906.43k · 8 March 2025')
    page.evaluate('''()=>{
      const root=document.querySelector('#description'),info=root.querySelector('#info-container');
      root.querySelector('#expand').onclick=()=>{info.textContent='906K views';root.querySelector('#attributed-description-text').textContent='Full description. '.repeat(35);};
      const collapse=document.createElement('button');collapse.id='collapse';collapse.textContent='Show less';collapse.onclick=()=>{info.textContent='906,435 views';};root.append(collapse);
    }''')
    for _ in range(3):
        button.click();expect(button).to_have_attribute('aria-expanded','true');expect(value).to_have_text('906.43k · 8 March 2025')
        button.scroll_into_view_if_needed()
        a,b=button.bounding_box(),page.locator('#myt-watch .description').bounding_box()
        assert abs(a['y']+a['height']-b['y']-b['height']+1)<1,(a,b)
        assert abs(a['x']-b['x']-1)<1 and abs(a['width']-b['width']+2)<1,(a,b)
        button.click();expect(button).to_have_attribute('aria-expanded','false');expect(value).to_have_text('906.43k · 8 March 2025')
    page.locator('ytd-watch-metadata').evaluate('''e=>e.insertAdjacentHTML('afterend','<ytd-watch-info-text><div id="info" aria-label="906,440 views"></div></ytd-watch-info-text>')''')
    expect(value).to_have_text('906.44k · 8 March 2025')
    page.locator('ytd-watch-info-text #info').evaluate('e=>e.setAttribute("aria-label","906K views")')
    expect(value).to_have_text('906.44k · 8 March 2025')
    page.locator('meta[itemprop=interactionCount]').evaluate('e=>e.content="906500"')
    expect(value).to_have_text('906.50k · 8 March 2025')
    page.evaluate('''()=>{
      document.querySelector('ytd-watch-info-text').remove();document.querySelector('meta[itemprop=interactionCount]').remove();
      document.querySelector('#info-container').textContent='906,435 views';
    }''')
    expect(value).to_have_text('906.43k · 8 March 2025')
    for _ in range(2):
        button.click();expect(button).to_have_attribute('aria-expanded','true');expect(value).to_have_text('906.43k · 8 March 2025')
        button.click();expect(button).to_have_attribute('aria-expanded','false');expect(value).to_have_text('906.43k · 8 March 2025')
    assert_stable(page)
    page.screenshot(path=f'/tmp/yt-min-description26-{width}.png')
    page.close()
    print(f'PASS stable precise views across toggles, live updates and bottom-aligned footer: {width}px',flush=True)


def short_and_lazy(browser,width):
    for content in ['', 'A short description.', 'Word '*60]:
        base=native_watch_fixture();before=base.split('<div id="description" role="button">',1)[0];after=base.split('</ytd-watch-metadata>',1)[1]
        body=before+'<div id="description"><div id="info-container">906K views</div><div id="snippet">'+html.escape(content)+'</div><button id="expand" onclick="window.__expandCalls=(window.__expandCalls||0)+1">Show more</button></div></ytd-watch-metadata>'+after
        page=setup(browser,'/watch?v=native',body,width=width,native_dark=True)
        prose=page.locator('#watch-description');button=page.locator('#myt-watch .expand');stats=page.locator('#myt-watch .stats-value')
        expect(stats).to_have_text('906.00k')
        overflow=prose.evaluate('e=>e.scrollHeight>parseFloat(getComputedStyle(e).fontSize)*8.75+1')
        if overflow:
            expect(button).to_be_visible();button.click();expect(button).to_have_attribute('aria-expanded','true')
            assert prose.evaluate('e=>e.clientHeight>=e.scrollHeight-1')
            button.click();expect(button).to_have_attribute('aria-expanded','false')
        else:expect(button).to_be_hidden()
        assert page.evaluate('__expandCalls')==1
        expect(stats).to_have_text('906.00k')
        # Long asynchronous full text must reveal a useful control. Then a short
        # live replacement and viewport changes must remove it again.
        page.locator('#snippet').evaluate('e=>e.textContent="Full description. ".repeat(100)')
        expect(button).to_be_visible();button.click();expect(button).to_have_attribute('aria-expanded','true')
        page.locator('#info-container').evaluate('e=>e.textContent="906,435 views"')
        expect(stats).to_have_text('906.43k')
        page.locator('#snippet').evaluate('e=>e.textContent="Short again."')
        expect(button).to_be_hidden();expect(button).to_have_attribute('aria-expanded','false')
        page.locator('#snippet').evaluate('e=>e.textContent="Word ".repeat(60)')
        page.set_viewport_size({'width':1440,'height':960});expect(button).to_be_hidden()
        page.set_viewport_size({'width':390,'height':960});expect(button).to_be_visible()
        assert page.evaluate('__expandCalls')==1
        assert_stable(page);page.screenshot(path=f'/tmp/yt-min-description-short-{width}-{len(content)}.png');page.close()
    print(f'PASS initial two decimals, empty/short/fitting text, lazy full text, replacement and responsive overflow: {width}px',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,390]:
            check(browser,width);short_and_lazy(browser,width)
        browser.close()


if __name__=='__main__':main()
