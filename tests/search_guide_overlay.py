"""YouTube's persistent guide must not swallow clicks on the owned search page.

Live diagnosis (Chrome, 1320px wide window, DevTools closed): every click on
the channel photo and on the own Filters button landed in
ytd-app > div#content > tp-yt-app-drawer#guide > #contentContainer >
#guide-wrapper > #guide-content > #guide-inner-content. YouTube opens that
drawer persistently on wide windows; the extension hid ytd-guide-renderer
inside it but not the drawer itself, so an invisible 240px column covered the
left side of the results. Narrower windows (DevTools docked, 884px) use no
persistent guide, which is why everything worked there.
"""
from playwright.sync_api import sync_playwright, expect
from smoke import setup
from search_channel_layout import fixture as channel_fixture

# The real wide-window guide: a fixed drawer inside ytd-app's #content.
GUIDE = '''<tp-yt-app-drawer id="guide" class="style-scope ytd-app" align="start" persistent opened swipe-open>
  <div id="contentContainer" class="style-scope tp-yt-app-drawer" opened persistent>
    <div id="guide-wrapper" class="style-scope ytd-app"><div id="guide-content" class="style-scope ytd-app">
      <div id="guide-inner-content" class="style-scope ytd-app"><ytd-guide-renderer id="guide-renderer" class="style-scope ytd-app"><a href="/feed/subscriptions">Subscriptions</a></ytd-guide-renderer></div>
    </div></div>
  </div>
  <div id="scrim" class="style-scope tp-yt-app-drawer"></div>
</tp-yt-app-drawer>'''
GUIDE_STYLE = '''<style>
  tp-yt-app-drawer#guide { position:fixed;top:0;left:0;bottom:0;width:240px;z-index:2030;visibility:visible; }
  tp-yt-app-drawer #contentContainer { position:absolute;top:0;bottom:0;left:0;width:240px; }
  #guide-wrapper,#guide-content { height:100%; }
  #guide-inner-content { height:100%;overflow-y:auto; }
  tp-yt-app-drawer #scrim { position:absolute;inset:0;opacity:0;visibility:hidden; }
</style>'''
# The live header: the filter button sits in ytd-search-sub-menu-renderer
# (whose data holds only trackingParams); the groups live in the header data.
HEADER = '''<ytd-search-header-renderer class="style-scope ytd-search"><ytd-search-sub-menu-renderer class="style-scope ytd-search-header-renderer">
  <div id="filter-menu" class="style-scope ytd-search-sub-menu-renderer"><div id="container"><ytd-toggle-button-renderer><yt-button-shape>
    <button aria-label="Фильтры поиска"><span>Фильтры</span></button>
  </yt-button-shape></ytd-toggle-button-renderer></div></div>
</ytd-search-sub-menu-renderer></ytd-search-header-renderer>'''
GROUPS = [
    ['Дата загрузки', [['Сегодня', 'EgIIAg%253D%253D'], ['За эту неделю', 'EgIIAw%253D%253D']]],
    ['Тип', [['Видео', 'EgIQAQ%253D%253D'], ['Shorts', 'EgIQCQ%253D%253D'], ['Каналы', 'EgIQAg%253D%253D']]],
    ['Длительность', [['Менее 3 минут', 'EgIYAQ%253D%253D']]],
    ['Особенности', [['Субтитры', 'EgIoAQ%253D%253D']]],
    ['Сортировка', [['По просмотрам', 'CAM%253D']]],
]


def fixture():
    page = channel_fixture('wrapped')
    page = page.replace('<ytd-app>', GUIDE_STYLE + '<ytd-app><div id="content" class="style-scope ytd-app">', 1)
    page = page.replace('<ytd-page-manager>', GUIDE + '<ytd-page-manager id="page-manager" class="style-scope ytd-app">', 1)
    page = page.replace('<ytd-search>', '<ytd-search>' + HEADER, 1)
    return page.replace('</ytd-app>', '</div></ytd-app>')


def install_filter_data(page):
    page.evaluate('''groups => {
      document.querySelector('ytd-search-sub-menu-renderer').data={trackingParams:'CEUQkXUiEwja'};
      document.querySelector('ytd-search-header-renderer').data={searchFilterButton:{buttonRenderer:{command:{openPopupAction:{popup:{searchFilterOptionsDialogRenderer:{
        title:{runs:[{text:'Фильтры поиска'}]},
        groups:groups.map(([title,options])=>({searchFilterGroupRenderer:{title:{simpleText:title},filters:options.map(([label,sp])=>({searchFilterRenderer:{
          label:{simpleText:label},status:'FILTER_STATUS_UNSELECTED',
          navigationEndpoint:{commandMetadata:{webCommandMetadata:{url:'/results?search_query=mrbeast&sp='+sp,webPageType:'WEB_PAGE_TYPE_SEARCH'}},searchEndpoint:{query:'mrbeast',params:sp}}}}))}}))}}}}}}};
      document.dispatchEvent(new Event('yt-page-data-updated'));
      document.querySelector('ytd-search').append(document.createElement('span'));
    }''', GROUPS)


def hit(page, selector):
    """The real hit target at the centre of an owned element."""
    return page.evaluate('''selector => {
      const shadow=document.querySelector('#myt-search').shadowRoot;
      const card=shadow.querySelector('[data-myt-search-channel-card]')?.shadowRoot;
      const node=shadow.querySelector(selector)||card?.querySelector(selector);
      const box=node.getBoundingClientRect(),x=box.x+box.width/2,y=box.y+box.height/2;
      const top=document.elementFromPoint(x,y);
      const inner=top?.shadowRoot?.elementFromPoint(x,y);
      const deepest=inner?.shadowRoot?.elementFromPoint(x,y)||inner||top;
      return {x,y,owned:node===deepest||node.contains(deepest),top:(top?.tagName||'')+'#'+(top?.id||'')};
    }''', selector)


def check(browser, width):
    page = setup(browser, '/results?search_query=mrbeast', fixture(), width=width)
    page.evaluate('''() => {
      window.__channelVisits=0;
      navigation.addEventListener('navigate',event=>{
        const url=new URL(event.destination.url);
        if(url.pathname.startsWith('/@')){event.preventDefault();window.__channelVisits++;}
        else if(url.searchParams.get('sp')){event.preventDefault();window.__filterDestination=url.href;}
      });
    }''')
    install_filter_data(page)
    expect(page.locator('[data-myt-search-channel-card] .avatar img')).to_be_visible()
    expect(page.locator('#myt-search .filters-toggle')).to_be_visible()

    photo = hit(page, '.avatar img')
    if width == 1320: assert photo['x'] < 240, ('fixture must put the photo under the guide column', photo)
    assert photo['owned'], ('the guide covers the channel photo', photo)
    page.mouse.click(photo['x'], photo['y'])
    page.wait_for_function('window.__channelVisits>0', timeout=3000)

    toggle = hit(page, '.filters-toggle')
    assert toggle['owned'], ('the guide covers the Filters button', toggle)
    page.mouse.click(toggle['x'], toggle['y'])
    expect(page.locator('#myt-search .filters-panel')).to_be_visible()
    expect(page.locator('#myt-search .filters-panel .filter-group')).to_have_count(5)
    option = page.locator('#myt-search .filters-panel a').first.bounding_box()
    page.mouse.click(option['x'] + option['width'] / 2, option['y'] + option['height'] / 2)
    page.wait_for_function('window.__filterDestination', timeout=3000)
    assert 'sp=EgIIAg' in page.evaluate('__filterDestination')

    # Disabling the extension returns YouTube's own guide.
    page.evaluate('__setEnabled(false)')
    expect(page.locator('tp-yt-app-drawer#guide')).to_be_visible()
    page.evaluate('__setEnabled(true)')
    expect(page.locator('tp-yt-app-drawer#guide')).to_be_hidden()
    page.close()
    print(f'PASS persistent guide does not cover search clicks: {width}px', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width in [1320, 1440, 1920]:
            check(browser, width)
        browser.close()


if __name__ == '__main__':
    main()
