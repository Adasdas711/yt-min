"""Search bursts, card updates, English shelves and native infinite scrolling."""
from playwright.sync_api import sync_playwright,expect
from smoke import setup,MASTHEAD,assert_stable
from search import video


def check(browser):
    body='<ytd-app>'+MASTHEAD+'<ytd-search><ytd-section-list-renderer><div class="results">'+''.join(video(i) for i in range(1,5))+'<ytd-continuation-item-renderer id="sentinel"></ytd-continuation-item-renderer></div></ytd-section-list-renderer></ytd-search></ytd-app>'
    page=setup(browser,'/results?search_query=loading',body,native_dark=True)
    page.evaluate("""()=>{
      window.__syncs=0;const original=MinimalYouTubeSearch.prototype.sync;
      MinimalYouTubeSearch.prototype.sync=function(...args){__syncs++;return original.apply(this,args)};
      window.__oldCard=document.querySelector('#myt-search').shadowRoot.querySelector('.media');
    }""")
    root=page.locator('#myt-search')
    page.locator('.results').evaluate('(node,html)=>node.insertAdjacentHTML("beforeend",html)',''.join(video(i) for i in range(5,105)))
    expect(root.locator('.media')).to_have_count(104)
    page.evaluate('document.documentElement.style.overflow="hidden";scrollTo(0,0)')
    page.mouse.move(300,400);page.mouse.wheel(0,350)
    page.wait_for_function('scrollY>=300')
    page.evaluate('document.documentElement.style.overflow="";scrollTo(0,0)')
    assert page.evaluate('__syncs')<5
    page.evaluate('__syncs=0')
    for _ in range(3):
        page.locator('#video-1 #video-title').evaluate('e=>e.firstChild.data+="."')
        expect(root.locator('.media-title').first).to_contain_text('Regular video 1.')
    assert page.evaluate('__syncs')==0
    assert page.evaluate('document.querySelector("#myt-search").shadowRoot.querySelector(".media")===__oldCard')
    page.evaluate('''()=>{
      const sentinel=document.querySelector('#sentinel');
      window.__sentinel=sentinel;window.__continuations=0;
      const observer=new IntersectionObserver(entries=>{
        if(entries.some(e=>e.isIntersecting)&&!__continuations){
          __continuations++;document.querySelector('.results').insertAdjacentHTML('beforeend','<ytd-video-renderer id="late-video"><h3><a href="/watch?v=late">New continuation video</a></h3></ytd-video-renderer>');observer.disconnect();
        }
      });observer.observe(sentinel);
    }''')
    page.locator('#sentinel').scroll_into_view_if_needed()
    expect(root.locator('.media')).to_have_count(105)
    assert page.evaluate('__continuations===1&&document.querySelector("#sentinel")===__sentinel')
    # New Shorts-labelled shelves must never enter the owned stream.
    page.locator('.results').evaluate('(node,html)=>node.insertAdjacentHTML("beforeend",html)','<ytd-shelf-renderer><div id="title-container"><h2>Latest Shorts from Creator</h2></div>'+video(201)+'</ytd-shelf-renderer>')
    expect(root.locator('.media')).to_have_count(105)
    assert_stable(page);page.close()
    print('PASS bounded burst, incremental title updates without global rebuild, original continuation sentinel and late Shorts exclusion',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        check(browser);browser.close()


if __name__=='__main__':main()
