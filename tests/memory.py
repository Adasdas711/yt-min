"""Memory-specific browser checks. Synthetic measurements are JS heap, not Arc RAM.

Run: python tests/memory.py. Real extension DNR registration is covered by the
API-contract checks in tests/optimization.cjs; this suite serves the exact local
landing page and MAIN-world script in Chromium without installing an extension.
"""
import base64
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, document

ORIGIN = 'https://minimal-extension.test'


def local_home(browser):
    page = browser.new_page(viewport={'width':1440,'height':960},reduced_motion='reduce')
    requests = []
    errors = []
    page.on('request',lambda request: requests.append(request.url))
    page.on('pageerror',lambda error: errors.append(str(error)))
    def route(request):
        url = urlparse(request.request.url)
        if url.netloc == 'minimal-extension.test':
            path = (ROOT / url.path.lstrip('/')).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), path
            request.fulfill(body=path.read_bytes(),content_type=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        elif url.netloc == 'www.youtube.com':
            request.fulfill(content_type='text/html',body='<html><title>Native YouTube</title><body id="native-page">Native YouTube page</body></html>')
        else:
            request.abort()
    page.route('**/*',route)
    init = f"""const saved=JSON.parse(localStorage.getItem('test-settings')||'{{"enabled":true,"language":"ru","theme":"dark"}}');
      ({MOCK})(saved);
      const originalSet=chrome.storage.local.set;
      chrome.storage.local.set=(value,done)=>{{localStorage.setItem('test-settings',JSON.stringify({{...window.__stored,...value}}));originalSet(value,done);}};
      chrome.runtime.getURL=path=>'{ORIGIN}/'+path;
      chrome.tabs={{getCurrent:done=>done({{id:7}})}};
      window.__messages=[];
      chrome.runtime.sendMessage=(message,done)=>{{window.__messages.push(message);
        if(message.action==='minimal-youtube:open-native-home')return done({{ok:true,url:'https://www.youtube.com/'}});
        done({{ok:true,cookies:message.action==='minimal-youtube:clear-cookies'?[]:[{{name:'PREF',domain:'.youtube.com'}}]}});
      }};
    """
    page.add_init_script(script=init)
    page.goto(ORIGIN+'/src/home/index.html')
    expect(page.locator('#myt-home')).to_be_visible()
    assert page.locator('ytd-app,ytd-player,video,iframe').count()==0
    assert not [url for url in requests if urlparse(url).netloc!='minimal-extension.test'], requests
    assert page.locator('script').evaluate_all("nodes=>nodes.every(node=>!node.src.includes('youtube.com'))")
    expect(page.locator('#myt-home')).to_have_attribute('data-myt-theme','dark')
    expect(page.locator('#myt-query')).to_have_attribute('placeholder','Поиск на YouTube')
    page.locator('#myt-settings-button').click()
    expect(page.locator('#myt-cookie-status')).to_contain_text('1')
    assert page.evaluate('window.__messages[0].tabId')==7
    assert page.locator('#myt-account-manage').get_attribute('href')=='https://www.youtube.com/account'
    page.locator('#myt-theme-light').click()
    expect(page.locator('#myt-home')).to_have_attribute('data-myt-theme','light')
    page.locator('#myt-settings-language').select_option('en')
    page.wait_for_url('**/src/home/index.html?hl=en&persist_hl=1')
    expect(page.locator('#myt-query')).to_have_attribute('placeholder','Search YouTube')
    expect(page.locator('#myt-home')).to_have_attribute('data-myt-theme','light')
    page.locator('#myt-settings-button').click()
    # On reload, settings start closed; this click opens them for the test.
    expect(page.locator('#myt-settings-panel')).to_be_visible()
    page.locator('#myt-settings-close').click()
    page.locator('#myt-query').fill('Кот & C++')
    page.locator('#myt-query').press('Enter')
    page.wait_for_url('https://www.youtube.com/results?**')
    query=parse_qs(urlparse(page.url).query)
    assert query['search_query']==['Кот & C++'] and query['hl']==['en']
    assert not errors, errors
    page.close()

    # Turning focus off waits for background rules to be removed, then restores
    # the real site; no disabled local landing page is left behind.
    page=browser.new_page()
    page.route('**/*',route)
    page.add_init_script(script=init)
    page.goto(ORIGIN+'/src/home/index.html')
    expect(page.locator('#myt-home')).to_be_visible()
    page.evaluate('chrome.storage.local.set({enabled:false})')
    page.wait_for_url('https://www.youtube.com/')
    expect(page.locator('#native-page')).to_be_visible()
    page.close()
    return {'initial_external_requests':0,'native_app_nodes':0}


BOOTSTRAP = """
(function(){
  const related=[];
  for(let i=0;i<320;i++) related.push({compactVideoRenderer:{videoId:String(i),title:{runs:[{text:'Recommendation '+i}]},thumbnail:{thumbnails:[{url:'https://i.ytimg.com/vi/'+i+'/hqdefault.jpg'}]},trackingCache:Array.from({length:4000},(_,j)=>i+j+.125)}});
  window.ytInitialData={contents:{twoColumnWatchNextResults:{results:{results:{contents:[{videoPrimaryInfoRenderer:{title:{runs:[{text:'Keep video'}]}}}]}},playlist:{playlist:{playlistId:'keep-playlist'}},secondaryResults:{secondaryResults:{results:related}}}}};
})();
window.__nativeBootstrapCount=ytInitialData.contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results.length;
window.__nativeCache=ytInitialData.contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results;
for(const item of window.__nativeCache){const card=document.createElement('ytd-compact-video-renderer');card.data=item;card.textContent=item.compactVideoRenderer.title.runs[0].text;document.body.append(card);}
"""


def feed_heap(browser, optimized):
    page=browser.new_page()
    page.route('https://www.youtube.com/**',lambda route: route.fulfill(content_type='text/html',body='<!doctype html><html><head></head><body></body></html>'))
    page.goto('https://www.youtube.com/watch?v=fixture')
    if optimized: page.add_script_tag(path=str(ROOT/'src/content/data-pruning.js'))
    page.add_script_tag(content=BOOTSTRAP)
    assert page.evaluate('ytInitialData.contents.twoColumnWatchNextResults.playlist.playlist.playlistId')=='keep-playlist'
    client=page.context.new_cdp_session(page)
    client.send('HeapProfiler.collectGarbage')
    heap=client.send('Runtime.getHeapUsage')
    nodes=client.send('Memory.getDOMCounters')
    result={'used_js_heap_bytes':heap['usedSize'],'dom_nodes':nodes['nodes'],'rendered_recommendations':page.evaluate('window.__nativeBootstrapCount')}
    page.close()
    return result


def actual_json_paths(browser):
    page=browser.new_page()
    code=(ROOT/'src/content/data-pruning.js').read_text()
    fixture='''<!doctype html><html><head><script>'''+code+'''</script></head><body><script>
      var ytInitialData={contents:{twoColumnSearchResultsRenderer:{contents:[{reelShelfRenderer:{}},{videoRenderer:{videoId:'keep',inlinePlaybackEndpoint:{videoId:'preview'},thumbnail:{url:'keep.jpg'}}}]}}};
      window.__beforeRender=ytInitialData.contents.twoColumnSearchResultsRenderer.contents.length;
      </script></body></html>'''
    data={'onResponseReceivedActions':[{'appendContinuationItemsAction':{'targetId':'watch-next-feed','continuationItems':[{'compactVideoRenderer':{'videoId':'drop'}}]}},{'appendContinuationItemsAction':{'targetId':'comments-section','continuationItems':[{'commentThreadRenderer':{'text':'keep'}}]}}]}
    def fulfill(route):
        if '/youtubei/' in route.request.url: route.fulfill(json=data)
        else: route.fulfill(content_type='text/html',body=fixture)
    page.route('https://www.youtube.com/**',fulfill)
    page.goto('https://www.youtube.com/watch?v=fixture')
    assert page.evaluate('window.__beforeRender')==1
    assert page.evaluate('ytInitialData.contents.twoColumnSearchResultsRenderer.contents[0].videoRenderer.thumbnail.url')=='keep.jpg'
    assert page.evaluate("'inlinePlaybackEndpoint' in ytInitialData.contents.twoColumnSearchResultsRenderer.contents[0].videoRenderer") is False
    fetched=page.evaluate("async()=>await(await fetch('/youtubei/v1/next',{method:'POST'})).json()")
    assert fetched['onResponseReceivedActions'][0]['appendContinuationItemsAction']['continuationItems']==[]
    assert fetched['onResponseReceivedActions'][1]['appendContinuationItemsAction']['continuationItems'][0]['commentThreadRenderer']['text']=='keep'
    page.evaluate("document.dispatchEvent(new CustomEvent('minimal-youtube:optimization',{detail:{enabled:false}}))")
    raw=page.evaluate("async()=>await(await fetch('/youtubei/v1/next',{method:'POST'})).json()")
    assert raw['onResponseReceivedActions'][0]['appendContinuationItemsAction']['continuationItems'][0]['compactVideoRenderer']['videoId']=='drop'
    page.close()


def main():
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        home=local_home(browser)
        print('PASS exact standalone landing page: no YouTube app/resources, shared settings/cookies, native search and disabled-mode navigation',flush=True)
        actual_json_paths(browser)
        print('PASS document-start initial data and real Response.json pruning; player data/comments/disabled parsing stay native',flush=True)
        baseline=feed_heap(browser,False)
        optimized=feed_heap(browser,True)
        assert baseline['rendered_recommendations']==320 and optimized['rendered_recommendations']==0
        assert optimized['used_js_heap_bytes'] < baseline['used_js_heap_bytes']*.6, (baseline,optimized)
        assert optimized['dom_nodes'] < baseline['dom_nodes'], (baseline,optimized)
        report={'scope':'Synthetic recommendation feed; retained JS heap after test-only GC. Not real YouTube/Arc process RAM.','standalone_home':home,'baseline':baseline,'optimized':optimized}
        Path('/tmp/yt-min-memory-profile.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS recommendation data discarded before native DOM/cache creation:',json.dumps(report),flush=True)
        browser.close()

if __name__=='__main__': main()
