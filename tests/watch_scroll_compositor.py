"""The player follows page scrolling on the compositor, never on the main thread.

Live: during the first seconds of a watch page only the video's position
lagged while scrolling; the owned page itself scrolled smoothly. YouTube's
startup keeps the main thread busy for seconds, and the player's
scroll-linked animation ran there: it animated translate and clip-path in one
effect, and Chrome cannot composite clip-path (trace: compositeFailed,
unsupportedProperties ["clip-path"]), so the movement fell back to the main
thread too. The movement is now its own translate-only animation that the
compositor runs; only the clip under the header stays a separate effect.
"""
import json
from playwright.sync_api import sync_playwright
from smoke import setup, native_watch_fixture


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = setup(browser, '/watch?v=native', native_watch_fixture())
        page.wait_for_selector('[data-myt-scroll-bound]', state='attached', timeout=5000)
        effects = page.evaluate('''() => document.querySelector('[data-myt-scroll-bound]').getAnimations()
            .map(animation => Object.keys(animation.effect.getKeyframes()[0]).filter(key => ['translate', 'clipPath'].includes(key)).sort().join('+'))''')
        # The movement never shares an effect with a property Chrome cannot composite.
        assert 'translate' in effects and 'clipPath+translate' not in effects, effects
        browser.start_tracing(page=page, categories=['devtools.timeline', 'blink.animations'])
        page.evaluate("() => { for (const animation of document.querySelector('[data-myt-scroll-bound]').getAnimations()) { animation.cancel(); animation.play(); } }")
        page.wait_for_timeout(500)
        trace = json.loads(browser.stop_tracing())
        events = [event.get('args', {}).get('data', {}) for event in (trace['traceEvents'] if isinstance(trace, dict) else trace) if event.get('name') == 'Animation']
        started = [event for event in events if event.get('nodeName', '').startswith('YTD-PLAYER')]
        failed = [event for event in events if 'compositeFailed' in event]
        assert started, events
        # Only the clip may fall back to the main thread; the movement is composited.
        assert len(failed) < len(started), (started, failed)
        assert all(event.get('unsupportedProperties') == ['clip-path'] for event in failed), failed
        page.close()
        browser.close()
        print(f'PASS the player moves on the compositor: {len(started)} scroll effects, {len(failed)} on the main thread (clip only)', flush=True)


if __name__ == '__main__':
    main()
