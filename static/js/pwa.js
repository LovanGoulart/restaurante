"use strict";
let deferredInstall = null,
  swReady = null;
const installButtons = [...document.querySelectorAll(".install-trigger")];
const standalone = () =>
  window.matchMedia("(display-mode: standalone)").matches ||
  navigator.standalone === true;
function installedMarker() {
  try {
    return localStorage.getItem("restaurant-installed") === "yes";
  } catch {
    return false;
  }
}
function updateInstall() {
  if (standalone()) {
    try {
      localStorage.setItem("restaurant-installed", "yes");
    } catch {}
  }
  installButtons.forEach((b) => (b.hidden = standalone() || installedMarker()));
  const banner = document.querySelector("#pwa-prompt");
  if (banner) banner.hidden = standalone() || installedMarker();
}
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstall = e;
  try {
    localStorage.removeItem("restaurant-installed");
  } catch {}
  updateInstall();
});
window.addEventListener("appinstalled", () => {
  deferredInstall = null;
  try {
    localStorage.setItem("restaurant-installed", "yes");
  } catch {}
  installButtons.forEach((b) => (b.hidden = true));
  updateInstall();
  toast("Aplicativo instalado com sucesso.");
});
window
  .matchMedia("(display-mode: standalone)")
  .addEventListener("change", updateInstall);
installButtons.forEach(
  (b) =>
    (b.onclick = async () => {
      if (deferredInstall) {
        const prompt = deferredInstall;
        deferredInstall = null;
        await prompt.prompt();
        await prompt.userChoice;
        return;
      }
      const ios =
        /iPad|iPhone|iPod/.test(navigator.userAgent) ||
        (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
      document.querySelector("#install-help").textContent = !window.isSecureContext
        ? "Para instalar, acesse o sistema por um endereço HTTPS. O endereço HTTP da rede local não permite instalar o PWA."
        : ios
          ? "No Safari, toque em Compartilhar e escolha “Adicionar à Tela de Início”. Depois, abra o Manager pelo ícone instalado."
          : "No menu do Chrome ou Edge, procure “Instalar aplicativo” ou “Adicionar à tela inicial”. Se a opção ainda não aparecer, o navegador pode não oferecer instalação ou o aplicativo já pode estar instalado.";
      document.querySelector("#install-dialog").showModal();
    }),
);
updateInstall();
if ("serviceWorker" in navigator && window.isSecureContext) {
  swReady = navigator.serviceWorker
    .register("/sw.js", { scope: "/" })
    .then(() => navigator.serviceWorker.ready)
    .catch((e) => {
      console.warn("Service worker indisponível:", e.name);
      return null;
    });
}
const pushButton = document.querySelector("#push-toggle"),
  pushHelp = document.querySelector("#push-help");
if (pushButton) {
  let config = null,
    subscribed = false;
  const capable = () =>
    window.isSecureContext &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window;
  function base64bytes(base64) {
    return Uint8Array.from(
      atob(
        base64.replace(/-/g, "+").replace(/_/g, "/") +
          "=".repeat((4 - (base64.length % 4)) % 4),
      ),
      (c) => c.charCodeAt(0),
    );
  }
  async function syncPush() {
    try {
      if (!capable()) {
        pushHelp.textContent =
          "Avisos no dispositivo exigem HTTPS e navegador compatível. No iPhone, instale o app pela Tela de Início.";
        return;
      }
      config = await api("/api/push/config");
      if (!config.available) {
        pushHelp.textContent =
          "Avisos na tela estão ativos. Para avisos com o app fechado, configure o serviço push no servidor (consulte o README).";
        return;
      }
      const reg = await swReady;
      if (!reg) return;
      const sub = await reg.pushManager.getSubscription();
      if (sub && Notification.permission === "granted") {
        await api("/api/push/subscribe", sub.toJSON());
        subscribed = true;
        pushButton.textContent = "🔔 Avisos ativados · desativar";
      }
      pushHelp.textContent = subscribed
        ? "Este dispositivo está inscrito. A entrega depende da conexão e das permissões do sistema."
        : "Ative para receber novos pedidos ou pedidos prontos, conforme seu perfil.";
    } catch (e) {
      pushHelp.textContent = e.message;
    }
  }
  pushButton.onclick = async () => {
    pushButton.disabled = true;
    try {
      if (!capable())
        throw Error(
          "Use HTTPS e um navegador compatível. No iPhone, abra o aplicativo instalado pela Tela de Início.",
        );
      if (!config?.available) {
        config = await api("/api/push/config");
        if (!config.available)
          throw Error(
            "O serviço push precisa ser configurado no servidor. Consulte setup_push.py e run.py no README.",
          );
      }
      const reg = await swReady;
      if (!reg) throw Error("Não foi possível ativar o aplicativo neste navegador.");
      let sub = await reg.pushManager.getSubscription();
      if (subscribed && sub) {
        await api("/api/push/unsubscribe", { endpoint: sub.endpoint });
        await sub.unsubscribe();
        subscribed = false;
        pushButton.textContent = "🔔 Ativar avisos no dispositivo";
        toast("Avisos neste dispositivo desativados.");
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted")
        throw Error(
          "Permissão de notificações não concedida. Ajuste a permissão nas configurações do navegador.",
        );
      sub ??= await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64bytes(config.public_key),
      });
      await api("/api/push/subscribe", sub.toJSON());
      subscribed = true;
      pushButton.textContent = "🔔 Avisos ativados · desativar";
      pushHelp.textContent =
        "Dispositivo inscrito para receber os avisos do seu perfil.";
      toast("Notificações ativadas neste dispositivo.");
    } catch (e) {
      toast(e.message);
      pushHelp.textContent = e.message;
    } finally {
      pushButton.disabled = false;
    }
  };
  syncPush();
}
