// Run in DevTools Console on a YouTube watch page where the player looks wrong.
// Collects the player's state and the extension's watch layout, then copies a
// JSON report to the clipboard. No page text beyond the video title is read.
(() => {
    const box = node => {
        if (!node) return null;
        const rect = node.getBoundingClientRect(), style = getComputedStyle(node);
        return {
            x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height),
            display: style.display, visibility: style.visibility, opacity: style.opacity, position: style.position,
            transform: style.transform === 'none' ? undefined : style.transform, clip: style.clipPath === 'none' ? undefined : style.clipPath,
            translate: style.translate === 'none' ? undefined : style.translate, background: style.backgroundColor,
            popover: node.getAttribute?.('popover') || undefined, open: node.matches?.(':popover-open') || undefined,
        };
    };
    const attrs = node => node ? Object.fromEntries(node.getAttributeNames().filter(name => !/^(style|class)$/.test(name) || name === 'class').map(name => [name, String(node.getAttribute(name)).slice(0, 160)])) : null;
    const html = document.documentElement, flexy = document.querySelector('ytd-watch-flexy'), player = document.querySelector('#movie_player'), video = document.querySelector('#movie_player video, video.html5-main-video');
    const host = document.querySelector('#myt-watch'), shadow = host?.shadowRoot;
    const islands = [...document.querySelectorAll('[data-myt-watch-island]')].map(node => ({ kind: node.getAttribute('data-myt-watch-island'), tag: node.localName, id: node.id || undefined, box: box(node),
        vars: ['--myt-island-x', '--myt-island-y', '--myt-island-w', '--myt-island-h', '--myt-island-clip'].map(name => [name, node.style.getPropertyValue(name)]).filter(([, value]) => value) }));
    const report = {
        url: location.href.replace(/([?&])(?:pp|si|t)=[^&]*/g, '$1'),
        viewport: { w: innerWidth, h: innerHeight, scrollY: Math.round(scrollY), dpr: devicePixelRatio },
        html: Object.fromEntries(html.getAttributeNames().filter(name => name.startsWith('data-myt') && !/snapshot|model|playlists|channels/.test(name)).map(name => [name, html.getAttribute(name).slice(0, 120)])),
        flexy: { attrs: attrs(flexy), box: box(flexy) },
        player: player ? { class: player.className, box: box(player), state: player.getPlayerState?.(), size: player.getPlayerSize?.(), videoData: (() => { try { const d = player.getVideoData?.(); return d && { id: d.video_id, title: String(d.title || '').slice(0, 120), isLive: d.isLive, author: String(d.author || '').slice(0, 80) }; } catch { return null; } })() } : null,
        video: video ? { box: box(video), videoWidth: video.videoWidth, videoHeight: video.videoHeight, readyState: video.readyState, paused: video.paused, src: Boolean(video.currentSrc), styleAttr: (video.getAttribute('style') || '').slice(0, 200) } : null,
        playerContainers: ['#player', '#player-container-outer', '#player-container-inner', '#player-container', '#full-bleed-container', '#player-full-bleed-container', '#cinematics', '#cinematic-container', 'ytd-player', '.html5-video-container']
            .map(selector => [selector, box(document.querySelector('ytd-watch-flexy ' + selector) || document.querySelector(selector))]).filter(([, value]) => value),
        ownedWatch: host ? { box: box(host), attrs: attrs(host), media: box(shadow?.querySelector('.media')), layout: shadow?.querySelector('.layout')?.className, details: box(shadow?.querySelector('.details')), sidecar: box(shadow?.querySelector('.sidecar')), surfaceVars: shadow ? ['--playlist-player-height', '--playlist-min-height'].map(name => [name, (shadow.querySelector('.surface,[theater]') || host).style?.getPropertyValue(name)]) : null } : null,
        islands,
        errors: (globalThis.__mytErrors || []).slice(-10),
    };
    const text = JSON.stringify(report, null, 1);
    try { copy(text); console.log('Report copied to clipboard (' + text.length + ' chars). Paste it into a file and send it.'); }
    catch { console.log(text); }
    return report;
})();
