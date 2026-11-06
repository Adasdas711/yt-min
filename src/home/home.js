"use strict";
// No YouTube bundle, renderer tree, preview decoder or feed is started here.
document.documentElement.lang = new URLSearchParams(location.search).get("hl") || navigator.language;
if (matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.setAttribute("dark", "");
