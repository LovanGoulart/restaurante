"use strict";
const money = (n) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    n / 100,
  );
const escapeHTML = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let toastTimer;
function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = uiText(message);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 7000);
}
// Aviso flutuante no aplicativo, inclusive quando um diálogo estiver aberto.
let headsUpTimer;
function notificationHeadsUp(title, message) {
  let box = document.getElementById("notification-heads-up");
  if (!box) {
    box = document.createElement("section");
    box.id = "notification-heads-up";
    box.setAttribute("role", "status");
    box.setAttribute("aria-live", "polite");
    box.setAttribute("popover", "manual");
    const content = document.createElement("div");
    content.append(document.createElement("strong"), document.createElement("p"));
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "×";
    close.setAttribute("aria-label", uiText("Fechar"));
    close.onclick = () => {
      clearTimeout(headsUpTimer);
      if (typeof box.hidePopover === "function" && box.matches(":popover-open")) box.hidePopover();
      box.hidden = true;
    };
    box.append(content, close);
    document.body.append(box);
  }
  box.querySelector("strong").textContent = uiText(title);
  box.querySelector("p").textContent = uiText(message);
  box.hidden = false;
  if (typeof box.showPopover === "function") {
    try { box.showPopover(); } catch {}
  } else {
    box.removeAttribute("popover");
  }
  clearTimeout(headsUpTimer);
  headsUpTimer = setTimeout(() => {
    if (typeof box.hidePopover === "function" && box.matches(":popover-open"))
      box.hidePopover();
    box.hidden = true;
  }, 10000);
}
async function api(url, data) {
  const response = await fetch(restaurantURL(url), {
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
    .catch(() => ({ error: uiText("Não foi possível ler a resposta do servidor.") }));
  if (response.status === 401) {
    window.dispatchEvent(new Event("session-expired"));
    throw Error(uiText("Sua sessão terminou. Entre novamente."));
  }
  if (!response.ok) {
    const error = Error(uiText(result.error) || uiText("Operação não permitida."));
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
  .forEach((b) =>
    b.addEventListener("click", () => b.closest("dialog").close()),
  );
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
  const detail = document.querySelector("#order-detail");
  let selectedOrder = null;
  const fullCards = new Map();
  const desktopBackdrop = document.createElement("div");
  desktopBackdrop.className = "order-detail-backdrop";
  desktopBackdrop.hidden = true;
  document.body.append(desktopBackdrop);
  let detailTrigger = null;
  function showDetail(id) {
    const html = fullCards.get(id);
    if (!detail || !html) {
      if (detail?.open) detail.close();
      return;
    }
    selectedOrder = id;
    const content = document.querySelector("#order-detail-content");
    const container = document.createElement("div");
    container.innerHTML = html;
    const normalized = container.firstElementChild.outerHTML;
    if (content.firstElementChild?.outerHTML !== normalized)
      content.innerHTML = normalized;
    if (!detail.open) {
      detailTrigger = document.activeElement;
      if (
        orders.dataset.role === "admin" &&
        matchMedia("(min-width: 851px)").matches
      ) {
        detail.classList.add("desktop-page-detail");
        detail.setAttribute("aria-modal", "true");
        detail.style.top = "";
        desktopBackdrop.hidden = false;
        detail.show();
      } else detail.showModal();
      detail.querySelector("[data-close]")?.focus({ preventScroll: true });
    }
  }
  desktopBackdrop.onclick = () => detail?.close();
  if (detail) {
    detail.addEventListener("close", () => {
      selectedOrder = null;
      linkedOrder = null;
      desktopBackdrop.hidden = true;
      detail.classList.remove("desktop-page-detail");
      detail.removeAttribute("aria-modal");
      detail.style.top = "";
      if (detailTrigger?.isConnected)
        detailTrigger.focus({ preventScroll: true });
    });
    document.addEventListener("keydown", (e) => {
      if (
        !detail.open ||
        !detail.classList.contains("desktop-page-detail") ||
        document.querySelector("#payment-dialog")?.open
      )
        return;
      if (e.key === "Escape") {
        detail.close();
        e.preventDefault();
      }
      if (e.key === "Tab") {
        const focusable = [
          ...detail.querySelectorAll(
            "button:not(:disabled),a[href],select,input:not([type=hidden])",
          ),
        ];
        const first = focusable[0],
          last = focusable.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          last?.focus();
          e.preventDefault();
        } else if (!e.shiftKey && document.activeElement === last) {
          first?.focus();
          e.preventDefault();
        }
      }
    });
  }
  let linkedOrder = null;
  let requestedOrder =
    Number(new URLSearchParams(location.search).get("pedido")) || null;
  const labels = {
      cancelado: uiText("Cancelado"),
      aberto: ["admin", "garcom"].includes(orders.dataset.role)
        ? uiText("Enviado à cozinha")
        : orders.dataset.role === "cozinha"
          ? uiText("Pendente")
          : uiText("Aberto"),
      em_preparo: uiText("Em preparo"),
      pronto: ["admin", "garcom"].includes(orders.dataset.role)
        ? uiText("Pedido pronto")
        : uiText("Pronto"),
      saiu_entrega: orders.dataset.role === "cliente" ? uiText("Em trânsito") : uiText("Saiu para entrega"),
      entregue: uiText("Entregue"),
    },
    paymentLabels = {
      pontos: uiText("Pontos de fidelidade"),
      pix: "Pix",
      dinheiro: uiText("Dinheiro"),
      credito: uiText("Cartão de crédito"),
      debito: uiText("Cartão de débito"),
    };
  const adminSummary = [
    { key: "a_receber", label: uiText("A receber"), css: "entregue" },
    { key: "pronto", label: uiText("Pronto"), css: "pronto" },
    { key: "em_preparo", label: uiText("Em preparo"), css: "em_preparo" },
    { key: "aberto", label: uiText("Enviado à cozinha"), css: "aberto" },
    { key: "saiu_entrega", label: uiText("Saiu para entrega"), css: "saiu_entrega" },
    { key: "aguardando_comanda", label: uiText("Aguardando comanda"), css: "awaiting-comanda" },
  ];
  if (orders.dataset.role === "admin") {
    const statusSelect = document.querySelector("#status-filter");
    for (const key of ["a_receber", "aguardando_comanda"]) {
      if (!statusSelect.querySelector('option[value="' + key + '"]'))
        statusSelect.add(new Option(adminSummary.find(s => s.key === key).label, key));
    }
  }
  function matchesStatus(p, filter, role) {
    if (!filter) return true;
    if (filter === "a_receber") return p.status === "entregue" && !p.pago;
    if (filter === "aguardando_comanda") return Boolean(p.aguardando_comanda);
    if (filter === "nao_pago") return !p.pago;
    if (role === "admin" && filter === "aberto")
      return p.status === "aberto" && !p.aguardando_comanda;
    return p.status === filter;
  }
  function matchesChannel(p, channel) {
    if (channel === "fidelidade") return Boolean(p.fidelidade_resgate);
    return !channel || p.modalidade === channel;
  }
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
      ? (p.aguardando_comanda ? uiText("Aguardando comanda") : "Comanda: " + p.mesa) +
          (p.numero_mesa ? " · Mesa " + p.numero_mesa : "")
      : p.modalidade === "entrega"
        ? uiText("Tele-entrega")
        : uiText("Retirada no caixa");
  }
  function addressHTML(p) {
    if (!p.endereco) return "";
    const a = p.endereco;
    return /* HTML */ `
      <div class="delivery-address">
        <b>${uiHtml("Endereço de entrega")}</b>
        <p>
          ${escapeHTML(a.endereco)}, ${escapeHTML(a.numero)}
          <br />
          ${escapeHTML(a.bairro)}
          <br />${uiHtml("\n          Referência:\n          ")}${escapeHTML(a.referencia)}${a.telefone ? "<br>Contato: " + escapeHTML(a.telefone) : ""}
        </p>
      </div>
    `;
  }
  function assignmentHTML(p, role) {
    if (role !== "admin" || p.modalidade !== "entrega") return "";
    let info = p.entregador
      ? /* HTML */ `
          <p class="muted">${uiHtml("\n            Entregador:\n            ")}<b>${escapeHTML(p.entregador.nome)}</b>
            ${p.entregador.concluida ? " · entrega concluída" : ""}
          </p>
        `
      : "";
    if (p.entregador?.concluida && p.entregador.forma_pagamento)
      info += /* HTML */ `
        <p class="muted">${uiHtml("\n          Recebido pelo entregador:\n          ")}${paymentLabels[p.entregador.forma_pagamento] || uiText("Pagamento antecipado")}
          · ${money(p.entregador.valor_recebido)} ·
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
                  <label>${uiHtml("\n                    Entregador\n                    ")}<select id="courier-${p.id}" data-courier-select="${p.id}">
                      <option value="">${uiHtml("Selecione um entregador")}</option>
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
                    ${p.entregador ? uiText("Reatribuir entrega") : uiText("Enviar com entregador →")}
                  </button>
                `
              : '<p>Cadastre um usuário com perfil entregador em <a href="' +
                restaurantURL("/cadastros/usuarios") +
                '">Equipe</a> para atribuir a entrega.</p>'
          }
        </div>
      `
    );
  }
  const itemStageLabels = {
    saiu_entrega: uiText("Em trânsito"),
    aberto: uiText("Pendente"),
    em_preparo: uiText("Em preparo"),
    pronto: uiText("Pronto para levar"),
    entregue: uiText("Entregue"),
  };
  function itemChecks(p, i, role) {
    if (!["admin", "garcom", "cozinha"].includes(role)) return "";
    const stage = i.etapa || "aberto";
    const locked =
      (p.pago && p.status === "entregue") ||
      p.status === "saiu_entrega" ||
      p.entregador?.concluida;
    const checkbox = (action, label, checked, disabled) =>
      `<label class="item-check"><input type="checkbox" data-item-check="${action}" data-order="${p.id}" data-item="${i.id}" data-stage="${escapeHTML(stage)}" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}><span>${label}</span></label>`;
    let html =
      '<div class="item-checklist" aria-label="Checklist de ' +
      escapeHTML(i.nome) +
      '">';
    if (role === "cozinha" || role === "admin")
      html += checkbox(
        "pronto",
        uiText("Pronto"),
        ["pronto", "entregue"].includes(stage),
        locked || stage === "entregue",
      );
    if ((role === "garcom" || role === "admin") && p.canal === "salao")
      html += checkbox(
        "entregue",
        uiText("Entregue na mesa"),
        stage === "entregue",
        locked || p.aguardando_comanda,
      );
    return html + "</div>";
  }
  function itemOptionsHTML(value) {
    if (!value) return "";
    const sections = String(value)
      .split(/\s+\|\s+/)
      .map((part) => {
        const colon = part.indexOf(":");
        const hasLabel = colon > 0 && colon <= 70;
        const title = hasLabel ? part.slice(0, colon).trim() : uiText("Observação");
        const text = hasLabel ? part.slice(colon + 1).trim() : part.trim();
        const isFlavors = /sabor/i.test(title);
        const values = isFlavors ? text.split(/,\s+/) : [text];
        return `<div class="order-item-option"><dt>${escapeHTML(title)}</dt><dd>${values.map((v) => `<span class="order-option-value${isFlavors ? " flavor-value" : ""}">${escapeHTML(v)}</span>`).join("")}</dd></div>`;
      });
    return `<dl class="order-item-options">${sections.join("")}</dl>`;
  }
  function orderItemHTML(p, i, role) {
    return `<li class="order-item-card"><div class="order-item-content">
      <div class="order-item-heading"><div class="order-item-name"><span class="item-qty">${i.quantidade}×</span><b>${escapeHTML(i.nome)}</b></div>${i.etapa ? `<span class="item-stage item-stage-${escapeHTML(i.etapa)}">${escapeHTML(itemStageLabels[i.etapa] || i.etapa)}</span>` : ""}</div>
      ${itemOptionsHTML(i.observacao)}
      <div class="order-item-footer">${itemChecks(p, i, role)}<div class="order-item-price">${i.quantidade > 1 ? `<span>${money(i.preco)} por unidade</span>` : ""}<strong>${money(i.preco * i.quantidade)}</strong></div></div>
    </div></li>`;
  }
  function orderHTML(p, role) {
    const online = p.canal === "online",
      next = nextFor(p),
      canAct =
        next &&
        !(
          role === "admin" &&
          p.modalidade === "entrega" &&
          (p.status === "pronto" ||
            (p.status === "saiu_entrega" && p.entregador))
        ) &&
        (role === "admin" ||
          (role === "cozinha" && ["aberto", "em_preparo"].includes(p.status)) ||
          (role === "garcom" &&
            !online &&
            p.status === "pronto" &&
            !p.aguardando_comanda));
    return /* HTML */ `
      <article
        data-order-id="${p.id}"
        class="panel order ${p.status} ${p.aguardando_comanda ? "awaiting-comanda" : ""} ${p.pago ? "order-paid" : ""} ${online ? "online-order" : ""}"
      >
        <div class="order-head">
          <div class="table-badge">
            <small>${online ? uiText("PEDIDO ONLINE") : uiText("COMANDA")}</small>
            <strong class="${online ? "online-title" : ""}">
              ${online ? (p.modalidade === "entrega" ? uiText("Tele-entrega") : uiText("Retirada no caixa")) : p.aguardando_comanda ? uiText("A definir") : escapeHTML(p.mesa)}
            </strong>
            <div class="order-number">${uiHtml("\n              PEDIDO\n              #")}${p.id}${p.numero_mesa ? " · MESA " + escapeHTML(p.numero_mesa) : ""}
            </div>
          </div>
          <span class="pill">${labels[p.status]}</span>
        </div>
        <div class="order-body">
          ${["admin", "garcom"].includes(role) && p.canal === "salao" && !p.pago ? (p.aguardando_comanda ? `<div class="qr-assignment"><label>${uiHtml("Comanda")}<input id="qr-comanda-${p.id}" inputmode="numeric" maxlength="12"></label><label>${uiHtml("Mesa")}<input id="qr-mesa-${p.id}" value="${escapeHTML(p.numero_mesa || "")}" inputmode="numeric" maxlength="12"></label><button data-qr-assign="${p.id}">${uiHtml("Definir comanda e mesa")}</button><p class="muted">${uiHtml("Confira a mesa informada pelo cliente e defina a comanda ao atender. Depois, registre a entrega.")}</p></div>` : `<a class="button-link secondary" href="${restaurantURL("/pdv")}?pedido=${p.id}">${uiHtml("+ Adicionar itens à comanda")}</a>`) : ""}
          <div class="order-meta">
            <span>
              ${online ? "👤 " + escapeHTML(p.cliente) : "♙ " + escapeHTML(p.garcom)}
            </span>
            <time>
              ${new Date(p.criado + "Z").toLocaleString(document.documentElement.lang || "pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
            </time>
          </div>
          <ul>
            ${p.itens.map((i) => orderItemHTML(p, i, role)).join("")}
          </ul>
          ${addressHTML(p)}${
            p.forma_pagamento
              ? /* HTML */ `
                  <p class="muted">${uiHtml("\n                    Pagamento escolhido:\n                    ")}<b>${paymentLabels[p.forma_pagamento]}</b>
                    ${p.troco_para !== null && p.troco_para !== undefined ? " · Troco para " + money(p.troco_para) : ""}
                  </p>
                `
              : ""
          }${
            p.taxa_entrega
              ? /* HTML */ `
                  <div class="fee-line">
                    <span>${uiHtml("Inclui taxa de entrega")}</span>
                    <b>${money(p.taxa_entrega)}</b>
                  </div>
                `
              : ""
          }
          <div class="total">
            <strong>${money(p.total)}</strong>
            <span class="payment-state ${p.pago ? "paid" : ""}">
              ${p.pago ? uiText("✓ Pago") : uiText("A receber")}
            </span>
          </div>
          ${
            canAct && !p.aguardando_comanda
              ? /* HTML */ `
                  <button
                    class="status-action"
                    data-status="${next}"
                    data-id="${p.id}"
                  >
                    ${p.status === "aberto" ? uiText("Iniciar preparo →") : p.status === "em_preparo" ? uiText("✓ Marcar como pronto") : next === "saiu_entrega" ? "Saiu para entrega →" : online && p.modalidade === "retirada" ? uiText("✓ Confirmar retirada") : uiText("✓ Registrar entrega")}
                  </button>
                `
              : ""
          }${assignmentHTML(p, role)}${role === "admin" && !p.pago && p.status !== "cancelado" && p.entregador?.concluida ? '<a class="button-link" href="' + restaurantURL("/acerto-entregadores") + '">Conferir acerto do entregador →</a>' : ""}${
            role === "admin" && !p.pago && p.status !== "cancelado" && !p.entregador?.concluida
              ? /* HTML */ `
                  <button class="secondary" data-pay="${p.id}">${uiHtml("\n                    Registrar pagamento\n                  ")}</button>
                `
              : ""
          }${
            role === "cliente" && p.status === "pronto"
              ? /* HTML */ `
                  <p class="ready-note">
                    ${p.modalidade === "retirada" ? uiText("Seu pedido está pronto! Retire no caixa.") : uiText("Seu pedido está pronto e aguarda saída para entrega.")}
                  </p>
                `
              : ""
          }
        </div>
      </article>
    `;
  }
  function normalizarComanda(valor) {
    return String(valor ?? "")
      .replace(/\D/g, "")
      .replace(/^0+(?=\d)/, "");
  }

  function correspondeComanda(pedido) {
    const campo = document.querySelector("#comanda-search");
    const busca = campo?.value.trim() || "";

    if (!busca) return true;

    const numero = normalizarComanda(busca);

    return (
      numero !== "" &&
      pedido.modalidade === "salao" &&
      normalizarComanda(pedido.mesa) === numero
    );
  }
  function render() {
    const filter = document.querySelector("#status-filter").value,
      role = orders.dataset.role,
      channel = document.querySelector("#channel-filter")?.value;
    document.querySelector("#status-summary").hidden = [
      "cliente",
      "visitante",
    ].includes(role);
    const summary = role === "admin" ? adminSummary : Object.keys(labels)
      .filter((status) => role !== "garcom" || status !== "saiu_entrega")
      .map(key => ({ key, label: labels[key], css: key }));
    document.querySelector("#status-summary").innerHTML = summary
      .map(
        (s) => /* HTML */ `
          <button class="status-card ${s.css}" data-filter="${s.key}">
            <span>${s.label}</span>
            <b>${list.filter((p) => matchesStatus(p, s.key, role)).length}</b>
          </button>
        `,
      )
      .join("");
    orders.innerHTML =
      list
        .filter(
          (p) =>
            matchesStatus(p, filter, role) &&
            matchesChannel(p, channel) &&
            correspondeComanda(p),
        )
        .map((p) => orderHTML(p, role))
        .join("") ||
      '<div class="panel empty"><span>✓</span><h3>Nenhum pedido por aqui.</h3><p>Os pedidos deste perfil aparecerão aqui.</p></div>';
    if (detail) {
      orders.classList.add("compact-orders");
      fullCards.clear();
      const visible = list.filter(
        (p) =>
          matchesStatus(p, filter, role) &&
          matchesChannel(p, channel) &&
          correspondeComanda(p),
      );
      const articles = [...orders.querySelectorAll("article.order")];
      articles.forEach((article, index) => {
        const p = visible[index];
        fullCards.set(p.id, article.outerHTML);
        const card = document.createElement("button");
        card.type = "button";
        card.className =
          "compact-order " + p.status + (p.pago ? " order-paid" : "");
        card.classList.toggle("awaiting-comanda", Boolean(p.aguardando_comanda));
        card.dataset.detail = p.id;
        const aguardandoEntregador =
          role === "admin" &&
          p.modalidade === "entrega" &&
          ["pronto", "saiu_entrega"].includes(p.status);

        card.classList.toggle("aguardando-entregador", aguardandoEntregador);
        const statusDoCard =
          role === "admin" && p.status === "entregue"
            ? p.pago
              ? uiText("Finalizado")
              : uiText("A receber")
            : aguardandoEntregador
              ? p.status === "pronto"
                ? uiText("Definir entregador")
                : uiText("Em trânsito")
              : labels[p.status];
        card.innerHTML = `<span class="compact-heading"><strong>${escapeHTML(titleFor(p))}</strong><span>${statusDoCard}</span></span><span>${uiHtml("Pedido #")}${p.id} · <span class="compact-person">${escapeHTML(p.cliente || p.garcom)}</span></span><span class="compact-items">${p.itens.map((i) => escapeHTML(i.quantidade + "× " + i.nome)).join(" · ")}</span><span class="compact-heading"><b>${money(p.total)}</b><b>${p.pago ? uiText("Pago") : uiText("Não pago")}</b></span><small>${p.itens.filter((i) => i.etapa === "pronto").length} item(ns) pronto(s) · ${p.itens.filter((i) => i.etapa === "entregue").length}/${p.itens.length} entregue(s) · Ver detalhes →</small>`;
        article.replaceWith(card);
      });
      if (detail.open && selectedOrder !== null) {
        if (
          !fullCards.has(selectedOrder) &&
          linkedOrder?.id === selectedOrder
        ) {
          fullCards.set(selectedOrder, orderHTML(linkedOrder, role));
        }
        if (fullCards.has(selectedOrder)) showDetail(selectedOrder);
        else detail.close();
      }
    }
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
      if (linkedOrder && !list.some((p) => p.id === linkedOrder.id)) {
        try {
          linkedOrder = await api(
            "/api/pedidos/" + linkedOrder.id + "/detalhes",
          );
          if (!detail) list.unshift(linkedOrder);
        } catch {
          linkedOrder = null;
          if (detail?.open) detail.close();
        }
      }
      if (requestedOrder) {
        document.querySelector("#status-filter").value = "";
        const channel = document.querySelector("#channel-filter");
        if (channel) channel.value = "";
      }
      render();
      if (requestedOrder) {
        const id = requestedOrder;
        requestedOrder = null;
        try {
          const listed = list.find((p) => p.id === id);
          const p = listed || (await api("/api/pedidos/" + id + "/detalhes"));
          if (!listed) linkedOrder = p;
          if (detail) {
            fullCards.set(id, orderHTML(p, orders.dataset.role));
            showDetail(id);
          } else {
            let card = orders.querySelector('[data-order-id="' + id + '"]');
            if (!card) {
              if (!list.length) orders.innerHTML = "";
              orders.insertAdjacentHTML(
                "afterbegin",
                orderHTML(p, orders.dataset.role),
              );
              card = orders.querySelector('[data-order-id="' + id + '"]');
            }
            card?.classList.add("notification-target");
            card?.scrollIntoView({ block: "center", behavior: "smooth" });
          }
        } catch (e) {
          toast("Não foi possível abrir este pedido: " + e.message);
        }
      }
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
  async function orderAction(e) {
    const open = e.target.closest("[data-detail]");
    if (open) {
      showDetail(Number(open.dataset.detail));
      return;
    }
    const qrButton = e.target.closest("[data-qr-assign]");
    if (qrButton) {
      const id = qrButton.dataset.qrAssign;
      qrButton.disabled = true;
      try {
        await api("/api/pedidos/" + id + "/comanda", {
          comanda: document.querySelector("#qr-comanda-" + id).value,
          numero_mesa: document.querySelector("#qr-mesa-" + id).value,
        });
        toast(uiText("Comanda vinculada."));
        await refresh();
      } catch (err) {
        toast(err.message);
      } finally {
        qrButton.disabled = false;
      }
      return;
    }
    const b = e.target.closest("button");
    if (!b || !(b.dataset.assign || b.dataset.pay || b.dataset.status)) return;
    if (b.dataset.assign) {
      const id = Number(b.dataset.assign),
        driver = Number(document.querySelector("#courier-" + id).value);
      if (!driver) {
        toast(uiText("Selecione um entregador."));
        return;
      }
      busy = true;
      b.disabled = true;
      try {
        await api("/api/pedidos/" + id + "/entregador", {
          entregador_id: driver,
        });
        choices.delete(id);
        toast(uiText("Entrega atribuída com sucesso."));
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
      document.querySelector("#payment-method").value =
        p.forma_pagamento || "pix";
      document.querySelector("#payment-dialog").showModal();
      return;
    }
    busy = true;
    b.disabled = true;
    try {
      await api(`/api/pedidos/${b.dataset.id}/status`, {
        status: b.dataset.status,
      });
      toast(uiText("Pedido atualizado com sucesso."));
    } catch (err) {
      toast(err.message);
    } finally {
      busy = false;
      refresh();
    }
  }
  async function checklistChanged(e) {
    const input = e.target.closest("[data-item-check]");
    if (!input) return;
    const checked = input.checked;
    if (busy) {
      input.checked = !checked;
      return;
    }
    busy = true;
    input.disabled = true;
    try {
      await api(
        `/api/pedidos/${input.dataset.order}/itens/${input.dataset.item}/checklist`,
        {
          acao: input.dataset.itemCheck,
          marcado: checked,
          etapa_anterior: input.dataset.stage,
        },
      );
      toast(
        checked
          ? input.dataset.itemCheck === "pronto"
            ? uiText("Item marcado como pronto.")
            : uiText("Item marcado como entregue.")
          : uiText("Marcação desfeita."),
      );
    } catch (err) {
      input.checked = !checked;
      toast(err.message);
    } finally {
      busy = false;
      input.disabled = false;
      refresh();
    }
  }
  orders.addEventListener("change", checklistChanged);
  detail?.addEventListener("change", checklistChanged);
  orders.addEventListener("click", orderAction);
  detail?.addEventListener("click", orderAction);
  detail?.addEventListener("change", (e) => {
    if (e.target.dataset.courierSelect)
      choices.set(Number(e.target.dataset.courierSelect), e.target.value);
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
      toast(uiText("Pagamento registrado."));
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
  const comandaSearch = document.querySelector("#comanda-search");

  if (comandaSearch) {
    function buscarComanda() {
      comandaSearch.value = comandaSearch.value.replace(/\D/g, "");
      // Durante a busca, mostra a comanda independentemente
      // dos filtros de situação e origem selecionados.
      if (comandaSearch.value.trim()) {
        document.querySelector("#status-filter").value = "";

        const origem = document.querySelector("#channel-filter");
        if (origem) origem.value = "";
      }

      render();
    }

    comandaSearch.addEventListener("input", buscarComanda);
    comandaSearch.addEventListener("search", buscarComanda);

    comandaSearch.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;

      event.preventDefault();

      const numero = normalizarComanda(comandaSearch.value);
      if (!numero) return;

      buscarComanda();

      const encontrados = list
        .filter(
          (pedido) =>
            pedido.modalidade === "salao" &&
            normalizarComanda(pedido.mesa) === numero,
        )
        .sort((a, b) => Number(a.pago) - Number(b.pago) || b.id - a.id);

      const pedido = encontrados[0];

      if (pedido) {
        showDetail(pedido.id);
      } else {
        alert(uiText("Nenhum pedido encontrado para essa comanda."));
        comandaSearch.select();
      }
    });
  }
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
              data-notification-id="${n.id}"
              href="${escapeHTML(n.url || "/pedidos")}"
            >
              <b>${escapeHTML(uiText(n.titulo))}</b>
              <p>${escapeHTML(uiText(n.mensagem))}</p>
              <time>${new Date(n.criado).toLocaleString(document.documentElement.lang || "pt-BR")}</time>
            </a>
          `,
        )
        .join("") ||
      ("<p>" + uiHtml("Você está em dia. Os próximos avisos aparecerão aqui.") + "</p>");
  }
  async function loadInbox() {
    try {
      drawInbox(await api("/api/notificacoes"));
    } catch (e) {
      document.querySelector("#notifications-list").textContent = e.message;
    }
  }
  document.querySelector("#notifications-open")?.addEventListener("click", () => {
    document.querySelector("#notifications-dialog").showModal();
    loadInbox();
  });
  document.querySelector("#notifications-list").addEventListener("click", async (event) => {
    const link = event.target.closest("a[data-notification-id]");
    if (!link) return;
    const normal = !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
    if (normal) event.preventDefault();
    if (link.dataset.reading) return;
    link.dataset.reading = "yes";
    try {
      await api("/api/notificacoes/lidas", { id: Number(link.dataset.notificationId) });
      link.classList.remove("unread");
      if (normal) window.location.assign(link.href);
      else loadInbox();
    } catch (e) {
      toast(e.message);
    } finally {
      delete link.dataset.reading;
    }
  });
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
      notificationHeadsUp(n.titulo, n.mensagem);
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
      live(uiText("Sem conexão"), "reconnecting");
      return;
    }
    if (!window.EventSource) {
      live(uiText("Atualização periódica"), "reconnecting");
      return;
    }
    stream = new EventSource(restaurantURL("/api/eventos?after=" + latest));
    stream.addEventListener("connected", () => {
      live(uiText("Ao vivo"), "connected");
      window.dispatchEvent(new Event("orders-updated"));
      loadInbox();
    });
    stream.addEventListener("pedido", (e) => {
      try {
        incoming(JSON.parse(e.data));
      } catch {}
    });
    stream.onerror = () =>
      live(navigator.onLine ? uiText("Reconectando") : uiText("Sem conexão"), "reconnecting");
  }
  window.addEventListener("session-expired", () => {
    stream?.close();
    live(uiText("Entre novamente"), "reconnecting");
  });
  window.addEventListener("offline", () => {
    stream?.close();
    live(uiText("Sem conexão"), "reconnecting");
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

// A visita QR é encerrada pelo servidor quando a comanda é paga.
if (document.body.dataset.qrGuest === "1") {
  let checkingVisit = false;
  async function checkVisit() {
    if (checkingVisit || !navigator.onLine) return;
    checkingVisit = true;
    try {
      const response = await fetch(restaurantURL("/api/salao/sessao"), {cache: "no-store"});
      if (!response.ok) return;
      const state = await response.json();
      if (!state.ativa) {
        window.location.replace(restaurantURL("/salao"));
        return;
      }
      document.querySelectorAll("[data-qr-table]").forEach(el => { el.textContent = state.mesa || ""; });
    } catch {} finally { checkingVisit = false; }
  }
  checkVisit();
  setInterval(checkVisit, 5000);
  window.addEventListener("orders-updated", checkVisit);
  window.addEventListener("online", checkVisit);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") checkVisit();
  });
}
