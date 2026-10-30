"use strict";

(() => {
  const manifest = document.querySelector('link[rel="manifest"]');
  if (!manifest) return;
  const scope = new URL("./", manifest.href);
  // Mantém compatibilidade com o endereço antigo /geral, dentro do novo escopo.
  if (location.pathname === scope.pathname.replace(/\/$/, "")) {
    history.replaceState(null, "", scope.pathname + location.search + location.hash);
  }
  const banner = document.querySelector("#owner-install");
  const button = document.querySelector("#owner-install-button");
  const status = document.querySelector("#owner-install-status");
  const standalone = matchMedia("(display-mode: standalone)");
  let promptEvent = null;
  let installedHere = standalone.matches || navigator.standalone === true;

  function message(text) {
    if (!status) return;
    status.textContent = text;
    status.hidden = !text;
  }

  function update() {
    if (!banner) return;
    banner.hidden = installedHere;
    button.hidden = !promptEvent || installedHere;
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    promptEvent = event;
    message("");
    update();
  });
  window.addEventListener("appinstalled", () => {
    installedHere = true;
    promptEvent = null;
    update();
  });
  standalone.addEventListener("change", () => {
    installedHere = standalone.matches || navigator.standalone === true;
    update();
  });
  button?.addEventListener("click", async () => {
    if (!promptEvent) return;
    const event = promptEvent;
    promptEvent = null;
    button.disabled = true;
    try {
      await event.prompt();
      const choice = await event.userChoice;
      if (choice.outcome === "accepted") installedHere = true;
      else message("Você pode instalar depois pelo ícone de instalação na barra de endereço.");
    } catch {
      message("Use o menu do navegador para instalar o Manager Geral como aplicativo.");
    } finally {
      button.disabled = false;
      update();
    }
  });

  if (!("serviceWorker" in navigator) || !window.isSecureContext) {
    message("Para instalar, abra este painel com HTTPS. No computador local, use localhost ou 127.0.0.1.");
    update();
    return;
  }
  message("Se já instalou, abra pelo atalho Manager Geral. Para instalar, use o ícone na barra de endereço ou o menu do navegador: instalar aplicativo/adicionar à tela inicial.");
  update();
  navigator.serviceWorker.register(new URL("sw.js", scope), { scope: scope.pathname, updateViaCache: "none" })
    .catch(() => {
      message("Não foi possível preparar a instalação. Confira a conexão e recarregue o painel.");
    });
})();
