"use strict";
(() => {
  const root = document.documentElement;
  const dictionary = JSON.parse(document.querySelector("#ui-translations").textContent);
  window.uiText = (source, values) => {
    if (typeof source !== "string") return source;
    const key = source.trim().replace(/\s+/g, " ");
    const translated = Object.hasOwn(dictionary, key) ? dictionary[key] : null;
    const text = translated
      ? source.match(/^\s*/)[0] + translated + source.match(/\s*$/)[0]
      : source;
    return values ? text.replace(/\{(\w+)\}/g, (token, name) =>
      Object.hasOwn(values, name) ? String(values[name]) : token) : text;
  };
  window.uiHtml = (source, values) => String(uiText(source, values)).replace(
    /[&<>"']/g,
    (character) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[character],
  );
  window.uiSize = (label) => {
    const match = label.match(/^(.+?) · (\d+) fatias$/);
    return match ? uiText(match[1]) + " · " + match[2] + " " + uiText("fatias") : label;
  };
  const attributes = "; Path=/; Max-Age=31536000; SameSite=Lax" +
    (location.protocol === "https:" ? "; Secure" : "");
  const setTheme = (theme) => {
    if (!["light", "dark"].includes(theme)) return;
    document.cookie = "manager_theme=" + theme + attributes;
    root.dataset.theme = theme;
    document.querySelectorAll("[data-ui-theme]").forEach(select => { select.value = theme; });
    document.querySelectorAll("[data-ui-theme-toggle]").forEach(button => {
      button.setAttribute("aria-pressed", String(theme === "dark"));
    });
  };
  document.querySelectorAll("[data-ui-language]").forEach(select => {
    select.addEventListener("change", () => {
      const language = select.value;
      if (!["pt-BR", "en", "es"].includes(language)) return;
      document.cookie = "manager_language=" + language + attributes;
      if (language !== root.lang) location.reload();
    });
  });
  document.querySelectorAll("[data-ui-theme]").forEach(select => {
    select.addEventListener("change", () => setTheme(select.value));
  });
  document.querySelectorAll("[data-ui-theme-toggle]").forEach(button => {
    button.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));
  });
})();
