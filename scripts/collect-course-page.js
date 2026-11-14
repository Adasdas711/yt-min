// Run in DevTools Console on a YouTube course page (/playlist?list=...).
// Collects the page's DOM shape and YouTube's page data structure, then copies
// a JSON report to the clipboard. Long strings are cut to 80 characters.
(() => {
    const cut = (v, n = 80) => typeof v === 'string' && v.length > n ? v.slice(0, n) + '…' : v;
    // Structure of a data object: every key, arrays reduced to their first 3 items.
    function shape(value, depth = 0) {
        if (depth > 22) return '…';
        if (Array.isArray(value)) return { __array: value.length, items: value.slice(0, 3).map(v => shape(v, depth + 1)) };
        if (value && typeof value === 'object') {
            const out = {};
            for (const [key, child] of Object.entries(value)) {
                if (/^(trackingParams|clickTrackingParams|loggingDirectives|accessibility|accessibilityData)$/.test(key)) continue;
                out[key] = shape(child, depth + 1);
            }
            return out;
        }
        return cut(value);
    }
    // DOM outline: custom elements and elements with id/class, 3 children per level.
    function outline(node, depth = 0) {
        if (!node || depth > 18) return null;
        const kids = [...node.children].filter(c => !/^(STYLE|SCRIPT|TEMPLATE|DOM-IF|DOM-REPEAT|svg|path)$/i.test(c.tagName));
        const attrs = {};
        for (const a of ['id', 'class', 'page-subtype', 'content-type', 'hidden', 'aria-hidden', 'role', 'href'])
            if (node.hasAttribute?.(a)) attrs[a] = cut(node.getAttribute(a), 60);
        for (const a of node.getAttributeNames?.() || []) if (a.startsWith('data-myt')) attrs[a] = cut(node.getAttribute(a), 40);
        const style = getComputedStyle(node);
        return {
            tag: node.tagName.toLowerCase(), ...attrs,
            display: style.display, visibility: style.visibility,
            text: kids.length ? undefined : cut(node.textContent.trim(), 60),
            children: kids.length > 3 ? [...kids.slice(0, 3).map(c => outline(c, depth + 1)), `…+${kids.length - 3}`] : kids.map(c => outline(c, depth + 1)),
        };
    }
    const browses = [...document.querySelectorAll('ytd-browse')];
    const browse = browses.find(b => !b.hidden && b.getClientRects().length) || browses[0];
    const tagCounts = {};
    for (const el of browse?.querySelectorAll('*') || []) if (el.tagName.includes('-')) tagCounts[el.tagName.toLowerCase()] = (tagCounts[el.tagName.toLowerCase()] || 0) + 1;
    const html = document.documentElement;
    const report = {
        url: location.href,
        html: Object.fromEntries(html.getAttributeNames().filter(a => a.startsWith('data-myt') && a !== 'data-myt-page-model' && !/snapshot|playlists|channels/.test(a)).map(a => [a, cut(html.getAttribute(a), 120)])),
        pageModel: cut(html.getAttribute('data-myt-page-model') || '', 400),
        browses: browses.map(b => ({ subtype: b.getAttribute('page-subtype'), hidden: b.hidden, visible: !!b.getClientRects().length })),
        tagCounts,
        firstRowHTML: cut(browse?.querySelector('yt-lockup-view-model,ytd-playlist-video-renderer,ytd-video-renderer,ytd-rich-item-renderer')?.outerHTML || '', 4000),
        dom: outline(browse),
        data: shape(browse?.data),
    };
    const text = JSON.stringify(report, null, 1);
    try { copy(text); console.log('Report copied to clipboard (' + text.length + ' chars). Paste it into a file and send it.'); }
    catch { console.log(text); }
    return report;
})();
