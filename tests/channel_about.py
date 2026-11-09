"""Full channel-description dialog: responsive cards and native interactions."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from smoke import setup, assert_stable
from channel_header import fixture


def about_dialog(legacy=False):
    renderer='ytd-channel-about-metadata-renderer' if legacy else 'ytd-about-channel-renderer'
    links=''.join(f'''<yt-channel-external-link-view-model><yt-icon><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor"/></svg></yt-icon><div>
        <div class="ytChannelExternalLinkViewModelTitle">{title}</div><a id="social-{i}" href="https://example.com/{i}" onclick="event.preventDefault();window.__aboutLink={i}">{url}</a>
        </div></yt-channel-external-link-view-model>''' for i,(title,url) in enumerate([
            ('РЕКЛАМА','vk.com/magic_manager'),('Моё Сообщество!','vk.com/dergdiverofficial'),
            ('telegram','t.me/dergdiver'),('tik-tok','tiktok.com/@dergdiverihodor')]))
    values=['<button id="email" onclick="window.__emailChecks=(window.__emailChecks||0)+1">View email address</button>',
            '<a href="https://www.youtube.com/@DERGIDVER">www.youtube.com/@DERGIDVER</a>',
            'Russia','Joined Sep 20, 2018','1.98M subscribers','280 videos','491,633,729 views']
    rows=''.join(f'<tr><td><yt-icon><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3" fill="none" stroke="currentColor"/></svg></yt-icon></td><td>{value}</td></tr>' for value in values)
    description=('Описание канала. Текст автора сохраняет переносы строк и исходный язык.\n'*5)+ 'Last line of the full description.'
    body=f'''<{renderer} style="width:560px"><div id="description-container"><yt-attributed-string id="description">{description}</yt-attributed-string><a id="description-link" href="https://example.com/author">Author source</a></div>
        <div id="links-section"><h3>Links</h3><div id="link-list-container">{links}</div></div>
        <div id="additional-info-container"><h3>More info</h3><table id="additional-info-table"><tbody>{rows}</tbody></table></div>
        </{renderer}>'''
    if not legacy:
        body='<ytd-engagement-panel-section-list-renderer target-id="engagement-panel-channel-about" style="width:600px"><div id="header"><h2>About this channel</h2><button id="close-about" aria-label="Close" onclick="document.querySelector(\'#about-dialog\').hidden=true">×</button></div><div id="content">'+body+'</div></ytd-engagement-panel-section-list-renderer>'
    else:
        body='<div id="header"><h2>About this channel</h2><button id="close-about" aria-label="Close" onclick="document.querySelector(\'#about-dialog\').hidden=true">×</button></div>'+body
    return '''<style>
        ytd-popup-container{position:fixed;inset:0;pointer-events:none;z-index:1000}
        tp-yt-paper-dialog{display:block;pointer-events:auto;position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:600px;max-width:calc(100vw - 32px);max-height:90vh;overflow:auto;background:#202020;color:#eee;font:16px/1.5 Arial,sans-serif}
        tp-yt-paper-dialog[hidden]{display:none!important}ytd-engagement-panel-section-list-renderer{display:block}
        #about-dialog #header{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;background:inherit}
        #about-dialog #header h2{margin:0;font-size:20px}#close-about{font:24px Arial;border:0;background:none;color:inherit;cursor:pointer}
        yt-channel-external-link-view-model{display:flex;gap:16px;margin-bottom:16px}yt-icon{display:inline-block;width:28px;height:28px;flex:none}yt-icon svg{width:100%;height:100%}
        #about-dialog a{color:#3ea6ff;text-decoration:none}#about-dialog td{padding:12px}#link-list-container{display:block}
        </style><ytd-popup-container><tp-yt-paper-dialog id="about-dialog" role="dialog" aria-label="About this channel">'''+body+'</tp-yt-paper-dialog><tp-yt-paper-dialog id="unrelated-dialog" hidden style="width:420px">Share video</tp-yt-paper-dialog></ytd-popup-container>'


def check(browser,width,dark,legacy,fallback=False):
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=dark)
    markup=about_dialog(legacy)
    if fallback:markup=markup.replace('ytd-about-channel-renderer','native-about-content')
    page.locator('#description-more').evaluate('(e,html)=>e.onclick=()=>document.body.insertAdjacentHTML("beforeend",html)',markup)
    page.locator('#description-more').click()
    modal=page.get_by_role('dialog',name='About this channel',exact=True)
    expect(modal).to_be_visible()
    expect(page.locator('[data-myt-channel-about-link]')).to_have_count(4)
    expect(page.locator('[data-myt-channel-about-info-row]')).to_have_count(7)
    bounds=modal.bounding_box()
    assert bounds['x']>=0 and bounds['x']+bounds['width']<=width, bounds
    if width>=900:assert bounds['width']>=width-64 if width<1100 else bounds['width']>=1000,bounds
    else:assert bounds['width']>=width-28,bounds
    assert bounds['y']>=0 and bounds['y']+bounds['height']<=960,bounds
    description=page.locator('#about-dialog #description')
    expect(description).to_contain_text('Last line of the full description.')
    assert 'Mono' in description.evaluate('e=>getComputedStyle(e).fontFamily')
    expect(page.locator('#description-link')).to_have_attribute('href','https://example.com/author')
    cards=page.locator('[data-myt-channel-about-link]')
    boxes=[card.bounding_box() for card in cards.all()]
    if width>=900:
        assert abs(boxes[0]['y']-boxes[1]['y'])<1 and boxes[1]['x']>boxes[0]['x'],boxes
    else:
        assert boxes[1]['y']>boxes[0]['y'] and abs(boxes[0]['x']-boxes[1]['x'])<1,boxes
    for card in cards.all():
        assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
    page.locator('#social-2').click()
    assert page.evaluate('__aboutLink')==2
    page.locator('#email').click()
    assert page.evaluate('__emailChecks')==1
    assert page.evaluate('scrollY')==0
    expect(page.locator('#close-about')).to_be_in_viewport()
    assert page.locator('#unrelated-dialog').evaluate('e=>e.hasAttribute("data-myt-channel-about-dialog")') is False
    page.wait_for_timeout(100)
    assert_stable(page)
    # A reused popup host must lose channel styling when it displays another dialog.
    page.locator('#about-dialog').evaluate('e=>{window.__aboutMarkup=e.innerHTML;e.innerHTML="<button id=share-action>Share</button>"}')
    expect(page.locator('#about-dialog')).not_to_have_attribute('data-myt-channel-about-dialog')
    assert page.locator('#about-dialog').evaluate('e=>parseFloat(getComputedStyle(e).width)')==min(600,width-32)
    page.locator('#about-dialog').evaluate('e=>e.innerHTML=window.__aboutMarkup')
    expect(page.locator('[data-myt-channel-about-link]')).to_have_count(4)
    # Verify that cards added by a native renderer update get styled as well.
    page.locator('#link-list-container').evaluate('e=>{const copy=e.firstElementChild.cloneNode(true);copy.removeAttribute("data-myt-channel-about-link");e.append(copy)}')
    expect(page.locator('[data-myt-channel-about-link]')).to_have_count(5)
    page.locator('#email').click()
    assert page.evaluate('__emailChecks')==2
    if not legacy:
        Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
        page.locator('[data-myt-channel-about-scroll]').evaluate('e=>e.scrollTop=0')
        page.screenshot(path=f'/tmp/yt-min-qa/about-{width}-{dark}.png')
        page.locator('#email').scroll_into_view_if_needed()
        page.screenshot(path=f'/tmp/yt-min-qa/about-info-{width}-{dark}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-channel-about]')).to_have_count(0)
    assert modal.evaluate('e=>parseFloat(getComputedStyle(e).width)')==min(600,width-32)
    page.locator('#close-about').click()
    expect(modal).to_be_hidden()
    page.close()
    print(f'PASS wider about dialog, responsive link/info cards, native links/email/close, restamps and restoration: {width}px, dark={dark}, legacy={legacy}, fallback={fallback}',flush=True)


def readable_description_and_info(browser,width,dark):
    markup=about_dialog()
    start=markup.index('<div id="description-container">')
    end=markup.index('</div>',start)+len('</div>')
    paragraphs=['SUBSCRIBE FOR A COOKIE!', 'New MrBeast Gaming video every single Saturday at noon eastern time!',
                'Helped people around the world and built an animal shelter.',
                'A long description must wrap inside the dialog instead of painting over adjacent lines. '*3]
    lines=''.join(f'<span id="about-line-{i}">{text}</span><br>' for i,text in enumerate(paragraphs))
    inline='<yt-attributed-string><span id="description" class="yt-core-attributed-string">'+lines+'<a id="description-link" href="https://example.com/author" onclick="event.preventDefault();window.__authorVisits=(window.__authorVisits||0)+1">Author source</a></span></yt-attributed-string>'
    markup=markup[:start]+inline+markup[end:]
    empty='<tr id="empty-phone"><td><yt-icon><svg><title>Phone</title></svg></yt-icon></td><td><button aria-label="More info"><svg><title>Information</title></svg></button></td></tr>'
    markup=markup.replace('<tbody>','<tbody>'+empty,1)
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=dark)
    page.locator('#description-more').evaluate('(e,html)=>e.onclick=()=>document.body.insertAdjacentHTML("beforeend",html)',markup)
    page.locator('#description-more').click()
    page.wait_for_selector('[data-myt-channel-about-description]')
    description=page.locator('#about-dialog #description')
    # An inline span needs a single panel box, rather than a padded fragment for
    # each text line (those fragments painted over the previous line of text).
    assert description.evaluate('e=>e.getClientRects().length')==1
    bounds=description.bounding_box()
    assert bounds['x']>=0 and bounds['x']+bounds['width']<=width,bounds
    last=None
    for i,text in enumerate(paragraphs):
        paragraph=page.locator('#about-line-'+str(i))
        expect(paragraph).to_have_text(text.strip())
        rect=paragraph.bounding_box()
        if last:assert rect['y']>=last['y']+last['height']-1,(last,rect)
        assert rect['x']>=bounds['x'] and rect['x']+rect['width']<=bounds['x']+bounds['width'],rect
        last=rect
    page.locator('#description-link').click()
    assert page.evaluate('__authorVisits')==1
    expect(page.locator('#empty-phone')).to_be_hidden()
    rows=page.locator('[data-myt-channel-about-info-row]:visible')
    expect(rows).to_have_count(7)
    boxes=[row.bounding_box() for row in rows.all()]
    for previous,current in zip(boxes,boxes[1:]):
        assert abs(previous['x']-current['x'])<1 and current['y']>=previous['y']+previous['height'],(previous,current)
    page.locator('#email').click()
    assert page.evaluate('__emailChecks')==1
    # Empty/loading native rows must reappear when a real value arrives.
    page.locator('#empty-phone td').last.evaluate('e=>e.textContent="Business phone: +1 555 0100"')
    expect(page.locator('#empty-phone')).to_be_visible()
    page.locator('#empty-phone td').last.evaluate('e=>e.textContent=""')
    expect(page.locator('#empty-phone')).to_be_hidden()
    page.wait_for_timeout(100)
    assert_stable(page)
    Path('/tmp/yt-min-qa').mkdir(exist_ok=True)
    page.locator('[data-myt-channel-about-scroll]').evaluate('e=>e.scrollTop=0')
    page.screenshot(path=f'/tmp/yt-min-qa/readable-about-{width}.png')
    page.locator('[data-myt-channel-about-scroll]').evaluate('e=>e.scrollTop=e.scrollHeight')
    page.screenshot(path=f'/tmp/yt-min-qa/compact-info-{width}.png')
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#empty-phone')).to_be_visible()
    page.close()
    print(f'PASS inline attributed description remains readable, compact info list, empty/loading rows and native actions: {width}px, dark={dark}',flush=True)


def unique_links(browser,width):
    markup=about_dialog()
    empty='<div id="reserve-links"><h3>Links</h3><div id="links-container"><div></div></div></div>'
    markup=markup.replace('<div id="additional-info-container">',empty+'<div id="additional-info-container">',1)
    page=setup(browser,'/@JoeSpeen/videos',fixture(),width=width,native_dark=True)
    page.locator('#description-more').evaluate('(e,html)=>e.onclick=()=>document.body.insertAdjacentHTML("beforeend",html)',markup)
    page.locator('#description-more').click()
    heading=page.get_by_role('heading',name='Links',exact=True)
    expect(heading).to_have_count(1)
    expect(page.locator('#links-section a')).to_have_count(4)
    page.locator('#social-1').click()
    assert page.evaluate('__aboutLink')==1
    # A second hydrated renderer can contain the same destinations but fresh
    # YouTube redirect tokens. It must not paint a second Links panel.
    page.locator('#reserve-links').evaluate('''e=>{
        const original=document.querySelector('#links-section');
        e.innerHTML=original.innerHTML;
        for(const a of e.querySelectorAll('a'))a.href='https://www.youtube.com/redirect?event=channel_description&redir_token=new&q='+encodeURIComponent(a.href);
    }''')
    expect(heading).to_have_count(1)
    expect(page.locator('#reserve-links')).to_be_hidden()
    # If the original native renderer is removed, the replacement takes over.
    page.locator('#links-section').evaluate('e=>{window.__originalLinks=e.cloneNode(true);e.remove()}')
    expect(page.locator('#reserve-links')).to_be_visible()
    expect(heading).to_have_count(1)
    expect(page.locator('#reserve-links a')).to_have_count(4)
    # A genuinely new destination is preserved, even in a separate native group.
    page.locator('#reserve-links').evaluate('''e=>e.insertAdjacentHTML('afterend','<div id="unique-group"><h3>Links</h3><div><yt-channel-external-link-view-model><a href="https://example.org/unique">Unique website</a></yt-channel-external-link-view-model></div></div>')''')
    expect(page.get_by_role('link',name='Unique website')).to_be_visible()
    # Native hidden populated copies stay hidden rather than replacing the live list.
    page.locator('#reserve-links').evaluate('''e=>{const hidden=e.cloneNode(true);hidden.id='hidden-links';hidden.hidden=true;e.before(hidden)}''')
    expect(page.locator('#hidden-links')).to_be_hidden()
    expect(page.locator('#reserve-links')).to_be_visible()
    page.locator('#reserve-links').evaluate('e=>e.innerHTML="<h3>Links</h3><div id=links-container></div>"')
    expect(page.locator('#reserve-links')).to_be_hidden()
    page.locator('#unique-group').evaluate('e=>e.remove()')
    expect(heading).to_have_count(0)
    # Restore the original populated renderer and reopen the same native dialog.
    page.locator('#hidden-links').evaluate('e=>e.after(window.__originalLinks)')
    expect(heading).to_have_count(1)
    page.locator('#close-about').click()
    page.locator('#about-dialog').evaluate('e=>e.hidden=false')
    expect(heading).to_have_count(1)
    page.wait_for_timeout(100)
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('#reserve-links')).to_be_visible()
    page.close()
    print(f'PASS empty/duplicate Links sections, redirect URLs, native restamps, replacements and reopen: {width}px',flush=True)


if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for legacy in (False,True):
            for width,dark in ((1440,True),(900,False),(390,True)):
                check(browser,width,dark,legacy)
        check(browser,900,True,False,True)
        for width,dark in ((1440,True),(900,False),(390,True)):
            readable_description_and_info(browser,width,dark)
        for width in (1440,390):
            unique_links(browser,width)
        browser.close()
