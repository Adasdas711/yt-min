"""Native comment actions, visual containment and wheel routing regressions."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup,native_watch_fixture,assert_stable


def check(browser,width,dark,panel=False):
    threads=''.join(f'''<ytd-comment-thread-renderer><ytd-comment-view-model><a id="author-text" href="/@author{i}">Author {i}</a><span id="published-time-text">2 days ago</span><p id="content-text">Comment {i}: a native comment with text and <a href="https://example.com">a link</a>.</p><button class="like" onclick="this.setAttribute('aria-pressed',this.getAttribute('aria-pressed')!=='true')" aria-pressed="false">Like</button><button class="reply" onclick="this.nextElementSibling.hidden=false">Reply</button><div class="reply-editor" hidden><input aria-label="Reply draft"></div></ytd-comment-view-model></ytd-comment-thread-renderer>''' for i in range(180))
    comments='<ytd-comments id="native-comments"><ytd-comments-header-renderer><h2>180 Comments</h2><button onclick="window.__sort=true">Sort by</button></ytd-comments-header-renderer><ytd-comment-simplebox-renderer><div contenteditable="true" role="textbox" aria-label="Add a comment"></div></ytd-comment-simplebox-renderer><div id="contents">'+threads+'</div></ytd-comments>'
    if panel:comments='<ytd-engagement-panel-section-list-renderer id="comments-panel" target-id="engagement-panel-comments-section" visibility="ENGAGEMENT_PANEL_VISIBILITY_HIDDEN">'+comments+'</ytd-engagement-panel-section-list-renderer>'
    body=native_watch_fixture().replace('</ytd-watch-metadata>','</ytd-watch-metadata>'+comments)
    page=setup(browser,'/watch?v=native',body,width=width,native_dark=dark)
    page.locator('#myt-watch .more-toggle').click();page.locator('#myt-comments-toggle').click()
    target=page.locator('[data-myt-watch-island="comments"]')
    expect(target).to_be_visible()
    expect(target).to_have_css('border-radius','20px' if width<=600 else '24px')
    expect(target).to_have_css('contain','content')
    expect(page.locator('ytd-comment-thread-renderer').first).to_have_css('content-visibility','auto')
    first=page.locator('ytd-comment-thread-renderer').first
    expect(first.locator('.like')).to_be_hidden();expect(first.locator('.reply')).to_be_hidden()
    # An already-open native draft is retained; the actions cannot be invoked.
    first.locator('.reply-editor').evaluate('e=>e.hidden=false')
    first.get_by_role('textbox',name='Reply draft').fill('Preserved native draft')
    page.evaluate('''() => {
      window.__commentNode=document.querySelector('ytd-comment-thread-renderer');window.__commentParent=__commentNode.parentElement;
      window.__nativeWheelLeaks=0;document.addEventListener('wheel',()=>__nativeWheelLeaks++,true);
      window.__commentFullScans=0;const query=Element.prototype.querySelectorAll;
      Element.prototype.querySelectorAll=function(selector){if(selector==='*')__commentFullScans++;return query.call(this,selector);};
      window.__commentSyncs=0;const sync=MinimalYouTubeWatch.prototype.sync;
      MinimalYouTubeWatch.prototype.sync=function(...args){__commentSyncs++;return sync.apply(this,args);};
    }''')
    viewport=page.locator('#myt-watch .viewport');before=viewport.evaluate('e=>e.scrollTop')
    box=target.bounding_box();page.mouse.move(box['x']+50,min(box['y']+150,850 if width>600 else 800));page.mouse.wheel(0,300)
    page.wait_for_function('document.querySelector("[data-myt-watch-island=comments]").scrollTop>0')
    assert viewport.evaluate('e=>e.scrollTop')==before
    result=target.evaluate('''e=>{
      const target=e.querySelector('#content-text'),start=performance.now();
      for(let i=0;i<120;i++)target.dispatchEvent(new WheelEvent('wheel',{deltaY:1,bubbles:true,cancelable:true,composed:true}));
      return {ms:performance.now()-start,leaks:__nativeWheelLeaks,scans:__commentFullScans};
    }''')
    assert result['leaks']==0 and result['scans']==0,result
    target.evaluate('e=>e.scrollTop=0');page.mouse.wheel(0,-160)
    page.wait_for_function('document.querySelector("#myt-watch").firstChild.shadowRoot.querySelector(".viewport").scrollTop<'+str(before))
    assert page.evaluate('document.scrollingElement.scrollTop')==0
    assert page.evaluate('__commentNode===document.querySelector("ytd-comment-thread-renderer")&&__commentParent===__commentNode.parentElement')
    assert page.evaluate('__commentSyncs')==0
    viewport.evaluate('e=>e.scrollTop=e.scrollHeight');target.evaluate('e=>e.scrollTop=0')
    expect(first.get_by_role('textbox',name='Reply draft')).to_have_value('Preserved native draft')
    assert_stable(page)
    page.screenshot(path=f'/tmp/yt-min-comments25-{width}-{dark}-{panel}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-watch-island]')).to_have_count(0)
    # A panel returns to its original collapsed state on disable; its buttons
    # must regain their own display styles even while the parent is hidden.
    expect(first.locator('.like')).not_to_have_css('display','none');expect(first.locator('.reply')).not_to_have_css('display','none')
    assert page.evaluate('__commentParent===__commentNode.parentElement')
    page.close()
    print(f'PASS native comments style/actions/scroll: width={width}, dark={dark}, panel={panel}, profile={result}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [1440,390]:
            for dark in [True,False]:check(browser,width,dark)
        check(browser,1440,True,True)
        browser.close()


if __name__=='__main__':main()
