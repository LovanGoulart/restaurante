/* Som da aplicação: reprodução somente após liberação pelo usuário. */
"use strict";
(() => {
  const user = document.body.dataset.user;
  if (!user) return;
  const key = restaurantURL("/") + "restaurant-sound-" + user,
    toggle = document.querySelector("#sound-toggle"),
    test = document.querySelector("#sound-test"),
    status = document.querySelector("#sound-status"),
    panel = document.querySelector("#sound-panel"),
    enable = document.querySelector("#sound-enable"),
    panelMessage = document.querySelector("#sound-panel-message");
  let enabled = false,
    context = null,
    unlocking = null;
  try {
    enabled = localStorage.getItem(key) === "on";
  } catch {}
  const supported = !!(window.AudioContext || window.webkitAudioContext);
  function update() {
    const running = context?.state === "running";
    toggle.setAttribute("aria-pressed", String(enabled));
    toggle.textContent = enabled
      ? uiText("♪ Som ativado · toque para silenciar")
      : uiText("♪ Ativar som dos avisos");
    status.textContent = !supported
      ? uiText("Este navegador não oferece áudio para os alertas.")
      : !enabled
        ? uiText("Som desativado. Ative para ouvir novos avisos.")
        : running
          ? uiText("Som liberado para os avisos desta sessão.")
          : uiText("Som ativado. A liberação do áudio será tentada ao interagir com a página.");
    panel.hidden = !supported || enabled;
    panelMessage.textContent = enabled
      ? uiText("O navegador precisa de um toque para liberar o áudio nesta tela.")
      : uiText("Ative para ouvir avisos de pedidos novos ou prontos, conforme seu perfil.");
    enable.textContent = enabled ? uiText("Liberar som ♪") : uiText("Ativar som ♪");
    test.disabled = !supported;
    toggle.disabled = !supported;
    enable.disabled = !supported;
  }
  function persist() {
    try {
      localStorage.setItem(key, enabled ? "on" : "off");
    } catch {}
  }
  async function unlock() {
    if (!supported) return false;
    try {
      if (!context || context.state === "closed") {
        const Audio = window.AudioContext || window.webkitAudioContext;
        context = new Audio();
        context.addEventListener("statechange", update);
      }
      if (context.state !== "running") await context.resume();
      update();
      return context.state === "running";
    } catch {
      update();
      return false;
    }
  }
  function play() {
    if (!context || context.state !== "running") {
      update();
      return false;
    }
    try {
      [0, 0.3, 0.6, 1.05, 1.35, 1.65].forEach((delay, index) => {
        const oscillator = context.createOscillator(),
          gain = context.createGain(),
          at = context.currentTime + delay;
        oscillator.type = "triangle";
        oscillator.frequency.value = index % 2 ? 1046 : 784;
        oscillator.connect(gain);
        gain.connect(context.destination);
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.45, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.24);
        oscillator.onended = () => {
          oscillator.disconnect();
          gain.disconnect();
        };
        oscillator.start(at);
        oscillator.stop(at + 0.26);
      });
      return true;
    } catch {
      status.textContent =
        uiText("Não foi possível tocar o som. Confira as permissões de áudio do navegador.");
      return false;
    }
  }
  async function activate() {
    enabled = true;
    persist();
    const ok = await unlock();
    update();
    if (ok) play();
    else
      status.textContent =
        uiText("O navegador não liberou o áudio. Confira o volume e a permissão de som.");
  }
  toggle.onclick = async () => {
    if (enabled) {
      enabled = false;
      persist();
      update();
    } else await activate();
  };
  enable.onclick = activate;
  test.onclick = async () => {
    const ok = await unlock();
    if (ok && play())
      status.textContent = enabled
        ? uiText("Som de teste reproduzido. Alertas ativados.")
        : uiText("Som de teste reproduzido. Ative os avisos para ouvir os próximos pedidos.");
    else
      status.textContent =
        uiText("Não foi possível reproduzir o teste. Confira as permissões e o volume.");
  };
  // A preferência sobrevive à navegação; a liberação do navegador pode precisar de novo toque.
  function gesture() {
    if (enabled && context?.state !== "running" && !unlocking) {
      unlocking = unlock().finally(() => {
        unlocking = null;
      });
    }
  }
  document.addEventListener("pointerdown", gesture, { passive: true });
  document.addEventListener("keydown", gesture);
  document.addEventListener("visibilitychange", update);
  window.RestaurantSound = {
    notify() {
      // Não há API web para detectar o modo silencioso; a vibração é solicitada
      // também quando o som está desativado, respeitando o sistema operacional.
      try {
        if (document.visibilityState === "visible" && navigator.vibrate)
          navigator.vibrate([250, 100, 250, 100, 450]);
      } catch {}
      if (!enabled) return false;
      return play();
    },
    get enabled() {
      return enabled;
    },
    get state() {
      return context?.state || "locked";
    },
  };
  window.addEventListener("storage", (event) => {
    if (event.key === key) {
      enabled = event.newValue === "on";
      update();
      if (enabled) gesture();
    }
  });
  update();
  if (enabled) gesture();
})();
