"use strict";
(() => {
  const root = document.querySelector("#delivery-orders"),
    date = document.querySelector("#delivery-date"),
    search = document.querySelector("#delivery-search"),
    error = document.querySelector("#delivery-error"),
    dialog = document.querySelector("#delivery-confirm-dialog");
  const confirmation = document.querySelector("#delivery-confirm-check");
  const confirmButton = document.querySelector("#delivery-confirm-button");
  const syncConfirmation = () => {
    confirmButton.disabled = !confirmation.checked || busy;
  };
  confirmation.addEventListener("change", syncConfirmation);
  let items = [],
    selected = null,
    busy = false,
    loading = false,
    pending = false;
  const forms = {
    dinheiro: "Dinheiro",
    pix: "Pix",
    credito: "Crédito",
    debito: "Débito",
    antecipado: "Pagamento antecipado",
  };
  date.value = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const linkedOrder =
    Number(new URLSearchParams(location.search).get("pedido")) || null;
  let requestedOrder =
    Number(new URLSearchParams(location.search).get("pedido")) || null;
  function normalize(value) {
    return String(value ?? "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR")
      .replace(/\s+/g, " ")
      .trim();
  }
  function matchesSearch(p) {
    const query = normalize(search?.value);
    if (!query) return true;
    const number = /^(?:pedido\s*)?#?\s*(\d+)$/.exec(query);
    if (number) return String(p.id) === number[1].replace(/^0+(?=\d)/, "");
    const address = p.endereco || {};
    const text = normalize(
      [p.cliente, address.endereco, address.numero, address.bairro].join(" "),
    );
    return query.split(" ").every((word) => text.includes(word));
  }
  function render() {
    root.innerHTML =
      items
        .filter(matchesSearch)
        .map((p) => {
          const r = p.recebimento,
            a = p.endereco;
          return /* HTML */ `
            <article
              data-order-id="${p.id}"
              class="panel order ${p.status} ${p.pago ? "order-paid" : ""} online-order"
            >
              <div class="order-head">
                <div class="table-badge">
                  <small>TELE-ENTREGA</small>
                  <strong class="online-title">Pedido #${p.id}</strong>
                </div>
                <span class="pill"
                  >${r.entregue_em ? "Entregue" : "Em entrega"}</span
                >
              </div>
              <div class="order-body">
                <h3>${escapeHTML(p.cliente)}</h3>
                <div class="delivery-address">
                  <b>Endereço</b>
                  <p>
                    ${escapeHTML(a.endereco)}, ${escapeHTML(a.numero)}
                    <br />
                    ${escapeHTML(a.bairro)}
                    <br />
                    Referência:
                    ${escapeHTML(a.referencia)}${a.telefone ? "<br>Contato: " + escapeHTML(a.telefone) : ""}
                  </p>
                </div>
                <ul>
                  ${p.itens
                    .map(
                      (i) => /* HTML */ `
                        <li>
                          <span class="item-qty">${i.quantidade}×</span>
                          <div>
                            <b>${escapeHTML(i.nome)}</b>
                            ${i.observacao ? "<small>" + escapeHTML(i.observacao) + "</small>" : ""}
                          </div>
                        </li>
                      `,
                    )
                    .join("")}
                </ul>
                <div class="total">
                  <strong>${money(p.total)}</strong>
                  <span class="payment-state ${p.pago ? "paid" : ""}">
                    ${r.entregue_em ? (r.acertado ? "Conferido" : "A conferir") : p.pago ? "Já pago" : "Cobrar na entrega"}
                  </span>
                </div>
                ${
                  r.entregue_em
                    ? /* HTML */ `
                        <p>
                          Pagamento:
                          <b>${forms[r.forma_pagamento]}</b>
                        </p>
                        <p class="muted">
                          ${r.pago_antecipado ? "Pago antecipadamente · não cobrado pelo entregador" : money(r.valor_recebido) + " recebido"}
                          ·
                          ${r.acertado ? "Acerto conferido" : "Aguardando conferência"}
                        </p>
                      `
                    : /* HTML */ `
                        <p class="muted">
                          Escolhido pelo cliente:
                          ${forms[p.forma_pagamento] || "A combinar"}${p.troco_para ? " · Troco para " + money(p.troco_para) : ""}
                        </p>
                        <button class="status-action" data-complete="${r.id}">
                          ✓ Confirmar entrega e pagamento
                        </button>
                      `
                }
              </div>
            </article>
          `;
        })
        .join("") ||
      (search?.value.trim()
        ? '<section class="panel empty"><h3>Nenhuma entrega encontrada.</h3><p>Confira a busca e a data selecionada. Os pedidos em andamento também entram na pesquisa.</p></section>'
        : '<section class="panel empty"><h3>Nenhuma entrega neste momento.</h3><p>As tele-entregas atribuídas pelo administrador aparecerão aqui.</p></section>');
  }
  async function refresh() {
    if (busy || loading) {
      pending = true;
      return;
    }
    loading = true;
    try {
      const data = await api(
        "/api/entregas?data=" +
          date.value +
          (linkedOrder ? "&pedido=" + linkedOrder : ""),
      );
      items = data.items;
      if (dialog.open && selected) {
        const fresh = items.find(
          (p) => p.recebimento.id === selected.recebimento.id,
        );
        if (!fresh || fresh.recebimento.entregue_em) {
          dialog.close();
          selected = null;
          toast("A entrega foi atualizada. Confira a lista.");
        } else {
          selected = fresh;
          document.querySelector("#delivery-form-label").hidden = selected.pago;
          document.querySelector("#delivery-prepaid").hidden = !selected.pago;
        }
      }
      render();
      if (requestedOrder) {
        const card = root.querySelector(
          '[data-order-id="' + requestedOrder + '"]',
        );
        if (card) {
          card.classList.add("notification-target");
          card.scrollIntoView({ block: "center" });
        } else toast("Esta entrega não está atribuída a você.");
        requestedOrder = null;
      }
      error.hidden = true;
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      loading = false;
      if (pending) {
        pending = false;
        setTimeout(refresh, 50);
      }
    }
  }
  root.onclick = (e) => {
    const b = e.target.closest("[data-complete]");
    if (!b) return;
    selected = items.find((p) => p.recebimento.id === +b.dataset.complete);
    document.querySelector("#delivery-confirm-summary").textContent =
      "Pedido #" +
      selected.id +
      " · " +
      selected.cliente +
      " · " +
      money(selected.total);
    document.querySelector("#delivery-form-label").hidden = selected.pago;
    document.querySelector("#delivery-prepaid").hidden = !selected.pago;
    document.querySelector("#delivery-method").value =
      selected.forma_pagamento || "dinheiro";
    document.querySelector("#delivery-confirm-check").checked = false;
    syncConfirmation();
    dialog.showModal();
  };
  document.querySelector("#delivery-confirm-button").onclick = async (e) => {
    if (!selected) return;
    if (!document.querySelector("#delivery-confirm-check").checked) {
      toast("Confirme a entrega e a conferência do pagamento.");
      return;
    }
    busy = true;
    e.target.disabled = true;
    try {
      await api("/api/entregas/" + selected.recebimento.id + "/concluir", {
        forma_pagamento: document.querySelector("#delivery-method").value,
        confirmado: true,
      });
      dialog.close();
      toast(
        "Entrega registrada. O recebimento ficará disponível para conferência.",
      );
    } catch (err) {
      toast(err.message);
    } finally {
      busy = false;
      syncConfirmation();
      refresh();
    }
  };
  syncConfirmation();
  if (search) search.addEventListener("input", render);
  date.onchange = refresh;
  document.querySelector("#delivery-refresh").onclick = refresh;
  window.addEventListener("orders-updated", refresh);
  window.addEventListener("online", refresh);
  setInterval(() => {
    if (document.visibilityState === "visible") refresh();
  }, 30000);
  refresh();
})();
