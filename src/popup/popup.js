"use strict";

(() => {
    const russian = false;
    const translations = { ru: {
        title: "Режим фокуса",
        on: "Включён",
        off: "Выключен",
        reload: "обновите вкладки YouTube",
        readError: "Не удалось загрузить настройки. Откройте расширение заново.",
        saveError: "Не удалось сохранить. Попробуйте ещё раз.",
    }, en: {
        title: "Focus mode",
        on: "Enabled",
        off: "Disabled",
        reload: "reload YouTube tabs",
        readError: "Could not load settings. Please reopen the extension.",
        saveError: "Could not save. Please try again.",
    }};
    let copy = translations[russian ? "ru" : "en"];
    const toggle = document.getElementById("toggle");
    const status = document.getElementById("status");
    const error = document.getElementById("error");
    let enabled = true;
    let ready = false;
    let changed = false;
    function applyLanguage(value) {
        // The extension interface is English for every browser/profile language.
        copy = translations[russian ? "ru" : "en"];
        document.documentElement.lang = russian ? "ru" : "en";
        document.getElementById("setting-title").textContent = copy.title;
    }
    applyLanguage(null);
    function render() {
        toggle.checked = enabled;
        // After a change, the status line also says that open tabs need a reload.
        status.textContent = (enabled ? copy.on : copy.off) + (changed ? " · " + copy.reload : "");
    }
    function showError(message) {
        // A symbol on screen; the message is spoken and shown on hover.
        error.querySelector(".visually-hidden").textContent = message;
        error.title = message;
        error.hidden = !message;
    }
    chrome.storage.local.get(["enabled", "language"], (data) => {
        if (chrome.runtime.lastError) {
            status.textContent = "Unknown";
            showError(copy.readError);
            return;
        }
        applyLanguage(data.language);
        enabled = typeof data.enabled === "undefined" ? true : Boolean(data.enabled);
        ready = true;
        render();
        toggle.disabled = false;
    });
    toggle.addEventListener("change", () => {
        if (!ready) return;
        const requested = toggle.checked;
        toggle.disabled = true;
        showError("");
        chrome.storage.local.set({ enabled: requested }, () => {
            if (chrome.runtime.lastError) {
                showError(copy.saveError);
            } else {
                enabled = requested;
                changed = true;
            }
            render();
            toggle.disabled = false;
        });
    });
    // Diagnostics: a report of the open YouTube tab, copied as JSON. It holds
    // page structure and timing only, never cookies or account data.
    const diagnostics = document.getElementById("diagnostics");
    const diagnosticsStatus = document.getElementById("diagnostics-status");
    let diagnosticsReset = 0;
    // The button itself says what happened, then returns to its label.
    const showReport = (state, text) => {
        diagnostics.dataset.state = state;diagnostics.title = text;diagnosticsStatus.textContent = text;
        clearTimeout(diagnosticsReset);
        if (state !== "busy") diagnosticsReset = setTimeout(() => { delete diagnostics.dataset.state;diagnostics.title = "Copy diagnostic report"; }, 2500);
    };
    diagnostics.addEventListener("click", async () => {
        diagnostics.disabled = true;
        showReport("busy", "Collecting…");
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            let host = "";
            try { host = new URL(tab?.url || "").hostname; } catch { /* No readable URL: not a YouTube tab. */ }
            if (!tab || !/(^|\.)youtube\.com$/.test(host)) throw new Error("Open a YouTube tab first.");
            const [result] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, world: "MAIN", func: globalThis.minimalYouTubeDiagnostics });
            const report = { version: chrome.runtime.getManifest().version, enabled, ...(result?.result || { error: "No report" }) };
            await navigator.clipboard.writeText(JSON.stringify(report, null, 1));
            showReport("done", "Copied. Paste it into the chat.");
        } catch (problem) {
            showReport("error", problem?.message === "Open a YouTube tab first." ? problem.message : "Could not collect the report.");
        } finally {
            diagnostics.disabled = false;
        }
    });
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== "local") return;
        if (changes.language) { applyLanguage(changes.language.newValue); render(); }
        if (!changes.enabled) return;
        enabled = typeof changes.enabled.newValue === "undefined" ? true : Boolean(changes.enabled.newValue);
        render();
    });
})();
