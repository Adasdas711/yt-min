"""Search mutation load, Shorts-labelled shelves and native carousel alignment."""
from playwright.sync_api import sync_playwright,expect
from smoke import setup,MASTHEAD,ROOT,assert_stable
from search import video


def burst(browser):
    body='<ytd-app><ytd-page-manager class="ytd-app"><ytd-search><ytd-section-list-renderer><div id="contents"><ytd-item-section-renderer><div id="contents" class="results"></div></ytd-item-section-renderer></div></ytd-section-list-renderer></ytd-search></ytd-page-manager></ytd-app>'
    page=setup(browser,'/results?search_query=burst',body)
    result=page.evaluate('''async()=>{
      let queries=0,syncs=0;const q=Element.prototype.querySelectorAll,original=MinimalYouTubeSearch.prototype.sync;
      Element.prototype.querySelectorAll=function(...args){queries++;return q.apply(this,args)};
      MinimalYouTubeSearch.prototype.sync=function(...args){syncs++;return original.apply(this,args)};
      const root=document.querySelector('.results'),start=performance.now();
      for(let group=0;group<20;group++){
        const wrapper=document.createElement('div');root.append(wrapper);
        for(let i=0;i<10;i++){
          const id=group*10+i,node=document.createElement('yt-lockup-view-model');wrapper.append(node);
          node.innerHTML='<div class="ytLockupViewModelHost"><a class="ytLockupViewModelContentImage" href="/watch?v=v'+id+'"><div style="aspect-ratio:16/9;background:#333"></div></a><div class="ytLockupMetadataViewModelHost"><h3><a href="/watch?v=v'+id+'">Video '+id+'</a></h3><a href="/@creator">Creator</a></div></div>';
        }
        await Promise.resolve();
      }
      for(let i=0;i<4;i++)await new Promise(requestAnimationFrame);
      const first={ms:performance.now()-start,queries,syncs};const before={queries,syncs};
      for(let i=0;i<20;i++){
        for(const node of root.querySelectorAll('h3 a'))node.firstChild.nodeValue+='.';
        await new Promise(requestAnimationFrame);
      }
      for(const node of root.querySelectorAll('.ytLockupViewModelContentImage')){const img=document.createElement('img');node.append(img);img.setAttribute('data-src','https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg');}
      for(let i=0;i<3;i++)await new Promise(requestAnimationFrame);
      return{first,updates:{queries:queries-before.queries,syncs:syncs-before.syncs},cards:root.querySelectorAll('[data-myt-search-video]').length};
    }''')
    assert result['cards']==200 and result['first']['queries']<1000,result
    assert result['updates']['syncs']==0 and result['updates']['queries']<100,result
    assert_stable(page);page.close();print('PASS bounded initial search work and no global rescan for 200 title/image updates:',result,flush=True)


def alignment_and_headings(browser,width):
    special='<ytd-shelf-renderer id="watch-again"><div id="title-container"><h2>Watch Again</h2></div><div id="content">'+''.join(video(i) for i in range(6,10))+'</div></ytd-shelf-renderer>'
    html='<style>ytd-shelf-renderer{display:block}ytd-thumbnail img{width:100%;height:auto}</style><ytd-app>'+MASTHEAD+'<ytd-page-manager class="ytd-app"><ytd-search><div id="generic-results"><div style="display:flex;justify-content:center;margin:0 auto;max-width:700px;transform:translateX(60px)">'+video(1)+video(2)+'</div><div style="width:70%;margin:auto;display:flex;justify-content:center">'+video(3)+video(4)+video(5)+'</div>'+special+'</div></ytd-search></ytd-page-manager></ytd-app>'
    page=setup(browser,'/results?search_query=alignment',html,width=width,native_dark=True,enabled=False)
    page.route('https://www.youtube.com/src/assets/fonts/**',lambda route:route.fulfill(content_type='font/ttf',body=(ROOT/'src/assets/fonts'/route.request.url.rsplit('/',1)[-1]).read_bytes()))
    page.evaluate("chrome.runtime.getURL=path=>'https://www.youtube.com/'+path;__setEnabled(true)")
    expect(page.locator('#generic-results')).to_have_attribute('data-myt-search-flow','')
    boxes=[page.locator('#video-'+str(i)).bounding_box() for i in range(1,6)];left=page.locator('#generic-results').bounding_box()['x']
    rows={}
    for box in boxes:rows.setdefault(round(box['y']),[]).append(box)
    assert all(abs(min(box['x'] for box in row)-left)<1 for row in rows.values()),(left,boxes)
    header=page.locator('#watch-again h2')
    expect(header).to_have_css('font-style','italic');expect(header).to_have_css('font-weight','900');expect(header).to_have_css('-webkit-text-stroke-width','0px')
    page.wait_for_function('Array.from(document.fonts).some(face=>face.family==="MYT Barlow Condensed"&&face.status==="loaded")')
    # Native formatted strings clip italic glyph overhang at their advance
    # width. Exercise the exact nested, shrink-to-fit heading shape.
    header.evaluate('''e=>e.innerHTML='<yt-formatted-string style="display:inline-block;overflow:hidden;white-space:nowrap;max-width:100%">WATCH AGAIN</yt-formatted-string>' ''')
    label=header.locator('yt-formatted-string')
    expect(label).to_have_css('overflow','visible')
    ink=label.evaluate('''e=>{
      const s=getComputedStyle(e),c=document.createElement('canvas').getContext('2d');
      c.font=s.fontStyle+' '+s.fontWeight+' '+s.fontSize+' '+s.fontFamily;c.letterSpacing=s.letterSpacing;
      const m=c.measureText(e.textContent);return{ink:m.actualBoundingBoxRight,width:e.getBoundingClientRect().width,padding:parseFloat(s.paddingRight)};
    }''')
    assert ink['padding']>=7 and ink['ink']<=ink['width'],ink
    page.screenshot(path=f'/tmp/yt-min-search-heading-{width}.png',full_page=True)
    header.evaluate('e=>e.textContent="Посмотреть снова"')
    page.wait_for_function('Array.from(document.fonts).some(face=>face.family==="MYT Cyrillic Condensed"&&face.status==="loaded")')
    page.evaluate('''()=>document.querySelector('#generic-results').insertAdjacentHTML('beforeend','<ytd-shelf-renderer id="latest-shorts"><div id="title-container"><yt-formatted-string id="title">Latest Shorts from MrBeast</yt-formatted-string></div><div id="content"><yt-lockup-view-model><h3><a href="/watch?v=vertical">A vertical video with a watch endpoint</a></h3></yt-lockup-view-model></div></ytd-shelf-renderer><yt-section-header-view-model id="orphan-latest"><h2>Latest Shorts from Creator</h2></yt-section-header-view-model>')''')
    expect(page.locator('#latest-shorts')).to_be_hidden();expect(page.locator('#orphan-latest')).to_be_hidden()
    page.locator('#latest-shorts #title').evaluate('e=>e.firstChild.data="Regular videos"')
    expect(page.locator('#latest-shorts')).to_be_visible()
    page.locator('#latest-shorts #title').evaluate('e=>e.firstChild.data="Latest Shorts from Creator"')
    expect(page.locator('#latest-shorts')).to_be_hidden()
    expect(page.locator('#video-1')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert_stable(page);page.screenshot(path=f'/tmp/yt-min-search26-{width}.png',full_page=True)
    page.evaluate('__setEnabled(false)');expect(page.locator('#watch-again h2[data-myt-search-heading-text]')).to_have_count(0)
    page.close();print(f'PASS left-aligned native wrappers, filled title fonts and Latest Shorts cleanup: {width}px',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        burst(browser)
        for width in [1440,900,390]:alignment_and_headings(browser,width)
        browser.close()


if __name__=='__main__':main()
