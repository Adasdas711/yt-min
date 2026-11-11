"""Original YouTube filter controls retain trusted input, commands and parents."""
from playwright.sync_api import sync_playwright,expect
from smoke import setup,MASTHEAD,assert_stable
from search import video
from native_search_filters import filters,NATIVE_STYLE


def check(browser,language,width,modern):
    toolbar,popup=filters(language,modern)
    toolbar='<ytd-search-sub-menu-renderer '+('hidden' if language=='ru' else 'style="display:none"')+'><button onclick="window.__wrongFilter=true">Filters</button></ytd-search-sub-menu-renderer>'+toolbar
    inner_popup=popup if modern and language=='ru' else ''
    body=NATIVE_STYLE+'<ytd-app>'+MASTHEAD+'<ytd-search><div id="native-search-wrapper">'+toolbar+'<ytd-section-list-renderer>'+video(1)+'</ytd-section-list-renderer></div>'+inner_popup+'</ytd-search></ytd-app>'+('' if inner_popup else popup)
    page=setup(browser,'/results?search_query=fixture',body,width=width,language=language,native_dark=True)
    page.evaluate('''()=>{
      window.__originalButton=document.querySelector('#native-filters-toggle');window.__originalPanel=document.querySelector('#native-filters');
      window.__filterParents=[...document.querySelectorAll('#native-toolbar *,#native-filters *')].map(node=>[node,node.parentElement]);
      document.querySelector('ytd-search').addEventListener('click',event=>{if(event.target.closest('#native-filters-toggle'))window.__nativeEventPath=true;});
    }''')
    root=page.locator('#myt-search');button=page.locator('#native-filters-toggle');panel=page.locator('#native-filters')
    # Without page data, the owned filters stay hidden and YouTube's own work.
    expect(root.locator('.filters')).to_be_hidden()
    expect(button).to_have_text('Filters');expect(button).to_have_attribute('aria-label','Filters')
    dimensions=page.evaluate('''()=>{const search=document.querySelector('ytd-search'),s=getComputedStyle(search),host=document.querySelector('#myt-search').getBoundingClientRect(),toolbar=document.querySelector('#native-toolbar').getBoundingClientRect();return{old:(search.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight))*.9,host:host.width,toolbar:toolbar.width,x:host.x,toolbarX:toolbar.x};}''')
    assert abs(dimensions['host']-dimensions['old']*.9)<.05,dimensions
    assert abs(dimensions['host']-dimensions['toolbar'])<.05 and abs(dimensions['x']-dimensions['toolbarX'])<.05,dimensions
    for _ in range(3):
        button.locator('svg').click();expect(panel).to_be_visible()
        assert page.evaluate('__filterButtonTrusted&&__nativeEventPath&&!window.__wrongFilter')
        expect(panel.locator('h3')).to_have_text(['Upload date','Type','Duration','Features','Sort by'])
        option=panel.locator('a',has_text='Video').first
        expect(option).to_have_attribute('href','/results?search_query=fixture&sp=EgIQAQ%3D%3D')
        option.click();expect(panel).to_be_hidden()
        assert page.evaluate('__filterOptionTrusted&&__filterChosen.endsWith("sp=EgIQAQ%3D%3D")')
    button.press('Enter');expect(panel).to_be_visible()
    panel.locator('#native-filters-close').click();expect(panel).to_be_hidden()
    button.press('Space');expect(panel).to_be_visible()
    # YouTube can rerender localized labels and swap the button after startup.
    panel.locator('h3').first.evaluate('node=>node.textContent="Hochladedatum"')
    expect(panel.locator('h3').first).to_have_text('Upload date')
    page.screenshot(path=f'/workspace/yt-min-qa/original-filters-{language}-{width}-{modern}.png',full_page=True)
    if modern:
        page.keyboard.press('Escape');expect(panel).to_be_hidden()
    else:
        panel.locator('#native-filters-close').click();expect(panel).to_be_hidden()
    assert page.evaluate('document.querySelector("#native-filters-toggle")===__originalButton&&document.querySelector("#native-filters")===__originalPanel&&__filterParents.every(([node,parent])=>node.parentElement===parent)')
    # A replacement has its own original handler; no proxy needs rebinding.
    button.evaluate('node=>node.replaceWith(node.cloneNode(true))')
    button.click();expect(panel).to_be_visible();assert page.evaluate('__filterButtonTrusted')
    panel.locator('#native-filters-close').click()
    assert_stable(page)
    page.evaluate('__setEnabled(false)')
    expect(page.locator('[data-myt-search-toolbar],[data-myt-search-layout-path],[data-myt-search-native-ui]')).to_have_count(0)
    expect(panel.locator('h3').first).to_have_text('Hochladedatum')
    page.evaluate('__setEnabled(true)');button.click();expect(panel).to_be_visible()
    assert page.evaluate('__filterButtonTrusted')
    page.close();print(f'PASS original filter button/panel, trusted input, commands, English labels, 10% narrower, restamp and restore: {language}, {width}px, modal={modern}',flush=True)


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for language in ['ru','de']:
            for width in [1440,390]:
                for modern in [False,True]:check(browser,language,width,modern)
        browser.close()


if __name__=='__main__':main()
