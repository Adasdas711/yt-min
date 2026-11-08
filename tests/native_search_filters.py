"""Page-owned filter controls: commands must receive the original trusted input."""
from html import escape


def filters(language='ru', modern=False):
    labels = {
        'ru': ['Фильтры', 'Фильтры поиска', 'Закрыть', 'Дата загрузки', 'Тип', 'Длительность', 'Особенности', 'Упорядочить', 'Сегодня', 'Видео', 'Плейлист', 'Менее 4 минут', 'С субтитрами', 'По числу просмотров'],
        'de': ['Filter', 'Suchfilter', 'Schließen', 'Hochladedatum', 'Typ', 'Dauer', 'Funktionen', 'Sortieren nach', 'Heute', 'Video', 'Playlist', 'Unter 4 Minuten', 'Untertitel', 'Anzahl der Aufrufe'],
    }[language]
    close = "const panel=document.querySelector('#native-filters');" + ('panel.close();' if modern else 'panel.hidden=true;') + "document.querySelector('#native-filters-toggle').setAttribute('aria-expanded','false');"
    groups = ''
    for title, options in zip(labels[3:8], [[(labels[8], 'EgIIAg%3D%3D')], [(labels[9], 'EgIQAQ%3D%3D'), (labels[10], 'EgIQAw%3D%3D')], [(labels[11], 'EgIYAQ%3D%3D')], [(labels[12], 'EgIoAQ%3D%3D')], [(labels[13], 'CAM%3D')]]):
        groups += '<ytd-search-filter-group-renderer><h3>' + title + '</h3>'
        for label, parameter in options:
            action = "event.preventDefault();window.__filterChosen=this.href;window.__filterOptionTrusted=event.isTrusted;" + close
            groups += '<ytd-search-filter-renderer><a href="/results?search_query=fixture&sp=' + parameter + '" onclick="' + escape(action, quote=True) + '">' + label + '</a></ytd-search-filter-renderer>'
        groups += '</ytd-search-filter-group-renderer>'
    panel = ('<dialog id="native-filters" oncancel="document.querySelector(\'#native-filters-toggle\').setAttribute(\'aria-expanded\',\'false\')">' if modern else '<div id="native-filters" hidden>')
    panel += '<ytd-search-filter-dialog-renderer><h2>' + labels[1] + '</h2><button id="native-filters-close" onclick="' + escape(close, quote=True) + '">' + labels[2] + '</button>' + groups + '</ytd-search-filter-dialog-renderer>'
    panel += '</dialog>' if modern else '</div>'
    open_action = "window.__filterClicks=(window.__filterClicks||0)+1;window.__filterButtonTrusted=event.isTrusted;const panel=document.querySelector('#native-filters');"
    open_action += "if(panel.open){panel.close();this.setAttribute('aria-expanded','false');}else{panel.showModal();this.setAttribute('aria-expanded','true');}" if modern else "panel.hidden=!panel.hidden;this.setAttribute('aria-expanded',String(!panel.hidden));"
    toolbar = '<ytd-search-sub-menu-renderer id="native-toolbar"><div id="filter-menu"><yt-button-shape><button id="native-filters-toggle" aria-label="' + labels[0] + '" aria-expanded="false" onclick="' + escape(open_action, quote=True) + '"><svg viewBox="0 0 24 24" width="24" height="24"><path d="M2 6h20M2 18h20" stroke="currentColor"/></svg><span>' + labels[0] + '</span></button></yt-button-shape></div>'
    if not modern:toolbar += panel
    toolbar += '</ytd-search-sub-menu-renderer>'
    return toolbar, ('<ytd-popup-container>' + panel + '</ytd-popup-container>' if modern else '')


NATIVE_STYLE = '''<style>
  #native-toolbar { font:16px/1.5 Arial,sans-serif; }
  #native-filters-toggle,#native-filters-close { display:inline-flex;align-items:center;gap:10px;min-height:44px;padding:8px 12px;border:0;border-radius:12px;background:transparent;color:inherit;font:600 16px Arial,sans-serif;cursor:pointer; }
  #native-filters-toggle svg { width:24px;height:24px; }
  #native-filters { color:var(--myt-ink);background:var(--myt-surface);border:1px solid var(--myt-border);border-radius:16px;padding:20px; }
  #native-filters[hidden] { display:none; }
  #native-filters h2 { font:600 20px Arial,sans-serif; }
  ytd-search-filter-dialog-renderer { display:block; }
  ytd-search-filter-group-renderer { display:inline-block;vertical-align:top;margin:0 24px 16px 0; }
  ytd-search-filter-group-renderer h3 { font:600 16px Arial,sans-serif; }
  ytd-search-filter-renderer a { display:block;padding:10px 0;color:inherit;font:14px Arial,sans-serif; }
</style>'''
