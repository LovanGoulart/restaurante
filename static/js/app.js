"use strict";
const money = (n) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    n / 100,
  );
const escapeHTML = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
let toastTimer;
function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 7000);
}
async function api(url, data) {
  const response = await fetch(url, {
    method: data === undefined ? "GET" : "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const result = await response
    .json()
    .catch(() => ({ error: "Não foi possível ler a resposta do servidor." }));
  if (response.status === 401) {
    window.dispatchEvent(new Event("session-expired"));
    throw Error("Sua sessão terminou. Entre novamente.");
  }
  if (!response.ok) {
    const error = Error(result.error || "Operação não permitida.");
    error.status = response.status;
    throw error;
  }
  return result;
}
// Menus usam dialog nativo: foco contido, Escape e retorno ao botão que abriu.
document
  .querySelectorAll("[data-open]")
  .forEach((b) =>
    b.addEventListener("click", () =>
      document.getElementById(b.dataset.open).showModal(),
    ),
  );
document
  .querySelectorAll("[data-close]")
  .forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
document.querySelectorAll("dialog").forEach((d) =>
  d.addEventListener("click", (e) => {
    if (e.target === d) {
      const r = d.getBoundingClientRect();
      if (
        e.clientX < r.left ||
        e.clientX > r.right ||
        e.clientY < r.top ||
        e.clientY > r.bottom
      )
        d.close();
    }
  }),
);
function networkState() {
  const offline = !navigator.onLine;
  document.querySelector("#offline-banner").hidden = !offline;
  document
    .querySelectorAll("[data-network-required]")
    .forEach((b) => (b.disabled = offline));
}
window.addEventListener("offline", networkState);
window.addEventListener("online", networkState);
networkState();
const orders = document.querySelector("#orders");
if (orders) {
  let list = [],
    busy = false,
    fetching = false,
    refreshPending = false,
    paymentId = null,
    driverOptions = [];
  const choices = new Map();
  const labels = {
      aberto: "Aberto",
      em_preparo: "Em preparo",
      pronto: "Pronto",
      saiu_entrega: "Saiu para entrega",
      entregue: "Entregue",
    },
    paymentLabels = {
      pix: "Pix",
      dinheiro: "Dinheiro",
      credito: "Cartão de crédito",
      debito: "Cartão de débito",
    };
  function nextFor(p) {
    return {
      aberto: "em_preparo",
      em_preparo: "pronto",
      pronto: p.modalidade === "entrega" ? "saiu_entrega" : "entregue",
      saiu_entrega: "entregue",
    }[p.status];
  }
  function titleFor(p) {
    return p.canal === "salao"
      ? "Mesa " + p.mesa
      : p.modalidade === "entrega"
        ? "Tele-entrega"
        : "Retirada no caixa";
  }
  function addressHTML(p) {
    if (!p.endereco) return "";
    const a = p.endereco;
    return /* HTML */ `
      <div class="delivery-address">
        <b>Endereço de entrega</b>
        <p>
          ${escapeHTML(a.endereco)}, ${escapeHTML(a.numero)}
          <br />
          ${escapeHTML(a.bairro)}
          <br />
          Referência:
          ${escapeHTML(a.referencia)}${a.telefone ? "<br>Contato: " + escapeHTML(a.telefone) : ""}
        </p>
      </div>
    `;
  }
  function assignmentHTML(p, role) {
    if (role !== "admin" || p.modalidade !== "entrega") return "";
    let info = p.entregador
      ? /* HTML */ `
          <p class="muted">
            Entregador:
            <b>${escapeHTML(p.entregador.nome)}</b>
            ${p.entregador.concluida ? " · entrega concluída" : ""}
          </p>
        `
      : "";
    if (p.entregador?.concluida && p.entregador.forma_pagamento)
      info += /* HTML */ `
        <p class="muted">
          Recebido pelo entregador:
          ${paymentLabels[p.entregador.forma_pagamento] || "Pagamento antecipado"} ·
          ${money(p.entregador.valor_recebido)} ·
          ${p.entregador.acertado ? "conferido" : "a conferir"}
        </p>
      `;
    if (!["pronto", "saiu_entrega"].includes(p.status)) return info;
    const selected = choices.get(p.id) || p.entregador?.id || "";
    return (
      info +
      /* HTML */ `
        <div class="courier-assignment">
          ${
            driverOptions.length
              ? /* HTML */ `
                  <label>
                    Entregador
                    <select id="courier-${p.id}" data-courier-select="${p.id}">
                      <option value="">Selecione um entregador</option>
                      ${driverOptions
                        .map(
                          (u) => /* HTML */ `
                            <option
                              value="${u.id}"
                              ${String(u.id) === String(selected) ? "selected" : ""}
                            >
                              ${escapeHTML(u.nome)}
                            </option>
                          `,
                        )
                        .join("")}
                    </select>
                  </label>
                  <button class="secondary" data-assign="${p.id}">
                    ${p.entregador ? "Reatribuir entrega" : "Enviar com entregador →"}
                  </button>
                `
              : '<p>Cadastre um usuário com perfil entregador em <a href="/cadastros/usuarios">Equipe</a> para atribuir a entrega.</p>'
          }
        </div>
      `
    );
  }
  function render() {
    const filter = document.querySelector("#status-filter").value,
      role = orders.dataset.role,
      channel = document.querySelector("#channel-filter")?.value;
    document.querySelector("#status-summary").innerHTML = Object.keys(labels)
      .map(
        (s) => /* HTML */ `
          <button class="status-card ${s}" data-filter="${s}">
            <span>${labels[s]}</span>
            <b>${list.filter((p) => p.status === s).length}</b>
          </button>
        `,
      )
      .join("");
    orders.innerHTML =
      list
        .filter(
          (p) =>
            (!filter || (filter === "nao_pago" ? !p.pago : p.status === filter)) &&
            (!channel || p.modalidade === channel),
        )
        .map((p) => {
          const online = p.canal === "online",
            next = nextFor(p),
            canAct =
              next &&
              !(
                role === "admin" &&
                p.modalidade === "entrega" &&
                (p.status === "pronto" || (p.status === "saiu_entrega" && p.entregador))
              ) &&
              (role === "admin" ||
                (role === "cozinha" && ["aberto", "em_preparo"].includes(p.status)) ||
                (role === "garcom" && !online && p.status === "pronto"));
          return /* HTML */ `
            <article class="panel order ${p.status} ${online ? "online-order" : ""}">
              <div class="order-head">
                <div class="table-badge">
                  <small>${online ? "PEDIDO ONLINE" : "MESA"}</small>
                  <strong class="${online ? "online-title" : ""}">
                    ${online ? (p.modalidade === "entrega" ? "Tele-entrega" : "Retirada no caixa") : escapeHTML(p.mesa.replace(/^mesa\s*/i, "")) || escapeHTML(p.mesa)}
                  </strong>
                  <div class="order-number">PEDIDO #${p.id}</div>
                </div>
                <span class="pill">${labels[p.status]}</span>
              </div>
              <div class="order-body">
                <div class="order-meta">
                  <span>
                    ${online ? "👤 " + escapeHTML(p.cliente) : "♙ " + escapeHTML(p.garcom)}
                  </span>
                  <time>
                    ${new Date(p.criado + "Z").toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                  </time>
                </div>
                <ul>
                  ${p.itens
                    .map(
                      (i) => /* HTML */ `
                        <li>
                          <span class="item-qty">${i.quantidade}×</span>
                          <div>
                            <b>${escapeHTML(i.nome)}</b>
                            ${
                              i.observacao
                                ? /* HTML */ `
                                    <small>Obs.: ${escapeHTML(i.observacao)}</small>
                                  `
                                : ""
                            }
                          </div>
                        </li>
                      `,
                    )
                    .join("")}
                </ul>
                ${addressHTML(p)}${
                  p.forma_pagamento
                    ? /* HTML */ `
                        <p class="muted">
                          Pagamento escolhido:
                          <b>${paymentLabels[p.forma_pagamento]}</b>
                          ${p.troco_para !== null && p.troco_para !== undefined ? " · Troco para " + money(p.troco_para) : ""}
                        </p>
                      `
                    : ""
                }${
                  p.taxa_entrega
                    ? /* HTML */ `
                        <div class="fee-line">
                          <span>Inclui taxa de entrega</span>
                          <b>${money(p.taxa_entrega)}</b>
                        </div>
                      `
                    : ""
                }
                <div class="total">
                  <strong>${money(p.total)}</strong>
                  <span class="payment-state ${p.pago ? "paid" : ""}">
                    ${p.pago ? "✓ Pago" : "A receber"}
                  </span>
                </div>
                ${
                  canAct
                    ? /* HTML */ `
                        <button
                          class="status-action"
                          data-status="${next}"
                          data-id="${p.id}"
                        >
                          ${p.status === "aberto" ? "Iniciar preparo →" : p.status === "em_preparo" ? "✓ Marcar como pronto" : next === "saiu_entrega" ? "Saiu para entrega →" : online && p.modalidade === "retirada" ? "✓ Confirmar retirada" : "✓ Registrar entrega"}
                        </button>
                      `
                    : ""
                }${assignmentHTML(p, role)}${role === "admin" && !p.pago && p.entregador?.concluida ? '<a class="button-link" href="/acerto-entregadores">Conferir acerto do entregador →</a>' : ""}${
                  role === "admin" && !p.pago && !p.entregador?.concluida
                    ? /* HTML */ `
                        <button class="secondary" data-pay="${p.id}">
                          Registrar pagamento
                        </button>
                      `
                    : ""
                }${
                  role === "cliente" && p.status === "pronto"
                    ? /* HTML */ `
                        <p class="ready-note">
                          ${p.modalidade === "retirada" ? "Seu pedido está pronto! Retire no caixa." : "Seu pedido está pronto e aguarda saída para entrega."}
                        </p>
                      `
                    : ""
                }
              </div>
            </article>
          `;
        })
        .join("") ||
      '<div class="panel empty"><span>✓</span><h3>Nenhum pedido por aqui.</h3><p>Os pedidos deste perfil aparecerão aqui.</p></div>';
  }
  async function refresh() {
    if (busy || fetching) {
      refreshPending = true;
      return;
    }
    fetching = true;
    try {
      list = await api(orders.dataset.api || "/api/pedidos");
      if (orders.dataset.role === "admin")
        driverOptions = await api("/api/entregadores");
      render();
      document.querySelector("#poll-error").hidden = true;
      document.querySelector("#last-updated").textContent =
        "Atualizado às " + new Date().toLocaleTimeString("pt-BR");
    } catch (e) {
      const el = document.querySelector("#poll-error");
      el.textContent = "Atualização interrompida: " + e.message;
      el.hidden = false;
    } finally {
      fetching = false;
      if (refreshPending) {
        refreshPending = false;
        setTimeout(refresh, 50);
      }
    }
  }
  window.refreshOrders = refresh;
  document.querySelector("#status-summary").onclick = (e) => {
    const b = e.target.closest("[data-filter]");
    if (b) {
      document.querySelector("#status-filter").value = b.dataset.filter;
      render();
    }
  };
  orders.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.assign) {
      const id = Number(b.dataset.assign),
        driver = Number(document.querySelector("#courier-" + id).value);
      if (!driver) {
        toast("Selecione um entregador.");
        return;
      }
      busy = true;
      b.disabled = true;
      try {
        await api("/api/pedidos/" + id + "/entregador", { entregador_id: driver });
        choices.delete(id);
        toast("Entrega atribuída com sucesso.");
      } catch (err) {
        toast(err.message);
      } finally {
        busy = false;
        refresh();
      }
      return;
    }
    if (b.dataset.pay) {
      paymentId = +b.dataset.pay;
      const p = list.find((p) => p.id === paymentId);
      document.querySelector("#payment-summary").textContent =
        `${titleFor(p)} · Pedido #${p.id} · ${money(p.total)}`;
      document.querySelector("#payment-method").value = p.forma_pagamento || "pix";
      document.querySelector("#payment-dialog").showModal();
      return;
    }
    busy = true;
    b.disabled = true;
    try {
      await api(`/api/pedidos/${b.dataset.id}/status`, { status: b.dataset.status });
      toast("Pedido atualizado com sucesso.");
    } catch (err) {
      toast(err.message);
    } finally {
      busy = false;
      refresh();
    }
  });
  document.querySelector("#payment-confirm").onclick = async (e) => {
    if (!paymentId) return;
    const b = e.currentTarget;
    b.disabled = true;
    busy = true;
    try {
      await api(`/api/pedidos/${paymentId}/pagar`, {
        forma: document.querySelector("#payment-method").value,
      });
      document.querySelector("#payment-dialog").close();
      toast("Pagamento registrado.");
      paymentId = null;
    } catch (err) {
      toast(err.message);
    } finally {
      b.disabled = false;
      busy = false;
      refresh();
    }
  };
  orders.addEventListener("change", (e) => {
    if (e.target.dataset.courierSelect)
      choices.set(Number(e.target.dataset.courierSelect), e.target.value);
  });
  document.querySelector("#status-filter").onchange = render;
  document.querySelector("#channel-filter")?.addEventListener("change", render);
  document.querySelector("#orders-refresh").onclick = refresh;
  window.addEventListener("orders-updated", refresh);
  window.addEventListener("online", refresh);
  refresh();
  setInterval(() => {
    if (document.visibilityState === "visible") refresh();
  }, 30000);
}
if (document.body.dataset.user) {
  let stream = null,
    unreadCursor = 0,
    inbox = [],
    reconnectTimer = null;
  const seen = new Set();
  function drawInbox(result) {
    inbox = result.items;
    unreadCursor = Math.max(0, ...inbox.map((n) => n.id));
    const count = document.querySelector("#notification-count");
    count.hidden = !result.nao_lidas;
    count.textContent = result.nao_lidas > 99 ? "99+" : result.nao_lidas;
    document.querySelector("#notifications-list").innerHTML =
      inbox
        .map(
          (n) => /* HTML */ `
            <a
              class="notification-item ${n.lida ? "" : "unread"}"
              href="${escapeHTML(n.url || "/pedidos")}"
            >
              <b>${escapeHTML(n.titulo)}</b>
              <p>${escapeHTML(n.mensagem)}</p>
              <time>${new Date(n.criado).toLocaleString("pt-BR")}</time>
            </a>
          `,
        )
        .join("") || "<p>Você está em dia. Os próximos avisos aparecerão aqui.</p>";
  }
  async function loadInbox() {
    try {
      drawInbox(await api("/api/notificacoes"));
    } catch (e) {
      document.querySelector("#notifications-list").textContent = e.message;
    }
  }
  document.querySelector("#notifications-open").onclick = () => {
    document.querySelector("#notifications-dialog").showModal();
    loadInbox();
  };
  document.querySelector("#notifications-read").onclick = async () => {
    try {
      await api("/api/notificacoes/lidas", { ate: unreadCursor });
      loadInbox();
    } catch (e) {
      toast(e.message);
    }
  };
  let latest = Number(document.body.dataset.cursor) || 0;
  function incoming(n) {
    if (!n || !Number.isInteger(n.id) || seen.has(n.id)) return;
    seen.add(n.id);
    if (seen.size > 500) seen.delete(seen.values().next().value);
    latest = Math.max(latest, n.id);
    window.dispatchEvent(new Event("orders-updated"));
    loadInbox();
    if (n.alerta) {
      toast(n.titulo + "\n" + n.mensagem);
      window.RestaurantSound?.notify();
    }
  }
  function live(text, state) {
    const el = document.querySelector("#live-status");

    if (!el) return;

    el.textContent = "● " + text;
    el.className = "live-status " + state;
  }
  function connect() {
    clearTimeout(reconnectTimer);
    if (stream) stream.close();
    if (!navigator.onLine) {
      live("Sem conexão", "reconnecting");
      return;
    }
    if (!window.EventSource) {
      live("Atualização periódica", "reconnecting");
      return;
    }
    stream = new EventSource("/api/eventos?after=" + latest);
    stream.addEventListener("connected", () => {
      live("Ao vivo", "connected");
      window.dispatchEvent(new Event("orders-updated"));
      loadInbox();
    });
    stream.addEventListener("pedido", (e) => {
      try {
        incoming(JSON.parse(e.data));
      } catch {}
    });
    stream.onerror = () =>
      live(navigator.onLine ? "Reconectando" : "Sem conexão", "reconnecting");
  }
  window.addEventListener("session-expired", () => {
    stream?.close();
    live("Entre novamente", "reconnecting");
  });
  window.addEventListener("offline", () => {
    stream?.close();
    live("Sem conexão", "reconnecting");
  });
  window.addEventListener("online", connect);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      loadInbox();
      connect();
      window.dispatchEvent(new Event("orders-updated"));
    }
  });
  document
    .querySelector("#logout-form")
    ?.addEventListener("submit", () => stream?.close());
  if ("serviceWorker" in navigator)
    navigator.serviceWorker.addEventListener("message", (e) => {
      if (e.data?.type === "push-update")
        incoming({
          ...e.data.data,
          titulo: e.data.data.title,
          mensagem: e.data.data.body,
          alerta: true,
        });
    });
  loadInbox();
  connect();
  setInterval(() => {
    if (document.visibilityState === "visible") loadInbox();
  }, 45000);
}
