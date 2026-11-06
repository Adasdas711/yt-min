"use strict";

(() => {
    let russian = navigator.language.toLowerCase().startsWith("ru");
    const translations = { ru: {
        tagline: "Больше внимания. Меньше шума.",
        title: "Режим фокуса",
        on: "Включён",
        off: "Выключен",
        details: "Чистая главная, каналы по центру и видео без Shorts и рекомендаций.",
        footer: "Обновите вкладки YouTube, чтобы применить экономию памяти.",
        disabledFooter: "Обновите YouTube, чтобы вернуть все его блоки.",
        readError: "Не удалось загрузить настройки. Откройте расширение заново.",
        saveError: "Не удалось сохранить. Попробуйте ещё раз.",
    }, en: {
        tagline: "More focus. Less noise.",
        title: "Focus mode",
        on: "Enabled",
        off: "Disabled",
        details: "A clean home, centered channels, and videos without Shorts or recommendations.",
        footer: "Reload YouTube tabs to apply memory savings.",
        disabledFooter: "Reload YouTube to restore all of its sections.",
        readError: "Could not load settings. Please reopen the extension.",
        saveError: "Could not save. Please try again.",
    }};
    let copy = translations[russian ? "ru" : "en"];
    const toggle = document.getElementById("toggle");
    const status = document.getElementById("status");
    const error = document.getElementById("error");
    let enabled = true;
    let ready = false;
    function applyLanguage(value) {
        russian = value === "ru" || (value !== "en" && navigator.language.toLowerCase().startsWith("ru"));
        copy = translations[russian ? "ru" : "en"];
        document.documentElement.lang = russian ? "ru" : "en";
        document.getElementById("tagline").textContent = copy.tagline;
        document.getElementById("setting-title").textContent = copy.title;
        document.getElementById("details").textContent = copy.details;
        document.getElementById("footer").textContent = copy.footer;
    }
    applyLanguage(null);
    function render() {
        toggle.checked = enabled;
        status.textContent = enabled ? copy.on : copy.off;
        document.getElementById("footer").textContent = enabled ? copy.footer : copy.disabledFooter;
    }
    function showError(message) {
        error.textContent = message;
        error.hidden = !message;
    }
    chrome.storage.local.get(["enabled", "language"], (data) => {
        if (chrome.runtime.lastError) {
            status.textContent = "—";
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
            }
            render();
            toggle.disabled = false;
        });
    });
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== "local") return;
        if (changes.language) { applyLanguage(changes.language.newValue); render(); }
        if (!changes.enabled) return;
        enabled = typeof changes.enabled.newValue === "undefined" ? true : Boolean(changes.enabled.newValue);
        render();
    });
})();
