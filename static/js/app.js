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
      if (orders.dataset.role === "admin" && matchMedia("(min-width: 851px)").matches) {
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
      if (detailTrigger?.isConnected) detailTrigger.focus({ preventScroll: true });
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
      ? "Comanda: " + p.mesa
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
  function orderHTML(p, role) {
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
      <article
        data-order-id="${p.id}"
        class="panel order ${p.status} ${p.pago ? "order-paid" : ""} ${online ? "online-order" : ""}"
      >
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
                  <button class="status-action" data-status="${next}" data-id="${p.id}">
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
    document.querySelector("#status-summary").innerHTML = Object.keys(labels)
      .filter(
        (status) =>
          role !== "garcom" || status !== "saiu_entrega"
      )
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
            (!channel || p.modalidade === channel) &&
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
          (!filter || (filter === "nao_pago" ? !p.pago : p.status === filter)) &&
          (!channel || p.modalidade === channel) &&
          correspondeComanda(p),
      );
      const articles = [...orders.querySelectorAll("article.order")];
      articles.forEach((article, index) => {
        const p = visible[index];
        fullCards.set(p.id, article.outerHTML);
        const card = document.createElement("button");
        card.type = "button";
        card.className = "compact-order " + p.status + (p.pago ? " order-paid" : "");
        card.dataset.detail = p.id;
        card.innerHTML = `<span class="compact-heading"><strong>${escapeHTML(titleFor(p))}</strong><span>${labels[p.status]}</span></span><span>Pedido #${p.id} · ${escapeHTML(p.cliente || p.garcom)}</span><span class="compact-items">${p.itens.map((i) => escapeHTML(i.quantidade + "× " + i.nome)).join(" · ")}</span><span class="compact-heading"><b>${money(p.total)}</b><b>${p.pago ? "Pago" : "Não pago"}</b></span><small>Ver detalhes e ações →</small>`;
        article.replaceWith(card);
      });
      if (detail.open && selectedOrder !== null) {
        if (!fullCards.has(selectedOrder) && linkedOrder?.id === selectedOrder) {
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
          linkedOrder = await api("/api/pedidos/" + linkedOrder.id + "/detalhes");
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
    const b = e.target.closest("button");
    if (!b || !(b.dataset.assign || b.dataset.pay || b.dataset.status)) return;
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
  }
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
        normalizarComanda(pedido.mesa) === numero
    )
    .sort(
      (a, b) =>
        Number(a.pago) - Number(b.pago) ||
        b.id - a.id
    );

  const pedido = encontrados[0];

  if (pedido) {
    showDetail(pedido.id);
  } else {
    alert("Nenhum pedido encontrado para essa comanda.");
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
