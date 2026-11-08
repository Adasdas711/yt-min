"""English native search filters after localized/late SPA responses."""
from playwright.sync_api import sync_playwright, expect
from smoke import setup, MASTHEAD, assert_stable, navigate_spa


COPY = {
    'ru': {
        'button': 'Фильтры', 'aria': 'Фильтры поиска',
        'groups': ['Дата загрузки', 'Тип', 'Длительность', 'Особенности', 'Упорядочить'],
        'options': ['За последний час', 'Сегодня', 'На этой неделе', 'В этом месяце', 'В этом году',
                    'Видео', 'Канал', 'Плейлист', 'Фильм', 'Менее 4 минут', '4–20 минут',
                    'Более 20 минут', 'В прямом эфире', 'С субтитрами', 'Лицензия Creative Commons',
                    'Местоположение', 'Купленные', 'По релевантности', 'По числу просмотров', 'По рейтингу'],
        'chips': ['Все', 'Каналы', 'Не просмотрено', 'Просмотрено', 'Недавно загружено'],
        'late': 'Субтитры', 'user': 'Фильтры',
    },
    'de': {
        'button': 'Filter', 'aria': 'Suchfilter',
        'groups': ['Hochladedatum', 'Typ', 'Dauer', 'Eigenschaften', 'Sortieren nach'],
        'options': ['Letzte Stunde', 'Heute', 'Diese Woche', 'Diesen Monat', 'Dieses Jahr',
                    'Video', 'Kanal', 'Playlist', 'Film', 'Unter 4 Minuten', '4 bis 20 Minuten',
                    'Über 20 Minuten', 'Live', 'Untertitel', 'Creative Commons', 'Standort',
                    'Gekauft', 'Relevanz', 'Aufrufanzahl', 'Bewertung'],
        'chips': ['Alle', 'Kanäle', 'Nicht angesehen', 'Angesehen', 'Kürzlich hochgeladen'],
        'late': 'Untertitel', 'user': 'Filter',
    },
}
GROUPS = ['Upload date', 'Type', 'Duration', 'Features', 'Sort by']
OPTIONS = ['Last hour', 'Today', 'This week', 'This month', 'This year', 'Video', 'Channel',
           'Playlist', 'Movie', 'Under 4 minutes', '4–20 minutes', 'Over 20 minutes', 'Live',
           'Subtitles/CC', 'Creative Commons', 'Location', 'Purchased', 'Relevance', 'View count', 'Rating']
CHIPS = ['All', 'Channels', 'Unwatched', 'Watched', 'Recently uploaded']


def check(browser, language, width):
    copy = COPY[language]
    groups = ''.join(f'<ytd-search-filter-group-renderer><h3 id="group-{i}">{label}</h3></ytd-search-filter-group-renderer>'
                     for i, label in enumerate(copy['groups']))
    options = ''.join(f'<ytd-search-filter-renderer><a id="option-{i}" href="/results?search_query=fixture&sp={i}" aria-label="{label}" title="{label}" onclick="event.preventDefault();window.__chosen=this.href;this.setAttribute(\'aria-selected\',\'true\')"><span>{label}</span><svg data-icon width="12" height="12"></svg></a></ytd-search-filter-renderer>'
                      for i, label in enumerate(copy['options']))
    chips = ''.join(f'<yt-chip-cloud-chip-renderer><button id="chip-{i}" aria-label="{label}" onclick="window.__chip={i}">{label}</button></yt-chip-cloud-chip-renderer>'
                    for i, label in enumerate(copy['chips']))
    body = f'''<style>ytd-search-sub-menu-renderer,ytd-search-filter-group-renderer,ytd-search-filter-renderer,tp-yt-iron-collapse{{display:block}}#collapse{{height:0;overflow:hidden}}</style>
      <ytd-app>{MASTHEAD}<ytd-page-manager><ytd-search>
      <ytd-search-sub-menu-renderer><button id="filter-button" aria-label="{copy['aria']}" title="{copy['button']}" aria-expanded="false"><svg data-icon width="16" height="16"></svg><span id="filter-label">{copy['button']}</span></button>
      <tp-yt-iron-collapse id="collapse" hidden>{groups}{options}<input id="user-query" value="{copy['user']}"></tp-yt-iron-collapse></ytd-search-sub-menu-renderer>
      {chips}<ytd-section-list-renderer><div id="contents"><ytd-video-renderer><a id="video-title" href="/watch?v=user">{copy['user']}</a><p id="user-description">{copy['options'][0]}</p></ytd-video-renderer></div></ytd-section-list-renderer>
      </ytd-search></ytd-page-manager></ytd-app>'''
    # Deliberately load localized native data after bootstrap, when a native
    # hl=en redirect cannot fix it. This reproduces stale SPA responses.
    page = setup(browser, '/results?search_query=fixture', body, language=language, width=width, native_dark=True)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.evaluate('''() => {
      window.__filterButton=document.querySelector('#filter-button');
      window.__option=document.querySelector('#option-0');window.__icon=__option.querySelector('svg');
    }''')
    button = page.locator('#filter-button')
    expect(button).to_have_text('Filters')
    expect(button).to_have_attribute('aria-label', 'Search filters')
    expect(button).to_have_attribute('title', 'Filters')
    for i, value in enumerate(GROUPS): expect(page.locator(f'#group-{i}')).to_have_text(value)
    for i, value in enumerate(OPTIONS):
        option = page.locator(f'#option-{i}')
        expect(option).to_have_text(value)
        expect(option).to_have_attribute('aria-label', value)
        expect(option).to_have_attribute('title', value)
        expect(option).to_have_attribute('href', f'/results?search_query=fixture&sp={i}')
    for i, value in enumerate(CHIPS):
        expect(page.locator(f'#chip-{i}')).to_have_text(value)
        expect(page.locator(f'#chip-{i}')).to_have_attribute('aria-label', value)
    expect(page.locator('#video-title')).to_have_text(copy['user'])
    expect(page.locator('#user-description')).to_have_text(copy['options'][0])
    expect(page.locator('#user-query')).to_have_value(copy['user'])
    for _ in range(4):
        button.click(); expect(page.locator('#collapse')).to_be_visible()
        page.locator('#option-0').click()
        assert page.evaluate('__chosen.endsWith("&sp=0")')
        expect(page.locator('#option-0')).to_have_attribute('aria-selected', 'true')
        button.click(); expect(page.locator('#collapse')).to_be_hidden()
    page.locator('#chip-1').click(); assert page.evaluate('__chip===1')
    assert page.evaluate('__filterButton===document.querySelector("#filter-button")&&__option===document.querySelector("#option-0")&&__icon===__option.querySelector("svg")')
    # Native code replaces a label and mounts another option after opening.
    button.click()
    page.locator('#option-0 span').evaluate('(e,label)=>e.firstChild.data=label', copy['late'])
    page.locator('#collapse').evaluate('(e,label)=>e.insertAdjacentHTML("beforeend",`<ytd-search-filter-renderer><a id="late-filter" href="/results?sp=late">${label}</a></ytd-search-filter-renderer>`)', copy['late'])
    expect(page.locator('#option-0')).to_have_text('Subtitles/CC')
    expect(page.locator('#late-filter')).to_have_text('Subtitles/CC')
    page.locator('#filter-label').evaluate('(e,label)=>e.textContent=label', copy['button'])
    expect(button).to_have_text('Filters')
    button.evaluate('(e,label)=>e.title=label', copy['button'])
    expect(button).to_have_attribute('title', 'Filters')
    button.evaluate('(e,label)=>e.setAttribute("aria-label",label)', copy['aria'])
    expect(button).to_have_attribute('aria-label', 'Search filters')
    # Some YouTube layouts mount the filters in a separate popup container.
    close, apply = ('Закрыть', 'Применить') if language == 'ru' else ('Schließen', 'Anwenden')
    page.evaluate('''copy => document.body.insertAdjacentHTML('beforeend',
      `<ytd-popup-container><ytd-search-filter-dialog-renderer><h2 id="popup-heading">${copy.heading}</h2>
      <ytd-search-filter-group-renderer><a id="popup-option" href="/results?sp=popup">${copy.option}</a></ytd-search-filter-group-renderer>
      <button id="popup-close" aria-label="${copy.close}" onclick="window.__closedFilter=true">${copy.close}</button>
      <button id="popup-apply" onclick="window.__appliedFilter=true">${copy.apply}</button></ytd-search-filter-dialog-renderer>
      <div role="dialog" id="unrelated-popup">${copy.user}</div></ytd-popup-container>`)''',
      {'heading': copy['aria'], 'option': copy['late'], 'close': close, 'apply': apply, 'user': copy['user']})
    expect(page.locator('#popup-heading')).to_have_text('Search filters')
    expect(page.locator('#popup-option')).to_have_text('Subtitles/CC')
    expect(page.locator('#popup-close')).to_have_text('Close')
    expect(page.locator('#popup-close')).to_have_attribute('aria-label', 'Close')
    page.locator('#popup-apply').click(); assert page.evaluate('__appliedFilter===true')
    page.locator('#popup-close').click(); assert page.evaluate('__closedFilter===true')
    expect(page.locator('#unrelated-popup')).to_have_text(copy['user'])
    page.locator('#popup-option').evaluate('(e,label)=>e.firstChild.data=label', copy['options'][0])
    expect(page.locator('#popup-option')).to_have_text('Last hour')
    assert_stable(page)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=f'/tmp/yt-min-english-filters-{language}-{width}.png')
    # Restore the latest source copy on disable, including detached/reused nodes.
    page.evaluate('__setEnabled(false)')
    expect(button).to_have_text(copy['button'])
    expect(button).to_have_attribute('aria-label', copy['aria'])
    expect(button).to_have_attribute('title', copy['button'])
    expect(page.locator('#group-0')).to_have_text(copy['groups'][0])
    expect(page.locator('#option-0')).to_have_text(copy['late'])
    expect(page.locator('#late-filter')).to_have_text(copy['late'])
    expect(page.locator('#chip-0')).to_have_text(copy['chips'][0])
    expect(page.locator('#popup-close')).to_have_text(close)
    expect(page.locator('#popup-option')).to_have_text(copy['options'][0])
    page.evaluate('__setEnabled(true)')
    expect(button).to_have_text('Filters')
    expect(page.locator('#option-0')).to_have_text('Subtitles/CC')
    navigate_spa(page, '/@creator/videos')
    page.evaluate('''() => {
      document.querySelector('ytd-search').hidden=true;
      document.querySelector('ytd-page-manager').insertAdjacentHTML('beforeend','<ytd-browse page-subtype="channels"><div id="contents">User channel content</div></ytd-browse>');
    }''')
    expect(button).to_have_text(copy['button'])
    assert not errors, errors
    page.close()
    print(f'PASS English filters/headings/options/chips, native actions, late SPA labels, user content and restore: {language}, {width}px', flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for language in COPY:
            for width in [1440, 390]: check(browser, language, width)
        browser.close()


if __name__ == '__main__': main()
