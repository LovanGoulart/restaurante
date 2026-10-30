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
      ? "♪ Som ativado · toque para silenciar"
      : "♪ Ativar som dos avisos";
    status.textContent = !supported
      ? "Este navegador não oferece áudio para os alertas."
      : !enabled
        ? "Som desativado. Ative para ouvir novos avisos."
        : running
          ? "Som liberado para os avisos desta sessão."
          : "Som ativado. A liberação do áudio será tentada ao interagir com a página.";
    panel.hidden = !supported || enabled;
    panelMessage.textContent = enabled
      ? "O navegador precisa de um toque para liberar o áudio nesta tela."
      : "Ative para ouvir avisos de pedidos novos ou prontos, conforme seu perfil.";
    enable.textContent = enabled ? "Liberar som ♪" : "Ativar som ♪";
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
      [0, 0.25, 0.5].forEach((delay, index) => {
        const oscillator = context.createOscillator(),
          gain = context.createGain(),
          at = context.currentTime + delay;
        oscillator.type = "sine";
        oscillator.frequency.value = index === 1 ? 880 : 660;
        oscillator.connect(gain);
        gain.connect(context.destination);
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.17, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.2);
        oscillator.onended = () => {
          oscillator.disconnect();
          gain.disconnect();
        };
        oscillator.start(at);
        oscillator.stop(at + 0.22);
      });
      return true;
    } catch {
      status.textContent =
        "Não foi possível tocar o som. Confira as permissões de áudio do navegador.";
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
        "O navegador não liberou o áudio. Confira o volume e a permissão de som.";
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
        ? "Som de teste reproduzido. Alertas ativados."
        : "Som de teste reproduzido. Ative os avisos para ouvir os próximos pedidos.";
    else
      status.textContent =
        "Não foi possível reproduzir o teste. Confira as permissões e o volume.";
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
  update();
})();
