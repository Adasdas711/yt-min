/* Native ad controls only: no seeking, playback-rate changes, polling or media
   replacement. Player-response and request filtering run before this fallback. */
(() => {
    "use strict";
    const skipSelector = ".ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button, .ytp-ad-skip-button-container button";
    const controls = skipSelector + ", .ytp-ad-skip-button-container";
    const adParents = ".ytp-ad-module, .ytp-ad-player-overlay, .ytp-ad-skip-button-container";
    class PlayerAds {
        constructor() {
            this.enabled = false;this.player = null;this.frame = 0;this.clicked = new WeakSet();this.active = false;this.controlsObserved = null;
            this.observer = new MutationObserver(records => {
                if (!this.showing()) { if (this.active) { this.active = false;this.clicked = new WeakSet(); }this.observeControls(false);return; }
                if (!this.controlsObserved) { this.observeControls(true);this.queue();return; }
                const relevant = records.some(record => record.type === "attributes" ?
                    record.target === this.player || record.target.matches(controls + "," + adParents) || Boolean(record.target.closest(".ytp-ad-skip-button-container")) :
                    [...record.addedNodes].some(node => node instanceof Element && (node.matches(controls) || node.querySelector(controls))));
                if (relevant) this.queue();
            });
            this.mediaChanged = () => { this.clicked = new WeakSet();this.observeControls(this.showing());if (this.showing()) this.queue(); };
        }
        showing() { return Boolean(this.enabled && this.player?.isConnected &&
            (this.player.classList.contains("ad-showing") || this.player.classList.contains("ad-interrupting"))); }
        setEnabled(enabled) { this.enabled = enabled;if (!enabled) this.bind(null); }
        observeControls(active) {
            if (!this.player || this.controlsObserved === active) return;
            this.observer.disconnect();this.controlsObserved = active;
            // During ordinary playback, observe only the player's ad-state class.
            // Progress-bar/clock style mutations can otherwise arrive every frame.
            this.observer.observe(this.player, active ? { subtree: true, childList: true, attributes: true,
                attributeFilter: ["class", "hidden", "style", "disabled", "aria-disabled", "aria-hidden"] } :
                { attributes: true, attributeFilter: ["class"] });
        }
        bind(player) {
            if (!this.enabled) player = null;
            if (player === this.player) return;
            this.observer.disconnect();cancelAnimationFrame(this.frame);this.frame = 0;
            this.player?.removeEventListener("loadedmetadata", this.mediaChanged, true);
            this.player = player;this.clicked = new WeakSet();this.active = false;this.controlsObserved = null;
            if (!player) return;
            this.observeControls(this.showing());
            player.addEventListener("loadedmetadata", this.mediaChanged, true);
            this.run();
        }
        queue() {
            if (document.hidden) { cancelAnimationFrame(this.frame);this.run(); }
            else if (!this.frame) this.frame = requestAnimationFrame(() => this.run());
        }
        run() {
            this.frame = 0;
            if (!this.showing()) return;
            this.active = true;
            for (const button of this.player.querySelectorAll(skipSelector)) {
                let visible = !button.disabled && button.getAttribute("aria-disabled") !== "true" &&
                    button.getAttribute("aria-hidden") !== "true" && button.getClientRects().length &&
                    getComputedStyle(button).visibility === "visible";
                for (let node = button; visible && node; node = node.parentElement) {
                    if (Number(getComputedStyle(node).opacity) === 0) visible = false;
                    if (node === this.player) break;
                }
                if (!visible) { this.clicked.delete(button);continue; }
                if (this.clicked.has(button)) continue;
                this.clicked.add(button);button.click();break;
            }
        }
    }
    globalThis.MinimalYouTubeAds = PlayerAds;
})();
