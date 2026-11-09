"""Full fallback About dialog, with MAIN-world public data and delayed browse replies."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from smoke import ROOT, MOCK, document
from channel_header import fixture


def response(name):
    model={
        'channelId':'UCfixture'+name,
        'description':f'Full {name} biography.\n\n'+('Original author paragraph, preserved with its line breaks.\n\n'*45),
        'canonicalChannelUrl':'https://www.youtube.com/@'+name,
        'country':'United States' if name=='MrBeast' else 'Russia',
        'joinedDateText':{'content':'Joined Feb 20, 2012' if name=='MrBeast' else 'Joined Sep 20, 2018'},
        'subscriberCountText':'526M subscribers' if name=='MrBeast' else '1.98M subscribers',
        'videoCountText':'1,012 videos' if name=='MrBeast' else '280 videos',
        'viewCountText':'146,386,719,125 views' if name=='MrBeast' else '491,633,729 views',
        'links':[
            {'channelExternalLinkViewModel':{'title':{'content':'Official site'},'link':{'content':'example.test/'+name,'commandRuns':[{'onTap':{'innertubeCommand':{'urlEndpoint':{'url':'https://example.test/'+name}}}}]}}},
            {'channelExternalLinkViewModel':{'title':{'content':'Community'},'link':{'content':'t.me/'+name}}},
            {'channelExternalLinkViewModel':{'title':{'content':'Social'},'link':{'content':'instagram.com/'+name}}},
            {'channelExternalLinkViewModel':{'title':{'content':'Repeated site'},'link':{'content':'ignored','commandRuns':[{'onTap':{'innertubeCommand':{'urlEndpoint':{'url':'https://www.youtube.com/redirect?redir_token=DO-NOT-COPY&q=https%3A%2F%2Fexample.test%2F'+name}}}}]}}},
            {'channelExternalLinkViewModel':{'title':{'content':'Invalid'},'link':{'content':'javascript:alert(1)'}}},
        ],
    }
    return {'responseContext':{'trackingParams':'DO-NOT-COPY'},'onResponseReceivedEndpoints':[{'appendContinuationItemsAction':{'continuationItems':[{'aboutChannelRenderer':{'metadata':{'aboutChannelViewModel':model}}}]}}]},model


def install_channel(page,name):
    page.evaluate('''name=>{
        history.replaceState({},'', '/@'+name+'/videos?hl=en');
        const source=document.querySelector('yt-description-preview-view-model');
        const data={descriptionPreviewViewModel:{
            description:{content:'Short '+name+' introduction.'},
            rendererContext:{commandContext:{onTap:{innertubeCommand:{showEngagementPanelEndpoint:{
                engagementPanel:{engagementPanelSectionListRenderer:{targetId:'engagement-panel-channel-about',content:{sectionListRenderer:{contents:[{itemSectionRenderer:{contents:[{
                    continuationItemRenderer:{continuationEndpoint:{commandMetadata:{webCommandMetadata:{apiUrl:'/youtubei/v1/browse'}},continuationCommand:{token:'about:'+name}}}
                }]}}]}}}}
            }}}}}},trackingParams:'DO-NOT-COPY'};
        source.data=data;
        document.querySelector('ytd-browse').data={metadata:{channelMetadataRenderer:{ownerUrls:['https://www.youtube.com/@'+name],externalId:'UCfixture'+name,description:'Short '+name+' introduction.'}},header:{pageHeaderRenderer:{content:{pageHeaderViewModel:{description:data}}}}};
        window.ytInitialData={metadata:{channelMetadataRenderer:{vanityChannelUrl:'https://www.youtube.com/@PreviousChannel',description:'DO-NOT-COPY stale biography'}}};
        document.querySelector('#author-description').textContent='Short '+name+' introduction.';
        document.querySelector('#description-more').onclick=()=>window.__nativeAttempts=(window.__nativeAttempts||0)+1;
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''',name)


def setup(browser,name,width):
    page=browser.new_page(viewport={'width':width,'height':720})
    page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html; charset=utf-8',body=document(fixture())))
    requests=[];pending=[];errors=[]
    def browse(route):
        requests.append(route.request.post_data_json);pending.append(route)
    page.route('https://www.youtube.com/youtubei/v1/browse?**',browse)
    page.context.route('https://example.test/**',lambda route:route.fulfill(content_type='text/html',body='Local external-link target'))
    page.on('pageerror',lambda error:errors.append(error))
    page.goto('https://www.youtube.com/@'+name+'/videos?hl=en')
    if name=='DERGIDVER':page.evaluate('document.documentElement.setAttribute("dark","")')
    page.add_style_tag(path=str(ROOT/'src/styles/styles.css'))
    install_channel(page,name)
    page.evaluate('''()=>{
        document.querySelector('ytd-browse').style.minHeight='4000px';
        window.ytcfg={get:key=>({
            INNERTUBE_CONTEXT:{client:{clientName:'WEB',clientVersion:'test-version',visitorData:'DO-NOT-COPY'}},
            INNERTUBE_API_KEY:'public-client-key'
        })[key]};
        window.addEventListener('wheel',event=>event.preventDefault(),{capture:true,passive:false});
    }''')
    page.add_script_tag(path=str(ROOT/'src/content/channel-main.js'))
    session=page.context.new_cdp_session(page)
    frame=session.send('Page.getFrameTree')['frameTree']['frame']['id']
    world=session.send('Page.createIsolatedWorld',{'frameId':frame,'worldName':'full-channel-about'})['executionContextId']
    def evaluate(code):
        result=session.send('Runtime.evaluate',{'expression':code,'contextId':world,'returnByValue':True})
        assert not result.get('exceptionDetails'),result.get('exceptionDetails')
        return result.get('result',{}).get('value')
    evaluate('('+MOCK+')({enabled:true});chrome.runtime.id="channel-details";')
    assert evaluate('document.querySelector("yt-description-preview-view-model").data===undefined')
    for module in ['ads','watch','playlist','search-data','search','channel','content']:
        evaluate((ROOT/'src/content'/f'{module}.js').read_text())
    return page,page.locator('#myt-channel-description'),requests,pending,errors


def full_dialog(browser,name,width):
    page,host,requests,pending,errors=setup(browser,name,width)
    assert not requests,'About data must be loaded only after opening the dialog'
    host.locator('.more').click()
    expect(host.locator('.details-status')).to_have_text('Loading channel details…')
    assert len(requests)==1
    assert requests[0]=={'continuation':'about:'+name,'context':{'client':{'clientName':'WEB','clientVersion':'test-version','visitorData':'DO-NOT-COPY','hl':'en'}}}
    payload,model=response(name)
    pending.pop().fulfill(content_type='application/json',body=json.dumps(payload))
    expect(host.locator('.full-text')).to_have_text(model['description'])
    expect(host.locator('.links-section h3')).to_have_text('Links')
    expect(host.locator('.external-link')).to_have_count(3)
    expect(host.locator('.link-title')).to_have_text(['Official site','Community','Social'])
    expect(host.locator('.info-section h3')).to_have_text('More info')
    expect(host.locator('.full-info dt')).to_have_text(['Channel','Country','Joined','Subscribers','Videos','Views'])
    expect(host.locator('.full-info dd')).to_have_text(['@'+name,model['country'],model['joinedDateText']['content'].removeprefix('Joined '),model['subscriberCountText'].removesuffix(' subscribers'),model['videoCountText'].removesuffix(' videos'),model['viewCountText'].removesuffix(' views')])
    expect(host.locator('.details-status')).to_be_hidden()
    snapshot=page.locator('yt-description-preview-view-model').get_attribute('data-myt-channel-description-data')
    assert not any(value in snapshot for value in ['DO-NOT-COPY','public-client-key','about:'+name])
    body=host.locator('.full-body');body.hover();page.mouse.wheel(0,320)
    page.wait_for_function('document.querySelector("#myt-channel-description").shadowRoot.querySelector(".full-body").scrollTop>=300')
    assert body.evaluate('e=>e.offsetWidth>e.clientWidth'),'The scrollport must expose its vertical scrollbar'
    before=body.evaluate('e=>e.scrollTop');box=body.bounding_box()
    page.mouse.click(box['x']+box['width']-5,box['y']+box['height']-35)
    page.wait_for_function('(before)=>document.querySelector("#myt-channel-description").shadowRoot.querySelector(".full-body").scrollTop>before',arg=before)
    body.focus();page.keyboard.press('End')
    expect(host.locator('.full-info dd').last).to_be_in_viewport()
    expect(host.locator('.close')).to_be_in_viewport()
    assert page.evaluate('scrollY')==0
    Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
    page.screenshot(path=f'/tmp/yt-min-qa/full-channel-{name}-{width}.png')
    with page.context.expect_page() as opened:host.locator('.external-link').first.click()
    external=opened.value;external.wait_for_load_state()
    assert external.url=='https://example.test/'+name
    assert external.evaluate('opener===null')
    external.close()
    host.locator('.close').click();host.locator('.more').click()
    expect(host.locator('.external-link')).to_have_count(3)
    assert len(requests)==1,'Reopening must reuse loaded details'
    host.locator('.close').click()
    assert not errors,errors
    page.close()
    print(f'PASS full delayed About data, safe links, channel details, one scrollport and reopen cache: {name}, {width}px',flush=True)


def retry_and_navigation(browser):
    page,host,requests,pending,errors=setup(browser,'MrBeast',1440)
    host.locator('.more').click()
    expect(host.locator('.details-status')).to_have_text('Loading channel details…')
    pending.pop().fulfill(status=503,content_type='application/json',body='{}')
    expect(host.locator('.retry')).to_be_visible()
    host.locator('.retry').click()
    expect(host.locator('.details-status')).to_have_text('Loading channel details…')
    old=pending.pop();host.locator('.close').click()
    install_channel(page,'DERGIDVER')
    expect(host.locator('.summary')).to_have_text('Short DERGIDVER introduction.')
    old.fulfill(content_type='application/json',body=json.dumps(response('MrBeast')[0]))
    host.locator('.more').click()
    expect(host.locator('.details-status')).to_have_text('Loading channel details…')
    pending.pop().fulfill(content_type='application/json',body=json.dumps(response('DERGIDVER')[0]))
    expect(host.locator('.full-text')).to_have_text(response('DERGIDVER')[1]['description'])
    assert 'MrBeast' not in host.locator('.full-body').text_content()
    assert [request['continuation'] for request in requests]==['about:MrBeast','about:MrBeast','about:DERGIDVER']
    assert not errors,errors
    page.close()
    print('PASS visible failure/retry and stale-response isolation between channels',flush=True)


def late_metadata_and_embedded_details(browser):
    page,host,requests,pending,errors=setup(browser,'MrBeast',1440)
    host.locator('.more').click()
    expect(host.locator('.details-status')).to_have_text('Loading channel details…')
    full='Late current-channel biography.\n'+('Public author text with original line breaks.\n'*50)
    page.evaluate('''full=>{
        document.querySelector('ytd-browse').data.metadata.channelMetadataRenderer.description=full;
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''',full)
    expect(host.locator('.full-text')).to_have_text(full)
    pending.pop().fulfill(content_type='application/json',body=json.dumps(response('MrBeast')[0]))
    expect(host.locator('.external-link')).to_have_count(3)
    expect(host.locator('.full-text')).to_have_text(response('MrBeast')[1]['description'])
    assert not errors,errors
    page.close()
    page,host,requests,pending,errors=setup(browser,'DERGIDVER',390)
    page.evaluate('''model=>{
        document.querySelector('yt-description-preview-view-model').data.about={aboutChannelViewModel:model};
        document.dispatchEvent(new Event('yt-page-data-updated'));
    }''',response('DERGIDVER')[1])
    host.locator('.more').click()
    expect(host.locator('.external-link')).to_have_count(3)
    expect(host.locator('.full-info dd').last).to_have_text('491,633,729')
    assert not requests,'Embedded public about data must not cause another request'
    assert not errors,errors
    page.close()
    print('PASS late browse metadata updates an open modal; embedded details render without fetching',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,ignore_default_args=['--hide-scrollbars'],args=['--no-sandbox'])
        for name in ('MrBeast','DERGIDVER'):
            for width in (1440,390):full_dialog(browser,name,width)
        retry_and_navigation(browser)
        late_metadata_and_embedded_details(browser)
        browser.close()
